/**
 * Projects overview Alpine component + DataTables cell renderers.
 * Filter dimensions come from OrtCodebook.filterDimensionsFromCodebook (not a hardcoded list).
 */
(function (global) {
  "use strict";

  const F = global.OrtProjectsFilters;
  const Codebook = global.OrtCodebook;

  document.addEventListener("alpine:init", function () {
    global.Alpine.data("projectsOverview", projectsOverview);
  });

  function projectsOverview() {
    return {
      loading: true,
      error: "",
      allRows: [],
      codebook: null,
      activeByDim: {},
      openDims: {},
      q: "",
      metaText: "",
      _table: null,
      _searchRegistered: false,

      async init() {
        try {
          const payload = await fetch("data/projects.json").then(readJson);
          const codebook = Codebook
            ? await Codebook.loadCodebook("data/codebook.json")
            : await fetch("data/codebook.json").then(readJson);
          this.codebook = codebook;
          this.allRows = payload.data || [];
          this.loading = false;
          this.metaText = this.allRows.length + " projects";
          this.$nextTick(() => {
            this.mountTable();
            this.updateMeta();
          });
        } catch (err) {
          this.loading = false;
          this.error = String(err);
          this.metaText = this.error;
        }
      },

      get filterBlocks() {
        if (!this.codebook || !Codebook) return [];
        const dims = Codebook.filterDimensionsFromCodebook(this.codebook);
        const blocks = [];
        dims.forEach((d) => {
          const chips = F.chipsForDimension(this.allRows, d.key);
          if (!chips.length) return;
          blocks.push({
            key: d.key,
            label: d.label,
            chips: chips,
          });
        });
        return blocks;
      },

      dimActiveCount(dim) {
        return (this.activeByDim[dim] || []).length;
      },

      isChipOn(dim, id) {
        return (this.activeByDim[dim] || []).indexOf(id) >= 0;
      },

      toggleChip(dim, id) {
        const cur = (this.activeByDim[dim] || []).slice();
        const idx = cur.indexOf(id);
        if (idx >= 0) cur.splice(idx, 1);
        else cur.push(id);
        this.activeByDim = Object.assign({}, this.activeByDim, { [dim]: cur });
        this.openDims = Object.assign({}, this.openDims, { [dim]: true });
        this.redraw();
      },

      clearFilters() {
        this.activeByDim = {};
        this.openDims = {};
        this.q = "";
        if (this._table) this._table.search("").draw();
        else this.redraw();
        this.updateMeta();
      },

      onSearchInput() {
        if (this._table) {
          this._table.search(this.q).draw();
          this.updateMeta();
        }
      },

      mountTable() {
        const $ = global.jQuery;
        const self = this;
        if (!this._searchRegistered) {
          $.fn.dataTable.ext.search.push(function (_s, _d, dataIndex) {
            const row = self.allRows[dataIndex];
            if (!row) return true;
            return F.projectMatchesFilters(row, self.activeByDim);
          });
          this._searchRegistered = true;
        }
        this._table = $("#projectstable").DataTable({
          data: this.allRows,
          paging: false,
          order: [[0, "asc"]],
          columns: [
            {
              data: "display_name",
              render: function (_d, _t, row) {
                return renderProjectCell(row);
              },
            },
            {
              data: "overall.stance",
              defaultContent: "",
              render: function (_d, _t, row) {
                return cellFromValues(row.overall && row.overall.stance);
              },
            },
            {
              data: "overall.scope",
              defaultContent: "",
              render: function (_d, _t, row) {
                return cellFromValues(row.overall && row.overall.scope);
              },
            },
            {
              data: "overall.stated_rationale",
              defaultContent: "",
              render: function (_d, _t, row) {
                return cellFromValues(
                  row.overall && row.overall.stated_rationale
                );
              },
            },
            {
              data: null,
              render: function (_d, _t, row) {
                return guidanceCell(row);
              },
            },
            {
              data: null,
              render: function (_d, _t, row) {
                return accountabilityCell(row);
              },
            },
            {
              data: "comment_count",
              render: function (n, _t, row) {
                return (
                  '<a href="' +
                  escapeAttr(row.comments_href || "#") +
                  '">' +
                  (n || 0) +
                  "</a>"
                );
              },
            },
          ],
        });
        this._table.draw();
      },

      redraw() {
        if (this._table) {
          this._table.draw();
          this.updateMeta();
        }
      },

      updateMeta() {
        if (!this._table) {
          this.metaText = this.allRows.length + " projects";
          return;
        }
        const visible = this._table.rows({ search: "applied" }).count();
        this.metaText =
          visible + " of " + this.allRows.length + " projects shown";
      },
    };
  }

  function readJson(res) {
    if (!res.ok) throw new Error("Failed to load " + res.url + ": " + res.status);
    return res.json();
  }

  function renderProjectCell(row) {
    const gov = (row.context && row.context.governance) || "";
    const domain = (row.context && row.context.domain) || "";
    const sub = [gov, domain].filter(Boolean).join(" · ");
    const href =
      row.comments_href || "index.html?project=" + encodeURIComponent(row.slug);
    const codingHref =
      "coding.html?project=" + encodeURIComponent(row.slug || "");
    return (
      '<div class="project-name"><a href="' +
      escapeAttr(href) +
      '">' +
      escapeHtml(row.display_name) +
      "</a>" +
      (sub ? '<span class="sub">' + escapeHtml(sub) + "</span>" : "") +
      '<span class="sub"><a href="' +
      escapeAttr(codingHref) +
      '">Coding view</a></span>' +
      "</div>"
    );
  }

  function pill(valueObj) {
    const links = valueObj.links || {};
    const all = links.all || {};
    const match = links.matching || {};
    const label = valueObj.label || valueObj.id;
    let pop = '<div class="pop" role="tooltip"><div class="hint">Evidence in comments</div>';
    if (all.href) {
      pop +=
        '<a href="' +
        escapeAttr(all.href) +
        '">All ' +
        escapeHtml((links.dimension_label || "dimension").toLowerCase()) +
        " (" +
        (all.count || 0) +
        ")</a>";
    }
    if (match.href) {
      pop +=
        '<a href="' +
        escapeAttr(match.href) +
        '">Matching: ' +
        escapeHtml(match.label || label) +
        " (" +
        (match.count || 0) +
        ")</a>";
    }
    pop += "</div>";
    return (
      '<span class="code-pill" tabindex="0">' +
      escapeHtml(label) +
      pop +
      "</span>"
    );
  }

  function cellFromValues(group) {
    const values = (group && group.values) || [];
    if (!values.length) return '<span class="empty">—</span>';
    return (
      '<div class="code-stack">' + values.map(pill).join("") + "</div>"
    );
  }

  function guidanceCell(row) {
    const parts = [];
    const level = row.overall && row.overall.guidance_level;
    const types = row.overall && row.overall.guidance_type;
    if (level) parts.push(cellFromValues(level));
    if (types) parts.push(cellFromValues(types));
    return parts.length ? parts.join("") : '<span class="empty">—</span>';
  }

  function accountabilityCell(row) {
    const o = row.overall || {};
    const parts = [];
    ["disclosure", "human_responsibility", "enforcement"].forEach(function (k) {
      if (o[k]) parts.push(cellFromValues(o[k]));
    });
    return parts.length ? parts.join("") : '<span class="empty">—</span>';
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(text) {
    return escapeHtml(text).replace(/'/g, "&#39;");
  }
})(typeof window !== "undefined" ? window : globalThis);
