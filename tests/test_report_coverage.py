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
SCRIPT = ROOT / "scripts" / "report_coverage.py"


class CoverageReportTests(unittest.TestCase):
    def run_report(self, root: Path, output_format="json"):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--format", output_format],
            text=True, capture_output=True, check=False,
        )

    def temporary_repository(self):
        temporary = tempfile.TemporaryDirectory()
        destination = Path(temporary.name) / "repo"
        shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns(".git", ".idea", "__pycache__", "*.pyc"))
        return temporary, destination

    def test_json_report_is_deterministic_and_explicitly_structural(self):
        first = self.run_report(ROOT)
        second = self.run_report(ROOT)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        report = json.loads(first.stdout)
        self.assertEqual(report["claim"], "structural_coverage_only")
        self.assertEqual(report["fresh_agent_behavior"], "UNRUN")
        self.assertTrue(all(item["status"] == "covered" for item in report["required_coverage"].values()))
        self.assertIn("clarification_required", report["scenario_dimensions"]["route_status"])
        self.assertEqual(report["scenario_dimensions"]["route_status"]["clarification_required"], [])
        self.assertEqual(
            set(report["scenario_dimensions"]["host_mode"]),
            {"full", "serial_only", "single_agent", "no_human_gate"},
        )

    def test_missing_and_unknown_coverage_fail(self):
        temporary, root = self.temporary_repository()
        self.addCleanup(temporary.cleanup)
        path = root / "references" / "workflow-scenarios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["scenarios"][0]["coverage"] = ["unknown-tag"]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        result = self.run_report(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("coverage tags absent from validation policy", result.stderr)
        self.assertIn("missing required coverage", result.stderr)


if __name__ == "__main__":
    unittest.main()
