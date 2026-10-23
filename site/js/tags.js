/**
 * Passage tag picker: catalog, search, stage, copy hashtags.
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
      copyStatus: "",

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

      get copyText() {
        return Stage.stagedToCopyText(this.staged);
      },

      isStaged(hashtag) {
        return this.staged.some(function (t) {
          return t.hashtag === hashtag;
        });
      },

      addTag(tag) {
        this.staged = Stage.stageTag(this.staged, tag);
        this.copyStatus = "";
      },

      removeTag(hashtag) {
        this.staged = Stage.removeStaged(this.staged, hashtag);
        this.copyStatus = "";
      },

      clearStaged() {
        this.staged = Stage.clearStaged(this.staged);
        this.copyStatus = "";
      },

      async copyStaged() {
        const text = this.copyText;
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

  /**
   * Clipboard API with textarea fallback (helps on http://localhost).
   * @param {string} text
   * @returns {Promise<void>}
   */
  function writeClipboard(text) {
    if (global.navigator && global.navigator.clipboard && global.navigator.clipboard.writeText) {
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
