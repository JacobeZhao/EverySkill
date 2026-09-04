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
ADVANCED_MARKER = "<!-- advanced-topology-examples -->"
COMPOSITION_MARKER = "<!-- workflow-composition-examples -->"


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

    def mutate_marked_json(self, root: Path, relative_path: str, marker: str, mutation) -> None:
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        prefix, remainder = text.split(marker, 1)
        fence, remainder = remainder.split("```json", 1)
        payload, suffix = remainder.split("```", 1)
        data = json.loads(payload)
        mutation(data)
        rendered = json.dumps(data, indent=2, ensure_ascii=True)
        path.write_text(f"{prefix}{marker}{fence}```json\n{rendered}\n```{suffix}", encoding="utf-8")

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

    def test_non_string_contract_enums_fail_cleanly(self):
        cases = [
            (
                lambda contract: contract.__setitem__("controller", {}),
                "controller must be one of",
            ),
            (
                lambda contract: contract["edges"][0].__setitem__("kind", {}),
                "kind must be one of",
            ),
            (
                lambda contract: contract["topology_regions"][0].__setitem__("primitive", {}),
                "has an invalid primitive",
            ),
            (
                lambda contract: next(
                    region for region in contract["topology_regions"] if region["primitive"] == "PARALLEL_SECTION"
                ).__setitem__("join_mode", {}),
                "join_mode must be one of",
            ),
        ]
        for mutation, message in cases:
            with self.subTest(message=message):
                self.assert_invalid(
                    lambda root, mutation=mutation: self.mutate_contract(
                        root, "references/workflow-software-change.md", mutation
                    ),
                    message,
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

    def test_invalid_edge_kind_fails(self):
        def change(contract):
            contract["edges"][0]["kind"] = "message"

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "kind must be one of",
        )

    def test_missing_topology_region_fails(self):
        def change(contract):
            contract["topology_regions"] = [
                region for region in contract["topology_regions"] if region["primitive"] != "REVIEW_LOOP"
            ]

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "topology primitives missing regions: REVIEW_LOOP",
        )

    def test_unknown_parallel_join_fails(self):
        def change(contract):
            region = next(item for item in contract["topology_regions"] if item["primitive"] == "PARALLEL_SECTION")
            region["join_task"] = "missing_task"

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "has an unknown join_task",
        )

    def test_parallel_branch_count_must_fit_workflow_budget(self):
        def change(contract):
            region = next(item for item in contract["topology_regions"] if item["primitive"] == "PARALLEL_SECTION")
            contract["budget"]["max_parallel_branches"] = len(region["branches"]) - 1

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "branch count exceeds the workflow parallel budget",
        )

    def test_review_exit_must_be_outside_region(self):
        def change(contract):
            region = next(item for item in contract["topology_regions"] if item["primitive"] == "REVIEW_LOOP")
            region["exit_task"] = region["task_ids"][-1]

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "exit_task must be outside the review region",
        )

    def test_human_gate_requires_activation_condition(self):
        def change(contract):
            region = next(item for item in contract["topology_regions"] if item["primitive"] == "HUMAN_GATE")
            del region["activation_condition"]

        self.assert_invalid(
            lambda root: self.mutate_contract(root, "references/workflow-software-change.md", change),
            "must declare activation_condition",
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

    def test_missing_scenario_decision_fails(self):
        def mutation(root: Path) -> None:
            path = root / "references" / "workflow-scenarios.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            del data["scenarios"][0]["expected"]["decision"]
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assert_invalid(mutation, "expected missing fields: decision")

    def test_invalid_scenario_authority_fails(self):
        def mutation(root: Path) -> None:
            path = root / "references" / "workflow-scenarios.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["scenarios"][0]["expected"]["decision"]["authority_status"] = "granted_by_router"
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assert_invalid(mutation, "expected.decision.authority_status is invalid")

    def test_routed_scenario_topology_must_match_workflow(self):
        def mutation(root: Path) -> None:
            path = root / "references" / "workflow-scenarios.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            scenario = next(item for item in data["scenarios"] if item["id"] == "software-change-positive")
            scenario["expected"]["topology"] = ["DIRECT"]
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assert_invalid(mutation, "expected.topology does not match the selected workflow topology")

    def test_invalid_host_mode_fails(self):
        def mutation(root: Path) -> None:
            path = root / "references" / "workflow-scenarios.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["scenarios"][0]["expected"]["decision"]["host_mode"] = "telepathic"
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assert_invalid(mutation, "expected.decision.host_mode is invalid")

    def test_non_string_scenario_enums_fail_cleanly(self):
        cases = [
            ("status", "expected.status is not a known route status"),
            ("authority_status", "expected.decision.authority_status is invalid"),
            ("host_mode", "expected.decision.host_mode is invalid"),
        ]
        for field, message in cases:
            def mutation(root: Path, field=field) -> None:
                path = root / "references" / "workflow-scenarios.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                expected = data["scenarios"][0]["expected"]
                if field == "status":
                    expected[field] = {}
                else:
                    expected["decision"][field] = {}
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")

            with self.subTest(field=field):
                self.assert_invalid(mutation, message)

    def test_quorum_requires_oracle_and_valid_threshold(self):
        def remove_oracle(data):
            region = next(
                region for example in data["examples"] for region in example["topology_regions"]
                if region.get("join_mode") == "quorum"
            )
            del region["acceptance_oracle"]

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/advanced-topology-examples.md", ADVANCED_MARKER, remove_oracle
            ),
            "quorum must declare acceptance_oracle",
        )

        def exceed_branches(data):
            region = next(
                region for example in data["examples"] for region in example["topology_regions"]
                if region.get("join_mode") == "quorum"
            )
            region["min_acceptable"] = len(region["branches"]) + 1

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/advanced-topology-examples.md", ADVANCED_MARKER, exceed_branches
            ),
            "quorum min_acceptable must be within branch count",
        )

    def test_first_acceptable_requires_safe_cancellation(self):
        def mutation(data):
            region = next(
                region for example in data["examples"] for region in example["topology_regions"]
                if region.get("join_mode") == "first_acceptable"
            )
            del region["disposable_or_cancellation_evidence"]

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/advanced-topology-examples.md", ADVANCED_MARKER, mutation
            ),
            "cancellation requires disposable_or_cancellation_evidence",
        )

    def test_dynamic_workers_are_depth_one_and_within_budget(self):
        def mutation(data):
            region = next(
                region for example in data["examples"] for region in example["topology_regions"]
                if region["primitive"] == "ORCHESTRATOR_WORKERS"
            )
            region["max_depth"] = 2

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/advanced-topology-examples.md", ADVANCED_MARKER, mutation
            ),
            "max_depth must be exactly 1",
        )

    def test_dynamic_workers_require_known_join_mode_and_complete_template(self):
        def mutation(data):
            region = next(
                region for example in data["examples"] for region in example["topology_regions"]
                if region["primitive"] == "ORCHESTRATOR_WORKERS"
            )
            region["join_mode"] = "banana"
            region["worker_template"]["objective"] = ""

        temporary, root = self.temporary_repository()
        self.addCleanup(temporary.cleanup)
        self.mutate_marked_json(
            root, "references/advanced-topology-examples.md", ADVANCED_MARKER, mutation
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("join_mode must be one of", result.stderr)
        self.assertIn("worker_template objective must be nonempty", result.stderr)

    def test_dynamic_worker_advanced_joins_require_their_semantics(self):
        def mutation(data):
            region = next(
                region for example in data["examples"] for region in example["topology_regions"]
                if region["primitive"] == "ORCHESTRATOR_WORKERS"
            )
            region["join_mode"] = "quorum"

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/advanced-topology-examples.md", ADVANCED_MARKER, mutation
            ),
            "quorum must declare acceptance_oracle",
        )

    def test_handoff_requires_known_target_and_context(self):
        def mutation(data):
            region = next(
                region for example in data["examples"] for region in example["topology_regions"]
                if region["primitive"] == "HANDOFF"
            )
            region["target_task"] = "missing"

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/advanced-topology-examples.md", ADVANCED_MARKER, mutation
            ),
            "unknown target_task",
        )

    def test_handoff_owners_must_match_tasks_and_transfer(self):
        def mutation(data):
            region = next(
                region for example in data["examples"] for region in example["topology_regions"]
                if region["primitive"] == "HANDOFF"
            )
            region["source_owner"] = "selected-skill"

        temporary, root = self.temporary_repository()
        self.addCleanup(temporary.cleanup)
        self.mutate_marked_json(
            root, "references/advanced-topology-examples.md", ADVANCED_MARKER, mutation
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("source_owner must match source_task owner", result.stderr)
        self.assertIn("must transfer ownership to a different owner", result.stderr)

    def test_composition_rejects_version_drift_and_dangling_edges(self):
        def wrong_version(data):
            data["examples"][0]["instances"][0]["workflow_version"] = "999"

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/workflow-composition.md", COMPOSITION_MARKER, wrong_version
            ),
            "workflow version does not match catalog",
        )

        def dangling(data):
            data["examples"][0]["edges"][0]["to"] = "missing"

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/workflow-composition.md", COMPOSITION_MARKER, dangling
            ),
            "dangling composition edge",
        )

    def test_composition_rejects_cycles_and_missing_acceptance(self):
        def cycle(data):
            example = data["examples"][0]
            example["edges"].append({
                "from": "publication.output",
                "to": "implementation.output",
                "kind": "control",
            })

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/workflow-composition.md", COMPOSITION_MARKER, cycle
            ),
            "composition graph contains a cycle",
        )

        def missing_acceptance(data):
            del data["examples"][0]["instances"][0]["acceptance_oracle"]

        self.assert_invalid(
            lambda root: self.mutate_marked_json(
                root, "references/workflow-composition.md", COMPOSITION_MARKER, missing_acceptance
            ),
            "independent acceptance_oracle",
        )

    def test_composition_requires_used_instances_and_cross_instance_edge(self):
        def mutation(data):
            example = data["examples"][0]
            for task in example["tasks"]:
                task["instance_id"] = "implementation"
            example["edges"] = [example["edges"][1]]

        temporary, root = self.temporary_repository()
        self.addCleanup(temporary.cleanup)
        self.mutate_marked_json(
            root, "references/workflow-composition.md", COMPOSITION_MARKER, mutation
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("instances without tasks", result.stderr)
        self.assertIn("requires at least one cross-instance edge", result.stderr)

    def test_behavior_cases_track_catalog_and_known_workflows(self):
        def mutation(root: Path) -> None:
            path = root / "references" / "behavior-evaluation-cases.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["catalog_version"] = "stale"
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assert_invalid(mutation, "catalog_version does not match workflow catalog")

    def test_workflow_case_links_require_matching_scenario_kind(self):
        def mutation(root: Path) -> None:
            path = root / "references" / "workflow-scenarios.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            scenario = next(item for item in data["scenarios"] if "positive_for" in item)
            scenario["kind"] = "coverage"
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assert_invalid(mutation, "positive_for requires kind='positive'")

    def test_invalid_human_review_example_fails(self):
        def mutation(root: Path) -> None:
            path = root / "references" / "behavior-evaluation-reviews.example.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["reviews"][0]["overall"] = "fail"
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assert_invalid(mutation, "overall must equal derived outcome pass")


if __name__ == "__main__":
    unittest.main()
