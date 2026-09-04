#!/usr/bin/env python3
"""Compute deterministic structural metrics for EverySkill workflow DAGs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path


CONTRACT_MARKER = "<!-- workflow-contract -->"


def _catalog_entries(root: Path) -> list[tuple[str, str, Path]]:
    text = (root / "references" / "workflow-catalog.md").read_text(encoding="utf-8")
    pattern = re.compile(
        r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|[^|]*\|[^|]*\|\s*\[[^]]+\]\(([^)]+)\)\s*\|\s*$",
        re.MULTILINE,
    )
    return [(match.group(1), match.group(2), root / "references" / match.group(3)) for match in pattern.finditer(text)]


def _contract(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(CONTRACT_MARKER) + r"[ \t]*\r?\n[ \t]*```json[ \t]*\r?\n(.*?)\r?\n[ \t]*```",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"{path}: missing workflow contract")
    data = json.loads(match.group(1))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: workflow contract must be an object")
    return data


def analyze_graph(contract: dict[str, object]) -> dict[str, object]:
    tasks = contract.get("tasks")
    edges = contract.get("edges")
    if not isinstance(tasks, list) or not isinstance(edges, list):
        raise ValueError("tasks and edges must be arrays")
    task_ids = [task.get("id") for task in tasks if isinstance(task, dict)]
    if len(task_ids) != len(tasks) or any(not isinstance(task_id, str) or not task_id for task_id in task_ids):
        raise ValueError("every task needs a nonempty string id")
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("duplicate task id")
    known = set(task_ids)
    adjacency = {task_id: [] for task_id in task_ids}
    reverse = {task_id: [] for task_id in task_ids}
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("every edge must be an object")
        source, target = edge.get("from"), edge.get("to")
        if source not in known or target not in known:
            raise ValueError(f"dangling edge {source}->{target}")
        adjacency[source].append(target)
        reverse[target].append(source)
    for values in (*adjacency.values(), *reverse.values()):
        values.sort()

    indegree = {task_id: len(reverse[task_id]) for task_id in task_ids}
    ready = sorted(task_id for task_id, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for target in adjacency[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if len(order) != len(task_ids):
        raise ValueError("workflow graph contains a cycle")

    best: dict[str, tuple[str, ...]] = {}
    for node in order:
        candidates = [best[parent] + (node,) for parent in reverse[node]] or [(node,)]
        best[node] = min(candidates, key=lambda path: (-len(path), path))
    critical = min(best.values(), key=lambda path: (-len(path), path)) if best else ()

    reachable = {node: set() for node in task_ids}
    for node in reversed(order):
        for target in adjacency[node]:
            reachable[node].add(target)
            reachable[node].update(reachable[target])
    match_right: dict[str, str] = {}

    def augment(left: str, seen: set[str]) -> bool:
        for right in sorted(reachable[left]):
            if right in seen:
                continue
            seen.add(right)
            if right not in match_right or augment(match_right[right], seen):
                match_right[right] = left
                return True
        return False

    matching = sum(augment(left, set()) for left in sorted(task_ids))
    width = len(task_ids) - matching
    fan_out = {node: len(adjacency[node]) for node in sorted(task_ids)}
    fan_in = {node: len(reverse[node]) for node in sorted(task_ids)}
    regions = contract.get("topology_regions", [])
    region_counts = {
        region["id"]: len(region.get("branches", []))
        for region in regions
        if isinstance(region, dict) and isinstance(region.get("id"), str) and "branches" in region
    }
    worker_bounds = {
        region["id"]: region.get("max_workers")
        for region in regions
        if isinstance(region, dict) and region.get("primitive") == "ORCHESTRATOR_WORKERS"
    }
    candidates = []
    if len(task_ids) == 1:
        candidates.append("DIRECT_or_ROUTE_ONE")
    if len(critical) > 1:
        candidates.append("SEQUENTIAL")
    if width >= 2 and any(value >= 2 for value in fan_out.values()) and any(value >= 2 for value in fan_in.values()):
        candidates.append("PARALLEL_SECTION_candidate")
    return {
        "workflow_id": contract.get("id"),
        "version": str(contract.get("version")),
        "task_count": len(task_ids),
        "edge_count": len(edges),
        "roots": sorted(node for node in task_ids if not reverse[node]),
        "sinks": sorted(node for node in task_ids if not adjacency[node]),
        "topological_order": order,
        "structural_critical_path": {"task_ids": list(critical), "task_count": len(critical)},
        "maximum_parallel_width": width,
        "task_fan_out": fan_out,
        "task_fan_in": fan_in,
        "region_branch_counts": dict(sorted(region_counts.items())),
        "planned_worker_upper_bounds": dict(sorted(worker_bounds.items())),
        "structural_candidates": candidates,
        "evidence_required": [
            "immutable shared inputs",
            "no shared mutable state",
            "declared join and failure semantics",
        ] if "PARALLEL_SECTION_candidate" in candidates else [],
        "diagnostics": [],
    }


def analyze_repository(root: Path, workflow_id: str | None = None) -> list[dict[str, object]]:
    results = []
    entries = _catalog_entries(root)
    selected = [entry for entry in entries if workflow_id is None or entry[0] == workflow_id]
    if workflow_id is not None and not selected:
        raise ValueError(f"unknown workflow {workflow_id}")
    for catalog_id, version, path in selected:
        result = analyze_graph(_contract(path))
        if result["workflow_id"] != catalog_id or result["version"] != version:
            raise ValueError(f"catalog mismatch for {catalog_id}")
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workflow")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        results = analyze_repository(args.root.resolve(), args.workflow)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Topology analysis failed: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps({"workflows": results}, indent=2, sort_keys=True))
    else:
        for result in results:
            path = " -> ".join(result["structural_critical_path"]["task_ids"])
            print(f"{result['workflow_id']}@{result['version']}: tasks={result['task_count']} edges={result['edge_count']} width={result['maximum_parallel_width']} critical={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
