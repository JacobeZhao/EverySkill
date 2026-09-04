from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_workflows.py"
LOADER_PATH = ROOT / "scripts" / "validation_policy.py"
SPEC = importlib.util.spec_from_file_location("validation_policy_test", LOADER_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidationPolicyTests(unittest.TestCase):
    def temporary_repository(self):
        temporary = tempfile.TemporaryDirectory()
        destination = Path(temporary.name) / "repo"
        shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns(".git", ".idea", "__pycache__", "*.pyc"))
        return temporary, destination

    def run_validator(self, root: Path):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root)],
            text=True, capture_output=True, check=False,
        )

    def mutate_policy(self, root: Path, mutation):
        path = root / "references" / "validation-policy.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        mutation(data)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def test_missing_malformed_and_unknown_policy_fail_closed(self):
        for mutation in (
            lambda root: (root / "references" / "validation-policy.json").unlink(),
            lambda root: (root / "references" / "validation-policy.json").write_text("{bad", encoding="utf-8"),
            lambda root: self.mutate_policy(root, lambda data: data.__setitem__("schema_version", "999")),
        ):
            temporary, root = self.temporary_repository()
            self.addCleanup(temporary.cleanup)
            mutation(root)
            result = self.run_validator(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("validation policy", result.stderr.lower())

    def test_policy_budget_and_coverage_changes_take_effect(self):
        temporary, root = self.temporary_repository()
        self.addCleanup(temporary.cleanup)
        self.mutate_policy(root, lambda data: data["budgets"]["required_caps"]["max_workers"].__setitem__("maximum", 1))
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeds limit 1", result.stderr)

        temporary2, root2 = self.temporary_repository()
        self.addCleanup(temporary2.cleanup)
        self.mutate_policy(root2, lambda data: data["scenarios"]["required_coverage"].append("new-required-tag"))
        result = self.run_validator(root2)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required coverage: new-required-tag", result.stderr)

    def test_policy_rejects_duplicates_and_unsafe_worker_depth(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            data = json.loads((ROOT / "references" / "validation-policy.json").read_text(encoding="utf-8"))
            data["topology"]["primitives"].append("DIRECT")
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicates"):
                MODULE.load_validation_policy(path)
            data["topology"]["primitives"].pop()
            data["topology"]["orchestrator_workers"]["max_depth"] = 2
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "max_depth"):
                MODULE.load_validation_policy(path)

    def test_policy_cannot_claim_unimplemented_topology_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            data = json.loads((ROOT / "references" / "validation-policy.json").read_text(encoding="utf-8"))
            data["topology"]["primitives"].append("MAGIC_SWARM")
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unimplemented semantic handler"):
                MODULE.load_validation_policy(path)

    def test_policy_rejects_nonfinite_budgets_unknown_internal_schemas_and_branch_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            source = (ROOT / "references" / "validation-policy.json").read_text(encoding="utf-8")
            path.write_text(source.replace('"maximum": 4', '"maximum": NaN', 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-standard JSON numeric constant"):
                MODULE.load_validation_policy(path)

            for mutation, message in (
                (lambda data: data["scenarios"].__setitem__("schema_version", "999"), "scenarios.schema_version"),
                (lambda data: data["behavior_evaluation"].__setitem__("schema_version", "999"), "behavior_evaluation.schema_version"),
                (lambda data: data["topology"]["remaining_branch_policies"].append("continue_unchecked"), "unimplemented semantic handler"),
            ):
                data = json.loads(source)
                mutation(data)
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    MODULE.load_validation_policy(path)

    def test_workflow_nonfinite_budget_fails_validation(self):
        temporary, root = self.temporary_repository()
        self.addCleanup(temporary.cleanup)
        path = root / "references" / "workflow-software-change.md"
        content = path.read_text(encoding="utf-8")
        path.write_text(content.replace('"max_workers": 3', '"max_workers": NaN', 1), encoding="utf-8")
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("budget cap max_workers must be numeric", result.stderr)


if __name__ == "__main__":
    unittest.main()
