/**
 * Passage tag picker: catalog, search, stage list (copy in 9c).
 * Depends on: Alpine, OrtCodebook, OrtTagsStage.
 */
(function (global) {
  "use strict";

  const Codebook = global.OrtCodebook;
  const Stage = global.OrtTagsStage;

  document.addEventListener("alpine:init", function () {
    global.Alpine.data("tagPicker", tagPicker);
  });

  function tagPicker() {
    return {
      loading: true,
      error: "",
      version: "",
      catalog: [],
      query: "",
      staged: [],

      async init() {
        try {
          const codebook = Codebook
            ? await Codebook.loadCodebook("data/codebook.json")
            : await fetch("data/codebook.json").then(function (res) {
                if (!res.ok) throw new Error("Failed to load codebook.json");
                return res.json();
              });
          this.version = codebook.version || "";
          this.catalog = codebook.tag_catalog || [];
          this.loading = false;
        } catch (err) {
          this.loading = false;
          this.error = String(err);
        }
      },

      get filteredCatalog() {
        return Stage.filterCatalog(this.catalog, this.query);
      },

      get grouped() {
        return Stage.groupByDimension(this.filteredCatalog);
      },

      get visibleCount() {
        return this.filteredCatalog.length;
      },

      isStaged(hashtag) {
        return this.staged.some(function (t) {
          return t.hashtag === hashtag;
        });
      },

      addTag(tag) {
        this.staged = Stage.stageTag(this.staged, tag);
      },

      removeTag(hashtag) {
        this.staged = Stage.removeStaged(this.staged, hashtag);
      },

      clearStaged() {
        this.staged = Stage.clearStaged(this.staged);
      },
    };
  }
})(typeof window !== "undefined" ? window : globalThis);
