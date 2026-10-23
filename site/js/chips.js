/**
 * Chip toggle helpers for codebook filter UIs (comments + projects pages).
 */
(function (global) {
  "use strict";

  /**
   * @param {HTMLElement} chip
   * @param {boolean} on
   */
  function setChipPressed(chip, on) {
    chip.classList.toggle("on", on);
    chip.setAttribute("aria-pressed", on ? "true" : "false");
  }

  /**
   * @param {HTMLElement} chip
   * @returns {boolean} new pressed state
   */
  function toggleChip(chip) {
    const next = chip.getAttribute("aria-pressed") !== "true";
    setChipPressed(chip, next);
    return next;
  }

  /**
   * Remember which dimension <details> blocks are open.
   * @param {ParentNode} root
   * @param {Set<string>} openDims
   */
  function rememberOpenState(root, openDims) {
    root.querySelectorAll("details.dim-block[data-dim]").forEach(function (el) {
      const dim = el.getAttribute("data-dim");
      if (!dim) return;
      if (el.open) openDims.add(dim);
      else openDims.delete(dim);
    });
  }

  global.OrtChips = {
    setChipPressed: setChipPressed,
    toggleChip: toggleChip,
    rememberOpenState: rememberOpenState,
  };
})(typeof window !== "undefined" ? window : globalThis);
