/**
 * Coding view: resolve ?project=, evidence pane, schema-driven form (12f).
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
      evidenceDim: "",
      coding: null,
      meta: null,
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
          // Prefill coding + meta BEFORE assigning codebook. schemaDimensions is
          // derived from codebook; if codebook is set first, Alpine renders the
          // form while coding is still null and the bindings throw (empty form).
          if (Form) {
            this.coding = Form.prefillCoding(
              resolved.project && resolved.project.coding,
              codebook
            );
            this.meta = Form.normalizeMeta(resolved.project || { slug: resolved.slug });
          }
          this.codebook = codebook;
          this.loading = false;
        } catch (err) {
          this.loading = false;
          this.error = String(err);
        }
      },

      get provenanceKeys() {
        return (Form && Form.PROVENANCE_KEYS) || [];
      },

      get policyLocationOptions() {
        return (Form && Form.POLICY_LOCATION_OPTIONS) || [];
      },

      provenanceLabel(key) {
        return String(key || "").replace(/_/g, " ");
      },

      get schemaDimensions() {
        if (!Form || !this.codebook) return [];
        return Form.schemaFrom(this.codebook).dimensions || [];
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
        this.evidenceDim = Form.evidenceDimForSection(section, this.codebook);
      },

      multiHas(list, id) {
        return (list || []).indexOf(id) >= 0;
      },

      /** Stable accessors for Alpine bindings on dynamic schema paths. */
      getScalar(dimId, layerId) {
        if (!this.coding || !this.coding[dimId]) return "";
        const v = this.coding[dimId][layerId];
        return v == null ? "" : String(v);
      },

      setScalar(dimId, layerId, value) {
        if (!this.coding || !this.coding[dimId]) return;
        this.coding[dimId][layerId] = value || null;
        this.copyStatus = "";
      },

      getField(dimId, layerId, fieldId) {
        if (!this.coding || !this.coding[dimId] || !this.coding[dimId][layerId]) {
          return "";
        }
        const v = this.coding[dimId][layerId][fieldId];
        return v == null ? "" : String(v);
      },

      setField(dimId, layerId, fieldId, value) {
        if (!this.coding || !this.coding[dimId] || !this.coding[dimId][layerId]) {
          return;
        }
        this.coding[dimId][layerId][fieldId] = value || null;
        this.copyStatus = "";
      },

      getScope(dimId, layerId, yamlKey) {
        if (!this.coding || !this.coding[dimId] || !this.coding[dimId][layerId]) {
          return "";
        }
        return this.coding[dimId][layerId][yamlKey] || "";
      },

      setScope(dimId, layerId, yamlKey, value) {
        if (!this.coding || !this.coding[dimId] || !this.coding[dimId][layerId]) {
          return;
        }
        this.coding[dimId][layerId][yamlKey] = value;
        this.copyStatus = "";
      },

      setScalarMulti(dimId, layerId, id, on) {
        if (!Form || !this.coding) return;
        this.coding[dimId][layerId] = Form.toggleMulti(
          this.coding[dimId][layerId],
          id,
          on
        );
        this.copyStatus = "";
      },

      setObjectMulti(dimId, layerId, fieldId, id, on) {
        if (!Form || !this.coding) return;
        this.coding[dimId][layerId][fieldId] = Form.toggleMulti(
          this.coding[dimId][layerId][fieldId],
          id,
          on
        );
        this.copyStatus = "";
      },

      get yamlPreview() {
        if (!Form || !this.coding || !this.meta) return "";
        return Form.emitProjectYaml(this.meta, this.coding, this.codebook);
      },

      touchMeta() {
        this.copyStatus = "";
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
