"""Synthetic input constructors, independent of production graph/event algorithms."""

from copy import deepcopy
from importlib.resources import files
import json


def fixture(name):
    return json.loads(files("evaluation_closure_toolkit").joinpath("data", name + ".json").read_bytes())


def known(value):
    return {"state": "known", "value": value}


def gap(state="unknown"):
    return {"state": state, "reason": "Synthetic explicit information gap.", "evidence_ids": []}


def wire(dossier):
    return json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def record(dossier, identity):
    return next(r for r in dossier["records"] if r["id"] == identity)


def result(report, identity):
    return next(r for r in report["results"] if r["request_id"] == identity)


def member(report, identity="p"):
    return next(r for r in result(report, "external-main")["values"]["member_states"] if r["member_id"] == identity)


def entity(identity, kind="artifact", **kwargs):
    return {"id": identity, "type": "entity", "kind": kind, "logical_id": identity, "version": "v1", **kwargs}


def relation(identity, source, target, kind="derived_from", **kwargs):
    return {"id": identity, "type": "relation", "scope_id": "scope", "from_id": source, "to_id": target, "kind": kind, **kwargs}


def copy_review(dossier, identity, *, template="external-p", verdict="supports", **kwargs):
    row = deepcopy(record(dossier, template))
    row.update(id=identity, verdict=known(verdict), **kwargs)
    dossier["records"].append(row)
    return row


def copy_event(dossier, identity, *, template="p-used", **kwargs):
    row = deepcopy(record(dossier, template))
    row.update(id=identity, **kwargs)
    dossier["records"].append(row)
    return row
