# Workflow Template

Use this template only after the workflow catalog shows a distinct repeated outcome that cannot be handled by `DIRECT` or `ROUTE_ONE`. Replace every placeholder and remove unused regions; budgets are caps, not targets.

The equivalent conservative skeleton can be generated with `scripts/scaffold_workflow.py`. Shared validation bounds and supported values are defined in [validation-policy.json](validation-policy.json).

## Minimal Contract

<!-- example-workflow-contract -->
```json
{
  "id": "example-workflow",
  "version": "1",
  "controller": "hybrid",
  "topology": "SEQUENTIAL(PARALLEL_SECTION)",
  "tasks": [
    {"id": "frame", "objective": "Define the bounded outcome.", "owner": "coordinator", "required_output": "Scope and acceptance criteria.", "dependencies": []},
    {"id": "branch_a", "objective": "Produce independent evidence A.", "owner": "worker", "required_output": "Evidence A.", "dependencies": ["frame"]},
    {"id": "branch_b", "objective": "Produce independent evidence B.", "owner": "worker", "required_output": "Evidence B.", "dependencies": ["frame"]},
    {"id": "join", "objective": "Reconcile branch results.", "owner": "coordinator", "required_output": "Joined result with failures preserved.", "dependencies": ["branch_a", "branch_b"]}
  ],
  "edges": [
    {"from": "frame", "to": "branch_a", "kind": "control"},
    {"from": "frame", "to": "branch_b", "kind": "control"},
    {"from": "branch_a", "to": "join", "kind": "data"},
    {"from": "branch_b", "to": "join", "kind": "data"}
  ],
  "topology_regions": [
    {"id": "main", "primitive": "SEQUENTIAL", "task_ids": ["frame", "branch_a", "branch_b", "join"]},
    {"id": "evidence", "primitive": "PARALLEL_SECTION", "branches": [["branch_a"], ["branch_b"]], "join_task": "join", "join_mode": "all_settled", "failure_mode": "preserve"}
  ],
  "join_policy": {"evidence": "Wait for all branches and preserve failures."},
  "context_policy": {"coordinator": "Retains canonical scope.", "workers": "Receive immutable frame inputs only."},
  "budget": {"max_workers": 2, "max_parallel_branches": 2, "max_delegation_depth": 1, "max_review_rounds": 0},
  "stop_conditions": ["Stop after an accepted joined result or exhausted budget."],
  "failure_policy": {"branch_failure": "Return surviving evidence and the failed branch explicitly."},
  "verification": {"checks": ["Every result traces to a declared task."], "evaluator": "coordinator", "acceptance": "The joined result satisfies the frame."},
  "output": {"owner": "coordinator", "required_sections": ["result", "failures"], "completion_rule": "Distinguish complete and partial outcomes."}
}
```

## Field Rules

- `id` and `version` must match the catalog entry.
- `controller` is `code`, `llm`, or `hybrid`.
- `topology` contains only canonical primitives and describes composition, not status.
- `tasks` own one bounded objective and output each; `dependencies` are startup barriers.
- `edges` mirror every dependency and use only `data`, `control`, or `context`.
- `topology_regions` map each selected primitive to concrete tasks. Parallel regions declare branches, join, join mode, and failure behavior. A `quorum` adds its threshold, acceptance oracle, independence basis, and no-quorum behavior. A `first_acceptable` join adds its oracle, remaining-branch policy, safe-cancellation evidence when applicable, and no-result behavior.
- Dynamic Worker regions declare a planner, worker template, creation and deduplication rules, join, worker cap, depth 1, stop conditions, and failure behavior. `HANDOFF` regions declare source/target tasks and owners, minimized context, acceptance, and failure semantics.
- Review regions declare tasks, maximum rounds, and an exit task outside the region. Human gates declare the exact activation condition.
- `join_policy`, `context_policy`, `failure_policy`, `verification`, and `output` remain structured and nonempty.
- `budget` values are numeric caps and must respect repository limits.
- `stop_conditions` include successful, partial/blocked, cancellation, and budget exits when applicable.

For a complete contract, start with the closest workflow in this repository and change only rules justified by the new outcome. Do not copy a topology merely because its shape looks familiar.
