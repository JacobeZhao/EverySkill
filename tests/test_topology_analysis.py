from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "topology_analysis.py"
SPEC = importlib.util.spec_from_file_location("topology_analysis", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def contract(task_ids, edges):
    return {
        "id": "fixture", "version": "1",
        "tasks": [{"id": task_id} for task_id in task_ids],
        "edges": [{"from": source, "to": target} for source, target in edges],
        "topology_regions": [],
    }


class TopologyAnalysisTests(unittest.TestCase):
    def test_single_node(self):
        result = MODULE.analyze_graph(contract(["only"], []))
        self.assertEqual(result["maximum_parallel_width"], 1)
        self.assertEqual(result["structural_candidates"], ["DIRECT_or_ROUTE_ONE"])

    def test_chain_and_diamond_metrics(self):
        chain = MODULE.analyze_graph(contract(["a", "b", "c"], [("a", "b"), ("b", "c")]))
        self.assertEqual(chain["structural_critical_path"]["task_ids"], ["a", "b", "c"])
        self.assertEqual(chain["maximum_parallel_width"], 1)
        diamond = MODULE.analyze_graph(contract(["a", "b", "c", "d"], [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]))
        self.assertEqual(diamond["maximum_parallel_width"], 2)
        self.assertEqual(diamond["structural_critical_path"]["task_ids"], ["a", "b", "d"])
        self.assertIn("PARALLEL_SECTION_candidate", diamond["structural_candidates"])

    def test_exact_antichain_width_handles_cross_edges(self):
        graph = contract(["a", "b", "c", "d"], [("a", "c"), ("b", "c"), ("b", "d")])
        self.assertEqual(MODULE.analyze_graph(graph)["maximum_parallel_width"], 2)

    def test_invalid_graphs_fail(self):
        fixtures = [
            contract(["a", "a"], []),
            contract(["a"], [("a", "missing")]),
            contract(["a", "b"], [("a", "b"), ("b", "a")]),
        ]
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                with self.assertRaises(ValueError):
                    MODULE.analyze_graph(fixture)

    def test_all_repository_workflows_analyze(self):
        results = MODULE.analyze_repository(ROOT)
        self.assertEqual({item["workflow_id"] for item in results}, {"software-change", "diagnosis", "research-decision", "artifact-creation"})
        self.assertTrue(all(item["structural_critical_path"]["task_count"] >= 1 for item in results))

    def test_json_cli_is_deterministic(self):
        command = [sys.executable, str(SCRIPT), "--root", str(ROOT), "--format", "json"]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertIn("workflows", json.loads(first.stdout))


if __name__ == "__main__":
    unittest.main()
