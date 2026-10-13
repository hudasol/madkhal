"""Generate artefacts from the L0 models: JSON Schema, TypeScript types, field dictionary.

All functions are pure and return text; the CLI writes the files and the tests compare
them with the committed copies (a stale artefact fails the build).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from madkhal.core.jsonio import dumps

from . import models as m

SCHEMA_PATH = "contract/madkhal.schema.json"
DICTIONARY_JSON_PATH = "contract/field_dictionary.json"
DICTIONARY_MD_PATH = "contract/FIELD_DICTIONARY.md"
TYPESCRIPT_PATH = "web/src/contract/types.ts"

ENUMS: tuple[type[StrEnum], ...] = (
    m.CoverageState,
    m.DetectorState,
    m.BloomState,
    m.EvidenceLevel,
    m.ParamSource,
    m.ActionKind,
    m.StatusClass,
    m.Dataset,
)


def json_schema() -> dict[str, Any]:
    _, top = models_json_schema(
        [(model, "serialization") for model in m.CONTRACT_MODELS],
        title="Madkhal contract",
        ref_template="#/$defs/{model}",
    )
    top["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    top["description"] = (
        "Generated from madkhal.contract.models. Do not edit by hand. "
        "Evidence: real satellite history from the Nadhir hindcast. Plant, drone and "
        "consequences: hypothetical, synthetic parameters."
    )
    return top


# ---------------------------------------------------------------- TypeScript
def _ts_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if "const" in schema:
        c = schema["const"]
        return dumps(c, indent=None) if not isinstance(c, bool) else ("true" if c else "false")
    if "enum" in schema:
        return " | ".join(dumps(v, indent=None) for v in schema["enum"])
    if "anyOf" in schema:
        parts = []
        for s in schema["anyOf"]:
            t = _ts_type(s)
            if t not in parts:
                parts.append(t)
        return " | ".join(parts)
    t = str(schema.get("type", ""))
    if t == "string":
        return "string"
    if t in ("number", "integer"):
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "null":
        return "null"
    if t == "array":
        inner = _ts_type(schema.get("items", {}))
        return f"Array<{inner}>"
    if t == "object":
        ap = schema.get("additionalProperties")
        if isinstance(ap, dict):
            return f"Record<string, {_ts_type(ap)}>"
        return "Record<string, unknown>"
    return "unknown"


def _comment(text: str, indent: str = "") -> list[str]:
    safe = text.replace("*/", "* /")
    return [f"{indent}/** {safe} */"]


def typescript() -> str:
    schema = json_schema()
    defs: dict[str, Any] = schema["$defs"]
    lines = [
        "// Generated from madkhal.contract.models by `madkhal docs build`. Do not edit by hand.",
        "// Evidence: real satellite history from the Nadhir hindcast.",
        "// Plant, drone and consequences: hypothetical, synthetic parameters.",
        "",
    ]
    for enum in sorted(ENUMS, key=lambda e: e.__name__):
        values = [dumps(v.value, indent=None) for v in enum]
        lines += _comment((enum.__doc__ or enum.__name__).strip().splitlines()[0])
        lines.append(f"export type {enum.__name__} = {' | '.join(values)};")
        lines.append(f"export const {enum.__name__}Values = [{', '.join(values)}] as const;")
        lines.append("")
    enum_names = {e.__name__ for e in ENUMS}
    for name in sorted(defs):
        d = defs[name]
        if name in enum_names:
            continue
        if "enum" in d:
            raise ValueError(f"enum {name} is used by a model but not listed in ENUMS")
        lines += _comment(d.get("description", name).strip().splitlines()[0])
        lines.append(f"export interface {name} {{")
        required = set(d.get("required", []))
        for field, fs in d.get("properties", {}).items():
            desc = fs.get("description")
            if desc:
                lines += _comment(desc, "  ")
            opt = "" if field in required else "?"
            lines.append(f"  {field}{opt}: {_ts_type(fs)};")
        lines.append("}")
        lines.append("")
    lines.append(
        "export const SIMULATION_NOTICE = " + dumps(m.SIMULATION_NOTICE, indent=None) + ";"
    )
    lines.append("export const BANNER_EVIDENCE = " + dumps(m.BANNER_EVIDENCE, indent=None) + ";")
    lines.append(
        "export const BANNER_HYPOTHETICAL = " + dumps(m.BANNER_HYPOTHETICAL, indent=None) + ";"
    )
    lines.append("export const REPLAY_LABEL = " + dumps(m.REPLAY_LABEL, indent=None) + ";")
    lines.append("export const ADVISORY_SCOPE = " + dumps(m.ADVISORY_SCOPE, indent=None) + ";")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- field dictionary
def field_dictionary() -> dict[str, Any]:
    schema = json_schema()
    defs: dict[str, Any] = schema["$defs"]
    out: dict[str, Any] = {}
    for model in m.CONTRACT_MODELS:
        name = model.__name__
        props = defs[name].get("properties", {})
        fields: dict[str, Any] = {}
        for fname, finfo in model.model_fields.items():
            extra = finfo.json_schema_extra if isinstance(finfo.json_schema_extra, dict) else {}
            fields[fname] = {
                "en": finfo.description or "",
                "ar": str(extra.get("x-ar", "")),
                "unit": extra.get("x-unit"),
                "type": _ts_type(props.get(fname, {})),
                "required": finfo.is_required(),
            }
        out[name] = {"description": (model.__doc__ or "").strip().splitlines()[0], "fields": fields}
    return out


def field_dictionary_markdown() -> str:
    fd = field_dictionary()
    lines = [
        "# Field dictionary",
        "",
        "Generated from `madkhal.contract.models` by `madkhal docs build`. Do not edit by hand.",
        "",
        "The Arabic descriptions are machine drafted and should be reviewed by a native speaker.",
        "",
        "Conventions: UTC is stored and Asia/Dubai is used for display; SI units; volumes in m3;",
        "flow in m3/h; percentages 0 to 100; probabilities 0 to 1; costs in hypothetical cost",
        "units (CU).",
        "",
    ]
    for name, entry in fd.items():
        lines += [
            f"## {name}",
            "",
            entry["description"],
            "",
            "| Field | Type | Unit | English | العربية |",
            "|---|---|---|---|---|",
        ]
        for fname, f in entry["fields"].items():
            t = str(f["type"]).replace("|", "\\|")
            unit = f["unit"] or ""
            lines.append(f"| `{fname}` | `{t}` | {unit} | {f['en']} | {f['ar']} |")
        lines.append("")
    return "\n".join(lines)


def artefacts() -> dict[str, str]:
    """Every generated contract artefact as {repo relative path: text}."""
    return {
        SCHEMA_PATH: dumps(json_schema()),
        DICTIONARY_JSON_PATH: dumps(field_dictionary()),
        DICTIONARY_MD_PATH: field_dictionary_markdown(),
        TYPESCRIPT_PATH: typescript(),
    }


def model_names() -> list[str]:
    return [model.__name__ for model in m.CONTRACT_MODELS]


def is_contract_model(obj: object) -> bool:
    return isinstance(obj, type) and issubclass(obj, BaseModel) and obj in m.CONTRACT_MODELS
