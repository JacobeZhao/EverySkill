#!/usr/bin/env python3
"""Generate a conservative workflow Markdown skeleton without editing the catalog."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SLUG = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def render(workflow_id: str, version: str, title: str) -> str:
    contract = {
        "id": workflow_id,
        "version": version,
        "controller": "hybrid",
        "topology": "SEQUENTIAL",
        "tasks": [
            {"id": "frame", "objective": "Define the bounded outcome and acceptance criteria.", "owner": "coordinator", "required_output": "Approved task frame.", "dependencies": []},
            {"id": "produce", "objective": "Produce the requested result within the frame.", "owner": "worker", "required_output": "Candidate result with evidence.", "dependencies": ["frame"]},
            {"id": "verify", "objective": "Verify the candidate against the frame.", "owner": "coordinator", "required_output": "Accepted result or explicit failure.", "dependencies": ["produce"]},
        ],
        "edges": [
            {"from": "frame", "to": "produce", "kind": "context"},
            {"from": "produce", "to": "verify", "kind": "data"},
        ],
        "topology_regions": [{"id": "main", "primitive": "SEQUENTIAL", "task_ids": ["frame", "produce", "verify"]}],
        "join_policy": {"main": "Each dependent stage must settle successfully before the next starts."},
        "context_policy": {"coordinator": "Retain the canonical request.", "workers": "Receive only the approved frame."},
        "budget": {"max_workers": 1, "max_parallel_branches": 1, "max_delegation_depth": 1, "max_review_rounds": 0},
        "stop_conditions": ["Stop after accepted verification, explicit block, failure, or exhausted budget."],
        "failure_policy": {"stage_failure": "Stop dependent work and report the failed stage with evidence."},
        "verification": {"checks": ["Every output traces to a task and acceptance criterion."], "evaluator": "coordinator", "acceptance": "The verified result satisfies the approved frame."},
        "output": {"owner": "coordinator", "required_sections": ["result", "checks", "unresolved"], "completion_rule": "Distinguish accepted, blocked, and failed outcomes."},
    }
    payload = json.dumps(contract, indent=2, ensure_ascii=True)
    return f"# {title}\n\nDescribe the primary deliverable and exclusions here.\n\n<!-- workflow-contract -->\n```json\n{payload}\n```\n"


def resolve_output(root: Path, output: Path) -> Path:
    resolved_root = root.resolve()
    resolved = (resolved_root / output).resolve() if not output.is_absolute() else output.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("output must remain inside the repository root") from exc
    if resolved.suffix.lower() != ".md":
        raise ValueError("output must be a Markdown file")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--id", required=True)
    parser.add_argument("--version", default="1")
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not SLUG.fullmatch(args.id):
        print("Workflow scaffold failed: id must be a lowercase hyphenated slug", file=sys.stderr)
        return 1
    if not args.version.isdigit() or int(args.version) < 1:
        print("Workflow scaffold failed: version must be a positive integer", file=sys.stderr)
        return 1
    if not args.title.strip():
        print("Workflow scaffold failed: title must be nonempty", file=sys.stderr)
        return 1
    try:
        output = resolve_output(args.root, args.output)
    except ValueError as exc:
        print(f"Workflow scaffold failed: {exc}", file=sys.stderr)
        return 1
    content = render(args.id, args.version, args.title.strip())
    if args.dry_run:
        print(content, end="")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as destination:
            destination.write(content)
    except FileExistsError:
        print(f"Workflow scaffold failed: output already exists: {output}", file=sys.stderr)
        return 1
    print(f"Created {output}")
    print("Next: add a catalog row, positive and near-miss scenarios, and every triggered risk case.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
