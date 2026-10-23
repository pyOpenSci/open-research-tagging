/**
 * Load codebook.json and derive filter dimensions (no hardcoded FILTER_DIMS).
 * Shared by comments browser, projects overview, and later helpers.
 */
(function (global) {
  "use strict";

  /**
   * @param {string} [url]
   * @returns {Promise<object>}
   */
  function loadCodebook(url) {
    return fetch(url || "data/codebook.json").then(function (res) {
      if (!res.ok) {
        throw new Error("Failed to load codebook.json: " + res.status);
      }
      return res.json();
    });
  }

  /**
   * Ordered filter dimensions from codebook.filter_order + namespace labels.
   * @param {object} codebook
   * @returns {{ key: string, label: string, kind: string }[]}
   */
  function filterDimensionsFromCodebook(codebook) {
    const namespaces = (codebook && codebook.namespaces) || {};
    const labelByDim = {};
    const kindByDim = {};
    Object.keys(namespaces).forEach(function (ns) {
      const meta = namespaces[ns] || {};
      const dim = meta.dimension;
      if (!dim) return;
      if (!labelByDim[dim]) labelByDim[dim] = meta.label || dim;
      if (!kindByDim[dim]) kindByDim[dim] = meta.kind || "value";
    });

    const order =
      (codebook && codebook.filter_order && codebook.filter_order.length
        ? codebook.filter_order
        : Object.keys((codebook && codebook.values) || {})) || [];

    return order.map(function (key) {
      return {
        key: key,
        label: labelByDim[key] || humanize(key),
        kind: kindByDim[key] || (key === "scope" ? "scope" : "value"),
      };
    });
  }

  /**
   * @param {object} codebook
   * @param {string} dimension
   * @returns {string}
   */
  function dimensionLabel(codebook, dimension) {
    const dims = filterDimensionsFromCodebook(codebook);
    const hit = dims.find(function (d) {
      return d.key === dimension;
    });
    if (hit) return hit.label;
    return humanize(dimension);
  }

  function humanize(slug) {
    return String(slug || "")
      .replace(/[_-]+/g, " ")
      .replace(/\b\w/g, function (c) {
        return c.toUpperCase();
      });
  }

  global.OrtCodebook = {
    loadCodebook: loadCodebook,
    filterDimensionsFromCodebook: filterDimensionsFromCodebook,
    dimensionLabel: dimensionLabel,
  };
})(typeof window !== "undefined" ? window : globalThis);
