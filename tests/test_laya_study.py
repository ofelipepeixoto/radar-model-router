"""Behavioral regressions for the optional, fixture-only Laya study."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from radar_router.contracts import ContractError, RouteInput, Scope
from radar_router.policy import decide

STUDY = Path(__file__).resolve().parents[1] / "experiments" / "laya-study"
spec = importlib.util.spec_from_file_location("radar_laya_study", STUDY / "study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class StudyContracts(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads((STUDY / "corpus.json").read_text())
        self.fixture = json.loads((STUDY / "observations.fixture.json").read_text())
        self.questions = json.loads((STUDY / "questions.json").read_text())
        self.corpus_sha = hashlib.sha256((STUDY / "corpus.json").read_bytes()).hexdigest()
        self.qsha = study.questions_hash(self.questions)

    def validate(self, fixture=None):
        return study.validate_observations(self.fixture if fixture is None else fixture,
                                           self.corpus["cases"], self.corpus_sha, self.qsha)

    def test_frozen_bundle_and_splits(self):
        result = study.run_study()
        self.assertEqual(result["baseline_cases_verified"], 24)
        self.assertEqual([x["total"] for x in result["splits"].values()], [12, 12])
        self.assertTrue(result["synthetic"])
        self.assertEqual(result["model_inference"], "not_run")
        self.assertFalse(result["model_quality_verified"])
        self.assertFalse(result["integration_enabled"])
        self.assertFalse(result["savings_verified"])
        self.assertEqual(result["api_calls"], 0)

    def test_extra_authority_or_transport_fields_rejected(self):
        for key in ("prompt", "tenant", "scope", "api_key", "endpoint", "model_path"):
            with self.subTest(key=key), self.assertRaises(ContractError):
                self.validate({**self.fixture, key: "PRIVATE_SENTINEL"})

    def test_exact_nested_schemas(self):
        for field in ("source", "observations"):
            bad = copy.deepcopy(self.fixture)
            target = bad[field] if field == "source" else bad[field][0]
            target["approval"] = True
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.validate(bad)

    def test_no_checkpoint_provenance_allowed(self):
        for key, value in (("kind", "checkpoint"), ("model_revision", "a" * 40),
                           ("model_sha256", "b" * 64), ("dtype", "float32")):
            bad = copy.deepcopy(self.fixture)
            bad["source"][key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                self.validate(bad)

    def test_probabilities_reject_invalid_numbers(self):
        for value in (True, False, "0.91", -1, 1.5, float("nan"), float("inf"), 10 ** 1000):
            bad = copy.deepcopy(self.fixture)
            bad["observations"][0]["probabilities"][0] = value
            with self.subTest(value=value), self.assertRaises(ContractError):
                self.validate(bad)

    def test_sum_and_dimensions(self):
        for value in ([0.2] * 4, [1, 0, 0], [1, 0, 0, 0, 0], None, {"leve": 1}):
            bad = copy.deepcopy(self.fixture)
            bad["observations"][0]["probabilities"] = value
            with self.subTest(value=value), self.assertRaises(ContractError):
                self.validate(bad)

    def test_duplicate_unknown_and_missing_cases(self):
        for operation in ("duplicate", "unknown", "missing"):
            bad = copy.deepcopy(self.fixture)
            if operation == "duplicate":
                bad["observations"][1]["case_id"] = "pt-01"
            elif operation == "unknown":
                bad["observations"][1]["case_id"] = "pt-99"
            else:
                bad["observations"].pop()
            with self.subTest(operation=operation), self.assertRaises(ContractError):
                self.validate(bad)

    def test_provenance_mismatch(self):
        for field in ("corpus_sha256", "questions_sha256"):
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.validate({**self.fixture, field: "0" * 64})

    def test_option_order_changes_identity_and_refuses_old_observation(self):
        self.questions["option_order"] = [1, 0, 2, 3]
        changed = study.questions_hash(self.questions)
        self.assertNotEqual(changed, self.qsha)
        with self.assertRaises(ContractError):
            study.validate_observations(self.fixture, self.corpus["cases"], self.corpus_sha, changed)

    def test_instructions_change_identity(self):
        self.questions["instructions"] += " Another question."
        self.assertNotEqual(study.questions_hash(self.questions), self.qsha)

    def test_probability_indices_are_canonical_not_presentation_order(self):
        self.questions["option_order"] = [1, 0, 2, 3]
        self.fixture["questions_sha256"] = study.questions_hash(self.questions)
        records = study.validate_observations(self.fixture, self.corpus["cases"], self.corpus_sha,
                                              self.fixture["questions_sha256"])
        row = study.compare_case(self.corpus["cases"][0], records["pt-01"], 0.85)
        self.assertEqual(row["candidate_tier"], 0)

    def test_code_hashes_identify_baseline_and_protocol(self):
        provenance = study.run_study()["provenance"]
        self.assertEqual(provenance["study_code_sha256"],
                         hashlib.sha256((STUDY / "study.py").read_bytes()).hexdigest())
        for name in ("contracts.py", "policy.py", "vendor/jev_policy.py"):
            self.assertEqual(provenance["baseline_code_sha256"][name],
                             hashlib.sha256((study.ROOT / "radar_router" / name).read_bytes()).hexdigest())

    def test_invalid_orders_and_labels(self):
        for order in ([True, 1, 2, 3], [0, 0, 2, 3], [0, 1, 2], "0,1,2,3"):
            with self.subTest(order=order), self.assertRaises(ContractError):
                study.questions_hash({**self.questions, "option_order": order})
        with self.assertRaises(ContractError):
            study.questions_hash({**self.questions, "labels": list(reversed(study.TIERS))})

    def test_not_run_cannot_carry_a_prediction(self):
        bad = copy.deepcopy(self.fixture)
        bad["observations"][0]["status"] = "not_run"
        with self.assertRaises(ContractError):
            self.validate(bad)

    def test_boolean_status_and_truncation(self):
        for field, value in (("status", True), ("abstention", []), ("truncated", "false")):
            bad = copy.deepcopy(self.fixture)
            bad["observations"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.validate(bad)

    def test_duplicate_json_keys_and_nonfinite_constants(self):
        for raw in (b'{"source":1,"source":2}', b'{"p":NaN}', b'{"p":Infinity}', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                study.parse_json(raw)

    def test_corpus_bounds_and_schema(self):
        for operation in ("extra", "duplicate", "long", "bool", "tag", "split", "count"):
            bad = copy.deepcopy(self.corpus)
            item = bad["cases"][0]
            if operation == "extra":
                item["endpoint"] = "PRIVATE_SENTINEL"
            elif operation == "duplicate":
                bad["cases"][1]["id"] = item["id"]
            elif operation == "long":
                item["text"] = "é" * 4097
            elif operation == "bool":
                item["trusted"]["minimum_tier"] = True
            elif operation == "tag":
                item["tags"] = ["arbitrary-tool"]
            elif operation == "split":
                item["split"] = "production"
            else:
                bad["cases"] *= 3
            with self.subTest(operation=operation), self.assertRaises(ContractError):
                study.validate_corpus(bad)

    def test_artifact_tamper_and_symlink_rejected(self):
        for name in study.FILES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                for source in (*study.FILES, "manifest.json"):
                    shutil.copyfile(STUDY / source, directory / source)
                with (directory / name).open("ab") as stream:
                    stream.write(b" ")
                with self.assertRaisesRegex(ContractError, "artifact_changed"):
                    study.load_bundle(directory)
                (directory / name).unlink()
                (directory / name).symlink_to(STUDY / name)
                with self.assertRaisesRegex(ContractError, "symlink"):
                    study.load_bundle(directory)

    def test_file_size_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "manifest.json").write_bytes(b" " * (study.MAX_BYTES + 1))
            with self.assertRaises(ContractError):
                study.load_bundle(path)

    def test_huge_threshold_is_a_contract_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            manifest = json.loads((STUDY / "manifest.json").read_text())
            manifest["candidate_min_probability"] = 10 ** 1000
            (path / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaises(ContractError):
                study.load_bundle(path)

    def test_unexpected_overflow_is_sanitized_by_cli(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["study.py"]), redirect_stderr(output):
            with patch.object(study, "run_study", side_effect=OverflowError("PRIVATE_SENTINEL")):
                self.assertEqual(study.main(), 2)
        self.assertEqual(json.loads(output.getvalue())["error"], "invalid_study")
        self.assertNotIn("PRIVATE_SENTINEL", output.getvalue())

    def test_baseline_annotation_mismatch_fails(self):
        case = copy.deepcopy(self.corpus["cases"][0])
        case["expected"]["tier"] = 3
        with self.assertRaisesRegex(ContractError, "baseline_expectation"):
            study.compare_case(case, self.fixture["observations"][0], 0.85)

    def test_high_confidence_error_does_not_replace_baseline(self):
        rows = {x["id"]: x for x in study.run_study()["cases"]}
        row = rows["pt-08"]
        self.assertEqual(row["candidate_tier"], 0)
        self.assertGreater(row["answer_confidence"], 0.85)
        self.assertTrue(row["critical_underroute"])
        self.assertEqual(row["gate"], "trusted_review")
        self.assertEqual(row["baseline"]["tier"], 3)
        self.assertTrue(row["baseline"]["review_required"])
        self.assertEqual(row["effective_source"], "baseline")

    def test_uncertainty_context_and_floors(self):
        rows = {x["id"]: x for x in study.run_study()["cases"]}
        expected = {"pt-03": "low_probability", "pt-06": "continuation_floor",
                    "pt-10": "abstained", "pt-11": "trusted_floor",
                    "pt-12": "incomplete_context", "pt-14": "not_run", "pt-15": "unevaluated"}
        for case, gate in expected.items():
            with self.subTest(case=case):
                self.assertEqual(rows[case]["gate"], gate)
                self.assertEqual(rows[case]["effective_source"], "baseline")

    def test_empty_text_rejects_even_a_confident_observation(self):
        case = self.corpus["cases"][13]
        observation = {"case_id": case["id"], "status": "observed", "probabilities": [1, 0, 0, 0],
                       "abstention": "passed", "truncated": False}
        row = study.compare_case(case, observation, 0.85)
        self.assertEqual(row["gate"], "incomplete_context")
        self.assertEqual(row["effective_source"], "baseline")

    def test_no_network_model_imports_or_state_created(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network")):
            with patch.dict(sys.modules, {"laya": None, "torch": None, "huggingface_hub": None}):
                result = study.run_study()
        self.assertEqual(result["api_calls"], 0)
        self.assertNotIn("laya", sys.modules)
        self.assertFalse((STUDY / ".router-state").exists())

    def test_baseline_identical_before_and_after_experiment(self):
        inputs = [RouteInput.from_dict({"session": "synthetic-study", "turn": x["id"], **x["metadata"]})
                  for x in self.corpus["cases"]]
        scopes = [Scope("laya-study", **x["trusted"]) for x in self.corpus["cases"]]
        before = [decide(x, s).to_dict() for x, s in zip(inputs, scopes)]
        study.run_study()
        self.assertEqual(before, [decide(x, s).to_dict() for x, s in zip(inputs, scopes)])

    def test_report_does_not_echo_text_or_questions(self):
        raw = json.dumps(study.run_study(), ensure_ascii=False)
        for case in self.corpus["cases"]:
            if case["text"]:
                self.assertNotIn(case["text"], raw)
        self.assertNotIn(self.questions["instructions"], raw)
        self.assertNotIn('"trusted"', raw)

    def test_metrics_null_when_no_candidates_or_no_passed_cases(self):
        rows = [{"candidate_tier": None, "gate": "not_run", "critical_underroute": False}]
        m = study.metrics(rows)
        self.assertIsNone(m["fixture_agreement_with_baseline"])
        self.assertIsNone(m["selective_fixture_agreement"])
        self.assertEqual(m["fixture_coverage"], 0)

    def test_cli_result_and_error_are_sanitized(self):
        good = subprocess.run([sys.executable, str(STUDY / "study.py")], capture_output=True)
        self.assertEqual(good.returncode, 0)
        self.assertEqual(json.loads(good.stdout)["model_inference"], "not_run")
        bad = subprocess.run([sys.executable, str(STUDY / "study.py"), "PRIVATE_SENTINEL"], capture_output=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, b"")
        self.assertEqual(json.loads(bad.stderr)["error"], "invalid_study")
        self.assertNotIn(b"PRIVATE_SENTINEL", bad.stderr)


if __name__ == "__main__":
    unittest.main()
