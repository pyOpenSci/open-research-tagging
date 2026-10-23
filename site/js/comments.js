/**
 * Comment browser Alpine component + DataTables cell renderers.
 * Depends on: Alpine, jQuery, DataTables, OrtCodebook, OrtCommentsFilters.
 */
(function (global) {
  "use strict";

  const F = global.OrtCommentsFilters;
  const Codebook = global.OrtCodebook;

  document.addEventListener("alpine:init", function () {
    global.Alpine.data("commentBrowser", commentBrowser);
  });

  function commentBrowser() {
    return {
      loading: true,
      error: "",
      allRows: [],
      codebook: null,
      meta: {},
      isFixture: false,
      urlBannerBits: [],
      onlyTagReview: false,
      activeByDim: {},
      openDims: {},
      project: "",
      pr: "",
      q: "",
      projectOptions: [],
      prOptions: [],
      reviewCount: 0,
      metaText: "",
      _table: null,
      _searchRegistered: false,

      async init() {
        try {
          const commentsUrl = "data/comments.json";
          const codebookUrl = "data/codebook.json";
          const payload = await fetch(commentsUrl).then(readJson);
          const codebook = Codebook
            ? await Codebook.loadCodebook(codebookUrl)
            : await fetch(codebookUrl).then(readJson);

          this.codebook = codebook;
          this.allRows = payload.data || [];
          this.meta = payload.meta || {};
          this.isFixture = !!this.meta.is_fixture;
          this.reviewCount = this.allRows.filter(function (r) {
            return r.needs_tag_review;
          }).length;
          this.metaText = formatMeta(this.allRows, this.meta);
          this.projectOptions = uniqueSorted(
            this.allRows.map(function (r) {
              return r.project;
            }).filter(Boolean)
          );
          this.prOptions = uniqueSorted(
            this.allRows
              .map(function (r) {
                return r.pr_number;
              })
              .filter(function (n) {
                return n != null;
              }),
            true
          );

          this.applyUrlFilters(new URLSearchParams(global.location.search));
          this.loading = false;
          this.$nextTick(() => {
            this.mountTable();
          });
        } catch (err) {
          this.loading = false;
          this.error = String(err);
          this.metaText = this.error;
        }
      },

      applyUrlFilters(params) {
        const parsed = F.parseUrlFilters(params);
        this.onlyTagReview = parsed.needsTagReview;
        this.activeByDim = F.activeSetsToArrays(parsed.activeByDim);
        this.openDims = {};
        parsed.openDims.forEach((dim) => {
          this.openDims[dim] = true;
        });
        if (parsed.project) this.project = parsed.project;
        this.urlBannerBits = F.describeUrlFilters(params);
      },

      get filterBlocks() {
        if (!this.codebook) return [];
        const order =
          this.codebook.filter_order ||
          Object.keys(this.codebook.values || {});
        const blocks = [];
        order.forEach((dimension) => {
          if (dimension === "scope") {
            blocks.push({ kind: "scope", key: "scope", label: "Scope" });
            return;
          }
          const values = (this.codebook.values || {})[dimension];
          if (!values) return;
          const chips = F.valueChipsForDimension(
            this.allRows,
            dimension,
            values
          );
          if (!chips.length) return;
          blocks.push({
            kind: "value",
            key: dimension,
            label: Codebook
              ? Codebook.dimensionLabel(this.codebook, dimension)
              : dimension,
            chips: chips,
          });
        });
        return blocks;
      },

      get scopeTypeOptions() {
        return F.appearingScopeOptions(
          this.allRows,
          "contribution_type",
          ((this.codebook || {}).scope || {}).contribution_types || {}
        );
      },

      get scopePositionOptions() {
        return F.appearingScopeOptions(
          this.allRows,
          "position",
          ((this.codebook || {}).scope || {}).positions || {}
        );
      },

      get scopeType() {
        return this._scopePart(1);
      },

      get scopePosition() {
        return this._scopePart(2);
      },

      _scopePart(index) {
        const keys = this.activeByDim.scope || [];
        for (let i = 0; i < keys.length; i++) {
          const key = keys[i];
          if (key.startsWith("scope-partial:") || key.startsWith("scope:")) {
            const parts = key.split(":");
            const part = parts[index] || "";
            return part === "*" ? "" : part;
          }
        }
        return "";
      },

      dimActiveCount(dim) {
        return (this.activeByDim[dim] || []).length;
      },

      isChipOn(dim, key) {
        return (this.activeByDim[dim] || []).indexOf(key) >= 0;
      },

      toggleChip(dim, key) {
        const cur = (this.activeByDim[dim] || []).slice();
        const idx = cur.indexOf(key);
        if (idx >= 0) cur.splice(idx, 1);
        else cur.push(key);
        this.activeByDim = Object.assign({}, this.activeByDim, { [dim]: cur });
        this.openDims = Object.assign({}, this.openDims, { [dim]: true });
        this.redraw();
      },

      setScope(typeId, posId) {
        const keys = [];
        if (typeId && posId) keys.push("scope:" + typeId + ":" + posId);
        else if (typeId || posId) {
          keys.push(
            "scope-partial:" + (typeId || "*") + ":" + (posId || "*")
          );
        }
        this.activeByDim = Object.assign({}, this.activeByDim, {
          scope: keys,
        });
        if (keys.length) {
          this.openDims = Object.assign({}, this.openDims, { scope: true });
        }
        this.redraw();
      },

      onScopeTypeChange(event) {
        this.setScope(event.target.value, this.scopePosition);
      },

      onScopePositionChange(event) {
        this.setScope(this.scopeType, event.target.value);
      },

      toggleTagReview() {
        this.onlyTagReview = !this.onlyTagReview;
        this.redraw();
      },

      clearFilters() {
        this.activeByDim = {};
        this.openDims = {};
        this.onlyTagReview = false;
        this.project = "";
        this.pr = "";
        this.q = "";
        if (this._table) this._table.search("").draw();
        else this.redraw();
      },

      onProjectOrPrChange() {
        this.redraw();
      },

      onSearchInput() {
        if (this._table) this._table.search(this.q).draw();
      },

      mountTable() {
        const $ = global.jQuery;
        const self = this;
        if (!this._searchRegistered) {
          $.fn.dataTable.ext.search.push(function (_s, _d, dataIndex) {
            const row = self.allRows[dataIndex];
            if (!row) return true;
            return F.rowMatchesFilters(row, {
              project: self.project,
              pr: self.pr,
              onlyTagReview: self.onlyTagReview,
              activeByDim: F.activeArraysToSets(self.activeByDim),
            });
          });
          this._searchRegistered = true;
        }
        this._table = $("#commentstable").DataTable({
          data: this.allRows,
          paging: false,
          info: true,
          order: [
            [2, "asc"],
            [5, "asc"],
          ],
          columns: [
            {
              data: "tags",
              render: function (_d, _t, row) {
                return renderTagsCell(row);
              },
            },
            {
              data: "body",
              render: function (_d, _t, row) {
                return renderCommentCell(row);
              },
            },
            { data: "project", defaultContent: "" },
            { data: "path", defaultContent: "" },
            { data: "user", defaultContent: "" },
            { data: "pr_number", defaultContent: "" },
            {
              data: "html_url",
              render: function (url) {
                return url
                  ? '<a href="' +
                      escapeAttr(url) +
                      '" target="_blank" rel="noopener">open</a>'
                  : "";
              },
            },
          ],
        });
        this._table.draw();
      },

      redraw() {
        if (this._table) this._table.draw();
      },
    };
  }

  function readJson(res) {
    if (!res.ok) throw new Error("Failed to load " + res.url + ": " + res.status);
    return res.json();
  }

  function formatMeta(rows, meta) {
    const reviewN = rows.filter(function (r) {
      return r.needs_tag_review;
    }).length;
    return (
      rows.length +
      " comments" +
      (reviewN ? " · " + reviewN + " need tag review" : "") +
      (meta.source_file ? " · from " + meta.source_file : "") +
      (meta.codebook_version ? " · codebook " + meta.codebook_version : "")
    );
  }

  function uniqueSorted(values, numeric) {
    const list = [];
    const seen = {};
    values.forEach(function (v) {
      const k = String(v);
      if (seen[k]) return;
      seen[k] = true;
      list.push(v);
    });
    if (numeric) {
      list.sort(function (a, b) {
        return a - b;
      });
    } else {
      list.sort();
    }
    return list;
  }

  function renderTagsCell(row) {
    const tags = row.tags || [];
    let html = tags
      .map(function (t) {
        const dim = t.dimension_label || t.dimension || "";
        const val = t.value_label || t.display || t.raw;
        return (
          '<span class="tag"><span class="dim">' +
          escapeHtml(dim) +
          "</span>" +
          escapeHtml(val) +
          "</span>"
        );
      })
      .join("");
    if (row.needs_tag_review) {
      const n = (row.parse_warnings || []).length;
      html +=
        '<span class="tag-warn-badge">Needs tag review' +
        (n ? " (" + n + ")" : "") +
        "</span>";
    } else if (!tags.length) {
      html += '<span class="empty">—</span>';
    }
    return html;
  }

  function renderCommentCell(row) {
    let html = "";
    if (row.quote) {
      const meta = [lineLabel(row), sourceLabel(row.quote_source)]
        .filter(Boolean)
        .join(" · ");
      const preview = truncateOneLine(row.quote, 72);
      const quoteEsc = escapeHtml(row.quote);
      html +=
        '<details class="passage-wrap">' +
        "<summary><span class=\"passage-meta\">" +
        escapeHtml(meta || "source text") +
        "</span>" +
        '<span class="preview"> — ' +
        escapeHtml(preview) +
        "</span></summary>" +
        '<div class="passage-peek" aria-hidden="true">' +
        quoteEsc +
        "</div>" +
        '<div class="passage">' +
        quoteEsc +
        "</div></details>";
    }
    html +=
      '<div class="excerpt coder-note">' +
      escapeHtml(excerpt(row.body)) +
      "</div>";
    (row.parse_warnings || []).forEach(function (w) {
      html += '<div class="parse-warn">' + escapeHtml(w);
      if (row.html_url) {
        html +=
          ' <a href="' +
          escapeAttr(row.html_url) +
          '" target="_blank" rel="noopener">Edit on GitHub</a>';
      }
      html += "</div>";
    });
    return html;
  }

  function excerpt(body) {
    const lines = (body || "").split("\n").filter(function (l) {
      return !l.trim().startsWith("#");
    });
    const text = lines.join("\n").trim() || body || "";
    return text.length > 280 ? text.slice(0, 277) + "…" : text;
  }

  function lineLabel(row) {
    if (row.start_line && row.line && row.start_line !== row.line) {
      return "L" + row.start_line + "–" + row.line;
    }
    if (row.line) return "L" + row.line;
    return "";
  }

  function sourceLabel(src) {
    if (src === "selection") return "selected lines";
    if (src === "diff_hunk") return "diff hunk";
    if (src === "paragraph") return "surrounding paragraph";
    return src || "";
  }

  function truncateOneLine(text, max) {
    const flat = (text || "").replace(/\s+/g, " ").trim();
    if (flat.length <= max) return flat;
    return flat.slice(0, max - 1) + "…";
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
