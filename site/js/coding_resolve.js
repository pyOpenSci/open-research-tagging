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

  /**
   * Comments that have at least one tag on dimension.
   * Pass null/"" for all comments (no dimension filter).
   * @param {object[]} comments
   * @param {string|null} dimension
   * @returns {object[]}
   */
  function commentsForDimension(comments, dimension) {
    const rows = comments || [];
    if (!dimension) return rows.slice();
    return rows.filter(function (c) {
      return (c.tags || []).some(function (t) {
        return t && t.dimension === dimension;
      });
    });
  }

  /**
   * Full passage text for evidence cards (quote, else body without hashtag lines).
   * @param {object} comment
   * @returns {string}
   */
  function evidenceText(comment) {
    if (comment && comment.quote) {
      return String(comment.quote).replace(/\s+/g, " ").trim();
    }
    const body = String((comment && comment.body) || "");
    const lines = body.split("\n").filter(function (l) {
      return !l.trim().startsWith("#");
    });
    return lines.join(" ").replace(/\s+/g, " ").trim() || body.trim();
  }

  /**
   * Truncated evidence text (tests / compact previews).
   * Cards use evidenceText + CSS clamp; expand on hover.
   * @param {object} comment
   * @param {number} [max]
   * @returns {string}
   */
  function evidenceExcerpt(comment, max) {
    const limit = max || 160;
    const text = evidenceText(comment);
    return text.length > limit ? text.slice(0, limit - 1) + "…" : text;
  }

  global.OrtCodingResolve = {
    resolveCodingView: resolveCodingView,
    commentsForDimension: commentsForDimension,
    evidenceText: evidenceText,
    evidenceExcerpt: evidenceExcerpt,
  };
})(typeof window !== "undefined" ? window : globalThis);
