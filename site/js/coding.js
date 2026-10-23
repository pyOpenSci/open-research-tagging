/**
 * Coding view: resolve ?project= + evidence pane (form in 10c).
 */
(function (global) {
  "use strict";

  const Codebook = global.OrtCodebook;
  const Resolve = global.OrtCodingResolve;

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
        return Resolve.evidenceExcerpt(comment);
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
    };
  }

  function fetchJson(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) throw new Error("Failed to load " + url + ": " + res.status);
      return res.json();
    });
  }
})(typeof window !== "undefined" ? window : globalThis);
