/**
 * Pure helpers for coding view project resolution (no DOM).
 */
(function (global) {
  "use strict";

  /**
   * @param {URLSearchParams} params
   * @param {object[]} projects
   * @param {object[]} comments
   * @returns {{
   *   state: 'missing'|'unknown'|'ready',
   *   slug: string|null,
   *   project: object|null,
   *   comments: object[]
   * }}
   */
  function resolveCodingView(params, projects, comments) {
    const slug = (params.get("project") || "").trim() || null;
    if (!slug) {
      return { state: "missing", slug: null, project: null, comments: [] };
    }
    const list = projects || [];
    const project =
      list.find(function (p) {
        return p && p.slug === slug;
      }) || null;
    if (!project) {
      return { state: "unknown", slug: slug, project: null, comments: [] };
    }
    const rows = (comments || []).filter(function (c) {
      return c && c.project === slug;
    });
    return {
      state: "ready",
      slug: slug,
      project: project,
      comments: rows,
    };
  }

  global.OrtCodingResolve = {
    resolveCodingView: resolveCodingView,
  };
})(typeof window !== "undefined" ? window : globalThis);
