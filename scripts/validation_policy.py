#!/usr/bin/env python3
"""Load and strictly validate EverySkill's machine-readable validation policy."""

from __future__ import annotations

import json
import math
from pathlib import Path


REQUIRED_SECTIONS = {"contract", "topology", "routing", "budgets", "scenarios", "behavior_evaluation"}
IMPLEMENTED_PRIMITIVES = {
    "DIRECT", "ROUTE_ONE", "HANDOFF", "SEQUENTIAL", "PARALLEL_SECTION",
    "PARALLEL_SAMPLE", "ORCHESTRATOR_WORKERS", "REVIEW_LOOP", "HUMAN_GATE",
}
IMPLEMENTED_JOIN_MODES = {"all", "all_settled", "quorum", "first_acceptable"}
IMPLEMENTED_REMAINING_BRANCH_POLICIES = {"cancel", "ignore"}
IMPLEMENTED_SCENARIO_SCHEMA_VERSION = "2"
IMPLEMENTED_BEHAVIOR_SCHEMA_VERSION = "1"


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant {value!r} is not allowed")


def _unique_strings(value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{label} must be a {'possibly empty' if allow_empty else 'nonempty'} array")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{label} must contain nonempty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must not contain duplicates")
    return value


def load_validation_policy(path: Path) -> dict[str, object]:
    try:
        data = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_nonstandard_constant,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load validation policy: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != "1":
        raise ValueError("validation policy schema_version must be '1'")
    missing = REQUIRED_SECTIONS - set(data)
    if missing:
        raise ValueError(f"validation policy missing sections: {', '.join(sorted(missing))}")

    contract = data["contract"]
    topology = data["topology"]
    routing = data["routing"]
    budgets = data["budgets"]
    scenarios = data["scenarios"]
    behavior = data["behavior_evaluation"]
    if not all(isinstance(item, dict) for item in (contract, topology, routing, budgets, scenarios, behavior)):
        raise ValueError("validation policy sections must be objects")

    for key in ("required_fields", "controllers", "edge_kinds"):
        _unique_strings(contract.get(key), f"contract.{key}")
    primitives = set(_unique_strings(topology.get("primitives"), "topology.primitives"))
    unsupported_primitives = primitives - IMPLEMENTED_PRIMITIVES
    if unsupported_primitives:
        raise ValueError(f"topology.primitives require an unimplemented semantic handler: {', '.join(sorted(unsupported_primitives))}")
    coordination = set(_unique_strings(topology.get("coordination_primitives"), "topology.coordination_primitives", allow_empty=True))
    if not coordination <= primitives:
        raise ValueError("coordination primitives must be declared topology primitives")
    for key in ("join_modes", "remaining_branch_policies", "advanced_example_required_primitives"):
        values = set(_unique_strings(topology.get(key), f"topology.{key}"))
        if key == "join_modes" and values - IMPLEMENTED_JOIN_MODES:
            raise ValueError("topology.join_modes contains an unimplemented semantic handler")
        if key == "remaining_branch_policies" and values - IMPLEMENTED_REMAINING_BRANCH_POLICIES:
            raise ValueError("topology.remaining_branch_policies contains an unimplemented semantic handler")
        if key == "advanced_example_required_primitives" and not values <= primitives:
            raise ValueError("advanced example primitives must be declared topology primitives")
    workers = topology.get("orchestrator_workers")
    if not isinstance(workers, dict) or workers.get("max_depth") != 1:
        raise ValueError("topology.orchestrator_workers.max_depth must be 1")

    for key in ("statuses", "authority_statuses"):
        _unique_strings(routing.get(key), f"routing.{key}")
    fallbacks = routing.get("host_fallbacks")
    if not isinstance(fallbacks, dict) or not fallbacks:
        raise ValueError("routing.host_fallbacks must be a nonempty object")
    for mode, values in fallbacks.items():
        if not isinstance(mode, str) or not mode:
            raise ValueError("host mode names must be nonempty strings")
        _unique_strings(values, f"routing.host_fallbacks.{mode}")

    caps = budgets.get("required_caps")
    if not isinstance(caps, dict) or not caps:
        raise ValueError("budgets.required_caps must be a nonempty object")
    for name, bounds in caps.items():
        if not isinstance(name, str) or not name or not isinstance(bounds, dict):
            raise ValueError("budget caps must be named objects")
        minimum, maximum = bounds.get("minimum"), bounds.get("maximum")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in (minimum, maximum)
        ):
            raise ValueError(f"budget cap {name} bounds must be numeric")
        if minimum < 0 or maximum < minimum:
            raise ValueError(f"budget cap {name} bounds are invalid")

    if scenarios.get("schema_version") != IMPLEMENTED_SCENARIO_SCHEMA_VERSION:
        raise ValueError(f"scenarios.schema_version must be {IMPLEMENTED_SCENARIO_SCHEMA_VERSION!r}")
    for key in ("kinds", "required_coverage", "required_workflow_case_kinds"):
        _unique_strings(scenarios.get(key), f"scenarios.{key}")
    if set(scenarios["required_workflow_case_kinds"]) != {"positive", "near_miss"}:
        raise ValueError("required_workflow_case_kinds must use the implemented positive and near_miss fields")
    if behavior.get("schema_version") != IMPLEMENTED_BEHAVIOR_SCHEMA_VERSION:
        raise ValueError(f"behavior_evaluation.schema_version must be {IMPLEMENTED_BEHAVIOR_SCHEMA_VERSION!r}")
    return data
