from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_workflows.py"
MARKER = "<!-- workflow-contract -->"


class WorkflowValidationTests(unittest.TestCase):
    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root)],
            text=True,
            capture_output=True,
            check=False,
        )

    def temporary_repository(self):
        temporary = tempfile.TemporaryDirectory()
        destination = Path(temporary.name) / "repo"
        shutil.copytree(
            ROOT,
            destination,
            ignore=shutil.ignore_patterns(".git", ".idea", "__pycache__", "*.pyc"),
        )
        return temporary, destination

    def mutate_contract(self, root: Path, relative_path: str, mutation) -> None:
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        prefix, remainder = text.split(MARKER, 1)
        fence, remainder = remainder.split("```json", 1)
        payload, suffix = remainder.split("```", 1)
        contract = json.loads(payload)
        mutation(contract)
        rendered = json.dumps(contract, indent=2, ensure_ascii=True)
        path.write_text(f"{prefix}{MARKER}{fence}```json\n{rendered}\n```{suffix}", encoding="utf-8")

    def assert_invalid(self, mutation, message: str) -> None:
        temporary, root = self.temporary_repository()
        self.addCleanup(temporary.cleanup)
        mutation(root)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)

    def test_clean_repository(self):
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Workflow validation passed.", result.stdout)

    def test_broken_skill_link_fails(self):
        def mutation(root: Path) -> None:
            path = root / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("references/workflow-diagnosis.md", "references/missing-diagnosis.md"), encoding="utf-8")

        self.assert_invalid(mutation, "not directly linked")

    def test_duplicate_workflow_id_fails(self):
        self.assert_invalid(
            lambda root: self.mutate_contract(
                root,
                "references/workflow-diagnosis.md",
                lambda contract: contract.__setitem__("id", "software-change"),
            ),
            "duplicate workflow ID",
        )

    def test_invalid_primitive_fails(self):
        self.assert_invalid(
            lambda root: self.mutate_contract(
                root,
                "references/workflow-software-change.md",
                lambda contract: contract.__setitem__("topology", "SEQUENTIAL(FAN_OUT)"),
            ),
            "invalid topology",
        )

    def test_invalid_controller_fails(self):
        self.assert_invalid(
            lambda root: self.mutate_contract(
                root,
                "references/workflow-software-change.md",
                lambda contract: contract.__setitem__("controller", "unbounded_magic"),
            ),
            "controller must be one of",
        )

    def test_malformed_topology_fails(self):
        self.assert_invalid(
            lambda root: self.mutate_contract(
                root,
                "references/workflow-software-change.md",
                lambda contract: contract.__setitem__("topology", "SEQUENTIAL(,PARALLEL_SECTION,,REVIEW_LOOP,)"),
            ),
            "invalid topology",
        )

    def test_dangling_edge_fails(self):
        def change(contract):
            contract["edges"][0]["to"] = "missing_task"

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "dangling edge",
        )

    def test_cycle_fails(self):
        def change(contract):
            contract["tasks"][0]["dependencies"] = ["report"]
            contract["edges"].append({"from": "report", "to": "scope", "kind": "control"})

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "contains a cycle",
        )

    def test_over_budget_cap_fails(self):
        def change(contract):
            contract["budget"]["max_workers"] = 5

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "exceeds limit 4",
        )

    def test_malformed_scenario_fails(self):
        def mutation(root: Path) -> None:
            (root / "references" / "workflow-scenarios.json").write_text("{not json", encoding="utf-8")

        self.assert_invalid(mutation, "malformed scenario JSON")

    def test_mismatched_scenario_reference_fails(self):
        def mutation(root: Path) -> None:
            path = root / "references" / "workflow-scenarios.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            scenario = next(item for item in data["scenarios"] if item["id"] == "software-change-positive")
            scenario["expected"]["references"] = ["references/workflow-diagnosis.md"]
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assert_invalid(mutation, "expected references do not correspond to workflow_ids")


if __name__ == "__main__":
    unittest.main()
