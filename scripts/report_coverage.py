#!/usr/bin/env python3
"""Report deterministic structural coverage without claiming Agent behavior quality."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from validate_workflows import ADVANCED_MARKER, _extract_contract, _extract_marked_json, _parse_catalog, _parse_topology, validate
from validation_policy import load_validation_policy


def build_report(root: Path) -> tuple[dict[str, object] | None, list[str]]:
    errors = validate(root)
    if errors:
        return None, errors
    policy = load_validation_policy(root / "references" / "validation-policy.json")
    _, rows = _parse_catalog(root / "references" / "workflow-catalog.md", [])
    workflow_ids = [row["id"] for row in rows]
    scenarios = json.loads((root / "references" / "workflow-scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    behavior_cases = json.loads((root / "references" / "behavior-evaluation-cases.json").read_text(encoding="utf-8"))["cases"]
    marked_errors: list[str] = []
    advanced = _extract_marked_json(
        root / "references" / "advanced-topology-examples.md", root, ADVANCED_MARKER, marked_errors
    )
    if marked_errors or advanced is None:
        return None, marked_errors

    workflow_cases = {}
    for workflow_id in workflow_ids:
        workflow_cases[workflow_id] = {
            "positive": sorted(item["id"] for item in scenarios if item.get("positive_for") == workflow_id),
            "near_miss": sorted(item["id"] for item in scenarios if item.get("near_miss_for") == workflow_id),
        }
    required_tags = policy["scenarios"]["required_coverage"]
    coverage_tags = {
        tag: sorted(item["id"] for item in scenarios if tag in item.get("coverage", []))
        for tag in required_tags
    }
    primitive_map = {primitive: {"workflows": [], "advanced_examples": [], "scenarios": []} for primitive in policy["topology"]["primitives"]}
    for row in rows:
        extraction_errors: list[str] = []
        contract = _extract_contract(root / "references" / row["reference"], root, extraction_errors)
        if extraction_errors or contract is None:
            return None, extraction_errors
        for primitive in _parse_topology(contract["topology"]):
            primitive_map[primitive]["workflows"].append(row["id"])
    for example in advanced["examples"]:
        for primitive in primitive_map:
            if re.search(rf"\b{re.escape(primitive)}\b", example.get("topology", "")):
                primitive_map[primitive]["advanced_examples"].append(example["id"])
    for scenario in scenarios:
        for primitive in scenario["expected"]["topology"]:
            primitive_map[primitive]["scenarios"].append(scenario["id"])
    for mapping in primitive_map.values():
        for values in mapping.values():
            values.sort()
    advanced_required = set(policy["topology"]["advanced_example_required_primitives"])
    for primitive, mapping in primitive_map.items():
        mapping["status"] = {
            "workflow": "covered" if mapping["workflows"] else "not_applicable",
            "advanced_example": "covered" if mapping["advanced_examples"] else ("missing" if primitive in advanced_required else "not_applicable"),
            "scenario": "covered" if mapping["scenarios"] else "not_applicable",
        }

    routing = policy["routing"]
    dimensions = {
        "route_status": {value: [] for value in routing["statuses"]},
        "authority_status": {value: [] for value in routing["authority_statuses"]},
        "host_mode": {value: [] for value in routing["host_fallbacks"]},
        "fallback": {
            value: []
            for values in routing["host_fallbacks"].values()
            for value in values
        },
    }
    for scenario in scenarios:
        expected = scenario["expected"]
        decision = expected["decision"]
        values = {
            "route_status": expected["status"],
            "authority_status": decision["authority_status"],
            "host_mode": decision["host_mode"],
            "fallback": decision["fallback"],
        }
        for dimension, value in values.items():
            dimensions[dimension].setdefault(value, []).append(scenario["id"])
    for mapping in dimensions.values():
        for values in mapping.values():
            values.sort()

    owners: dict[str, list[str]] = {}
    handoffs: dict[str, list[str]] = {}
    safety = []
    for case in behavior_cases:
        oracle = case["oracle"]
        for option in oracle["allowed_primary_owner_sets"]:
            for owner in option:
                owners.setdefault(owner, []).append(case["id"])
        for order in oracle["allowed_handoff_orders"]:
            if order:
                handoffs.setdefault(" -> ".join(order), []).append(case["id"])
        if oracle["safety_critical"]:
            safety.append(case["id"])
    for mapping in (owners, handoffs):
        for values in mapping.values():
            values.sort()
    return {
        "claim": "structural_coverage_only",
        "fresh_agent_behavior": "UNRUN",
        "workflows": workflow_cases,
        "required_coverage": {
            tag: {"status": "covered" if cases else "missing", "cases": cases}
            for tag, cases in coverage_tags.items()
        },
        "topology_primitives": primitive_map,
        "scenario_dimensions": dimensions,
        "behavior_cases": {
            "owners": dict(sorted(owners.items())),
            "handoff_orders": dict(sorted(handoffs.items())),
            "safety_critical": sorted(safety),
        },
    }, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    report, errors = build_report(args.root.resolve())
    if errors:
        print("Coverage report failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Structural coverage report (fresh-agent behavior: UNRUN)")
        for workflow_id, cases in report["workflows"].items():
            print(f"{workflow_id}: positive={len(cases['positive'])} near_miss={len(cases['near_miss'])}")
        covered = sum(item["status"] == "covered" for item in report["required_coverage"].values())
        print(f"required coverage: {covered}/{len(report['required_coverage'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
