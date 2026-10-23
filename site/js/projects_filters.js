/**
 * Pure helpers for the projects overview filters (no DOM).
 */
(function (global) {
  "use strict";

  /**
   * @param {object} row
   * @param {string} dim
   * @param {string} valueId
   * @returns {boolean}
   */
  function projectHasCode(row, dim, valueId) {
    const group = row.overall && row.overall[dim];
    const values = (group && group.values) || [];
    return values.some(function (v) {
      return v.id === valueId;
    });
  }

  /**
   * OR within each dimension; AND across dimensions.
   * @param {object} row
   * @param {Object.<string, string[]>} activeByDim
   * @returns {boolean}
   */
  function projectMatchesFilters(row, activeByDim) {
    const active = activeByDim || {};
    const dims = Object.keys(active);
    for (let i = 0; i < dims.length; i++) {
      const dim = dims[i];
      const ids = active[dim] || [];
      if (!ids.length) continue;
      let ok = false;
      for (let j = 0; j < ids.length; j++) {
        if (projectHasCode(row, dim, ids[j])) {
          ok = true;
          break;
        }
      }
      if (!ok) return false;
    }
    return true;
  }

  /**
   * Value ids present on any project for a dimension, with labels + counts.
   * @param {object[]} rows
   * @param {string} dim
   * @returns {Object.<string, { label: string, count: number }>}
   */
  function codesPresent(rows, dim) {
    const counts = {};
    (rows || []).forEach(function (row) {
      const values =
        (row.overall && row.overall[dim] && row.overall[dim].values) || [];
      values.forEach(function (v) {
        if (!counts[v.id]) {
          counts[v.id] = { label: v.label || v.id, count: 0 };
        }
        counts[v.id].count += 1;
      });
    });
    return counts;
  }

  /**
   * Chip list for a dimension, sorted by label; empty if nothing present.
   * @param {object[]} rows
   * @param {string} dim
   * @returns {{ id: string, label: string, count: number }[]}
   */
  function chipsForDimension(rows, dim) {
    const present = codesPresent(rows, dim);
    return Object.keys(present)
      .map(function (id) {
        return {
          id: id,
          label: present[id].label,
          count: present[id].count,
        };
      })
      .sort(function (a, b) {
        return a.label.localeCompare(b.label);
      });
  }

  global.OrtProjectsFilters = {
    projectHasCode: projectHasCode,
    projectMatchesFilters: projectMatchesFilters,
    codesPresent: codesPresent,
    chipsForDimension: chipsForDimension,
  };
})(typeof window !== "undefined" ? window : globalThis);
