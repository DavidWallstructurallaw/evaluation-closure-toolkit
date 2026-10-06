"""Bounded, closed, offline admission for ect-dossier/0.1.

Admission establishes data shape and referential integrity. Documentary
qualification, chronology of a correction, and scientific claims are evaluated
later. Incomplete semantic facts and wrong-scope reviews remain inspectable.
"""

from __future__ import annotations

import datetime as dt
import json
import re

from .errors import AdmissionError
from . import schema_data as s

MAX_BYTES = 10 * 1024 * 1024
MAX_DEPTH = 32
MAX_VALUES = 250_000
MAX_STRING_BYTES = 65_536
MAX_INTEGER = 9_007_199_254_740_991
ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}\Z", re.ASCII)
TIME_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z", re.ASCII)
INTEGER_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)\Z", re.ASCII)


def _fail(code, pointer=""):
    raise AdmissionError(code, pointer)


def _integer(token):
    if len(token) > 17 or not INTEGER_PATTERN.fullmatch(token):
        _fail("INPUT_NUMBER")
    value = int(token)
    if abs(value) > MAX_INTEGER:
        _fail("INPUT_NUMBER")
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("INPUT_DUPLICATE_KEY")
        result[key] = value
    return result


def _prescan(text):
    """Bound tokens before the recursive standard-library decoder runs."""
    pos = 0
    depth = 0
    values = 0
    length = len(text)
    while pos < length:
        char = text[pos]
        if char in " \t\r\n:,":
            pos += 1
            continue
        if char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                _fail("INPUT_DEPTH_LIMIT")
            values += 1
            pos += 1
        elif char in "]}":
            depth -= 1
            if depth < 0:
                _fail("INPUT_JSON")
            pos += 1
        elif char == '"':
            start = pos
            pos += 1
            while pos < length:
                char = text[pos]
                if char == '"':
                    pos += 1
                    break
                if ord(char) < 32:
                    _fail("INPUT_JSON")
                if char == "\\":
                    pos += 1
                    if pos >= length:
                        _fail("INPUT_JSON")
                pos += 1
                # A valid decoded string cannot require more than six source
                # characters per UTF-8 byte, even with Unicode escapes.
                if pos - start > 6 * MAX_STRING_BYTES + 2:
                    _fail("INPUT_STRING_LIMIT")
            else:
                _fail("INPUT_JSON")
            try:
                decoded = json.loads(text[start:pos])
                byte_length = len(decoded.encode("utf-8"))
            except UnicodeEncodeError:
                _fail("INPUT_UNICODE")
            except (ValueError, TypeError):
                _fail("INPUT_JSON")
            if byte_length > MAX_STRING_BYTES:
                _fail("INPUT_STRING_LIMIT")
            values += 1
        else:
            start = pos
            while pos < length and text[pos] not in " \t\r\n,:[]{}\"":
                pos += 1
            if pos == start:
                _fail("INPUT_JSON")
            token = text[start:pos]
            if token == "null":
                _fail("INPUT_NULL")
            if token not in ("true", "false"):
                if token[0] in "-0123456789" or token in ("NaN", "Infinity"):
                    _integer(token)
                else:
                    _fail("INPUT_JSON")
            values += 1
        if values > MAX_VALUES:
            _fail("INPUT_VALUE_LIMIT")
    if depth != 0:
        _fail("INPUT_JSON")


def _decode(data):
    if not isinstance(data, bytes):
        _fail("INPUT_TYPE")
    if len(data) > MAX_BYTES:
        _fail("INPUT_BYTE_LIMIT")
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError:
        _fail("INPUT_UTF8")
    if text.startswith("\ufeff"):
        _fail("INPUT_BOM")
    _prescan(text)
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_int=_integer,
                          parse_float=lambda _: _fail("INPUT_NUMBER"),
                          parse_constant=lambda _: _fail("INPUT_NUMBER"))
    except (json.JSONDecodeError, RecursionError, UnicodeError):
        _fail("INPUT_JSON")


def _known(record, key):
    field = record.get(key)
    if isinstance(field, dict) and field.get("state") == "known":
        return field["value"]
    return None


def _fact_values(record, key):
    field = record.get(key, {})
    if field.get("state") == "known":
        return [field["value"]]
    return field.get("candidates", [])


