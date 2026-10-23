/**
 * Passage tag picker shell (9a): render codebook.tag_catalog.
 * Search/stage/copy land in later tasks.
 */
(function (global) {
  "use strict";

  const Codebook = global.OrtCodebook;

  document.addEventListener("alpine:init", function () {
    global.Alpine.data("tagPicker", tagPicker);
  });

  function tagPicker() {
    return {
      loading: true,
      error: "",
      version: "",
      catalog: [],
      grouped: [],

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
          this.grouped = groupByDimension(this.catalog);
          this.loading = false;
        } catch (err) {
          this.loading = false;
          this.error = String(err);
        }
      },
    };
  }

  function groupByDimension(catalog) {
    const order = [];
    const byDim = {};
    (catalog || []).forEach(function (entry) {
      const key = entry.dimension;
      if (!byDim[key]) {
        byDim[key] = {
          dimension: key,
          label: entry.dimension_label || key,
          tags: [],
        };
        order.push(key);
      }
      byDim[key].tags.push(entry);
    });
    return order.map(function (key) {
      return byDim[key];
    });
  }
})(typeof window !== "undefined" ? window : globalThis);
