/**
 * Explicit adapter: nested project.yaml coding shape for the coding form.
 * draft-0.2: each dimension has explicit / implicit subsections.
 * Not a generic codebook→form engine (same mindset as build_overall / 5c).
 */
(function (global) {
  "use strict";

  const SCOPE_KEYS_EXPLICIT = [
    "code",
    "tests",
    "docs_and_text",
    "issues_and_pr_descriptions",
    "review",
    "autonomous_agents",
    "contribution_types_not_defined",
  ];

  const SCOPE_KEYS_IMPLICIT = [
    "code",
    "comments",
    "tests",
    "docs_and_text",
    "issues_and_pr_descriptions",
    "review",
    "autonomous_agents",
  ];

  /** @deprecated alias — explicit scope keys */
  const DEFAULT_SCOPE_KEYS = SCOPE_KEYS_EXPLICIT;

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

  const POLICY_LOCATION_OPTIONS = [
    { id: "CONTRIBUTING", label: "CONTRIBUTING" },
    { id: "standalone-file", label: "Standalone file" },
    { id: "governance-doc", label: "Governance doc" },
    { id: "other", label: "Other" },
  ];

  function emptyScopeExplicit() {
    const scope = {};
    SCOPE_KEYS_EXPLICIT.forEach(function (key) {
      scope[key] = "not_addressed";
    });
    return scope;
  }

  function emptyScopeImplicit() {
    const scope = {};
    SCOPE_KEYS_IMPLICIT.forEach(function (key) {
      scope[key] = "not_seen";
    });
    return scope;
  }

  function emptyCoding() {
    return {
      stance: { explicit: null, implicit: [] },
      scope: {
        explicit: emptyScopeExplicit(),
        implicit: emptyScopeImplicit(),
      },
      stated_rationale: { explicit: [], implicit: [] },
      guidance_on_use: {
        explicit: { level: null, types: [] },
        implicit: {
          level: null,
          types: [],
          notes: "",
          written_for: "",
          not_ai_specific: "",
        },
      },
      accountability: {
        explicit: {
          human_responsibility: "not_stated",
          disclosure: "none",
          disclosure_format: [],
          enforcement: [],
          new_contributors: "not_stated",
        },
        implicit: {
          disclosure_in_practice: "none-seen",
          notes: "",
        },
      },
      context: {
        explicit: {
          project_size: "",
          governance: null,
          decision_process: "",
          domain: "",
          policy_date: "",
          policy_location: null,
          notes: "",
        },
        implicit: {
          contributors: "",
          who_decides: "",
          outside_activity: "",
          when_ai_began: "",
          ai_file_locations: "",
          notes: "",
        },
      },
    };
  }

  function liftFlatCoding(raw) {
    if (!raw || typeof raw !== "object") return raw;
    const out = Object.assign({}, raw);
    if (out.stance != null && typeof out.stance !== "object") {
      out.stance = { explicit: out.stance, implicit: [] };
    }
    if (
      out.scope &&
      typeof out.scope === "object" &&
      out.scope.explicit == null &&
      out.scope.implicit == null
    ) {
      out.scope = { explicit: Object.assign({}, out.scope), implicit: {} };
    }
    if (Array.isArray(out.stated_rationale)) {
      out.stated_rationale = { explicit: out.stated_rationale, implicit: [] };
    }
    if (
      out.guidance_on_use &&
      typeof out.guidance_on_use === "object" &&
      out.guidance_on_use.explicit == null &&
      (out.guidance_on_use.level != null || out.guidance_on_use.types != null)
    ) {
      out.guidance_on_use = {
        explicit: {
          level: out.guidance_on_use.level,
          types: out.guidance_on_use.types || [],
        },
        implicit: {},
      };
    }
    if (
      out.accountability &&
      typeof out.accountability === "object" &&
      out.accountability.explicit == null &&
      (out.accountability.disclosure != null ||
        out.accountability.human_responsibility != null)
    ) {
      out.accountability = {
        explicit: Object.assign({}, out.accountability),
        implicit: {},
      };
    }
    if (
      out.context &&
      typeof out.context === "object" &&
      out.context.explicit == null &&
      out.context.implicit == null
    ) {
      out.context = { explicit: Object.assign({}, out.context), implicit: {} };
    }
    return out;
  }

  /**
   * Deep-ish merge of raw project.coding into empty defaults.
   * @param {object|null|undefined} raw
   * @returns {object}
   */
  function prefillCoding(raw) {
    const base = emptyCoding();
    raw = liftFlatCoding(raw);
    if (!raw || typeof raw !== "object") return base;

    const stance = raw.stance;
    if (stance && typeof stance === "object") {
      if (stance.explicit != null && stance.explicit !== "") {
        base.stance.explicit = String(stance.explicit);
      }
      base.stance.implicit = asStringList(stance.implicit);
    }

    const scope = raw.scope;
    if (scope && typeof scope === "object") {
      mergeScopeMap(base.scope.explicit, scope.explicit);
      mergeScopeMap(base.scope.implicit, scope.implicit);
    }

    const rationale = raw.stated_rationale;
    if (rationale && typeof rationale === "object") {
      base.stated_rationale.explicit = asStringList(rationale.explicit);
      base.stated_rationale.implicit = asStringList(rationale.implicit);
    }

    const guid = raw.guidance_on_use;
    if (guid && typeof guid === "object") {
      mergeGuidance(base.guidance_on_use.explicit, guid.explicit);
      mergeGuidance(base.guidance_on_use.implicit, guid.implicit);
      if (guid.implicit && typeof guid.implicit === "object") {
        ["notes", "written_for", "not_ai_specific"].forEach(function (k) {
          if (guid.implicit[k] != null) {
            base.guidance_on_use.implicit[k] = String(guid.implicit[k]);
          }
        });
      }
    }

    const acct = raw.accountability;
    if (acct && typeof acct === "object") {
      mergeAcctExplicit(base.accountability.explicit, acct.explicit);
      if (acct.implicit && typeof acct.implicit === "object") {
        if (
          acct.implicit.disclosure_in_practice != null &&
          acct.implicit.disclosure_in_practice !== ""
        ) {
          base.accountability.implicit.disclosure_in_practice = String(
            acct.implicit.disclosure_in_practice
          );
        }
        if (acct.implicit.notes != null) {
          base.accountability.implicit.notes = String(acct.implicit.notes);
        }
      }
    }

    const ctx = raw.context;
    if (ctx && typeof ctx === "object") {
      mergeContext(base.context.explicit, ctx.explicit);
      mergeContext(base.context.implicit, ctx.implicit);
    }

    return base;
  }

  function mergeScopeMap(dest, src) {
    if (!src || typeof src !== "object") return;
    Object.keys(src).forEach(function (key) {
      const yamlKey = yamlScopeKey(key);
      if (src[key] != null && src[key] !== "") {
        dest[yamlKey] = String(src[key]);
      }
    });
  }

  function mergeGuidance(dest, src) {
    if (!src || typeof src !== "object") return;
    if (src.level != null && src.level !== "") dest.level = String(src.level);
    if (src.types != null) dest.types = asStringList(src.types);
  }

  function mergeAcctExplicit(dest, src) {
    if (!src || typeof src !== "object") return;
    if (src.human_responsibility != null && src.human_responsibility !== "") {
      dest.human_responsibility = boolishId(src.human_responsibility);
    }
    if (src.disclosure != null && src.disclosure !== "") {
      dest.disclosure = String(src.disclosure);
    }
    if (src.disclosure_format != null) {
      dest.disclosure_format = asStringList(src.disclosure_format);
    }
    if (src.enforcement != null) {
      dest.enforcement = asStringList(src.enforcement);
    }
    if (src.new_contributors != null && src.new_contributors !== "") {
      dest.new_contributors = boolishId(src.new_contributors);
    }
  }

  function mergeContext(dest, src) {
    if (!src || typeof src !== "object") return;
    Object.keys(src).forEach(function (key) {
      const val = src[key];
      if (
        (val == null || val === "") &&
        (key === "governance" || key === "policy_location")
      ) {
        dest[key] = null;
      } else if (val != null) {
        dest[key] = String(val);
      }
    });
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

  function valueOptions(codebook, dimension) {
    const values = (codebook && codebook.values) || {};
    let map = values[dimension] || {};
    // Implicit layers often reuse the same codes as explicit (e.g. guidance).
    if (
      Object.keys(map).length === 0 &&
      typeof dimension === "string" &&
      dimension.indexOf("_implicit") > 0
    ) {
      map = values[dimension.replace(/_implicit$/, "")] || {};
    }
    return Object.keys(map).map(function (id) {
      return { id: id, label: map[id] || id };
    });
  }

  function scopeTypeRows(codebook, layer) {
    const block =
      layer === "implicit"
        ? (codebook && codebook.scope_implicit) || {}
        : (codebook && codebook.scope) || {};
    const types = block.contribution_types || {};
    const fallback =
      layer === "implicit" ? SCOPE_KEYS_IMPLICIT : SCOPE_KEYS_EXPLICIT;
    const keys = Object.keys(types);
    if (keys.length === 0) {
      return fallback.map(function (key) {
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

  function scopePositionOptions(codebook, layer) {
    const block =
      layer === "implicit"
        ? (codebook && codebook.scope_implicit) || {}
        : (codebook && codebook.scope) || {};
    const positions = block.positions || {};
    const keys = Object.keys(positions);
    if (keys.length === 0) {
      const fallback =
        layer === "implicit"
          ? ["seen", "not_seen"]
          : ["allowed", "restricted", "banned", "not_addressed"];
      return fallback.map(function (id) {
        return { id: id, label: humanize(id) };
      });
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

  function policyLocationOptions() {
    return POLICY_LOCATION_OPTIONS.slice();
  }

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

  function emitCodingYaml(raw) {
    const c = prefillCoding(raw);
    const lines = ["coding:"];

    lines.push("  stance:");
    lines.push("    explicit: " + yamlScalar(c.stance.explicit));
    appendListField(lines, "    implicit", c.stance.implicit);

    lines.push("  scope:");
    lines.push("    explicit:");
    appendScopeMap(lines, "      ", c.scope.explicit, SCOPE_KEYS_EXPLICIT);
    lines.push("    implicit:");
    appendScopeMap(lines, "      ", c.scope.implicit, SCOPE_KEYS_IMPLICIT);

    lines.push("  stated_rationale:");
    appendListField(lines, "    explicit", c.stated_rationale.explicit);
    appendListField(lines, "    implicit", c.stated_rationale.implicit);

    lines.push("  guidance_on_use:");
    ["explicit", "implicit"].forEach(function (layer) {
      const guid = c.guidance_on_use[layer];
      lines.push("    " + layer + ":");
      lines.push("      level: " + yamlScalar(guid.level));
      appendListField(lines, "      types", guid.types);
      if (layer === "implicit") {
        lines.push("      notes: " + yamlScalar(guid.notes || ""));
        lines.push("      written_for: " + yamlScalar(guid.written_for || ""));
        lines.push(
          "      not_ai_specific: " + yamlScalar(guid.not_ai_specific || "")
        );
      }
    });

    lines.push("  accountability:");
    const ae = c.accountability.explicit;
    lines.push("    explicit:");
    lines.push(
      "      human_responsibility: " + yamlScalar(ae.human_responsibility)
    );
    lines.push("      disclosure: " + yamlScalar(ae.disclosure));
    appendListField(lines, "      disclosure_format", ae.disclosure_format);
    appendListField(lines, "      enforcement", ae.enforcement);
    lines.push("      new_contributors: " + yamlScalar(ae.new_contributors));
    const ai = c.accountability.implicit;
    lines.push("    implicit:");
    lines.push(
      "      disclosure_in_practice: " + yamlScalar(ai.disclosure_in_practice)
    );
    lines.push("      notes: " + yamlScalar(ai.notes));

    lines.push("  context:");
    ["explicit", "implicit"].forEach(function (layer) {
      const ctx = c.context[layer];
      lines.push("    " + layer + ":");
      Object.keys(ctx).forEach(function (key) {
        lines.push("      " + key + ": " + yamlScalar(ctx[key]));
      });
    });

    return lines.join("\n") + "\n";
  }

  function appendScopeMap(lines, indent, scope, order) {
    const seen = {};
    order.forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(scope, key)) {
        lines.push(indent + key + ": " + yamlScalar(scope[key]));
        seen[key] = 1;
      }
    });
    Object.keys(scope).forEach(function (key) {
      if (!seen[key]) {
        lines.push(indent + key + ": " + yamlScalar(scope[key]));
      }
    });
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
    policyLocationOptions: policyLocationOptions,
    evidenceDimForSection: evidenceDimForSection,
    DEFAULT_SCOPE_KEYS: DEFAULT_SCOPE_KEYS,
    SCOPE_KEYS_EXPLICIT: SCOPE_KEYS_EXPLICIT,
    SCOPE_KEYS_IMPLICIT: SCOPE_KEYS_IMPLICIT,
  };
})(typeof window !== "undefined" ? window : globalThis);
