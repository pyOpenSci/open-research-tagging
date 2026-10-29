/**
 * Coding form driven by codebook.coding_schema (12f).
 * Python emit_coding_block remains the YAML contract; JS mirrors schema walk.
 */
(function (global) {
  "use strict";

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

  function schemaFrom(codebook) {
    return (codebook && codebook.coding_schema) || { dimensions: [] };
  }

  function emptyCoding(codebook) {
    return emptyFromSchema(schemaFrom(codebook));
  }

  function emptyFromSchema(schema) {
    const coding = {};
    (schema.dimensions || []).forEach(function (dim) {
      const dimObj = {};
      (dim.layers || []).forEach(function (layer) {
        dimObj[layer.id] = emptyLayerValue(layer);
      });
      coding[dim.id] = dimObj;
    });
    return coding;
  }

  function emptyLayerValue(layer) {
    const storage = layer.storage || "object";
    const fields = layer.fields || [];
    if (storage === "scalar") {
      return defaultForField(fields[0] || {});
    }
    if (storage === "scope_map") {
      const field = fields[0] || {};
      const defaultPos = field.default_position || "not_addressed";
      const scope = {};
      (field.contribution_types || []).forEach(function (t) {
        scope[t.yaml_key] = defaultPos;
      });
      return scope;
    }
    const obj = {};
    fields.forEach(function (field) {
      obj[field.id] = defaultForField(field);
    });
    return obj;
  }

  function defaultForField(field) {
    if (Object.prototype.hasOwnProperty.call(field, "default")) {
      return field.default;
    }
    if (field.kind === "multi") return [];
    if (field.kind === "text") return "";
    return null;
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

  function prefillCoding(raw, codebook) {
    const schema = schemaFrom(codebook);
    const base = emptyFromSchema(schema);
    raw = liftFlatCoding(raw);
    if (!raw || typeof raw !== "object") return base;

    (schema.dimensions || []).forEach(function (dim) {
      const rawDim = raw[dim.id];
      if (!rawDim || typeof rawDim !== "object") return;
      (dim.layers || []).forEach(function (layer) {
        if (!(layer.id in rawDim)) return;
        const storage = layer.storage || "object";
        const rawLayer = rawDim[layer.id];
        if (storage === "scalar") {
          const field = (layer.fields || [])[0] || {};
          if (field.kind === "multi") {
            base[dim.id][layer.id] = asStringList(rawLayer);
          } else if (rawLayer != null && rawLayer !== "") {
            base[dim.id][layer.id] = String(rawLayer);
          } else {
            base[dim.id][layer.id] = null;
          }
        } else if (storage === "scope_map" && rawLayer && typeof rawLayer === "object") {
          const dest = base[dim.id][layer.id];
          Object.keys(rawLayer).forEach(function (key) {
            const yamlKey = yamlScopeKey(key);
            if (rawLayer[key] != null && rawLayer[key] !== "") {
              dest[yamlKey] = String(rawLayer[key]);
            }
          });
        } else if (storage === "object" && rawLayer && typeof rawLayer === "object") {
          const dest = base[dim.id][layer.id];
          (layer.fields || []).forEach(function (field) {
            if (!(field.id in rawLayer)) return;
            const val = rawLayer[field.id];
            if (field.kind === "multi") {
              dest[field.id] = asStringList(val);
            } else if (field.kind === "text") {
              if (val != null) dest[field.id] = String(val);
            } else if (field.kind === "single") {
              if (val == null || val === "") dest[field.id] = null;
              else dest[field.id] = boolishId(val);
            } else if (val != null && val !== "") {
              dest[field.id] = boolishId(val);
            }
          });
        }
      });
    });
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

  function evidenceDimForSection(section, codebook) {
    const dims = schemaFrom(codebook).dimensions || [];
    for (let i = 0; i < dims.length; i++) {
      if (dims[i].id === section) {
        return dims[i].evidence_dimension || "";
      }
    }
    return "";
  }

  function emitCodingYaml(raw, codebook) {
    const schema = schemaFrom(codebook);
    const c = prefillCoding(raw, codebook);
    const lines = ["coding:"];
    (schema.dimensions || []).forEach(function (dim) {
      const dimVal = c[dim.id] || {};
      lines.push("  " + dim.id + ":");
      (dim.layers || []).forEach(function (layer) {
        emitLayer(lines, "    ", layer, dimVal[layer.id]);
      });
    });
    return lines.join("\n") + "\n";
  }

  /** Provenance key order — keep in sync with Python project_yaml.PROVENANCE_KEYS. */
  const PROVENANCE_KEYS = [
    "source_repo",
    "source_path",
    "source_commit",
    "source_url",
    "retrieved_at",
    "policy_location",
    "policy_date",
    "notes",
  ];

  const POLICY_LOCATION_OPTIONS = [
    { id: "CONTRIBUTING", label: "CONTRIBUTING" },
    { id: "standalone-file", label: "Standalone file" },
    { id: "governance-doc", label: "Governance doc" },
    { id: "other", label: "Other" },
  ];

  function emptyProvenance() {
    const out = {};
    PROVENANCE_KEYS.forEach(function (key) {
      out[key] = key === "notes" ? "" : null;
    });
    return out;
  }

  function emptyMeta() {
    return {
      slug: "",
      display_name: "",
      provenance: emptyProvenance(),
      files: [],
    };
  }

  function normalizeMeta(raw) {
    const base = emptyMeta();
    if (!raw || typeof raw !== "object") return base;
    const slug = String(raw.slug || "").trim();
    base.slug = slug;
    const display = raw.display_name;
    base.display_name =
      display != null && String(display).trim() !== ""
        ? String(display).trim()
        : slug;
    const provIn =
      raw.provenance && typeof raw.provenance === "object" ? raw.provenance : {};
    const prov = emptyProvenance();
    PROVENANCE_KEYS.forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(provIn, key)) {
        prov[key] = key === "notes" && provIn[key] == null ? "" : provIn[key];
      }
    });
    base.provenance = prov;
    if (Array.isArray(raw.files)) {
      base.files = raw.files.map(function (f) {
        if (f && typeof f === "object") return Object.assign({}, f);
        return { path: String(f) };
      });
    }
    return base;
  }

  function emitProjectYaml(meta, coding, codebook) {
    const m = normalizeMeta(meta);
    const lines = [
      "slug: " + yamlScalar(m.slug || "example-project"),
      "display_name: " + yamlScalar(m.display_name || m.slug || "Example Project"),
      "",
      "provenance:",
    ];
    PROVENANCE_KEYS.forEach(function (key) {
      lines.push("  " + key + ": " + yamlScalar(m.provenance[key]));
    });
    lines.push("");
    const codingText = emitCodingYaml(coding, codebook).replace(/\n$/, "");
    lines.push(codingText);
    lines.push("");
    lines.push("files:");
    if (!m.files.length) {
      lines.push("  []");
    } else {
      m.files.forEach(function (row) {
        const path = row && row.path != null ? row.path : row;
        lines.push("  - path: " + yamlScalar(path));
        if (row && typeof row === "object" && "description" in row) {
          lines.push("    description: " + yamlScalar(row.description));
        }
        if (row && typeof row === "object") {
          Object.keys(row).forEach(function (extra) {
            if (extra === "path" || extra === "description") return;
            lines.push("    " + extra + ": " + yamlScalar(row[extra]));
          });
        }
      });
    }
    return lines.join("\n") + "\n";
  }

  function emitLayer(lines, indent, layer, layerVal) {
    const storage = layer.storage || "object";
    const fields = layer.fields || [];
    if (storage === "scalar") {
      const field = fields[0] || {};
      if (field.kind === "multi") {
        appendListField(lines, indent + layer.id, asStringList(layerVal));
      } else {
        lines.push(indent + layer.id + ": " + yamlScalar(layerVal));
      }
      return;
    }
    lines.push(indent + layer.id + ":");
    const inner = indent + "  ";
    if (storage === "scope_map") {
      const field = fields[0] || {};
      const scope = layerVal && typeof layerVal === "object" ? layerVal : {};
      const seen = {};
      (field.contribution_types || []).forEach(function (t) {
        lines.push(inner + t.yaml_key + ": " + yamlScalar(scope[t.yaml_key]));
        seen[t.yaml_key] = 1;
      });
      Object.keys(scope).forEach(function (key) {
        if (!seen[key]) {
          lines.push(inner + key + ": " + yamlScalar(scope[key]));
        }
      });
      return;
    }
    const obj = layerVal && typeof layerVal === "object" ? layerVal : {};
    fields.forEach(function (field) {
      const val = obj[field.id];
      if (field.kind === "multi") {
        appendListField(lines, inner + field.id, asStringList(val));
      } else {
        lines.push(inner + field.id + ": " + yamlScalar(val));
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

  /** @deprecated — prefer schema field.options */
  function valueOptions(codebook, dimension) {
    const map = (codebook && codebook.values && codebook.values[dimension]) || {};
    return Object.keys(map).map(function (id) {
      return { id: id, label: map[id] || id };
    });
  }

  global.OrtCodingForm = {
    emptyCoding: emptyCoding,
    emptyFromSchema: emptyFromSchema,
    prefillCoding: prefillCoding,
    emitCodingYaml: emitCodingYaml,
    emitProjectYaml: emitProjectYaml,
    emptyMeta: emptyMeta,
    normalizeMeta: normalizeMeta,
    PROVENANCE_KEYS: PROVENANCE_KEYS,
    POLICY_LOCATION_OPTIONS: POLICY_LOCATION_OPTIONS,
    toggleMulti: toggleMulti,
    yamlScopeKey: yamlScopeKey,
    hashtagScopeKey: hashtagScopeKey,
    evidenceDimForSection: evidenceDimForSection,
    valueOptions: valueOptions,
    schemaFrom: schemaFrom,
  };
})(typeof window !== "undefined" ? window : globalThis);
