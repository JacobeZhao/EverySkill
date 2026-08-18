#!/usr/bin/env python3
"""Validate EverySkill workflow contracts and their scenario fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path, PurePosixPath


REQUIRED_CONTRACT_FIELDS = {
    "id",
    "version",
    "controller",
    "topology",
    "tasks",
    "edges",
    "join_policy",
    "context_policy",
    "budget",
    "stop_conditions",
    "failure_policy",
    "verification",
    "output",
}
CANONICAL_PRIMITIVES = {
    "DIRECT",
    "ROUTE_ONE",
    "HANDOFF",
    "SEQUENTIAL",
    "PARALLEL_SECTION",
    "PARALLEL_SAMPLE",
    "ORCHESTRATOR_WORKERS",
    "REVIEW_LOOP",
    "HUMAN_GATE",
}
CONTROLLERS = {"code", "llm", "hybrid"}
ROUTE_STATUSES = {
    "core_direct",
    "routed",
    "clarification_required",
    "blocked",
    "failed",
}
BUDGET_LIMITS = {
    "max_workers": 4,
    "max_parallel_branches": 4,
    "max_delegation_depth": 2,
    "max_review_rounds": 2,
}
REQUIRED_COVERAGE = {
    "direct-fast-path",
    "route-one-fast-path",
    "diagnose-then-fix",
    "research-then-artifact",
    "software-plus-documentation",
    "two-distinct-deliverables-composition",
    "explicit-skill-dominance",
    "read-only-mode",
    "missing-capability",
    "worker-partial-failure",
    "budget-stop",
    "no-progress-stop",
    "missing-authority",
    "forbidden-authority",
    "stale-workflow-marker",
    "v1-incompatible",
    "v1-rebuild",
}
CONTRACT_MARKER = "<!-- workflow-contract -->"


def _parse_topology(value: str) -> set[str]:
    """Parse PRIMITIVE or PRIMITIVE(expr,...) and return used primitives."""
    position = 0
    tokens: set[str] = set()

    def skip_space() -> None:
        nonlocal position
        while position < len(value) and value[position].isspace():
            position += 1

    def parse_expression() -> None:
        nonlocal position
        skip_space()
        match = re.match(r"[A-Z][A-Z0-9_]*", value[position:])
        if not match:
            raise ValueError(f"expected primitive at offset {position}")
        primitive = match.group(0)
        if primitive not in CANONICAL_PRIMITIVES:
            raise ValueError(f"invalid topology primitive {primitive}")
        tokens.add(primitive)
        position += len(primitive)
        skip_space()
        if position >= len(value) or value[position] != "(":
            return
        position += 1
        parse_expression()
        skip_space()
        while position < len(value) and value[position] == ",":
            position += 1
            parse_expression()
            skip_space()
        if position >= len(value) or value[position] != ")":
            raise ValueError(f"expected ')' at offset {position}")
        position += 1

    parse_expression()
    skip_space()
    if position != len(value):
        raise ValueError(f"unexpected content at offset {position}")
    return tokens


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _nonempty(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def _parse_catalog(path: Path, errors: list[str]) -> tuple[str | None, list[dict[str, str]]]:
    label = path.as_posix()
    if not path.is_file():
        errors.append(f"{label}: missing workflow catalog")
        return None, []
    text = path.read_text(encoding="utf-8")
    version_match = re.search(r"^Catalog version:\s*`([^`]+)`\s*$", text, re.MULTILINE)
    if not version_match:
        errors.append(f"{label}: missing or malformed catalog version")
        version = None
    else:
        version = version_match.group(1)

    rows: list[dict[str, str]] = []
    row_pattern = re.compile(
        r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|([^|]*)\|([^|]*)\|\s*\[[^]]+\]\(([^)]+)\)\s*\|\s*$",
        re.MULTILINE,
    )
    for match in row_pattern.finditer(text):
        rows.append(
            {
                "id": match.group(1).strip(),
                "version": match.group(2).strip(),
                "outcome": match.group(3).strip(),
                "exclude": match.group(4).strip(),
                "reference": match.group(5).strip(),
            }
        )
    if not rows:
        errors.append(f"{label}: selection table contains no workflow rows")
    return version, rows


def _extract_contract(path: Path, root: Path, errors: list[str]) -> dict[str, object] | None:
    label = _relative(path, root)
    if not path.is_file():
        errors.append(f"{label}: catalog reference does not exist")
        return None
    text = path.read_text(encoding="utf-8")
    marker_count = text.count(CONTRACT_MARKER)
    if marker_count != 1:
        errors.append(f"{label}: expected exactly one workflow-contract marker, found {marker_count}")
        return None
    pattern = re.compile(
        re.escape(CONTRACT_MARKER) + r"[ \t]*\r?\n[ \t]*```json[ \t]*\r?\n(.*?)\r?\n[ \t]*```",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        errors.append(f"{label}: marker must be immediately followed by one fenced JSON contract")
        return None
    try:
        contract = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: malformed workflow contract JSON: {exc.msg} at line {exc.lineno}")
        return None
    if not isinstance(contract, dict):
        errors.append(f"{label}: workflow contract must be a JSON object")
        return None
    return contract


def _validate_graph(contract: dict[str, object], label: str, errors: list[str]) -> None:
    tasks = contract.get("tasks")
    edges = contract.get("edges")
    if not isinstance(tasks, list) or not tasks:
        errors.append(f"{label}: tasks must be a nonempty array")
        return
    if not isinstance(edges, list):
        errors.append(f"{label}: edges must be an array")
        return

    task_ids: list[str] = []
    dependencies: set[tuple[str, str]] = set()
    task_records_valid = True
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"{label}: task {index} must be an object")
            task_records_valid = False
            continue
        missing = {"id", "objective", "owner", "required_output", "dependencies"} - set(task)
        if missing:
            errors.append(f"{label}: task {index} missing fields: {', '.join(sorted(missing))}")
            task_records_valid = False
            continue
        task_id = task.get("id")
        deps = task.get("dependencies")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"{label}: task {index} has an invalid id")
            task_records_valid = False
            continue
        task_ids.append(task_id)
        for field in ("objective", "owner", "required_output"):
            if not isinstance(task.get(field), str) or not task[field].strip():
                errors.append(f"{label}: task {task_id} has an empty {field}")
        if not isinstance(deps, list) or any(not isinstance(dep, str) or not dep for dep in deps):
            errors.append(f"{label}: task {task_id} dependencies must be an array of task IDs")
            task_records_valid = False
            continue
        if len(deps) != len(set(deps)):
            errors.append(f"{label}: task {task_id} has duplicate dependencies")
        dependencies.update((dep, task_id) for dep in deps)

    if len(task_ids) != len(set(task_ids)):
        errors.append(f"{label}: duplicate task ID")
    known = set(task_ids)
    for source, target in dependencies:
        if source not in known:
            errors.append(f"{label}: task {target} has dangling dependency {source}")

    edge_pairs: set[tuple[str, str]] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"{label}: edge {index} must be an object")
            continue
        source, target = edge.get("from"), edge.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            errors.append(f"{label}: edge {index} must have string from/to endpoints")
            continue
        if source not in known or target not in known:
            errors.append(f"{label}: dangling edge {source}->{target}")
        pair = (source, target)
        if pair in edge_pairs:
            errors.append(f"{label}: duplicate edge {source}->{target}")
        edge_pairs.add(pair)
        if not isinstance(edge.get("kind"), str) or not edge["kind"].strip():
            errors.append(f"{label}: edge {source}->{target} has an empty kind")

    if dependencies != edge_pairs:
        missing_edges = dependencies - edge_pairs
        extra_edges = edge_pairs - dependencies
        if missing_edges:
            rendered = ", ".join(f"{a}->{b}" for a, b in sorted(missing_edges))
            errors.append(f"{label}: task dependencies missing matching edges: {rendered}")
        if extra_edges:
            rendered = ", ".join(f"{a}->{b}" for a, b in sorted(extra_edges))
            errors.append(f"{label}: edges missing matching task dependencies: {rendered}")

    if not task_records_valid or not known:
        return
    graph = {task_id: [] for task_id in known}
    indegree = {task_id: 0 for task_id in known}
    for source, target in edge_pairs:
        if source in known and target in known:
            graph[source].append(target)
            indegree[target] += 1
    roots = [task_id for task_id, degree in indegree.items() if degree == 0]
    if not roots:
        errors.append(f"{label}: graph must contain at least one root")
    reachable: set[str] = set()
    queue = deque(roots)
    while queue:
        node = queue.popleft()
        if node in reachable:
            continue
        reachable.add(node)
        queue.extend(graph[node])
    unreachable = known - reachable
    if unreachable:
        errors.append(f"{label}: tasks are unreachable from roots: {', '.join(sorted(unreachable))}")

    remaining = indegree.copy()
    queue = deque(node for node, degree in remaining.items() if degree == 0)
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for target in graph[node]:
            remaining[target] -= 1
            if remaining[target] == 0:
                queue.append(target)
    if visited != len(known):
        errors.append(f"{label}: workflow graph contains a cycle")


def _validate_contract(contract: dict[str, object], row: dict[str, str], label: str, errors: list[str]) -> None:
    missing = REQUIRED_CONTRACT_FIELDS - set(contract)
    if missing:
        errors.append(f"{label}: contract missing fields: {', '.join(sorted(missing))}")
    if contract.get("id") != row["id"]:
        errors.append(f"{label}: catalog ID {row['id']!r} does not match contract ID {contract.get('id')!r}")
    if str(contract.get("version")) != row["version"]:
        errors.append(
            f"{label}: catalog version {row['version']!r} does not match contract version {contract.get('version')!r}"
        )
    for field in ("id", "version", "controller", "topology"):
        if not _nonempty(contract.get(field)):
            errors.append(f"{label}: contract field {field} must be nonempty")

    controller = contract.get("controller")
    if controller not in CONTROLLERS:
        errors.append(f"{label}: controller must be one of {', '.join(sorted(CONTROLLERS))}")

    topology = contract.get("topology")
    if isinstance(topology, str):
        try:
            _parse_topology(topology)
        except ValueError as exc:
            errors.append(f"{label}: invalid topology: {exc}")
    else:
        errors.append(f"{label}: topology must be a string")

    budget = contract.get("budget")
    if not isinstance(budget, dict) or not budget:
        errors.append(f"{label}: budget must be a nonempty object")
    else:
        for name, value in budget.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{label}: budget cap {name} must be numeric")
            elif value < 0:
                errors.append(f"{label}: budget cap {name} must not be negative")
        for name, limit in BUDGET_LIMITS.items():
            if name not in budget:
                errors.append(f"{label}: budget missing required cap {name}")
            else:
                value = budget[name]
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value > limit:
                    errors.append(f"{label}: budget cap {name}={value} exceeds limit {limit}")

    structured = ("join_policy", "context_policy", "failure_policy", "verification", "output")
    for field in structured:
        if not isinstance(contract.get(field), dict) or not contract[field]:
            errors.append(f"{label}: {field} must be a nonempty object")
    stops = contract.get("stop_conditions")
    if not isinstance(stops, list) or not stops or any(not isinstance(item, str) or not item.strip() for item in stops):
        errors.append(f"{label}: stop_conditions must be a nonempty array of nonempty strings")
    _validate_graph(contract, label, errors)


def _validate_scenarios(
    path: Path,
    root: Path,
    catalog_version: str | None,
    workflow_references: dict[str, str],
    errors: list[str],
) -> None:
    label = _relative(path, root)
    if not path.is_file():
        errors.append(f"{label}: missing scenario fixture")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: malformed scenario JSON: {exc.msg} at line {exc.lineno}")
        return
    if not isinstance(data, dict):
        errors.append(f"{label}: scenario fixture must be an object")
        return
    workflow_ids = set(workflow_references)
    references = set(workflow_references.values())
    if data.get("schema_version") != "1":
        errors.append(f"{label}: schema_version must be '1'")
    if str(data.get("catalog_version")) != catalog_version:
        errors.append(f"{label}: catalog_version does not match workflow catalog")
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append(f"{label}: scenarios must be a nonempty array")
        return

    scenario_ids: list[str] = []
    coverage: set[str] = set()
    positives: set[str] = set()
    near_misses: set[str] = set()
    for index, scenario in enumerate(scenarios):
        prefix = f"{label}: scenario {index}"
        if not isinstance(scenario, dict):
            errors.append(f"{prefix} must be an object")
            continue
        required = {"id", "description", "request", "kind", "coverage", "expected"}
        missing = required - set(scenario)
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")
            continue
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            errors.append(f"{prefix} has an invalid id")
        else:
            scenario_ids.append(scenario_id)
            prefix = f"{label}: scenario {scenario_id}"
        for field in ("description", "request"):
            if not isinstance(scenario.get(field), str) or not scenario[field].strip():
                errors.append(f"{prefix} has an empty {field}")
        if scenario.get("kind") not in {"positive", "near_miss", "coverage"}:
            errors.append(f"{prefix} has an invalid kind")
        tags = scenario.get("coverage")
        if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag for tag in tags):
            errors.append(f"{prefix} coverage must be an array of nonempty strings")
        else:
            coverage.update(tags)
        for field, target in (("positive_for", positives), ("near_miss_for", near_misses)):
            value = scenario.get(field)
            if value is not None:
                if value not in workflow_ids:
                    errors.append(f"{prefix} {field} refers to unknown workflow {value!r}")
                else:
                    target.add(value)

        expected = scenario.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{prefix} expected must be an object")
            continue
        expected_required = {"workflow_ids", "references", "topology", "status", "behavior"}
        expected_missing = expected_required - set(expected)
        if expected_missing:
            errors.append(f"{prefix} expected missing fields: {', '.join(sorted(expected_missing))}")
            continue
        workflow_values = expected.get("workflow_ids")
        reference_values = expected.get("references")
        topology_values = expected.get("topology")
        if not isinstance(workflow_values, list) or any(value not in workflow_ids for value in workflow_values):
            errors.append(f"{prefix} expected.workflow_ids contains an unknown workflow")
        if not isinstance(reference_values, list) or any(value not in references for value in reference_values):
            errors.append(f"{prefix} expected.references contains an unknown reference")
        if isinstance(workflow_values, list) and all(value in workflow_ids for value in workflow_values):
            expected_references = [workflow_references[value] for value in workflow_values]
            if reference_values != expected_references:
                errors.append(f"{prefix} expected references do not correspond to workflow_ids")
        if not isinstance(topology_values, list) or not topology_values or any(
            value not in CANONICAL_PRIMITIVES for value in topology_values
        ):
            errors.append(f"{prefix} expected.topology must contain only canonical primitives")
        if expected.get("status") not in ROUTE_STATUSES:
            errors.append(f"{prefix} expected.status is not a known route status")
        if not isinstance(expected.get("behavior"), str) or not expected["behavior"].strip():
            errors.append(f"{prefix} expected.behavior must be nonempty")

    if len(scenario_ids) != len(set(scenario_ids)):
        errors.append(f"{label}: duplicate scenario ID")
    missing_coverage = REQUIRED_COVERAGE - coverage
    if missing_coverage:
        errors.append(f"{label}: missing required coverage: {', '.join(sorted(missing_coverage))}")
    if positives != workflow_ids:
        errors.append(f"{label}: every workflow needs a positive scenario; missing {', '.join(sorted(workflow_ids - positives))}")
    if near_misses != workflow_ids:
        errors.append(f"{label}: every workflow needs a near-miss scenario; missing {', '.join(sorted(workflow_ids - near_misses))}")


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    skill_path = root / "SKILL.md"
    catalog_path = root / "references" / "workflow-catalog.md"
    catalog_version, rows = _parse_catalog(catalog_path, errors)

    ids = [row["id"] for row in rows]
    references = [row["reference"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("references/workflow-catalog.md: duplicate workflow ID")
    if len(references) != len(set(references)):
        errors.append("references/workflow-catalog.md: duplicate workflow reference")

    skill_text = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""
    if not skill_text:
        errors.append("SKILL.md: missing or empty")
    skill_links = set(re.findall(r"\[[^]]+\]\(([^)]+)\)", skill_text))
    contracts: list[tuple[dict[str, str], dict[str, object], str]] = []
    workflow_references: dict[str, str] = {}
    catalog_dir = catalog_path.parent
    for row in rows:
        raw_reference = row["reference"]
        pure = PurePosixPath(raw_reference.replace("\\", "/"))
        if pure.is_absolute() or ".." in pure.parts or len(pure.parts) != 1:
            errors.append(f"references/workflow-catalog.md: reference must be a shallow relative path: {raw_reference}")
            continue
        reference_path = catalog_dir / Path(*pure.parts)
        repo_reference = _relative(reference_path, root)
        workflow_references[row["id"]] = repo_reference
        if repo_reference not in skill_links:
            errors.append(f"SKILL.md: workflow reference is not directly linked: {repo_reference}")
        contract = _extract_contract(reference_path, root, errors)
        if contract is not None:
            contracts.append((row, contract, repo_reference))

    contract_ids: list[object] = [contract.get("id") for _, contract, _ in contracts]
    if len(contract_ids) != len(set(map(str, contract_ids))):
        errors.append("workflow contracts: duplicate workflow ID")
    for row, contract, label in contracts:
        _validate_contract(contract, row, label, errors)

    _validate_scenarios(
        root / "references" / "workflow-scenarios.json",
        root,
        catalog_version,
        workflow_references,
        errors,
    )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    args = parser.parse_args(argv)
    errors = validate(args.root)
    if errors:
        print(f"Workflow validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Workflow validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
