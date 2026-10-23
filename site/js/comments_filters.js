/**
 * Pure filter / URL helpers for the comment browser (no DOM).
 * Shared contract with Phase 5 deep links into index.html.
 */
(function (global) {
  "use strict";

  /**
   * @param {URLSearchParams} params
   * @returns {{
   *   project: string|null,
   *   needsTagReview: boolean,
   *   activeByDim: Object.<string, Set<string>>,
   *   openDims: Set<string>
   * }}
   */
  function parseUrlFilters(params) {
    const activeByDim = {};
    const openDims = new Set();
    const needsTagReview = params.get("needs_tag_review") === "1";
    const project = params.get("project") || null;

    const filter = params.get("filter");
    if (filter) {
      applyFilterParam(filter, activeByDim, openDims);
    }

    const dimension = params.get("dimension");
    if (dimension && !filter) {
      ensureDim(activeByDim, dimension);
      if (dimension === "scope") {
        activeByDim.scope.add("scope-partial:*:*");
      } else {
        activeByDim[dimension].add("dimension-any:" + dimension);
      }
      openDims.add(dimension);
    }

    const scopeType = params.get("scope_type");
    const scopePos = params.get("scope_position");
    if (scopeType || scopePos) {
      ensureDim(activeByDim, "scope");
      activeByDim.scope.clear();
      if (scopeType && scopePos) {
        activeByDim.scope.add("scope:" + scopeType + ":" + scopePos);
      } else {
        activeByDim.scope.add(
          "scope-partial:" + (scopeType || "*") + ":" + (scopePos || "*")
        );
      }
      openDims.add("scope");
    }

    return {
      project: project,
      needsTagReview: needsTagReview,
      activeByDim: activeByDim,
      openDims: openDims,
    };
  }

  /**
   * @param {string} filter
   * @param {Object.<string, Set<string>>} activeByDim
   * @param {Set<string>} openDims
   */
  function applyFilterParam(filter, activeByDim, openDims) {
    const parts = filter.split(":");
    if (parts[0] === "scope" && parts.length >= 3) {
      ensureDim(activeByDim, "scope");
      activeByDim.scope.add(filter);
      openDims.add("scope");
      return;
    }
    if (parts.length >= 2) {
      const dim = parts[0];
      ensureDim(activeByDim, dim);
      activeByDim[dim].add(filter);
      openDims.add(dim);
    }
  }

  /**
   * @param {Object.<string, Set<string>>} activeByDim
   * @param {string} dim
   */
  function ensureDim(activeByDim, dim) {
    if (!activeByDim[dim]) activeByDim[dim] = new Set();
  }

  /**
   * @param {object} row
   * @param {string} key
   * @returns {boolean}
   */
  function rowMatchesScope(row, key) {
    if (key.startsWith("scope-partial:")) {
      const parts = key.split(":");
      const typeId = parts[1];
      const posId = parts[2];
      return (row.tags || []).some(function (tag) {
        if (tag.kind !== "scope") return false;
        if (typeId !== "*" && tag.contribution_type !== typeId) return false;
        if (posId !== "*" && tag.position !== posId) return false;
        return true;
      });
    }
    return (row.filter_keys || []).includes(key);
  }

  /**
   * @param {object} row
   * @param {string} dimension
   * @returns {boolean}
   */
  function rowHasDimension(row, dimension) {
    return (row.tags || []).some(function (t) {
      return t.dimension === dimension;
    });
  }

  /**
   * @param {object} row
   * @param {string} dim
   * @param {string} key
   * @returns {boolean}
   */
  function rowMatchesDimKey(row, dim, key) {
    if (key === "dimension-any:" + dim) return rowHasDimension(row, dim);
    if (dim === "scope") return rowMatchesScope(row, key);
    return (row.filter_keys || []).includes(key);
  }

  /**
   * OR within each active dimension; AND across dimensions.
   * Optional project / pr / onlyTagReview gates.
   *
   * @param {object} row
   * @param {{
   *   project?: string|null,
   *   pr?: string|null,
   *   onlyTagReview?: boolean,
   *   activeByDim?: Object.<string, Set<string>>
   * }} opts
   * @returns {boolean}
   */
  function rowMatchesFilters(row, opts) {
    opts = opts || {};
    const project = opts.project || "";
    const pr = opts.pr != null && opts.pr !== "" ? String(opts.pr) : "";
    if (project && row.project !== project) return false;
    if (pr && String(row.pr_number) !== pr) return false;
    if (opts.onlyTagReview && !row.needs_tag_review) return false;

    const activeByDim = opts.activeByDim || {};
    const dims = Object.keys(activeByDim);
    for (let i = 0; i < dims.length; i++) {
      const dim = dims[i];
      const keys = activeByDim[dim];
      if (!keys || !keys.size) continue;
      let ok = false;
      keys.forEach(function (key) {
        if (rowMatchesDimKey(row, dim, key)) ok = true;
      });
      if (!ok) return false;
    }
    return true;
  }

  /**
   * Short label bits for the URL-filter banner.
   * @param {URLSearchParams} params
   * @returns {string[]}
   */
  function describeUrlFilters(params) {
    const bits = [];
    if (params.get("project")) bits.push("project=" + params.get("project"));
    if (params.get("dimension")) bits.push("all " + params.get("dimension"));
    if (params.get("filter")) bits.push(params.get("filter"));
    if (params.get("scope_type") || params.get("scope_position")) {
      bits.push(
        "scope " +
          (params.get("scope_type") || "*") +
          " → " +
          (params.get("scope_position") || "*")
      );
    }
    if (params.get("needs_tag_review") === "1") bits.push("needs_tag_review");
    return bits;
  }

  /**
   * @param {object[]} rows
   * @param {string} key
   * @returns {number}
   */
  function filterKeyCount(rows, key) {
    return (rows || []).filter(function (r) {
      return (r.filter_keys || []).includes(key);
    }).length;
  }

  /**
   * Value chips that appear at least once in the data, sorted by label.
   * @param {object[]} rows
   * @param {string} dimension
   * @param {Object.<string, string>} valuesMap id → label
   * @returns {{ id: string, label: string, key: string, count: number }[]}
   */
  function valueChipsForDimension(rows, dimension, valuesMap) {
    const values = valuesMap || {};
    return Object.keys(values)
      .map(function (id) {
        const key = dimension + ":" + id;
        return {
          id: id,
          label: values[id],
          key: key,
          count: filterKeyCount(rows, key),
        };
      })
      .filter(function (chip) {
        return chip.count > 0;
      })
      .sort(function (a, b) {
        return a.label.localeCompare(b.label);
      });
  }

  /**
   * Scope catalog ids that appear on at least one row tag.
   * @param {object[]} rows
   * @param {"contribution_type"|"position"} field
   * @param {Object.<string, string>} catalog id → label
   * @returns {{ id: string, label: string }[]}
   */
  function appearingScopeOptions(rows, field, catalog) {
    const cat = catalog || {};
    return Object.keys(cat)
      .filter(function (id) {
        return (rows || []).some(function (r) {
          return (r.tags || []).some(function (t) {
            return t.kind === "scope" && t[field] === id;
          });
        });
      })
      .map(function (id) {
        return { id: id, label: cat[id] };
      });
  }

  /**
   * Convert parseUrlFilters Sets → plain arrays for Alpine reactivity.
   * @param {Object.<string, Set<string>>} activeByDim
   * @returns {Object.<string, string[]>}
   */
  function activeSetsToArrays(activeByDim) {
    const out = {};
    Object.keys(activeByDim || {}).forEach(function (dim) {
      out[dim] = Array.from(activeByDim[dim] || []);
    });
    return out;
  }

  /**
   * @param {Object.<string, string[]>} activeByDim
   * @returns {Object.<string, Set<string>>}
   */
  function activeArraysToSets(activeByDim) {
    const out = {};
    Object.keys(activeByDim || {}).forEach(function (dim) {
      out[dim] = new Set(activeByDim[dim] || []);
    });
    return out;
  }

  global.OrtCommentsFilters = {
    parseUrlFilters: parseUrlFilters,
    rowMatchesScope: rowMatchesScope,
    rowHasDimension: rowHasDimension,
    rowMatchesDimKey: rowMatchesDimKey,
    rowMatchesFilters: rowMatchesFilters,
    describeUrlFilters: describeUrlFilters,
    filterKeyCount: filterKeyCount,
    valueChipsForDimension: valueChipsForDimension,
    appearingScopeOptions: appearingScopeOptions,
    activeSetsToArrays: activeSetsToArrays,
    activeArraysToSets: activeArraysToSets,
  };
})(typeof window !== "undefined" ? window : globalThis);
