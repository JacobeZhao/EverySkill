#!/usr/bin/env python3
"""Score captured EverySkill routing trials without invoking a model."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from validation_policy import load_validation_policy

CANONICAL_PRIMITIVES: set[str]
ROUTE_STATUSES: set[str]
AUTHORITY_STATUSES: set[str]
COORDINATION_PRIMITIVES: set[str]
HOST_FALLBACKS: dict[str, set[str]]
BEHAVIOR_SCHEMA_VERSION: str
CASE_ORACLE_FIELDS = {
    "allowed_workflow_sets", "allowed_topology_sets", "allowed_primary_owner_sets",
    "allowed_handoff_orders", "route_status", "error_codes",
    "authority_status", "fallback", "max_workflows", "max_coordination_primitives",
    "forbidden_topology", "safety_critical",
}
PACKET_FIELDS = {
    "workflow_ids", "topology", "route_status", "error_code", "authority_status",
    "fallback", "primary_owners", "handoff_order", "intent_count",
}
REVIEW_DIMENSIONS = {
    "node_atomicity", "dependency_correctness", "owner_and_output",
    "context_minimization", "parallel_and_join_justification",
    "budget_failure_stop_verification",
}


def _configure_policy(policy: dict[str, object]) -> None:
    global CANONICAL_PRIMITIVES, ROUTE_STATUSES, AUTHORITY_STATUSES
    global COORDINATION_PRIMITIVES, HOST_FALLBACKS, BEHAVIOR_SCHEMA_VERSION
    topology = policy["topology"]
    routing = policy["routing"]
    CANONICAL_PRIMITIVES = set(topology["primitives"])
    COORDINATION_PRIMITIVES = set(topology["coordination_primitives"])
    ROUTE_STATUSES = set(routing["statuses"])
    AUTHORITY_STATUSES = set(routing["authority_statuses"])
    HOST_FALLBACKS = {key: set(value) for key, value in routing["host_fallbacks"].items()}
    BEHAVIOR_SCHEMA_VERSION = policy["behavior_evaluation"]["schema_version"]


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "references" / "validation-policy.json"
_configure_policy(load_validation_policy(DEFAULT_POLICY_PATH))


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _nonempty_string_list(value: object) -> bool:
    return bool(value) and _string_list(value)


def _set_options(value: object, allowed: set[str] | None = None) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for option in value:
        if not _string_list(option):
            return False
        if len(option) != len(set(option)):
            return False
        if allowed is not None and any(item not in allowed for item in option):
            return False
    return True


def validate_case_suite(
    data: object,
    *,
    catalog_version: str | None = None,
    workflow_ids: set[str] | None = None,
    policy: dict[str, object] | None = None,
) -> list[str]:
    if policy is not None:
        _configure_policy(policy)
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["behavior evaluation suite must be an object"]
    if data.get("schema_version") != BEHAVIOR_SCHEMA_VERSION:
        errors.append(f"behavior evaluation schema_version must be {BEHAVIOR_SCHEMA_VERSION!r}")
    if catalog_version is not None and str(data.get("catalog_version")) != catalog_version:
        errors.append("behavior evaluation catalog_version does not match workflow catalog")
    suite = data.get("suite")
    if not isinstance(suite, dict):
        errors.append("behavior evaluation suite settings must be an object")
        return errors
    repetitions = suite.get("default_repetitions")
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 2:
        errors.append("default_repetitions must be an integer of at least 2")
    thresholds = suite.get("thresholds")
    required_thresholds = {
        "packet_validity", "route_accuracy", "stability",
        "max_over_orchestration_rate", "safety_pass_rate",
    }
    if not isinstance(thresholds, dict) or required_thresholds - set(thresholds):
        errors.append("behavior evaluation thresholds are incomplete")
    else:
        for name in required_thresholds:
            value = thresholds.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                errors.append(f"threshold {name} must be between 0 and 1")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("behavior evaluation cases must be a nonempty array")
        return errors
    case_ids: list[str] = []
    for index, case in enumerate(cases):
        prefix = f"behavior evaluation case {index}"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = {"id", "request", "context", "oracle"} - set(case)
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix} has an invalid id")
        else:
            case_ids.append(case_id)
            prefix = f"behavior evaluation case {case_id}"
        if not isinstance(case.get("request"), str) or not case["request"].strip():
            errors.append(f"{prefix} request must be nonempty")
        context = case.get("context")
        if not isinstance(context, dict) or context.get("authority_status") not in AUTHORITY_STATUSES:
            errors.append(f"{prefix} context has an invalid authority_status")
        if not isinstance(context, dict) or not isinstance(context.get("host_mode"), str) or not context["host_mode"]:
            errors.append(f"{prefix} context has an invalid host_mode")
        required_skills = case.get("required_visible_skills", [])
        if not _string_list(required_skills) or len(required_skills) != len(set(required_skills)):
            errors.append(f"{prefix} required_visible_skills must be unique nonempty strings")
        case_repetitions = case.get("repetitions", repetitions)
        if isinstance(case_repetitions, bool) or not isinstance(case_repetitions, int) or case_repetitions < 2:
            errors.append(f"{prefix} repetitions must be an integer of at least 2")
        oracle = case.get("oracle")
        if not isinstance(oracle, dict):
            errors.append(f"{prefix} oracle must be an object")
            continue
        missing_oracle = CASE_ORACLE_FIELDS - set(oracle)
        if missing_oracle:
            errors.append(f"{prefix} oracle missing fields: {', '.join(sorted(missing_oracle))}")
            continue
        if not _set_options(oracle.get("allowed_workflow_sets"), workflow_ids):
            errors.append(f"{prefix} allowed_workflow_sets is invalid")
        if not _set_options(oracle.get("allowed_topology_sets"), CANONICAL_PRIMITIVES):
            errors.append(f"{prefix} allowed_topology_sets is invalid")
        if not _set_options(oracle.get("allowed_primary_owner_sets")):
            errors.append(f"{prefix} allowed_primary_owner_sets is invalid")
        elif any(not option for option in oracle["allowed_primary_owner_sets"]):
            errors.append(f"{prefix} allowed_primary_owner_sets cannot contain an empty owner set")
        if not _set_options(oracle.get("allowed_handoff_orders")):
            errors.append(f"{prefix} allowed_handoff_orders is invalid")
        if oracle.get("route_status") not in ROUTE_STATUSES:
            errors.append(f"{prefix} route_status is invalid")
        if not _nonempty_string_list(oracle.get("error_codes")):
            errors.append(f"{prefix} error_codes must be nonempty strings")
        if oracle.get("authority_status") not in AUTHORITY_STATUSES:
            errors.append(f"{prefix} authority_status is invalid")
        if not isinstance(oracle.get("fallback"), str) or not oracle["fallback"]:
            errors.append(f"{prefix} fallback must be nonempty")
        elif isinstance(context, dict) and context.get("host_mode") in HOST_FALLBACKS:
            if oracle["fallback"] not in HOST_FALLBACKS[context["host_mode"]]:
                errors.append(f"{prefix} fallback is invalid for host_mode {context['host_mode']}")
        elif isinstance(context, dict):
            errors.append(f"{prefix} host_mode is not declared by validation policy")
        for field in ("max_workflows", "max_coordination_primitives"):
            value = oracle.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{prefix} {field} must be a nonnegative integer")
        forbidden = oracle.get("forbidden_topology")
        if not _string_list(forbidden) or any(value not in CANONICAL_PRIMITIVES for value in forbidden):
            errors.append(f"{prefix} forbidden_topology is invalid")
        if not isinstance(oracle.get("safety_critical"), bool):
            errors.append(f"{prefix} safety_critical must be boolean")
    if len(case_ids) != len(set(case_ids)):
        errors.append("behavior evaluation contains duplicate case IDs")
    return errors


def _packet_errors(packet: object) -> list[str]:
    if not isinstance(packet, dict):
        return ["packet must be an object"]
    errors: list[str] = []
    missing = PACKET_FIELDS - set(packet)
    if missing:
        errors.append(f"packet missing fields: {', '.join(sorted(missing))}")
        return errors
    if not _string_list(packet.get("workflow_ids")):
        errors.append("workflow_ids must be strings")
    elif len(packet["workflow_ids"]) != len(set(packet["workflow_ids"])):
        errors.append("workflow_ids must not contain duplicates")
    if not _nonempty_string_list(packet.get("topology")) or any(
        value not in CANONICAL_PRIMITIVES for value in packet.get("topology", []) if isinstance(value, str)
    ):
        errors.append("topology is invalid")
    elif len(packet["topology"]) != len(set(packet["topology"])):
        errors.append("topology must not contain duplicates")
    if packet.get("route_status") not in ROUTE_STATUSES:
        errors.append("route_status is invalid")
    if not isinstance(packet.get("error_code"), str) or not packet["error_code"]:
        errors.append("error_code is invalid")
    if packet.get("authority_status") not in AUTHORITY_STATUSES:
        errors.append("authority_status is invalid")
    if not isinstance(packet.get("fallback"), str) or not packet["fallback"]:
        errors.append("fallback is invalid")
    if not _nonempty_string_list(packet.get("primary_owners")):
        errors.append("primary_owners must be strings")
    elif len(packet["primary_owners"]) != len(set(packet["primary_owners"])):
        errors.append("primary_owners must not contain duplicates")
    if not _string_list(packet.get("handoff_order")):
        errors.append("handoff_order must be strings")
    elif len(packet["handoff_order"]) != len(set(packet["handoff_order"])):
        errors.append("handoff_order must not contain duplicates")
    intent_count = packet.get("intent_count")
    if isinstance(intent_count, bool) or not isinstance(intent_count, int) or intent_count < 1:
        errors.append("intent_count must be a positive integer")
    return errors


def validate_reviews(
    data: object,
    *,
    case_ids: set[str],
    run_id: str,
    valid_trials: set[tuple[str, int]],
) -> tuple[dict[str, object] | None, list[str]]:
    if not isinstance(data, dict) or data.get("schema_version") != "1":
        return None, ["human review schema_version must be '1'"]
    errors: list[str] = []
    if data.get("run_id") != run_id:
        errors.append("human review run_id does not match evaluation run")
    if not isinstance(data.get("sampling_rule"), str) or not data["sampling_rule"].strip():
        errors.append("human review sampling_rule must be nonempty")
    reviews = data.get("reviews")
    if not isinstance(reviews, list):
        return None, errors + ["human reviews must be an array"]
    summaries = []
    keys: set[tuple[str, int]] = set()
    for index, review in enumerate(reviews):
        prefix = f"human review {index}"
        if not isinstance(review, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id, trial_index = review.get("case_id"), review.get("trial_index")
        if case_id not in case_ids:
            errors.append(f"{prefix} refers to an unknown case")
        if isinstance(trial_index, bool) or not isinstance(trial_index, int) or trial_index < 1:
            errors.append(f"{prefix} has an invalid trial_index")
            continue
        key = (case_id, trial_index)
        if case_id in case_ids and key not in valid_trials:
            errors.append(f"{prefix} refers to a trial absent from the evaluation results")
        if key in keys:
            errors.append(f"duplicate human review {case_id}/{trial_index}")
        keys.add(key)
        if not isinstance(review.get("reviewer_role"), str) or not review["reviewer_role"].strip():
            errors.append(f"{prefix} reviewer_role must be nonempty")
        dimensions = review.get("dimensions")
        if not isinstance(dimensions, dict) or set(dimensions) != REVIEW_DIMENSIONS:
            errors.append(f"{prefix} dimensions must contain the exact rubric")
            continue
        outcomes = []
        for name, dimension in dimensions.items():
            if not isinstance(dimension, dict) or dimension.get("outcome") not in {"pass", "fail", "unrun"}:
                errors.append(f"{prefix} dimension {name} has an invalid outcome")
                continue
            outcome = dimension["outcome"]
            outcomes.append(outcome)
            support_field = "reason" if outcome == "unrun" else "evidence"
            if not isinstance(dimension.get(support_field), str) or not dimension[support_field].strip():
                errors.append(f"{prefix} dimension {name} requires {support_field}")
        derived = "fail" if "fail" in outcomes else "unrun" if "unrun" in outcomes else "pass"
        if review.get("overall") != derived:
            errors.append(f"{prefix} overall must equal derived outcome {derived}")
        summaries.append({"case_id": case_id, "trial_index": trial_index, "overall": derived})
    if errors:
        return None, errors
    counts = {outcome: sum(item["overall"] == outcome for item in summaries) for outcome in ("pass", "fail", "unrun")}
    return {"status": "RECORDED" if summaries else "UNRUN", "counts": counts, "reviews": summaries}, []


def _signature(packet: dict[str, object]) -> tuple[object, ...]:
    return (
        tuple(sorted(packet["workflow_ids"])),
        tuple(sorted(packet["topology"])),
        packet["route_status"],
        packet["error_code"],
        packet["authority_status"],
        packet["fallback"],
        tuple(sorted(packet["primary_owners"])),
        tuple(packet["handoff_order"]),
        packet["intent_count"],
    )


def _matches(packet: dict[str, object], oracle: dict[str, object]) -> bool:
    workflows = set(packet["workflow_ids"])
    topology = set(packet["topology"])
    return (
        any(workflows == set(option) for option in oracle["allowed_workflow_sets"])
        and any(topology == set(option) for option in oracle["allowed_topology_sets"])
        and any(
            set(packet["primary_owners"]) == set(option)
            and packet["intent_count"] == len(option)
            for option in oracle["allowed_primary_owner_sets"]
        )
        and any(packet["handoff_order"] == option for option in oracle["allowed_handoff_orders"])
        and packet["route_status"] == oracle["route_status"]
        and packet["error_code"] in oracle["error_codes"]
        and packet["authority_status"] == oracle["authority_status"]
        and packet["fallback"] == oracle["fallback"]
    )


def _over_orchestrated(packet: dict[str, object], oracle: dict[str, object]) -> bool:
    topology = set(packet["topology"])
    return (
        len(packet["workflow_ids"]) > oracle["max_workflows"]
        or len(topology & COORDINATION_PRIMITIVES) > oracle["max_coordination_primitives"]
        or bool(topology & set(oracle["forbidden_topology"]))
    )


def evaluate(case_data: dict[str, object], result_data: object) -> tuple[dict[str, object] | None, list[str]]:
    structural_errors: list[str] = []
    if not isinstance(result_data, dict):
        return None, ["evaluation results must be an object"]
    if result_data.get("schema_version") != BEHAVIOR_SCHEMA_VERSION:
        structural_errors.append(f"evaluation results schema_version must be {BEHAVIOR_SCHEMA_VERSION!r}")
    run = result_data.get("run")
    run_fields = {
        "run_id", "skill_revision", "workflow_catalog_marker", "host", "model",
        "sampling", "capability_profile", "visible_skills",
    }
    if not isinstance(run, dict) or run_fields - set(run):
        structural_errors.append("evaluation run metadata is incomplete")
    else:
        for field in ("run_id", "skill_revision", "workflow_catalog_marker", "host", "model", "capability_profile"):
            if not isinstance(run.get(field), str) or not run[field].strip():
                structural_errors.append(f"evaluation run {field} must be nonempty")
        if run.get("workflow_catalog_marker") != f"catalog-{case_data['catalog_version']}":
            structural_errors.append("evaluation run workflow_catalog_marker does not match case catalog")
        if not isinstance(run.get("sampling"), dict):
            structural_errors.append("evaluation run sampling must be an object")
        if not _string_list(run.get("visible_skills")) or len(run["visible_skills"]) != len(set(run["visible_skills"])):
            structural_errors.append("evaluation run visible_skills must be unique nonempty strings")
    trials = result_data.get("trials")
    if not isinstance(trials, list):
        structural_errors.append("evaluation trials must be an array")
        return None, structural_errors

    defaults = case_data["suite"]["default_repetitions"]
    cases = {case["id"]: case for case in case_data["cases"]}
    trial_map: dict[tuple[str, int], object] = {}
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict):
            structural_errors.append(f"trial {index} must be an object")
            continue
        case_id, trial_index = trial.get("case_id"), trial.get("trial_index")
        if case_id not in cases:
            structural_errors.append(f"trial {index} refers to an unknown case")
            continue
        if isinstance(trial_index, bool) or not isinstance(trial_index, int) or trial_index < 1:
            structural_errors.append(f"trial {index} has an invalid trial_index")
            continue
        repetitions = cases[case_id].get("repetitions", defaults)
        if trial_index > repetitions:
            structural_errors.append(f"trial {case_id}/{trial_index} exceeds repetitions")
            continue
        key = (case_id, trial_index)
        if key in trial_map:
            structural_errors.append(f"duplicate trial {case_id}/{trial_index}")
            continue
        trial_map[key] = trial.get("packet")
    if structural_errors:
        return None, structural_errors

    visible_skills = set(run["visible_skills"])
    runnable_cases = {
        case_id: case
        for case_id, case in cases.items()
        if set(case.get("required_visible_skills", [])) <= visible_skills
    }
    expected_total = sum(case.get("repetitions", defaults) for case in runnable_cases.values())
    if not runnable_cases:
        return {
            "status": "UNRUN",
            "metrics": {},
            "gates": {},
            "evaluated_cases": 0,
            "unrun_cases": len(cases),
            "cases": [
                {
                    "case_id": case_id,
                    "status": "UNRUN",
                    "reason": "missing_capability",
                    "missing_visible_skills": sorted(
                        set(case.get("required_visible_skills", [])) - visible_skills
                    ),
                }
                for case_id, case in cases.items()
            ],
        }, []
    valid_total = correct_total = over_total = safety_correct = safety_total = 0
    case_reports: list[dict[str, object]] = []
    for case_id, case in cases.items():
        repetitions = case.get("repetitions", defaults)
        oracle = case["oracle"]
        missing_skills = sorted(set(case.get("required_visible_skills", [])) - visible_skills)
        if missing_skills:
            case_reports.append({
                "case_id": case_id,
                "status": "UNRUN",
                "reason": "missing_capability",
                "missing_visible_skills": missing_skills,
            })
            continue
        correct = valid = over = 0
        signatures: Counter[tuple[object, ...]] = Counter()
        trial_reports: list[dict[str, object]] = []
        for trial_index in range(1, repetitions + 1):
            packet = trial_map.get((case_id, trial_index))
            errors = ["missing trial"] if packet is None else _packet_errors(packet)
            matched = False
            excessive = False
            if not errors:
                valid += 1
                valid_total += 1
                signatures[_signature(packet)] += 1
                matched = _matches(packet, oracle)
                excessive = _over_orchestrated(packet, oracle)
                correct += int(matched)
                correct_total += int(matched)
                over += int(excessive)
                over_total += int(excessive)
            if oracle["safety_critical"]:
                safety_total += 1
                safety_correct += int(matched)
            trial_reports.append({"trial_index": trial_index, "valid": not errors, "correct": matched, "over_orchestrated": excessive, "errors": errors})
        stability = (max(signatures.values()) / repetitions) if signatures else 0.0
        case_reports.append({"case_id": case_id, "status": "EVALUATED", "accuracy": correct / repetitions, "stability": stability, "valid_packets": valid, "over_orchestrated": over, "trials": trial_reports})

    metrics = {
        "packet_validity": valid_total / expected_total,
        "route_accuracy": sum(case["accuracy"] for case in case_reports if case["status"] == "EVALUATED") / len(runnable_cases),
        "stability": sum(case["stability"] for case in case_reports if case["status"] == "EVALUATED") / len(runnable_cases),
        "over_orchestration_rate": over_total / expected_total,
        "safety_pass_rate": safety_correct / safety_total if safety_total else 1.0,
    }
    thresholds = case_data["suite"]["thresholds"]
    gates = {
        "packet_validity": metrics["packet_validity"] >= thresholds["packet_validity"],
        "route_accuracy": metrics["route_accuracy"] >= thresholds["route_accuracy"],
        "stability": metrics["stability"] >= thresholds["stability"],
        "over_orchestration_rate": metrics["over_orchestration_rate"] <= thresholds["max_over_orchestration_rate"],
        "safety_pass_rate": metrics["safety_pass_rate"] >= thresholds["safety_pass_rate"],
    }
    report = {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "metrics": metrics,
        "gates": gates,
        "evaluated_cases": len(runnable_cases),
        "unrun_cases": len(cases) - len(runnable_cases),
        "cases": case_reports,
    }
    return report, []


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=root / "references" / "behavior-evaluation-cases.json")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--json-report", type=Path)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args(argv)
    try:
        policy = load_validation_policy(args.policy)
        _configure_policy(policy)
        cases = _load_json(args.cases)
        results = _load_json(args.results)
        reviews = _load_json(args.reviews) if args.reviews else None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Behavior evaluation input error: {exc}", file=sys.stderr)
        return 2
    errors = validate_case_suite(cases, policy=policy)
    if errors:
        print("Behavior evaluation case validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    report, errors = evaluate(cases, results)
    if errors:
        print("Behavior evaluation result validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    if reviews is not None:
        human_report, review_errors = validate_reviews(
            reviews,
            case_ids={case["id"] for case in cases["cases"]},
            run_id=results["run"]["run_id"],
            valid_trials={
                (trial.get("case_id"), trial.get("trial_index"))
                for trial in results["trials"]
                if isinstance(trial, dict)
            },
        )
        if review_errors:
            print("Human review validation failed:", file=sys.stderr)
            for error in review_errors:
                print(f"- {error}", file=sys.stderr)
            return 2
        report["human_review"] = human_report
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_report:
        args.json_report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
