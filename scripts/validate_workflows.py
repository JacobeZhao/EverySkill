#!/usr/bin/env python3
"""Validate EverySkill workflow contracts and their scenario fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path, PurePosixPath

from evaluate_behavior import validate_case_suite


REQUIRED_CONTRACT_FIELDS = {
    "id",
    "version",
    "controller",
    "topology",
    "topology_regions",
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
EDGE_KINDS = {"data", "control", "context"}
JOIN_MODES = {"all", "all_settled", "quorum", "first_acceptable"}
AUTHORITY_STATUSES = {"sufficient", "conditional", "missing", "forbidden", "unknown"}
HOST_FALLBACKS = {
    "full": {
        "none",
        "block_without_simulation",
        "partial_result",
        "stop_with_collected_evidence",
        "stop_with_unresolved_findings",
        "wait_for_authority",
        "block_forbidden",
        "rebuild_or_block",
        "reject_incompatible_packet",
        "rebuild_v2",
    },
    "serial_only": {"serialize_parallel_regions"},
    "single_agent": {"isolated_sequential_tasks"},
    "no_human_gate": {"block_with_required_decision"},
}
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
    "sequential-dependency",
    "parallel-independence",
    "parallel-sample",
    "review-loop",
    "human-gate",
    "host-parallel-fallback",
    "host-single-agent-fallback",
    "no-human-gate-fallback",
}
CONTRACT_MARKER = "<!-- workflow-contract -->"
ADVANCED_MARKER = "<!-- advanced-topology-examples -->"
COMPOSITION_MARKER = "<!-- workflow-composition-examples -->"


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
        if not isinstance(primitive, str) or primitive not in CANONICAL_PRIMITIVES:
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


def _extract_marked_json(
    path: Path, root: Path, marker: str, errors: list[str]
) -> dict[str, object] | None:
    label = _relative(path, root)
    if not path.is_file():
        errors.append(f"{label}: missing reference")
        return None
    text = path.read_text(encoding="utf-8")
    if text.count(marker) != 1:
        errors.append(f"{label}: expected exactly one {marker} marker")
        return None
    pattern = re.compile(
        re.escape(marker) + r"[ \t]*\r?\n[ \t]*```json[ \t]*\r?\n(.*?)\r?\n[ \t]*```",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        errors.append(f"{label}: marker must be immediately followed by fenced JSON")
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: malformed JSON: {exc.msg} at line {exc.lineno}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{label}: marked JSON must be an object")
        return None
    return data


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
        edge_kind = edge.get("kind")
        if not isinstance(edge_kind, str) or edge_kind not in EDGE_KINDS:
            errors.append(f"{label}: edge {source}->{target} kind must be one of {', '.join(sorted(EDGE_KINDS))}")

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


def _validate_topology_regions(
    contract: dict[str, object], topology_tokens: set[str], label: str, errors: list[str]
) -> None:
    regions = contract.get("topology_regions")
    tasks = contract.get("tasks")
    edges = contract.get("edges")
    if not isinstance(regions, list) or not regions:
        errors.append(f"{label}: topology_regions must be a nonempty array")
        return
    if not isinstance(tasks, list) or not isinstance(edges, list):
        return

    known_tasks = {
        task.get("id") for task in tasks if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    task_owners = {
        task["id"]: task.get("owner")
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    adjacency = {task_id: [] for task_id in known_tasks}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source, target = edge.get("from"), edge.get("to")
        if source in adjacency and target in known_tasks:
            adjacency[source].append(target)

    def reaches(source: str, target: str) -> bool:
        pending = deque([source])
        seen: set[str] = set()
        while pending:
            node = pending.popleft()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            pending.extend(adjacency.get(node, []))
        return False

    region_ids: list[str] = []
    mapped_primitives: set[str] = set()
    for index, region in enumerate(regions):
        prefix = f"{label}: topology region {index}"
        if not isinstance(region, dict):
            errors.append(f"{prefix} must be an object")
            continue
        region_id = region.get("id")
        primitive = region.get("primitive")
        if not isinstance(region_id, str) or not region_id.strip():
            errors.append(f"{prefix} has an invalid id")
        else:
            region_ids.append(region_id)
            prefix = f"{label}: topology region {region_id}"
        if not isinstance(primitive, str) or primitive not in CANONICAL_PRIMITIVES:
            errors.append(f"{prefix} has an invalid primitive")
            continue
        mapped_primitives.add(primitive)
        if primitive not in topology_tokens:
            errors.append(f"{prefix} primitive {primitive} is absent from topology")

        if primitive in {"PARALLEL_SECTION", "PARALLEL_SAMPLE"}:
            branches = region.get("branches")
            join_task = region.get("join_task")
            if not isinstance(branches, list) or len(branches) < 2:
                errors.append(f"{prefix} branches must contain at least two branches")
            else:
                branch_tasks: list[str] = []
                for branch_index, branch in enumerate(branches):
                    if not isinstance(branch, list) or not branch or any(
                        not isinstance(task_id, str) or task_id not in known_tasks for task_id in branch
                    ):
                        errors.append(f"{prefix} branch {branch_index} must contain known task IDs")
                        continue
                    branch_tasks.extend(branch)
                    if isinstance(join_task, str) and join_task in known_tasks and not reaches(branch[-1], join_task):
                        errors.append(f"{prefix} branch {branch_index} does not reach join task {join_task}")
                if len(branch_tasks) != len(set(branch_tasks)):
                    errors.append(f"{prefix} branches must not share tasks")
            if not isinstance(join_task, str) or join_task not in known_tasks:
                errors.append(f"{prefix} has an unknown join_task")
            join_mode = region.get("join_mode")
            if not isinstance(join_mode, str) or join_mode not in JOIN_MODES:
                errors.append(f"{prefix} join_mode must be one of {', '.join(sorted(JOIN_MODES))}")
            elif join_mode == "quorum":
                minimum = region.get("min_acceptable")
                if (
                    isinstance(minimum, bool)
                    or not isinstance(minimum, int)
                    or minimum < 1
                    or not isinstance(branches, list)
                    or minimum > len(branches)
                ):
                    errors.append(f"{prefix} quorum min_acceptable must be within branch count")
                for field in ("acceptance_oracle", "independence_basis", "on_quorum_failure"):
                    if not isinstance(region.get(field), str) or not region[field].strip():
                        errors.append(f"{prefix} quorum must declare {field}")
            elif join_mode == "first_acceptable":
                for field in ("acceptance_oracle", "remaining_branch_policy", "no_result_behavior"):
                    if not isinstance(region.get(field), str) or not region[field].strip():
                        errors.append(f"{prefix} first_acceptable must declare {field}")
                policy = region.get("remaining_branch_policy")
                if policy not in {"cancel", "ignore"}:
                    errors.append(f"{prefix} remaining_branch_policy must be cancel or ignore")
                if policy == "cancel" and (
                    not isinstance(region.get("disposable_or_cancellation_evidence"), str)
                    or not region["disposable_or_cancellation_evidence"].strip()
                ):
                    errors.append(f"{prefix} cancellation requires disposable_or_cancellation_evidence")
            if not isinstance(region.get("failure_mode"), str) or not region["failure_mode"].strip():
                errors.append(f"{prefix} must declare failure_mode")
        elif primitive == "ORCHESTRATOR_WORKERS":
            for field in ("planner_task", "join_task"):
                if not isinstance(region.get(field), str) or region[field] not in known_tasks:
                    errors.append(f"{prefix} has an unknown {field}")
            template = region.get("worker_template")
            if not isinstance(template, dict) or {
                "objective", "owner", "required_output"
            } - set(template):
                errors.append(f"{prefix} worker_template is incomplete")
            else:
                for field in ("objective", "owner", "required_output"):
                    if not isinstance(template.get(field), str) or not template[field].strip():
                        errors.append(f"{prefix} worker_template {field} must be nonempty")
            for field in ("creation_rule", "dedup_key", "failure_mode"):
                if not isinstance(region.get(field), str) or not region[field].strip():
                    errors.append(f"{prefix} must declare {field}")
            max_workers = region.get("max_workers")
            if region.get("join_mode") not in JOIN_MODES:
                errors.append(f"{prefix} join_mode must be one of {', '.join(sorted(JOIN_MODES))}")
            elif region["join_mode"] == "quorum":
                minimum = region.get("min_acceptable")
                if (
                    isinstance(minimum, bool)
                    or not isinstance(minimum, int)
                    or minimum < 1
                    or not isinstance(max_workers, int)
                    or minimum > max_workers
                ):
                    errors.append(f"{prefix} quorum min_acceptable must be within worker count")
                for field in ("acceptance_oracle", "independence_basis", "on_quorum_failure"):
                    if not isinstance(region.get(field), str) or not region[field].strip():
                        errors.append(f"{prefix} quorum must declare {field}")
            elif region["join_mode"] == "first_acceptable":
                for field in ("acceptance_oracle", "remaining_branch_policy", "no_result_behavior"):
                    if not isinstance(region.get(field), str) or not region[field].strip():
                        errors.append(f"{prefix} first_acceptable must declare {field}")
                policy = region.get("remaining_branch_policy")
                if policy not in {"cancel", "ignore"}:
                    errors.append(f"{prefix} remaining_branch_policy must be cancel or ignore")
                if policy == "cancel" and (
                    not isinstance(region.get("disposable_or_cancellation_evidence"), str)
                    or not region["disposable_or_cancellation_evidence"].strip()
                ):
                    errors.append(f"{prefix} cancellation requires disposable_or_cancellation_evidence")
            max_depth = region.get("max_depth")
            budget = contract.get("budget")
            worker_budget = budget.get("max_workers") if isinstance(budget, dict) else None
            depth_budget = budget.get("max_delegation_depth") if isinstance(budget, dict) else None
            if isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1:
                errors.append(f"{prefix} max_workers must be a positive integer")
            elif isinstance(worker_budget, (int, float)) and max_workers > worker_budget:
                errors.append(f"{prefix} max_workers exceeds the workflow worker budget")
            if max_depth != 1:
                errors.append(f"{prefix} max_depth must be exactly 1")
            elif isinstance(depth_budget, (int, float)) and max_depth > depth_budget:
                errors.append(f"{prefix} max_depth exceeds the workflow delegation budget")
            stops = region.get("stop_conditions")
            if not isinstance(stops, list) or not stops or any(not isinstance(item, str) or not item for item in stops):
                errors.append(f"{prefix} stop_conditions must be nonempty strings")
        elif primitive == "HANDOFF":
            source_task = region.get("source_task")
            target_task = region.get("target_task")
            if not isinstance(source_task, str) or source_task not in known_tasks:
                errors.append(f"{prefix} has an unknown source_task")
            if not isinstance(target_task, str) or target_task not in known_tasks:
                errors.append(f"{prefix} has an unknown target_task")
            elif isinstance(source_task, str) and source_task in known_tasks and not reaches(source_task, target_task):
                errors.append(f"{prefix} source_task does not reach target_task")
            for field in ("source_owner", "target_owner", "acceptance_oracle", "failure_mode"):
                if not isinstance(region.get(field), str) or not region[field].strip():
                    errors.append(f"{prefix} must declare {field}")
            if isinstance(source_task, str) and source_task in task_owners and region.get("source_owner") != task_owners[source_task]:
                errors.append(f"{prefix} source_owner must match source_task owner")
            if isinstance(target_task, str) and target_task in task_owners and region.get("target_owner") != task_owners[target_task]:
                errors.append(f"{prefix} target_owner must match target_task owner")
            if region.get("source_owner") == region.get("target_owner"):
                errors.append(f"{prefix} must transfer ownership to a different owner")
            context_contract = region.get("context_contract")
            if not isinstance(context_contract, list) or not context_contract or any(
                not isinstance(item, str) or not item for item in context_contract
            ):
                errors.append(f"{prefix} context_contract must be nonempty strings")
        elif primitive == "REVIEW_LOOP":
            task_ids = region.get("task_ids")
            max_rounds = region.get("max_rounds")
            exits = region.get("exit_conditions")
            if not isinstance(task_ids, list) or len(task_ids) < 2 or any(
                not isinstance(task_id, str) or task_id not in known_tasks for task_id in task_ids
            ):
                errors.append(f"{prefix} task_ids must contain at least two known tasks")
            if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 1:
                errors.append(f"{prefix} max_rounds must be a positive integer")
            budget = contract.get("budget")
            review_budget = budget.get("max_review_rounds") if isinstance(budget, dict) else None
            if (
                isinstance(max_rounds, int)
                and not isinstance(max_rounds, bool)
                and isinstance(review_budget, (int, float))
                and not isinstance(review_budget, bool)
                and max_rounds > review_budget
            ):
                errors.append(f"{prefix} max_rounds exceeds the workflow review budget")
            exit_task = region.get("exit_task")
            if not isinstance(exit_task, str) or exit_task not in known_tasks:
                errors.append(f"{prefix} has an unknown exit_task")
            elif isinstance(task_ids, list) and exit_task in task_ids:
                errors.append(f"{prefix} exit_task must be outside the review region")
            elif isinstance(task_ids, list) and all(isinstance(task_id, str) for task_id in task_ids):
                if any(task_id in known_tasks and not reaches(task_id, exit_task) for task_id in task_ids):
                    errors.append(f"{prefix} review tasks must reach exit_task {exit_task}")
            if not isinstance(exits, list) or not exits or any(not isinstance(item, str) or not item for item in exits):
                errors.append(f"{prefix} exit_conditions must be nonempty strings")
        else:
            task_ids = region.get("task_ids")
            if not isinstance(task_ids, list) or not task_ids or any(
                not isinstance(task_id, str) or task_id not in known_tasks for task_id in task_ids
            ):
                errors.append(f"{prefix} task_ids must contain known tasks")
            if primitive == "HUMAN_GATE":
                resume_task = region.get("resume_task")
                if not isinstance(resume_task, str) or resume_task not in known_tasks:
                    errors.append(f"{prefix} has an unknown resume_task")
                if region.get("blocked_status") != "blocked":
                    errors.append(f"{prefix} blocked_status must be 'blocked'")
                if not isinstance(region.get("activation_condition"), str) or not region["activation_condition"].strip():
                    errors.append(f"{prefix} must declare activation_condition")

    if len(region_ids) != len(set(region_ids)):
        errors.append(f"{label}: duplicate topology region ID")
    missing_regions = topology_tokens - mapped_primitives
    if missing_regions:
        errors.append(f"{label}: topology primitives missing regions: {', '.join(sorted(missing_regions))}")


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
    if not isinstance(controller, str) or controller not in CONTROLLERS:
        errors.append(f"{label}: controller must be one of {', '.join(sorted(CONTROLLERS))}")

    topology = contract.get("topology")
    topology_tokens: set[str] = set()
    if isinstance(topology, str):
        try:
            topology_tokens = _parse_topology(topology)
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
    _validate_topology_regions(contract, topology_tokens, label, errors)


def _validate_scenarios(
    path: Path,
    root: Path,
    catalog_version: str | None,
    workflow_references: dict[str, str],
    workflow_topologies: dict[str, set[str]],
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
    if data.get("schema_version") != "2":
        errors.append(f"{label}: schema_version must be '2'")
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
                if not isinstance(value, str) or value not in workflow_ids:
                    errors.append(f"{prefix} {field} refers to unknown workflow {value!r}")
                else:
                    target.add(value)

        expected = scenario.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{prefix} expected must be an object")
            continue
        expected_required = {"workflow_ids", "references", "topology", "status", "behavior", "decision"}
        expected_missing = expected_required - set(expected)
        if expected_missing:
            errors.append(f"{prefix} expected missing fields: {', '.join(sorted(expected_missing))}")
            continue
        workflow_values = expected.get("workflow_ids")
        reference_values = expected.get("references")
        topology_values = expected.get("topology")
        if not isinstance(workflow_values, list) or any(
            not isinstance(value, str) or value not in workflow_ids for value in workflow_values
        ):
            errors.append(f"{prefix} expected.workflow_ids contains an unknown workflow")
        if not isinstance(reference_values, list) or any(
            not isinstance(value, str) or value not in references for value in reference_values
        ):
            errors.append(f"{prefix} expected.references contains an unknown reference")
        if isinstance(workflow_values, list) and all(
            isinstance(value, str) and value in workflow_ids for value in workflow_values
        ):
            expected_references = [workflow_references[value] for value in workflow_values]
            if reference_values != expected_references:
                errors.append(f"{prefix} expected references do not correspond to workflow_ids")
        if not isinstance(topology_values, list) or not topology_values or any(
            not isinstance(value, str) or value not in CANONICAL_PRIMITIVES for value in topology_values
        ):
            errors.append(f"{prefix} expected.topology must contain only canonical primitives")
        elif (
            expected.get("status") == "routed"
            and isinstance(workflow_values, list)
            and all(isinstance(value, str) and value in workflow_ids for value in workflow_values)
        ):
            required_topology = (
                set().union(*(workflow_topologies.get(value, set()) for value in workflow_values))
                if workflow_values
                else {"ROUTE_ONE"}
            )
            if set(topology_values) != required_topology:
                errors.append(
                    f"{prefix} expected.topology does not match the selected workflow topology: "
                    f"expected {', '.join(sorted(required_topology))}"
                )
        status = expected.get("status")
        if not isinstance(status, str) or status not in ROUTE_STATUSES:
            errors.append(f"{prefix} expected.status is not a known route status")
        if not isinstance(expected.get("behavior"), str) or not expected["behavior"].strip():
            errors.append(f"{prefix} expected.behavior must be nonempty")
        decision = expected.get("decision")
        if not isinstance(decision, dict):
            errors.append(f"{prefix} expected.decision must be an object")
        else:
            decision_required = {"reason", "authority_status", "host_mode", "fallback"}
            decision_missing = decision_required - set(decision)
            if decision_missing:
                errors.append(f"{prefix} expected.decision missing fields: {', '.join(sorted(decision_missing))}")
            if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
                errors.append(f"{prefix} expected.decision.reason must be nonempty")
            authority_status = decision.get("authority_status")
            if not isinstance(authority_status, str) or authority_status not in AUTHORITY_STATUSES:
                errors.append(f"{prefix} expected.decision.authority_status is invalid")
            host_mode = decision.get("host_mode")
            fallback = decision.get("fallback")
            if not isinstance(host_mode, str) or host_mode not in HOST_FALLBACKS:
                errors.append(f"{prefix} expected.decision.host_mode is invalid")
            elif not isinstance(fallback, str) or fallback not in HOST_FALLBACKS[host_mode]:
                errors.append(f"{prefix} expected.decision fallback is invalid for host_mode {host_mode}")

    if len(scenario_ids) != len(set(scenario_ids)):
        errors.append(f"{label}: duplicate scenario ID")
    missing_coverage = REQUIRED_COVERAGE - coverage
    if missing_coverage:
        errors.append(f"{label}: missing required coverage: {', '.join(sorted(missing_coverage))}")
    if positives != workflow_ids:
        errors.append(f"{label}: every workflow needs a positive scenario; missing {', '.join(sorted(workflow_ids - positives))}")
    if near_misses != workflow_ids:
        errors.append(f"{label}: every workflow needs a near-miss scenario; missing {', '.join(sorted(workflow_ids - near_misses))}")


def _validate_advanced_examples(path: Path, root: Path, errors: list[str]) -> None:
    label = _relative(path, root)
    data = _extract_marked_json(path, root, ADVANCED_MARKER, errors)
    if data is None:
        return
    if data.get("schema_version") != "1":
        errors.append(f"{label}: schema_version must be '1'")
    examples = data.get("examples")
    if not isinstance(examples, list) or not examples:
        errors.append(f"{label}: examples must be a nonempty array")
        return
    example_ids: list[str] = []
    covered: set[str] = set()
    for index, example in enumerate(examples):
        prefix = f"{label}: example {index}"
        if not isinstance(example, dict):
            errors.append(f"{prefix} must be an object")
            continue
        example_id = example.get("id")
        if not isinstance(example_id, str) or not example_id:
            errors.append(f"{prefix} has an invalid id")
        else:
            example_ids.append(example_id)
            prefix = f"{label}: example {example_id}"
        topology = example.get("topology")
        try:
            tokens = _parse_topology(topology) if isinstance(topology, str) else set()
        except ValueError as exc:
            errors.append(f"{prefix}: invalid topology: {exc}")
            tokens = set()
        if not tokens:
            errors.append(f"{prefix}: topology must be nonempty")
        covered.update(tokens)
        budget = example.get("budget")
        if not isinstance(budget, dict):
            errors.append(f"{prefix}: budget must be an object")
        else:
            for name, limit in BUDGET_LIMITS.items():
                value = budget.get(name)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or value > limit:
                    errors.append(f"{prefix}: budget cap {name} must be between 0 and {limit}")
        _validate_graph(example, prefix, errors)
        _validate_topology_regions(example, tokens, prefix, errors)
    if len(example_ids) != len(set(example_ids)):
        errors.append(f"{label}: duplicate example ID")
    required = {"HANDOFF", "PARALLEL_SECTION", "PARALLEL_SAMPLE", "ORCHESTRATOR_WORKERS"}
    missing = required - covered
    if missing:
        errors.append(f"{label}: missing advanced primitive examples: {', '.join(sorted(missing))}")


def _validate_compositions(
    path: Path,
    root: Path,
    workflow_versions: dict[str, str],
    errors: list[str],
) -> None:
    label = _relative(path, root)
    data = _extract_marked_json(path, root, COMPOSITION_MARKER, errors)
    if data is None:
        return
    if data.get("schema_version") != "1":
        errors.append(f"{label}: schema_version must be '1'")
    examples = data.get("examples")
    if not isinstance(examples, list) or not examples:
        errors.append(f"{label}: examples must be a nonempty array")
        return
    example_ids: list[str] = []
    for index, example in enumerate(examples):
        prefix = f"{label}: example {index}"
        if not isinstance(example, dict):
            errors.append(f"{prefix} must be an object")
            continue
        example_id = example.get("id")
        if isinstance(example_id, str) and example_id:
            example_ids.append(example_id)
            prefix = f"{label}: example {example_id}"
        else:
            errors.append(f"{prefix} has an invalid id")
        instances = example.get("instances")
        if not isinstance(instances, list) or len(instances) < 2:
            errors.append(f"{prefix}: instances must contain at least two workflows")
            continue
        instance_ids: list[str] = []
        for instance in instances:
            if not isinstance(instance, dict):
                errors.append(f"{prefix}: instance must be an object")
                continue
            instance_id = instance.get("instance_id")
            workflow_id = instance.get("workflow_id")
            if not isinstance(instance_id, str) or not instance_id:
                errors.append(f"{prefix}: instance has an invalid instance_id")
            else:
                instance_ids.append(instance_id)
            if workflow_id not in workflow_versions:
                errors.append(f"{prefix}: instance refers to unknown workflow {workflow_id!r}")
            elif str(instance.get("workflow_version")) != workflow_versions[workflow_id]:
                errors.append(f"{prefix}: instance workflow version does not match catalog")
            if not isinstance(instance.get("acceptance_oracle"), str) or not instance["acceptance_oracle"].strip():
                errors.append(f"{prefix}: every instance needs an independent acceptance_oracle")
        if len(instance_ids) != len(set(instance_ids)):
            errors.append(f"{prefix}: duplicate instance_id")
        known_instances = set(instance_ids)
        tasks = example.get("tasks")
        task_ids: list[str] = []
        task_instances: dict[str, str] = {}
        if not isinstance(tasks, list) or not tasks:
            errors.append(f"{prefix}: tasks must be a nonempty array")
            continue
        for task in tasks:
            if not isinstance(task, dict) or not isinstance(task.get("id"), str):
                errors.append(f"{prefix}: task has an invalid id")
                continue
            task_ids.append(task["id"])
            if task.get("instance_id") not in known_instances:
                errors.append(f"{prefix}: task refers to unknown instance")
            else:
                task_instances[task["id"]] = task["instance_id"]
        if len(task_ids) != len(set(task_ids)):
            errors.append(f"{prefix}: duplicate composition task ID")
        known_tasks = set(task_ids)
        adjacency = {task_id: [] for task_id in known_tasks}
        indegree = {task_id: 0 for task_id in known_tasks}
        instance_adjacency = {instance_id: set() for instance_id in known_instances}
        cross_instance_edges = 0
        edges = example.get("edges")
        if not isinstance(edges, list):
            errors.append(f"{prefix}: edges must be an array")
        else:
            for edge in edges:
                if not isinstance(edge, dict):
                    errors.append(f"{prefix}: edge must be an object")
                    continue
                source, target = edge.get("from"), edge.get("to")
                if source not in known_tasks or target not in known_tasks:
                    errors.append(f"{prefix}: dangling composition edge {source}->{target}")
                    continue
                if edge.get("kind") not in EDGE_KINDS:
                    errors.append(f"{prefix}: composition edge kind is invalid")
                adjacency[source].append(target)
                indegree[target] += 1
                source_instance = task_instances.get(source)
                target_instance = task_instances.get(target)
                if source_instance != target_instance:
                    cross_instance_edges += 1
                    if source_instance in instance_adjacency and target_instance in instance_adjacency:
                        instance_adjacency[source_instance].add(target_instance)
        pending = deque(node for node, degree in indegree.items() if degree == 0)
        visited = 0
        while pending:
            node = pending.popleft()
            visited += 1
            for target in adjacency[node]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    pending.append(target)
        if visited != len(known_tasks):
            errors.append(f"{prefix}: composition graph contains a cycle")
        unused_instances = known_instances - set(task_instances.values())
        if unused_instances:
            errors.append(f"{prefix}: instances without tasks: {', '.join(sorted(unused_instances))}")
        if cross_instance_edges == 0:
            errors.append(f"{prefix}: composition requires at least one cross-instance edge")
        instance_indegree = {instance_id: 0 for instance_id in known_instances}
        for targets in instance_adjacency.values():
            for target in targets:
                instance_indegree[target] += 1
        instance_pending = deque(node for node, degree in instance_indegree.items() if degree == 0)
        visited_instances = 0
        while instance_pending:
            node = instance_pending.popleft()
            visited_instances += 1
            for target in instance_adjacency[node]:
                instance_indegree[target] -= 1
                if instance_indegree[target] == 0:
                    instance_pending.append(target)
        if visited_instances != len(known_instances):
            errors.append(f"{prefix}: cross-workflow instance graph contains a cycle")
        if not isinstance(example.get("join_policy"), str) or not example["join_policy"].strip():
            errors.append(f"{prefix}: join_policy must be nonempty")
    if len(example_ids) != len(set(example_ids)):
        errors.append(f"{label}: duplicate example ID")


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

    workflow_topologies: dict[str, set[str]] = {}
    for _, contract, _ in contracts:
        workflow_id = contract.get("id")
        topology = contract.get("topology")
        if not isinstance(workflow_id, str) or not isinstance(topology, str):
            continue
        try:
            tokens = _parse_topology(topology)
        except ValueError:
            continue
        regions = contract.get("topology_regions")
        conditional: set[str] = set()
        if isinstance(regions, list):
            conditional = {
                region["primitive"]
                for region in regions
                if isinstance(region, dict)
                and isinstance(region.get("primitive"), str)
                and isinstance(region.get("activation_condition"), str)
            }
        workflow_topologies[workflow_id] = tokens - conditional

    _validate_scenarios(
        root / "references" / "workflow-scenarios.json",
        root,
        catalog_version,
        workflow_references,
        workflow_topologies,
        errors,
    )
    _validate_advanced_examples(root / "references" / "advanced-topology-examples.md", root, errors)
    _validate_compositions(
        root / "references" / "workflow-composition.md",
        root,
        {row["id"]: row["version"] for row in rows},
        errors,
    )
    behavior_path = root / "references" / "behavior-evaluation-cases.json"
    try:
        behavior_data = json.loads(behavior_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{_relative(behavior_path, root)}: invalid behavior evaluation cases: {exc}")
    else:
        errors.extend(
            f"{_relative(behavior_path, root)}: {error}"
            for error in validate_case_suite(
                behavior_data,
                catalog_version=catalog_version,
                workflow_ids=set(ids),
            )
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
