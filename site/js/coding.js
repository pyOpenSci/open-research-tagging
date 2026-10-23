/**
 * Coding view shell (10a): load JSON, resolve ?project=, empty states.
 * Evidence + form land in later tasks.
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
    };
  }

  function fetchJson(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) throw new Error("Failed to load " + url + ": " + res.status);
      return res.json();
    });
  }
})(typeof window !== "undefined" ? window : globalThis);
