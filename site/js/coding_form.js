/**
 * Explicit adapter: nested project.yaml coding shape for the coding form.
 * Not a generic codebook→form engine (same mindset as build_overall / 5c).
 */
(function (global) {
  "use strict";

  /** YAML scope keys matching projects/_template/project.yaml */
  const DEFAULT_SCOPE_KEYS = [
    "code",
    "tests",
    "docs_and_text",
    "issues_and_pr_descriptions",
    "review",
    "autonomous_agents",
    "contribution_types_not_defined",
  ];

  /** Not emitted in codebook.json values (no comment namespace); template ids. */
  const DISCLOSURE_FORMAT_OPTIONS = [
    { id: "label-or-tag", label: "Label or tag" },
    { id: "free-text", label: "Free text" },
    { id: "other", label: "Other" },
  ];

  const GOVERNANCE_OPTIONS = [
    { id: "solo", label: "Solo" },
    { id: "community", label: "Community" },
    { id: "foundation-backed", label: "Foundation-backed" },
    { id: "corporate-backed", label: "Corporate-backed" },
  ];

  function emptyScope() {
    const scope = {};
    DEFAULT_SCOPE_KEYS.forEach(function (key) {
      scope[key] = "not_addressed";
    });
    return scope;
  }

  function emptyCoding() {
    return {
      stance: null,
      scope: emptyScope(),
      stated_rationale: [],
      guidance_on_use: { level: null, types: [] },
      accountability: {
        human_responsibility: "not_stated",
        disclosure: "none",
        disclosure_format: [],
        enforcement: [],
      },
      context: {
        project_size: "",
        governance: null,
        domain: "",
        notes: "",
      },
    };
  }

  /**
   * Deep-ish merge of raw project.coding into empty defaults.
   * @param {object|null|undefined} raw
   * @returns {object}
   */
  function prefillCoding(raw) {
    const base = emptyCoding();
    if (!raw || typeof raw !== "object") return base;

    if (raw.stance != null && raw.stance !== "") {
      base.stance = String(raw.stance);
    }

    const scopeIn = raw.scope;
    if (scopeIn && typeof scopeIn === "object") {
      Object.keys(scopeIn).forEach(function (key) {
        const yamlKey = yamlScopeKey(key);
        if (scopeIn[key] != null && scopeIn[key] !== "") {
          base.scope[yamlKey] = String(scopeIn[key]);
        }
      });
    }

    base.stated_rationale = asStringList(raw.stated_rationale);

    const guid = raw.guidance_on_use;
    if (guid && typeof guid === "object") {
      if (guid.level != null && guid.level !== "") {
        base.guidance_on_use.level = String(guid.level);
      }
      base.guidance_on_use.types = asStringList(guid.types);
    }

    const acct = raw.accountability;
    if (acct && typeof acct === "object") {
      if (acct.human_responsibility != null && acct.human_responsibility !== "") {
        base.accountability.human_responsibility = boolishId(
          acct.human_responsibility
        );
      }
      if (acct.disclosure != null && acct.disclosure !== "") {
        base.accountability.disclosure = String(acct.disclosure);
      }
      base.accountability.disclosure_format = asStringList(
        acct.disclosure_format
      );
      base.accountability.enforcement = asStringList(acct.enforcement);
    }

    const ctx = raw.context;
    if (ctx && typeof ctx === "object") {
      if (ctx.project_size != null) {
        base.context.project_size = String(ctx.project_size);
      }
      if (ctx.governance != null && ctx.governance !== "") {
        base.context.governance = String(ctx.governance);
      }
      if (ctx.domain != null) base.context.domain = String(ctx.domain);
      if (ctx.notes != null) base.context.notes = String(ctx.notes);
    }

    return base;
  }

  function asStringList(value) {
    if (value == null) return [];
    if (Array.isArray(value)) {
      return value
        .filter(function (v) {
          return v != null && v !== "";
        })
        .map(String);
    }
    return [String(value)];
  }

  /** YAML 1.1 may load bare yes/no as booleans; map to codebook ids. */
  function boolishId(value) {
    if (value === true) return "yes";
    if (value === false) return "no";
    return String(value);
  }

  function toggleMulti(list, id, on) {
    const cur = (list || []).slice();
    const i = cur.indexOf(id);
    if (on) {
      if (i < 0) cur.push(id);
    } else if (i >= 0) {
      cur.splice(i, 1);
    }
    return cur;
  }

  function yamlScopeKey(key) {
    return String(key || "").replace(/-/g, "_");
  }

  function hashtagScopeKey(key) {
    return String(key || "").replace(/_/g, "-");
  }

  /**
   * @param {object} codebook
   * @param {string} dimension
   * @returns {{id: string, label: string}[]}
   */
  function valueOptions(codebook, dimension) {
    const map = (codebook && codebook.values && codebook.values[dimension]) || {};
    return Object.keys(map).map(function (id) {
      return { id: id, label: map[id] || id };
    });
  }

  /**
   * Scope rows for the form: yaml key + label + position options.
   * @param {object} codebook
   * @returns {{key: string, label: string}[]}
   */
  function scopeTypeRows(codebook) {
    const types =
      (codebook && codebook.scope && codebook.scope.contribution_types) || {};
    const keys = Object.keys(types);
    if (keys.length === 0) {
      return DEFAULT_SCOPE_KEYS.map(function (key) {
        return { key: key, label: humanize(key) };
      });
    }
    return keys.map(function (hashKey) {
      return {
        key: yamlScopeKey(hashKey),
        label: types[hashKey] || humanize(hashKey),
      };
    });
  }

  function scopePositionOptions(codebook) {
    const positions =
      (codebook && codebook.scope && codebook.scope.positions) || {};
    const keys = Object.keys(positions);
    if (keys.length === 0) {
      return ["allowed", "restricted", "banned", "not_addressed"].map(
        function (id) {
          return { id: id, label: humanize(id) };
        }
      );
    }
    return keys.map(function (id) {
      return { id: id, label: positions[id] || humanize(id) };
    });
  }

  function disclosureFormatOptions() {
    return DISCLOSURE_FORMAT_OPTIONS.slice();
  }

  function governanceOptions() {
    return GOVERNANCE_OPTIONS.slice();
  }

  /**
   * Evidence-pane dimension key for a form section id.
   * @param {string} section
   * @returns {string} empty string = all comments
   */
  function evidenceDimForSection(section) {
    const map = {
      stance: "stance",
      scope: "scope",
      stated_rationale: "stated_rationale",
      guidance_on_use: "guidance_level",
      accountability: "disclosure",
      context: "",
    };
    return map[section] != null ? map[section] : "";
  }

  function humanize(slug) {
    return String(slug || "")
      .replace(/[_-]+/g, " ")
      .replace(/\b\w/g, function (c) {
        return c.toUpperCase();
      });
  }

  const QUOTE_WORDS = {
    yes: 1,
    no: 1,
    true: 1,
    false: 1,
    null: 1,
    on: 1,
    off: 1,
    y: 1,
    n: 1,
  };

  /**
   * Paste-ready coding: YAML block. Must match Python emit_coding_block.
   * @param {object|null|undefined} raw
   * @returns {string}
   */
  function emitCodingYaml(raw) {
    const c = prefillCoding(raw);
    const lines = ["coding:"];
    lines.push("  stance: " + yamlScalar(c.stance));
    lines.push("  scope:");
    DEFAULT_SCOPE_KEYS.forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(c.scope, key)) {
        lines.push("    " + key + ": " + yamlScalar(c.scope[key]));
      }
    });
    Object.keys(c.scope).forEach(function (key) {
      if (DEFAULT_SCOPE_KEYS.indexOf(key) < 0) {
        lines.push("    " + key + ": " + yamlScalar(c.scope[key]));
      }
    });
    appendListField(lines, "  stated_rationale", c.stated_rationale);
    lines.push("  guidance_on_use:");
    lines.push("    level: " + yamlScalar(c.guidance_on_use.level));
    appendListField(lines, "    types", c.guidance_on_use.types);
    lines.push("  accountability:");
    lines.push(
      "    human_responsibility: " +
        yamlScalar(c.accountability.human_responsibility)
    );
    lines.push(
      "    disclosure: " + yamlScalar(c.accountability.disclosure)
    );
    appendListField(
      lines,
      "    disclosure_format",
      c.accountability.disclosure_format
    );
    appendListField(lines, "    enforcement", c.accountability.enforcement);
    lines.push("  context:");
    lines.push(
      "    project_size: " + yamlScalar(c.context.project_size)
    );
    lines.push("    governance: " + yamlScalar(c.context.governance));
    lines.push("    domain: " + yamlScalar(c.context.domain));
    lines.push("    notes: " + yamlScalar(c.context.notes));
    return lines.join("\n") + "\n";
  }

  function appendListField(lines, keyLine, items) {
    const list = items || [];
    if (list.length === 0) {
      lines.push(keyLine + ": []");
      return;
    }
    lines.push(keyLine + ":");
    const leading = keyLine.match(/^ */)[0].length;
    const pad = new Array(leading + 3).join(" ");
    list.forEach(function (item) {
      lines.push(pad + "- " + yamlScalar(item));
    });
  }

  function yamlScalar(value) {
    if (value === null || value === undefined) return "null";
    if (typeof value === "boolean") return value ? "true" : "false";
    const s = String(value);
    if (s === "") return '""';
    if (QUOTE_WORDS[s.toLowerCase()] || /[\s:#\[\]{},&*!|>'"%@`]/.test(s)) {
      return JSON.stringify(s);
    }
    return s;
  }

  global.OrtCodingForm = {
    emptyCoding: emptyCoding,
    prefillCoding: prefillCoding,
    emitCodingYaml: emitCodingYaml,
    toggleMulti: toggleMulti,
    yamlScopeKey: yamlScopeKey,
    hashtagScopeKey: hashtagScopeKey,
    valueOptions: valueOptions,
    scopeTypeRows: scopeTypeRows,
    scopePositionOptions: scopePositionOptions,
    disclosureFormatOptions: disclosureFormatOptions,
    governanceOptions: governanceOptions,
    evidenceDimForSection: evidenceDimForSection,
    DEFAULT_SCOPE_KEYS: DEFAULT_SCOPE_KEYS,
  };
})(typeof window !== "undefined" ? window : globalThis);
