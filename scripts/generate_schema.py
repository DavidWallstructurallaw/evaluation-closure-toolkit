#!/usr/bin/env python3
"""Generate the closed ect-dossier/0.1 JSON Schema from admission descriptors.

This Draft 2020-12 schema describes the decoded document grammar. Admission is
still mandatory: ordinary JSON Schema cannot recover duplicate keys or numeric
lexemes, validate captured UTF-8 bytes, enforce the byte/depth/value/aggregate
resource limits, or resolve record IDs and scoped references. ``maxLength`` is a
necessary code-point bound, while admission enforces the 65,536 UTF-8-byte bound.
Timestamp ``format`` is an annotation for validators without format assertion;
admission checks Gregorian dates, exact UTC spelling, and ordered windows.
Reference-target annotations (``x-ect-*``) explain checks enforced by admission.

Run from any working directory: python scripts/generate_schema.py [--check].
The generator uses only the Python standard library and never imports runtime
API modules. No external schema resolution is needed to consume the artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTORS = ROOT / "src/evaluation_closure_toolkit/schema_data.py"
DESTINATION = ROOT / "src/evaluation_closure_toolkit/data/dossier.schema.json"


class SchemaBuilder:
    """Translate inert descriptor tuples into local-reference schema objects."""

    def __init__(self) -> None:
        self.definitions: dict[str, dict] = {
            "id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 96,
                "pattern": r"^[A-Za-z][A-Za-z0-9_.:-]{0,95}$(?![\s\S])",
            },
            "text": {
                "type": "string",
                "minLength": 1,
                "maxLength": 65536,
                "x-ect-maxUtf8Bytes": 65536,
            },
            "timestamp": {
                "type": "string",
                "minLength": 20,
                "maxLength": 20,
                "pattern": (
                    r"^(?!0000)[0-9]{4}-(0[1-9]|1[0-2])-"
                    r"(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):"
                    r"[0-5][0-9]:[0-5][0-9]Z$(?![\s\S])"
                ),
                "format": "date-time",
                "$comment": "Admission additionally validates Gregorian calendar dates.",
            },
        }

    def shape(self, descriptor: tuple) -> dict:
        kind = descriptor[0]
        if kind in {"id", "text", "time"}:
            return {"$ref": "#/$defs/" + ("timestamp" if kind == "time" else kind)}
        if kind == "boolean":
            return {"type": "boolean"}
        if kind == "enum":
            return {"type": "string", "enum": list(descriptor[1])}
        if kind in {"ref", "entity"}:
            result = {"$ref": "#/$defs/id"}
            if kind == "ref":
                result["x-ect-recordTypes"] = list(descriptor[1]) or ["*"]
            else:
                result["x-ect-recordTypes"] = ["entity"]
                result["x-ect-entityKinds"] = list(descriptor[1]) or ["*"]
            return result
        if kind == "array":
            result = {"type": "array", "items": self.shape(descriptor[1])}
            if descriptor[2]:
                result["minItems"] = descriptor[2]
            if descriptor[3]:
                result["uniqueItems"] = True
            return result
        if kind == "object":
            return self.object(descriptor[1], descriptor[2])
        if kind == "fact":
            # Content addressing gives a stable name independent of traversal.
            identity = json.dumps(descriptor[1], sort_keys=True, separators=(",", ":"))
            name = "fact_" + hashlib.sha256(identity.encode("ascii")).hexdigest()[:16]
            if name not in self.definitions:
                value = self.shape(descriptor[1])
                gap_properties = {
                    "reason": {"$ref": "#/$defs/text"},
                    "evidence_ids": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {"$ref": "#/$defs/id", "x-ect-recordTypes": ["evidence"]},
                    },
                }
                self.definitions[name] = {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {"state": {"const": "known"}, "value": value},
                            "required": ["state", "value"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "state": {"enum": ["unknown", "withheld", "absent", "not_applicable"]},
                                **gap_properties,
                            },
                            "required": ["state", "reason", "evidence_ids"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "state": {"const": "disputed"},
                                **gap_properties,
                                "candidates": {"type": "array", "items": value},
                            },
                            "required": ["state", "reason", "evidence_ids"],
                            "additionalProperties": False,
                        },
                    ]
                }
            return {"$ref": "#/$defs/" + name}
        raise ValueError(f"Unsupported grammar descriptor: {kind}")

    def object(self, required: dict, optional: dict) -> dict:
        if set(required) & set(optional):
            raise ValueError("Required and optional grammar fields overlap")
        result = {
            "type": "object",
            "properties": {key: self.shape(value) for key, value in {**required, **optional}.items()},
            "additionalProperties": False,
        }
        if required:
            result["required"] = sorted(required)
        return result


def build_schema() -> dict:
    grammar = runpy.run_path(str(DESCRIPTORS))
    builder = SchemaBuilder()
    record_definitions = []
    for kind, (required, optional) in grammar["RECORD_FIELDS"].items():
        common = {} if kind in {"entity", "scope", "evidence", "review"} else grammar["COMMON"]
        descriptor = builder.object(
            {"id": grammar["ID"], "type": ("enum", (kind,)), **required},
            {**common, **optional},
        )
        if kind == "independence":
            descriptor["allOf"] = [{
                "if": {"properties": {"form": {"const": "pairwise"}}},
                "then": {"properties": {"members": {"maxItems": 2}}},
            }]
        if kind == "review":
            bindings = {
                "member_id": ["externality", "input_qualification", "retention"],
                "target_event_id": ["correction_outcome"],
                "request_id": ["matching_basis"],
                "disclosure_id": ["applicability"],
            }
            descriptor["allOf"] = [{
                "if": {"properties": {"criterion": {"enum": criteria}}},
                "then": {"required": [key]},
                "else": {"properties": {key: False}},
            } for key, criteria in bindings.items()]
            descriptor["allOf"].append({
                "if": {"properties": {"criterion": {"enum": ["claim_validation", "validation_type_fit"]}}},
                "else": {"properties": {"disclosure_ids": False}},
            })
        builder.definitions["record_" + kind] = descriptor
        record_definitions.append({"$ref": "#/$defs/record_" + kind})
    request_definitions = []
    for operation, (required, optional) in grammar["REQUEST_FIELDS"].items():
        descriptor = builder.object(
            {"id": grammar["ID"], "operation": ("enum", (operation,)), "scope_id": ("ref", ("scope",)), **required},
            optional,
        )
        builder.definitions["request_" + operation] = descriptor
        request_definitions.append({"$ref": "#/$defs/request_" + operation})
    builder.definitions["record"] = {"oneOf": sorted(record_definitions, key=lambda entry: entry["$ref"])}
    builder.definitions["request"] = {"oneOf": sorted(request_definitions, key=lambda entry: entry["$ref"])}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:ect:dossier:0.1",
        "title": "Evaluation Closure Toolkit dossier 0.1",
        "description": "Closed decoded-document grammar for ect-dossier/0.1; strict admission remains required.",
        "$comment": (
            "Generated by scripts/generate_schema.py. Byte identity, strict JSON token decoding, "
            "UTF-8 byte lengths, Gregorian dates, ordered windows, aggregate resource limits, "
            "ID uniqueness by namespace, immutable-version uniqueness, typed reference resolution, "
            "scope agreement and endpoint constraints are additionally enforced by admission.py. "
            "x-ect-* keys are annotations, not portable validation keywords."
        ),
        "type": "object",
        "properties": {
            "schema": {"const": "ect-dossier/0.1"},
            "id": {"$ref": "#/$defs/id"},
            "analysis_time": {"$ref": "#/$defs/timestamp"},
            "policy": {"const": "ect-core/0.1"},
            "records": {"type": "array", "maxItems": 30000, "items": {"$ref": "#/$defs/record"}},
            "requests": {"type": "array", "maxItems": 64, "items": {"$ref": "#/$defs/request"}},
        },
        "required": ["analysis_time", "id", "policy", "records", "requests", "schema"],
        "additionalProperties": False,
        "$defs": builder.definitions,
    }


def schema_bytes() -> bytes:
    return (json.dumps(build_schema(), ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the packaged schema is stale")
    args = parser.parse_args()
    expected = schema_bytes()
    if args.check:
        if not DESTINATION.is_file() or DESTINATION.read_bytes() != expected:
            parser.exit(1, "Packaged dossier.schema.json is stale; regenerate it.\n")
    else:
        DESTINATION.write_bytes(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
