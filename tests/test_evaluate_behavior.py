from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_behavior.py"
CASES_PATH = ROOT / "references" / "behavior-evaluation-cases.json"
SPEC = importlib.util.spec_from_file_location("evaluate_behavior", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BehaviorEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        visible = sorted({
            skill
            for case in self.cases["cases"]
            for skill in case.get("required_visible_skills", [])
        } | {"named-document-skill"})
        self.results = {
            "schema_version": "1",
            "run": {
                "run_id": "test-run",
                "skill_revision": "test",
                "workflow_catalog_marker": "catalog-2",
                "host": "test-host",
                "model": "test-model",
                "sampling": {"temperature": 0},
                "capability_profile": "full",
                "visible_skills": visible,
            },
            "trials": [],
        }
        repetitions = self.cases["suite"]["default_repetitions"]
        for case in self.cases["cases"]:
            oracle = case["oracle"]
            for trial_index in range(1, case.get("repetitions", repetitions) + 1):
                self.results["trials"].append({
                    "case_id": case["id"],
                    "trial_index": trial_index,
                    "packet": {
                        "workflow_ids": copy.deepcopy(oracle["allowed_workflow_sets"][0]),
                        "topology": copy.deepcopy(oracle["allowed_topology_sets"][0]),
                        "route_status": oracle["route_status"],
                        "error_code": oracle["error_codes"][0],
                        "authority_status": oracle["authority_status"],
                        "fallback": oracle["fallback"],
                        "primary_owners": copy.deepcopy(oracle["allowed_primary_owner_sets"][0]),
                        "handoff_order": copy.deepcopy(oracle["allowed_handoff_orders"][0]),
                        "intent_count": max(1, len(oracle["allowed_primary_owner_sets"][0])),
                    },
                })

    def evaluate(self, results=None):
        return MODULE.evaluate(self.cases, results or self.results)

    def trial(self, case_id: str, trial_index: int = 1):
        return next(
            trial for trial in self.results["trials"]
            if trial["case_id"] == case_id and trial["trial_index"] == trial_index
        )

    def test_complete_matching_results_pass_with_deterministic_metrics(self):
        first, errors = self.evaluate()
        second, repeated_errors = self.evaluate(copy.deepcopy(self.results))
        self.assertEqual(errors, [])
        self.assertEqual(repeated_errors, [])
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["metrics"]["route_accuracy"], 1.0)
        self.assertEqual(first["metrics"]["stability"], 1.0)

    def test_wrong_owner_fails_route_accuracy(self):
        self.trial("eval-guided-explicit-feature")["packet"]["primary_owners"] = ["core"]
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        case = next(item for item in report["cases"] if item["case_id"] == "eval-guided-explicit-feature")
        self.assertLess(case["accuracy"], 1.0)

    def test_wrong_handoff_order_and_intent_count_are_incorrect(self):
        trial = self.trial("eval-combined-development-first")
        trial["packet"]["handoff_order"].reverse()
        trial["packet"]["intent_count"] = 999
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        case = next(item for item in report["cases"] if item["case_id"] == "eval-combined-development-first")
        self.assertLess(case["accuracy"], 1.0)

    def test_duplicate_decision_values_invalidate_packet(self):
        packet = self.results["trials"][0]["packet"]
        packet["topology"] *= 2
        packet["primary_owners"] *= 2
        self.trial("eval-guided-explicit-feature")["packet"]["handoff_order"] *= 2
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        self.assertFalse(report["gates"]["packet_validity"])

    def test_owner_alternatives_match_their_own_intent_count(self):
        case = next(case for case in self.cases["cases"] if case["id"] == "eval-direct")
        case["oracle"]["allowed_primary_owner_sets"] = [["core"], ["core", "helper"]]
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        direct = next(item for item in report["cases"] if item["case_id"] == "eval-direct")
        self.assertEqual(direct["accuracy"], 1.0)

    def test_unstable_trials_fail_stability_gate(self):
        for index, trial in enumerate(self.results["trials"]):
            trial["packet"]["primary_owners"] = [f"owner-{index}"]
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        self.assertFalse(report["gates"]["stability"])

    def test_missing_trial_fails_packet_validity(self):
        self.results["trials"].pop()
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        self.assertFalse(report["gates"]["packet_validity"])

    def test_over_orchestration_fails_gate(self):
        for trial in self.results["trials"]:
            if "ORCHESTRATOR_WORKERS" not in trial["packet"]["topology"]:
                trial["packet"]["topology"].append("ORCHESTRATOR_WORKERS")
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        self.assertFalse(report["gates"]["over_orchestration_rate"])

    def test_safety_error_code_failure_fails_safety_gate(self):
        self.trial("eval-missing-authority")["packet"]["error_code"] = "NONE"
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        self.assertFalse(report["gates"]["safety_pass_rate"])

    def test_malformed_packet_is_reported_without_crash(self):
        del self.results["trials"][0]["packet"]["topology"]
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        self.assertFalse(report["gates"]["packet_validity"])

    def test_missing_visible_skill_marks_cases_unrun(self):
        self.results["run"]["visible_skills"] = ["named-document-skill"]
        report, errors = self.evaluate()
        self.assertEqual(errors, [])
        self.assertGreater(report["unrun_cases"], 0)
        unrun = [case for case in report["cases"] if case["status"] == "UNRUN"]
        self.assertTrue(all(case["reason"] == "missing_capability" for case in unrun))

    def test_invalid_case_suite_is_rejected(self):
        del self.cases["cases"][0]["oracle"]["error_codes"]
        errors = MODULE.validate_case_suite(self.cases)
        self.assertTrue(any("oracle missing fields" in error for error in errors))

    def test_invalid_run_metadata_is_rejected(self):
        self.results["run"]["host"] = ""
        self.results["run"]["sampling"] = None
        self.results["run"]["workflow_catalog_marker"] = "catalog-stale"
        report, errors = self.evaluate()
        self.assertIsNone(report)
        self.assertTrue(any("host must be nonempty" in error for error in errors))
        self.assertTrue(any("sampling must be an object" in error for error in errors))
        self.assertTrue(any("does not match case catalog" in error for error in errors))

    def test_cli_exit_codes_distinguish_pass_fail_and_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_path = root / "results.json"
            results_path.write_text(json.dumps(self.results), encoding="utf-8")
            passed = subprocess.run(
                [sys.executable, str(SCRIPT), "--results", str(results_path)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(passed.returncode, 0, passed.stderr)

            self.trial("eval-forbidden-authority")["packet"]["error_code"] = "NONE"
            results_path.write_text(json.dumps(self.results), encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(SCRIPT), "--results", str(results_path)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(failed.returncode, 1, failed.stderr)

            results_path.write_text("{not json", encoding="utf-8")
            invalid = subprocess.run(
                [sys.executable, str(SCRIPT), "--results", str(results_path)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(invalid.returncode, 2)


if __name__ == "__main__":
    unittest.main()
