/**
 * Coding view: resolve ?project=, evidence pane, nested coding form (10c).
 * Copy YAML lands in 10d.
 */
(function (global) {
  "use strict";

  const Codebook = global.OrtCodebook;
  const Resolve = global.OrtCodingResolve;
  const Form = global.OrtCodingForm;

  document.addEventListener("alpine:init", function () {
    global.Alpine.data("codingView", codingView);
  });

  function codingView() {
    return {
      loading: true,
      error: "",
      codebook: null,
      allProjects: [],
      state: "missing",
      slug: null,
      project: null,
      comments: [],
      /** "" = all comments; else codebook dimension key */
      evidenceDim: "",
      /** Nested coding: block (mirrors project.yaml) */
      coding: Form ? Form.emptyCoding() : null,
      copyStatus: "",

      async init() {
        try {
          const params = new URLSearchParams(global.location.search);
          const [codebook, projectsPayload, commentsPayload] = await Promise.all([
            Codebook
              ? Codebook.loadCodebook("data/codebook.json")
              : fetchJson("data/codebook.json"),
            fetchJson("data/projects.json"),
            fetchJson("data/comments.json"),
          ]);
          this.codebook = codebook;
          this.allProjects = projectsPayload.data || [];
          const resolved = Resolve.resolveCodingView(
            params,
            this.allProjects,
            commentsPayload.data || []
          );
          this.state = resolved.state;
          this.slug = resolved.slug;
          this.project = resolved.project;
          this.comments = resolved.comments;
          if (Form) {
            this.coding = Form.prefillCoding(
              resolved.project && resolved.project.coding
            );
          }
          this.loading = false;
        } catch (err) {
          this.loading = false;
          this.error = String(err);
        }
      },

      get evidenceDimensions() {
        if (!this.codebook || !Codebook) return [];
        return Codebook.filterDimensionsFromCodebook(this.codebook);
      },

      get evidenceComments() {
        return Resolve.commentsForDimension(this.comments, this.evidenceDim);
      },

      excerpt(comment) {
        return Resolve.evidenceText
          ? Resolve.evidenceText(comment)
          : Resolve.evidenceExcerpt(comment);
      },

      tagDisplays(comment) {
        return (comment.tags || [])
          .map(function (t) {
            return t.display || t.raw || "";
          })
          .filter(Boolean);
      },

      browserHref(comment) {
        if (!this.project) return "index.html";
        const base =
          this.project.comments_href ||
          "index.html?project=" + encodeURIComponent(this.project.slug);
        if (this.evidenceDim) {
          const join = base.indexOf("?") >= 0 ? "&" : "?";
          return base + join + "dimension=" + encodeURIComponent(this.evidenceDim);
        }
        return base;
      },

      focusSection(section) {
        if (!Form) return;
        this.evidenceDim = Form.evidenceDimForSection(section);
      },

      options(dimension) {
        return Form ? Form.valueOptions(this.codebook, dimension) : [];
      },

      scopeRows() {
        return Form ? Form.scopeTypeRows(this.codebook) : [];
      },

      scopePositions() {
        return Form ? Form.scopePositionOptions(this.codebook) : [];
      },

      disclosureFormats() {
        return Form ? Form.disclosureFormatOptions() : [];
      },

      governances() {
        return Form ? Form.governanceOptions() : [];
      },

      multiHas(list, id) {
        return (list || []).indexOf(id) >= 0;
      },

      setMulti(path, id, on) {
        if (!Form || !this.coding) return;
        const parts = path.split(".");
        let parent = this.coding;
        for (let i = 0; i < parts.length - 1; i++) {
          parent = parent[parts[i]];
        }
        const key = parts[parts.length - 1];
        parent[key] = Form.toggleMulti(parent[key], id, on);
        this.copyStatus = "";
      },

      get yamlPreview() {
        if (!Form || !this.coding) return "";
        return Form.emitCodingYaml(this.coding);
      },

      async copyYaml() {
        const text = this.yamlPreview;
        if (!text) return;
        try {
          await writeClipboard(text);
          this.copyStatus = "Copied";
        } catch (err) {
          this.copyStatus = "Copy failed — select preview and copy manually";
        }
      },
    };
  }

  function fetchJson(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) throw new Error("Failed to load " + url + ": " + res.status);
      return res.json();
    });
  }

  function writeClipboard(text) {
    if (
      global.navigator &&
      global.navigator.clipboard &&
      global.navigator.clipboard.writeText
    ) {
      return global.navigator.clipboard.writeText(text).catch(function () {
        return fallbackCopy(text);
      });
    }
    return fallbackCopy(text);
  }

  function fallbackCopy(text) {
    return new Promise(function (resolve, reject) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      try {
        const ok = document.execCommand("copy");
        document.body.removeChild(ta);
        if (ok) resolve();
        else reject(new Error("execCommand copy failed"));
      } catch (err) {
        document.body.removeChild(ta);
        reject(err);
      }
    });
  }
})(typeof window !== "undefined" ? window : globalThis);
