/**
 * Pure search + staging helpers for the passage tag picker (no DOM).
 */
(function (global) {
  "use strict";

  /**
   * @param {object} tag
   * @param {string} query
   * @returns {boolean}
   */
  function tagMatchesQuery(tag, query) {
    const q = String(query || "")
      .trim()
      .toLowerCase();
    if (!q) return true;
    const fields = [
      tag.hashtag,
      tag.label,
      tag.description,
      tag.namespace,
      tag.dimension,
      tag.dimension_label,
    ];
    return fields.some(function (field) {
      return String(field || "")
        .toLowerCase()
        .indexOf(q) >= 0;
    });
  }

  /**
   * @param {object[]} catalog
   * @param {string} query
   * @returns {object[]}
   */
  function filterCatalog(catalog, query) {
    return (catalog || []).filter(function (tag) {
      return tagMatchesQuery(tag, query);
    });
  }

  /**
   * Append tag if hashtag not already staged (preserves order).
   * @param {object[]} staged
   * @param {object} tag
   * @returns {object[]}
   */
  function stageTag(staged, tag) {
    const list = (staged || []).slice();
    if (!tag || !tag.hashtag) return list;
    if (
      list.some(function (t) {
        return t.hashtag === tag.hashtag;
      })
    ) {
      return list;
    }
    list.push(tag);
    return list;
  }

  /**
   * @param {object[]} staged
   * @param {string} hashtag
   * @returns {object[]}
   */
  function removeStaged(staged, hashtag) {
    return (staged || []).filter(function (t) {
      return t.hashtag !== hashtag;
    });
  }

  /**
   * @param {object[]} [_staged]
   * @returns {object[]}
   */
  function clearStaged(_staged) {
    return [];
  }

  /**
   * Group filtered tags by dimension (stable first-seen order).
   * @param {object[]} catalog
   * @returns {{ dimension: string, label: string, tags: object[] }[]}
   */
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

  /**
   * Multiline hashtags only (one per line), ready to paste above a review note.
   * @param {object[]} staged
   * @returns {string}
   */
  function stagedToCopyText(staged) {
    return (staged || [])
      .map(function (t) {
        return t && t.hashtag ? String(t.hashtag) : "";
      })
      .filter(Boolean)
      .join("\n");
  }

  global.OrtTagsStage = {
    tagMatchesQuery: tagMatchesQuery,
    filterCatalog: filterCatalog,
    stageTag: stageTag,
    removeStaged: removeStaged,
    clearStaged: clearStaged,
    groupByDimension: groupByDimension,
    stagedToCopyText: stagedToCopyText,
  };
})(typeof window !== "undefined" ? window : globalThis);
