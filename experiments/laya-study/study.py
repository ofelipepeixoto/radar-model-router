"""Original Radar contract study. Synthetic fixtures only; no Laya inference or adapter."""
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from radar_router.contracts import (ContractError, RouteInput, Scope, TIERS,
                                    fingerprint, integer, number, parse_json)
from radar_router.policy import decide

HERE = Path(__file__).resolve().parent
UPSTREAM = "c4a805b5160621bbfc53417126990a67d3163bc5"
MAX_BYTES = 131072
FILES = ("corpus.json", "questions.json", "observations.fixture.json", "contract.schema.json")
TAGS = {"simple", "negation", "ambiguous", "high-risk", "mixed-language", "unknown",
        "empty", "unicode", "truncation", "injection", "continuation", "trusted-floor"}
SOURCE = {"kind": "synthetic-fixture", "revision": "synthetic-v1", "dtype": "fixture",
          "model_revision": None, "model_sha256": None}


def exact(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ContractError("study_schema")


def enum(value, allowed):
    if type(value) is not str or value not in allowed:
        raise ContractError("study_enum")


def case_id(value):
    if type(value) is not str or re.fullmatch(r"pt-[0-9]{2}", value) is None:
        raise ContractError("study_case_id")


def digest(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContractError("study_digest")


def bounded_probability(value):
    # Check range before math.isfinite converts a potentially huge JSON integer to float.
    if type(value) not in (int, float) or not 0 <= value <= 1:
        raise ContractError("study_number")
    return number(value, 0, 1)


def questions_hash(value):
    exact(value, ("schema", "id", "type", "instructions", "labels", "option_order", "language"))
    if (value["schema"] != "radar-laya-questions/1" or value["id"] != "candidate-tier"
            or value["type"] != "choice" or value["language"] != "pt-BR"
            or value["labels"] != list(TIERS)):
        raise ContractError("study_questions")
    instruction = value["instructions"]
    if type(instruction) is not str or not 1 <= len(instruction.encode("utf-8")) <= 1024:
        raise ContractError("study_instructions")
    order = value["option_order"]
    if (type(order) is not list or len(order) != 4 or any(type(x) is not int for x in order)
            or sorted(order) != [0, 1, 2, 3]):
        raise ContractError("study_order")
    return fingerprint(value)


def validate_corpus(value):
    exact(value, ("schema", "synthetic", "cases"))
    if value["schema"] != "radar-laya-corpus/1" or value["synthetic"] is not True:
        raise ContractError("study_corpus")
    cases = value["cases"]
    if type(cases) is not list or not 1 <= len(cases) <= 64:
        raise ContractError("study_case_limit")
    seen = set()
    for item in cases:
        exact(item, ("id", "split", "text", "tags", "metadata", "trusted", "expected"))
        case_id(item["id"])
        if item["id"] in seen:
            raise ContractError("study_duplicate_case")
        seen.add(item["id"])
        enum(item["split"], ("development", "reserve"))
        if type(item["text"]) is not str or len(item["text"].encode("utf-8")) > 8192:
            raise ContractError("study_text_limit")
        tags = item["tags"]
        if type(tags) is not list or not 1 <= len(tags) <= 6:
            raise ContractError("study_tags")
        for tag in tags:
            enum(tag, TAGS)
        if len(set(tags)) != len(tags):
            raise ContractError("study_tags")
        exact(item["metadata"], ("task", "risk", "current_tier", "continuation"))
        RouteInput.from_dict({"session": "synthetic-study", "turn": item["id"], **item["metadata"]})
        exact(item["trusted"], ("minimum_tier", "require_review"))
        Scope("laya-study", **item["trusted"])
        exact(item["expected"], ("tier", "review_required"))
        integer(item["expected"]["tier"], 0, 3)
        if type(item["expected"]["review_required"]) is not bool:
            raise ContractError("study_review")
    if {x["split"] for x in cases} != {"development", "reserve"}:
        raise ContractError("study_split")
    return cases


def validate_observations(value, cases, corpus_sha, question_sha):
    exact(value, ("schema", "corpus_sha256", "questions_sha256", "source", "observations"))
    if value["schema"] != "radar-laya-observations/1":
        raise ContractError("study_observations")
    digest(value["corpus_sha256"])
    digest(value["questions_sha256"])
    if value["corpus_sha256"] != corpus_sha or value["questions_sha256"] != question_sha:
        raise ContractError("study_identity")
    exact(value["source"], SOURCE)
    if value["source"] != SOURCE:
        raise ContractError("study_fixture_only")
    observations = value["observations"]
    if type(observations) is not list or len(observations) != len(cases):
        raise ContractError("study_observation_count")
    by_id = {}
    for item in observations:
        exact(item, ("case_id", "status", "probabilities", "abstention", "truncated"))
        case_id(item["case_id"])
        if item["case_id"] in by_id:
            raise ContractError("study_duplicate_observation")
        enum(item["status"], ("observed", "not_run"))
        enum(item["abstention"], ("passed", "abstained", "unevaluated"))
        if type(item["truncated"]) is not bool:
            raise ContractError("study_truncated")
        probabilities = item["probabilities"]
        if item["status"] == "not_run":
            if probabilities is not None or item["abstention"] != "unevaluated" or item["truncated"]:
                raise ContractError("study_not_run")
        else:
            if type(probabilities) is not list or len(probabilities) != 4:
                raise ContractError("study_probabilities")
            values = [bounded_probability(p) for p in probabilities]
            if not math.isclose(sum(values), 1, rel_tol=0, abs_tol=1e-9):
                raise ContractError("study_probability_sum")
        by_id[item["case_id"]] = item
    if set(by_id) != {item["id"] for item in cases}:
        raise ContractError("study_case_join")
    return by_id


def read_file(directory, name):
    path = directory / name
    if path.is_symlink():
        raise ContractError("study_symlink")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    return raw, parse_json(raw, maximum=MAX_BYTES)


def load_bundle(directory=HERE):
    manifest_raw, manifest = read_file(directory, "manifest.json")
    exact(manifest, ("schema", "upstream_code_revision", "candidate_min_probability", "files"))
    if manifest["schema"] != "radar-laya-manifest/1" or manifest["upstream_code_revision"] != UPSTREAM:
        raise ContractError("study_manifest")
    threshold = bounded_probability(manifest["candidate_min_probability"])
    if threshold != 0.85:
        raise ContractError("study_protocol")
    exact(manifest["files"], FILES)
    payloads, hashes = {}, {}
    for name in FILES:
        digest(manifest["files"][name])
        raw, payloads[name] = read_file(directory, name)
        hashes[name] = hashlib.sha256(raw).hexdigest()
        if hashes[name] != manifest["files"][name]:
            raise ContractError("study_artifact_changed")
    cases = validate_corpus(payloads["corpus.json"])
    qhash = questions_hash(payloads["questions.json"])
    observations = validate_observations(payloads["observations.fixture.json"], cases,
                                         hashes["corpus.json"], qhash)
    return cases, observations, {"manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
                                "corpus_sha256": hashes["corpus.json"], "questions_sha256": qhash,
                                "fixture_sha256": hashes["observations.fixture.json"],
                                "contract_sha256": hashes["contract.schema.json"],
                                "study_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                "baseline_code_sha256": {
                                    name: hashlib.sha256((ROOT / "radar_router" / name).read_bytes()).hexdigest()
                                    for name in ("contracts.py", "policy.py", "vendor/jev_policy.py")},
                                "candidate_min_probability": threshold,
                                "upstream_code_revision": UPSTREAM, **SOURCE}


def compare_case(case, observation, threshold):
    value = RouteInput.from_dict({"session": "synthetic-study", "turn": case["id"], **case["metadata"]})
    baseline = decide(value, Scope("laya-study", **case["trusted"]))
    if {"tier": baseline.tier, "review_required": baseline.review_required} != case["expected"]:
        raise ContractError("study_baseline_expectation")
    candidate, confidence = None, None
    gate = "not_run"
    if observation["status"] == "observed":
        p = observation["probabilities"]
        candidate = max(range(4), key=lambda i: p[i])
        confidence = max(p)
        if observation["abstention"] != "passed":
            gate = observation["abstention"]
        elif observation["truncated"] or not case["text"].strip():
            gate = "incomplete_context"
        elif baseline.review_required:
            gate = "trusted_review"
        elif candidate < case["trusted"]["minimum_tier"]:
            gate = "trusted_floor"
        elif value.continuation and candidate < value.current_tier:
            gate = "continuation_floor"
        elif confidence < threshold:
            gate = "low_probability"
        else:
            gate = "passed"
    # Candidate never becomes Prediction or enters policy; baseline is always unchanged.
    return {"id": case["id"], "split": case["split"], "baseline": baseline.to_dict(),
            "observation_status": observation["status"], "candidate_tier": candidate,
            "answer_confidence": confidence, "gate": gate, "effective_source": "baseline",
            "critical_underroute": candidate is not None and candidate < baseline.tier
            and baseline.review_required}


def metrics(rows):
    observed = [x for x in rows if x["candidate_tier"] is not None]
    passed = [x for x in rows if x["gate"] == "passed"]
    matrix = [[0] * 4 for _ in range(4)]
    for row in observed:
        matrix[row["baseline"]["tier"]][row["candidate_tier"]] += 1
    def agreement(items):
        return sum(x["candidate_tier"] == x["baseline"]["tier"] for x in items) / len(items) if items else None
    return {"total": len(rows), "observed_fixtures": len(observed), "not_run": len(rows) - len(observed),
            "fixture_agreement_with_baseline": agreement(observed),
            "fixture_coverage": len(passed) / len(rows) if rows else None,
            "selective_fixture_agreement": agreement(passed),
            "critical_underroute_fixtures": sum(x["critical_underroute"] for x in rows),
            "confusion_matrix_baseline_by_candidate": matrix, "labels": list(TIERS)}


def run_study(directory=HERE):
    cases, observations, provenance = load_bundle(directory)
    rows = [compare_case(case, observations[case["id"]], provenance["candidate_min_probability"])
            for case in cases]
    return {"schema": "radar-laya-study-report/1", "synthetic": True,
            "model_inference": "not_run", "model_quality_verified": False,
            "savings_verified": False, "api_calls": 0, "integration_enabled": False,
            "provenance": provenance, "baseline_cases_verified": len(rows),
            "splits": {split: metrics([row for row in rows if row["split"] == split])
                       for split in ("development", "reserve")}, "cases": rows}


def main():
    try:
        if len(sys.argv) != 1:
            raise ContractError("study_arguments")
        result = run_study()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0
    except (ContractError, OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        print('{"error":"invalid_study","model_inference":"not_run"}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
