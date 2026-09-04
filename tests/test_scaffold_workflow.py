from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scaffold_workflow.py"


class ScaffoldWorkflowTests(unittest.TestCase):
    def run_script(self, root: Path, *args: str):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), *args],
            text=True, capture_output=True, check=False,
        )

    def test_dry_run_is_deterministic_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = ("--id", "sample-flow", "--title", "Sample Flow", "--output", "references/workflow-sample-flow.md", "--dry-run")
            first = self.run_script(root, *args)
            second = self.run_script(root, *args)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertFalse((root / "references" / "workflow-sample-flow.md").exists())
            payload = re.search(r"```json\n(.*?)\n```", first.stdout, re.DOTALL)
            self.assertEqual(json.loads(payload.group(1))["topology"], "SEQUENTIAL")

    def test_create_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = ("--id", "sample-flow", "--title", "Sample Flow", "--output", "references/workflow-sample-flow.md")
            created = self.run_script(root, *args)
            refused = self.run_script(root, *args)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("already exists", refused.stderr)

    def test_invalid_id_and_outside_output_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = self.run_script(root, "--id", "Bad ID", "--title", "Bad", "--output", "bad.md")
            outside = self.run_script(root, "--id", "valid", "--title", "Valid", "--output", "../outside.md")
            self.assertNotEqual(invalid.returncode, 0)
            self.assertNotEqual(outside.returncode, 0)
            self.assertIn("inside the repository", outside.stderr)


if __name__ == "__main__":
    unittest.main()