class _Validator:
    def __init__(self):
        self.references = []
        self.records = {}
        self.requests = {}
        self.class_ids = {}
        self.member_ids = {}
        self.outcome_ids = {}
        self.scope_snapshots = {}

    def shape(self, value, descriptor, pointer):
        kind = descriptor[0]
        if kind in ("id", "ref", "entity"):
            if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
                _fail("INPUT_ID", pointer)
            if kind != "id":
                self.references.append((value, descriptor, pointer))
        elif kind == "text":
            if not isinstance(value, str) or not value:
                _fail("INPUT_TEXT", pointer)
        elif kind == "time":
            if not isinstance(value, str) or not TIME_PATTERN.fullmatch(value):
                _fail("INPUT_TIMESTAMP", pointer)
            try:
                dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                _fail("INPUT_TIMESTAMP", pointer)
        elif kind == "boolean":
            if type(value) is not bool:
                _fail("INPUT_TYPE", pointer)
        elif kind == "enum":
            if not isinstance(value, str) or value not in descriptor[1]:
                _fail("INPUT_ENUM", pointer)
        elif kind == "array":
            if not isinstance(value, list):
                _fail("INPUT_TYPE", pointer)
            if len(value) < descriptor[2]:
                _fail("INPUT_CARDINALITY", pointer)
            for i, member in enumerate(value):
                self.shape(member, descriptor[1], f"{pointer}/{i}")
            if descriptor[3] and len(set(value)) != len(value):
                _fail("INPUT_DUPLICATE_MEMBER", pointer)
        elif kind == "object":
            if not isinstance(value, dict):
                _fail("INPUT_TYPE", pointer)
            required, optional = descriptor[1:]
            # Point at the owning object for unknown keys. Never echo an
            # arbitrary attacker-supplied key through a diagnostic pointer.
            if value.keys() - required.keys() - optional.keys():
                _fail("INPUT_UNKNOWN_KEY", pointer)
            for key, child in required.items():
                if key not in value:
                    _fail("INPUT_REQUIRED", f"{pointer}/{key}")
                self.shape(value[key], child, f"{pointer}/{key}")
            for key, child in optional.items():
                if key in value:
                    self.shape(value[key], child, f"{pointer}/{key}")
            if "start" in required and "end" in required and value["start"] >= value["end"]:
                _fail("INPUT_WINDOW", pointer)
        elif kind == "fact":
            if not isinstance(value, dict):
                _fail("INPUT_TYPE", pointer)
            state = value.get("state")
            if state == "known":
                self.shape(value, s.obj({"state": s.enum("known"), "value": descriptor[1]}), pointer)
            elif state in ("unknown", "withheld", "disputed", "absent", "not_applicable"):
                options = {"candidates": s.array(descriptor[1])} if state == "disputed" else {}
                self.shape(value, s.obj({"state": s.enum(state), "reason": s.TEXT, "evidence_ids": s.ids(s.EV)}, options), pointer)
            else:
                _fail("INPUT_FACT", pointer)
        else:  # A programmer error, never controlled by the dossier.
            raise RuntimeError("Unknown internal shape descriptor")

    def validate(self, data):
        # Top-level arrays receive their dynamic discriminated record shapes
        # below; all other top-level keys are fixed here.
        if not isinstance(data, dict):
            _fail("INPUT_TYPE")
        keys = {"schema", "id", "analysis_time", "policy", "records", "requests"}
        if data.keys() - keys:
            _fail("INPUT_UNKNOWN_KEY")
        for key in sorted(keys):
            if key not in data:
                _fail("INPUT_REQUIRED", "/" + key)
        for key, descriptor in (("schema", s.enum("ect-dossier/0.1")), ("policy", s.enum("ect-core/0.1")), ("id", s.ID), ("analysis_time", s.TIME)):
            self.shape(data[key], descriptor, "/" + key)
        for key, limit in (("records", 30_000), ("requests", 64)):
            if not isinstance(data[key], list):
                _fail("INPUT_TYPE", "/" + key)
            if len(data[key]) > limit:
                _fail("INPUT_RECORD_LIMIT" if key == "records" else "INPUT_REQUEST_LIMIT", "/" + key)
        immutable = set()
        nodes = relations = memberships = 0
        for i, record in enumerate(data["records"]):
            pointer = f"/records/{i}"
            if not isinstance(record, dict):
                _fail("INPUT_TYPE", pointer)
            record_type = record.get("type")
            if not isinstance(record_type, str) or record_type not in s.RECORD_FIELDS:
                _fail("INPUT_RECORD_TYPE", pointer + "/type")
            required, optional = s.RECORD_FIELDS[record_type]
            common = {} if record_type in ("entity", "scope", "evidence", "review") else s.COMMON
            self.shape(record, s.obj({"id": s.ID, "type": s.enum(record_type), **required}, {**common, **optional}), pointer)
            identity = record["id"]
            if identity in self.records:
                _fail("INPUT_DUPLICATE_ID", pointer + "/id")
            self.records[identity] = record
            if record_type in ("item", "entity"):
                nodes += 1
                key = (record_type, record.get("kind"), record["logical_id"], record["version"])
                if key in immutable:
                    _fail("INPUT_IMMUTABLE_IDENTITY", pointer)
                immutable.add(key)
            relations += record_type == "relation"
            if record_type == "snapshot":
                memberships += len(record["members"])
        if nodes > 10_000:
            _fail("INPUT_NODE_LIMIT", "/records")
        if relations > 20_000:
            _fail("INPUT_RELATION_LIMIT", "/records")
        if memberships > 50_000:
            _fail("INPUT_MEMBERSHIP_LIMIT", "/records")
        for i, request in enumerate(data["requests"]):
            pointer = f"/requests/{i}"
            if not isinstance(request, dict):
                _fail("INPUT_TYPE", pointer)
            operation = request.get("operation")
            if not isinstance(operation, str) or operation not in s.REQUEST_FIELDS:
                _fail("INPUT_OPERATION", pointer + "/operation")
            required, optional = s.REQUEST_FIELDS[operation]
            self.shape(request, s.obj({"id": s.ID, "operation": s.enum(operation), "scope_id": s.ref("scope"), **required}, optional), pointer)
            if request["id"] in self.requests:
                _fail("INPUT_DUPLICATE_ID", pointer + "/id")
            self.requests[request["id"]] = request
        for value, descriptor, pointer in self.references:
            target = self.records.get(value)
            if target is None:
                _fail("INPUT_REFERENCE", pointer)
            if descriptor[0] == "ref":
                if descriptor[1] and target["type"] not in descriptor[1]:
                    _fail("INPUT_REFERENCE_TYPE", pointer)
            elif target["type"] != "entity" or (descriptor[1] and target["kind"] not in descriptor[1]):
                _fail("INPUT_REFERENCE_TYPE", pointer)
        # Build indexes once: many admissions may refer to one large class
        # roster, cohort, or case. Reference checking must not rescan it for
        # every assignment, review, or event.
        for record in data["records"]:
            identity = record["id"]
            if record["type"] == "frame":
                classes = _known(record, "classes")
                if classes is not None:
                    self.class_ids[identity] = {row["id"] for row in classes}
            elif record["type"] == "external_cohort":
                self.member_ids[identity] = set(record["members"])
            elif record["type"] == "correction_case":
                self.outcome_ids[identity] = {row["id"] for row in record.get("outcomes", [])}
            elif record["type"] == "scope":
                self.scope_snapshots[identity] = set(record.get("snapshot_ids", []))
        for i, record in enumerate(data["records"]):
            self.cross_record(record, f"/records/{i}")
        for i, request in enumerate(data["requests"]):
            self.cross_request(request, f"/requests/{i}")

    @staticmethod
    def unique_rows(rows, field, pointer):
        seen = set()
        for i, row in enumerate(rows):
            value = row[field]
            if value in seen:
                _fail("INPUT_DUPLICATE_MEMBER", f"{pointer}/{i}/{field}")
            seen.add(value)

    def class_ref(self, class_id, frame_id, pointer):
        classes = self.class_ids.get(frame_id)
        if classes is not None and class_id not in classes:
            _fail("INPUT_CLASS_REFERENCE", pointer)

    def same_scope(self, record, scope_id, pointer):
        if record.get("scope_id") != scope_id:
            _fail("INPUT_SCOPE_REFERENCE", pointer)

    def cross_record(self, record, pointer):
        kind = record["type"]
        records = self.records
        if kind == "scope":
            if "claim_id" in record:
                claim = records[record["claim_id"]]
                if claim["scope_id"] != record["id"]:
                    _fail("INPUT_SCOPE_REFERENCE", pointer + "/claim_id")
                frame = _known(claim, "frame_id")
                if frame is not None and "frame_id" in record and frame != record["frame_id"]:
                    _fail("INPUT_SCOPE_REFERENCE", pointer + "/frame_id")
            for snapshot_id in record.get("snapshot_ids", []):
                if "frame_id" in record and records[snapshot_id]["frame_id"] != record["frame_id"]:
                    _fail("INPUT_SCOPE_REFERENCE", pointer + "/snapshot_ids")
            return
        if kind == "claim":
            scope = records[record["scope_id"]]
            if "claim_id" in scope and scope["claim_id"] != record["id"]:
                _fail("INPUT_SCOPE_REFERENCE", pointer + "/scope_id")
            frame = _known(record, "frame_id")
            if frame is not None and "frame_id" in scope and frame != scope["frame_id"]:
                _fail("INPUT_SCOPE_REFERENCE", pointer + "/frame_id")
        elif kind == "frame":
            for value in _fact_values(record, "classes"):
                self.unique_rows(value, "id", pointer + "/classes")
            for value in _fact_values(record, "tail_designations"):
                self.unique_rows(value, "class_id", pointer + "/tail_designations")
                for row in value:
                    self.class_ref(row["class_id"], record["id"], pointer + "/tail_designations")
        elif kind == "assignment":
            for value in _fact_values(record, "class_id"):
                self.class_ref(value, record["frame_id"], pointer + "/class_id")
            for value in _fact_values(record, "supersedes"):
                previous = records[value]
                if (previous["item_id"], previous["frame_id"]) != (record["item_id"], record["frame_id"]):
                    _fail("INPUT_REFERENCE_BINDING", pointer + "/supersedes")
        elif kind == "snapshot":
            members = set(record["members"])
            logical = [records[item]["logical_id"] for item in record["members"]]
            if len(set(logical)) != len(logical):
                _fail("INPUT_IMMUTABLE_IDENTITY", pointer + "/members")
            for field, reference in (("assignments", "assignment_id"), ("validities", "validity_id")):
                rows = record.get(field, [])
                self.unique_rows(rows, "item_id", pointer + "/" + field)
                for i, row in enumerate(rows):
                    selected = records[row[reference]]
                    if row["item_id"] not in members or selected["item_id"] != row["item_id"] or selected["frame_id"] != record["frame_id"]:
                        _fail("INPUT_REFERENCE_BINDING", f"{pointer}/{field}/{i}")
            self.unique_rows(record.get("excluded", []), "item_id", pointer + "/excluded")
            if any(row["item_id"] in members for row in record.get("excluded", [])):
                _fail("INPUT_REFERENCE_BINDING", pointer + "/excluded")
            for value in _fact_values(record, "tail_results"):
                self.unique_rows(value, "class_id", pointer + "/tail_results")
                for row in value:
                    self.class_ref(row["class_id"], record["frame_id"], pointer + "/tail_results")
        elif kind == "review":
            self.review_links(record, pointer)
        elif kind == "relation":
            self.relation_links(record, pointer)
        elif kind == "independence":
            if record["form"] == "pairwise" and len(record["members"]) != 2:
                _fail("INPUT_CARDINALITY", pointer + "/members")
        elif kind == "external_cohort":
            members = set(record["members"])
            if not set(record.get("carryover_ids", [])) <= members:
                _fail("INPUT_REFERENCE_BINDING", pointer + "/carryover_ids")
            for field, criterion in (("externality_reviews", "externality"), ("qualifications", "input_qualification")):
                self.unique_rows(record.get(field, []), "member_id", pointer + "/" + field)
                for i, row in enumerate(record.get(field, [])):
                    review = records[row["review_id"]]
                    if row["member_id"] not in members or review["target_id"] != record["id"] or review["criterion"] != criterion or review.get("member_id") != row["member_id"]:
                        _fail("INPUT_REFERENCE_BINDING", f"{pointer}/{field}/{i}")
        elif kind == "external_event":
            cohort = records[record["cohort_id"]]
            if record["member_id"] not in self.member_ids[cohort["id"]]:
                _fail("INPUT_REFERENCE_BINDING", pointer + "/member_id")
            self.same_scope(cohort, record["scope_id"], pointer + "/cohort_id")
        elif kind == "revision":
            pairs = set()
            for i, row in enumerate(record.get("class_map", [])):
                self.class_ref(row["from_class"], record["from_frame"], f"{pointer}/class_map/{i}/from_class")
                self.class_ref(row["to_class"], record["to_frame"], f"{pointer}/class_map/{i}/to_class")
                pair = (row["from_class"], row["to_class"])
                if pair in pairs:
                    _fail("INPUT_DUPLICATE_MEMBER", f"{pointer}/class_map/{i}")
                pairs.add(pair)
            for assignment in record.get("new_assignment_ids", []):
                if records[assignment]["frame_id"] != record["to_frame"]:
                    _fail("INPUT_REFERENCE_BINDING", pointer + "/new_assignment_ids")
        elif kind == "correction_case":
            self.same_scope(records[record["claim_id"]], record["scope_id"], pointer + "/claim_id")
            nested = set()
            for field in ("handling", "attempts", "actions", "outcomes"):
                for i, row in enumerate(record.get(field, [])):
                    if row["id"] in nested:
                        _fail("INPUT_DUPLICATE_ID", f"{pointer}/{field}/{i}/id")
                    nested.add(row["id"])
            attempts = {row["id"] for row in record.get("attempts", [])}
            actions = {row["id"] for row in record.get("actions", [])}
            for i, row in enumerate(record.get("actions", [])):
                if row["attempt_id"] not in attempts:
                    _fail("INPUT_REFERENCE", f"{pointer}/actions/{i}/attempt_id")
            for i, row in enumerate(record.get("outcomes", [])):
                if row["action_id"] not in actions:
                    _fail("INPUT_REFERENCE", f"{pointer}/outcomes/{i}/action_id")
                for review_id in _fact_values(row, "review_id"):
                    review = records[review_id]
                    if review["criterion"] != "correction_outcome" or review["target_id"] != record["id"] or review.get("target_event_id") != row["id"]:
                        _fail("INPUT_REFERENCE_BINDING", f"{pointer}/outcomes/{i}/review_id")

    def review_links(self, review, pointer):
        criterion = review["criterion"]
        target = self.records[review["target_id"]]
        target_types = {
            "assignment_resolution": "assignment", "frame_equivalence": "revision", "matching_basis": "scope",
            "independence": "independence", "externality": "external_cohort", "input_qualification": "external_cohort",
            "retention": "external_cohort", "correction_outcome": "correction_case", "structural_revision": "revision",
        }
        if target["type"] != target_types.get(criterion, "claim"):
            _fail("INPUT_REFERENCE_TYPE", pointer + "/target_id")
        linkage = {
            "member_id": ("externality", "input_qualification", "retention"),
            "target_event_id": ("correction_outcome",), "request_id": ("matching_basis",), "disclosure_id": ("applicability",),
        }
        for field, criteria in linkage.items():
            if criterion in criteria and field not in review:
                _fail("INPUT_REQUIRED", pointer + "/" + field)
            if criterion not in criteria and field in review:
                _fail("INPUT_REFERENCE_BINDING", pointer + "/" + field)
        if "disclosure_ids" in review and criterion not in ("claim_validation", "validation_type_fit"):
            _fail("INPUT_REFERENCE_BINDING", pointer + "/disclosure_ids")
        if "member_id" in review and review["member_id"] not in self.member_ids[target["id"]]:
            _fail("INPUT_REFERENCE_BINDING", pointer + "/member_id")
        if "target_event_id" in review and review["target_event_id"] not in self.outcome_ids[target["id"]]:
            _fail("INPUT_REFERENCE_BINDING", pointer + "/target_event_id")
        if "request_id" in review:
            request = self.requests.get(review["request_id"])
            if request is None or request["operation"] != "compare" or request["scope_id"] != target["id"]:
                _fail("INPUT_REFERENCE_BINDING", pointer + "/request_id")

    def relation_links(self, relation, pointer):
        def node_kind(identity):
            record = self.records[identity]
            return record.get("kind") if record["type"] == "entity" else "item"
        before, after = node_kind(relation["from_id"]), node_kind(relation["to_id"])
        kind = relation["kind"]
        allowed = {
            "derived_from": ({"item", "artifact", "contribution"}, None),
            "acquired_from": ({"item", "artifact", "contribution"}, None),
            "trained_on": ({"model"}, {"item", "artifact", "model"}),
            "exposed_to": ({"model"}, {"item", "artifact"}),
            "rubric_from": ({"contribution", "artifact"}, None),
            "reference_from": ({"contribution", "artifact"}, None),
            "produced_by": ({"item", "artifact", "contribution"}, {"process"}),
            "semantic_influence": ({"process", "contribution"}, {"contribution"}),
            "evaluated_by": ({"model", "item"}, {"actor", "process", "model", "artifact", "contribution"}),
        }
        if kind.startswith("uses_"):
            source_types, target_types = {"process"}, {"artifact", "item", "contribution", "model"}
        else:
            source_types, target_types = allowed[kind]
        if before not in source_types:
            _fail("INPUT_RELATION_ENDPOINT", pointer + "/from_id")
        if target_types is not None and after not in target_types:
            _fail("INPUT_RELATION_ENDPOINT", pointer + "/to_id")

    def cross_request(self, request, pointer):
        scope = self.records[request["scope_id"]]
        operation = request["operation"]
        if "claim_id" in request:
            claim = self.records[request["claim_id"]]
            self.same_scope(claim, scope["id"], pointer + "/claim_id")
            if "claim_id" in scope and scope["claim_id"] != claim["id"]:
                _fail("INPUT_SCOPE_REFERENCE", pointer + "/claim_id")
        snapshots = []
        if "snapshot_id" in request:
            snapshots.append(request["snapshot_id"])
        if operation == "compare":
            snapshots.extend((request["before_id"], request["after_id"]))
            pairs = request.get("pairs", [])
            self.unique_rows(pairs, "before_item_id", pointer + "/pairs")
            self.unique_rows(pairs, "after_item_id", pointer + "/pairs")
            if "revision_id" in request:
                revision = self.records[request["revision_id"]]
                self.same_scope(revision, scope["id"], pointer + "/revision_id")
                if (revision["from_frame"], revision["to_frame"]) != (self.records[request["before_id"]]["frame_id"], self.records[request["after_id"]]["frame_id"]):
                    _fail("INPUT_REFERENCE_BINDING", pointer + "/revision_id")
        for identity in snapshots:
            snapshot = self.records[identity]
            if identity not in self.scope_snapshots[scope["id"]]:
                _fail("INPUT_SCOPE_REFERENCE", pointer)
            if "frame_id" in scope and scope["frame_id"] != snapshot["frame_id"]:
                _fail("INPUT_SCOPE_REFERENCE", pointer)
            if "claim_id" in scope:
                frame = _known(self.records[scope["claim_id"]], "frame_id")
                if frame is not None and frame != snapshot["frame_id"]:
                    _fail("INPUT_SCOPE_REFERENCE", pointer)
        if "cohort_id" in request:
            self.same_scope(self.records[request["cohort_id"]], scope["id"], pointer + "/cohort_id")
        for field in ("case_ids", "anomaly_ids", "revision_ids"):
            for value in request.get(field, []):
                self.same_scope(self.records[value], scope["id"], pointer + "/" + field)
        if operation == "lineage":
            for value in request.get("independence_ids", []):
                independence = self.records[value]
                self.same_scope(independence, scope["id"], pointer + "/independence_ids")
                if set(independence["members"]) != set(request["seed_ids"]):
                    _fail("INPUT_REFERENCE_BINDING", pointer + "/independence_ids")


def admit(data: bytes) -> dict:
    """Return a newly decoded valid dossier, or raise AdmissionError.

No network, filesystem, clock, or environment lookup is performed. Optional
fields remain absent so missing facts and explicit empty selections stay distinct.
"""
    dossier = _decode(data)
    _Validator().validate(dossier)
    return dossier
