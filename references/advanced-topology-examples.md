# Advanced Topology Examples

These examples are configuration fixtures, not executable schedulers. They show the minimum evidence required before selecting advanced joins, dynamic workers, or a cross-owner handoff.

<!-- advanced-topology-examples -->
```json
{
  "schema_version": "1",
  "examples": [
    {
      "id": "independent-evidence-quorum",
      "topology": "SEQUENTIAL(PARALLEL_SECTION)",
      "tasks": [
        {"id": "frame", "objective": "Freeze the question and evidence frame.", "owner": "coordinator", "required_output": "immutable frame", "dependencies": []},
        {"id": "lane-a", "objective": "Collect source class A.", "owner": "researcher-a", "required_output": "cited findings", "dependencies": ["frame"]},
        {"id": "lane-b", "objective": "Collect source class B.", "owner": "researcher-b", "required_output": "cited findings", "dependencies": ["frame"]},
        {"id": "lane-c", "objective": "Collect source class C.", "owner": "researcher-c", "required_output": "cited findings", "dependencies": ["frame"]},
        {"id": "join", "objective": "Accept a sufficient independent evidence set.", "owner": "coordinator", "required_output": "quorum decision", "dependencies": ["lane-a", "lane-b", "lane-c"]}
      ],
      "edges": [
        {"from": "frame", "to": "lane-a", "kind": "context"},
        {"from": "frame", "to": "lane-b", "kind": "context"},
        {"from": "frame", "to": "lane-c", "kind": "context"},
        {"from": "lane-a", "to": "join", "kind": "data"},
        {"from": "lane-b", "to": "join", "kind": "data"},
        {"from": "lane-c", "to": "join", "kind": "data"}
      ],
      "topology_regions": [
        {"id": "ordered-frame", "primitive": "SEQUENTIAL", "task_ids": ["frame", "join"]},
        {"id": "evidence-quorum", "primitive": "PARALLEL_SECTION", "branches": [["lane-a"], ["lane-b"], ["lane-c"]], "join_task": "join", "join_mode": "quorum", "min_acceptable": 2, "acceptance_oracle": "Each accepted lane supplies traceable evidence for the same frozen question.", "independence_basis": "The lanes use disjoint source classes and do not consume one another's output.", "on_quorum_failure": "Stop and report missing or rejected lanes.", "failure_mode": "Preserve every failed lane and do not treat vote count as truth."}
      ],
      "budget": {"max_workers": 3, "max_parallel_branches": 3, "max_delegation_depth": 1, "max_review_rounds": 0}
    },
    {
      "id": "first-safe-repro",
      "topology": "SEQUENTIAL(PARALLEL_SAMPLE)",
      "tasks": [
        {"id": "freeze", "objective": "Freeze the defect and isolated fixture.", "owner": "coordinator", "required_output": "reproduction frame", "dependencies": []},
        {"id": "attempt-a", "objective": "Try reproduction strategy A.", "owner": "diagnostician-a", "required_output": "reproduction evidence", "dependencies": ["freeze"]},
        {"id": "attempt-b", "objective": "Try reproduction strategy B.", "owner": "diagnostician-b", "required_output": "reproduction evidence", "dependencies": ["freeze"]},
        {"id": "accept", "objective": "Accept the first independently reproducible result.", "owner": "coordinator", "required_output": "accepted reproduction", "dependencies": ["attempt-a", "attempt-b"]}
      ],
      "edges": [
        {"from": "freeze", "to": "attempt-a", "kind": "context"},
        {"from": "freeze", "to": "attempt-b", "kind": "context"},
        {"from": "attempt-a", "to": "accept", "kind": "data"},
        {"from": "attempt-b", "to": "accept", "kind": "data"}
      ],
      "topology_regions": [
        {"id": "ordered-repro", "primitive": "SEQUENTIAL", "task_ids": ["freeze", "accept"]},
        {"id": "first-repro", "primitive": "PARALLEL_SAMPLE", "branches": [["attempt-a"], ["attempt-b"]], "join_task": "accept", "join_mode": "first_acceptable", "acceptance_oracle": "The isolated test fails repeatedly for the claimed reason.", "remaining_branch_policy": "cancel", "disposable_or_cancellation_evidence": "Both attempts use disposable fixtures and expose cooperative cancellation before external effects.", "no_result_behavior": "Wait for all settled attempts, then report that reproduction is unproven.", "failure_mode": "Never infer a cause from an unaccepted attempt."}
      ],
      "budget": {"max_workers": 2, "max_parallel_branches": 2, "max_delegation_depth": 1, "max_review_rounds": 0}
    },
    {
      "id": "bounded-discovery-workers",
      "topology": "SEQUENTIAL(ORCHESTRATOR_WORKERS)",
      "tasks": [
        {"id": "plan", "objective": "Inspect an index and identify unknown bounded partitions.", "owner": "coordinator", "required_output": "deduplicated worker specifications", "dependencies": []},
        {"id": "join", "objective": "Reconcile worker reports.", "owner": "coordinator", "required_output": "coverage report", "dependencies": ["plan"]},
        {"id": "report", "objective": "Report covered and uncovered partitions.", "owner": "coordinator", "required_output": "bounded result", "dependencies": ["join"]}
      ],
      "edges": [
        {"from": "plan", "to": "join", "kind": "control"},
        {"from": "join", "to": "report", "kind": "data"}
      ],
      "topology_regions": [
        {"id": "ordered-workers", "primitive": "SEQUENTIAL", "task_ids": ["plan", "join", "report"]},
        {"id": "dynamic-partitions", "primitive": "ORCHESTRATOR_WORKERS", "planner_task": "plan", "worker_template": {"objective": "Inspect exactly one discovered partition.", "owner": "read-only worker", "required_output": "partition evidence"}, "creation_rule": "Create one worker only for each uncovered partition returned by plan.", "dedup_key": "canonical partition identifier", "max_workers": 4, "max_depth": 1, "join_task": "join", "join_mode": "all_settled", "stop_conditions": ["all discovered partitions settled", "worker cap reached", "no new deduplicated partition"], "failure_mode": "Preserve failed and uncovered partitions in the coverage report."}
      ],
      "budget": {"max_workers": 4, "max_parallel_branches": 4, "max_delegation_depth": 1, "max_review_rounds": 0}
    },
    {
      "id": "same-context-owner-handoff",
      "topology": "SEQUENTIAL(HANDOFF)",
      "tasks": [
        {"id": "route", "objective": "Select the visible owner and minimize its packet slice.", "owner": "everyskill", "required_output": "bounded route packet", "dependencies": []},
        {"id": "target", "objective": "Apply the selected Skill in the current Agent context.", "owner": "selected-skill", "required_output": "skill-owned result", "dependencies": ["route"]},
        {"id": "integrate", "objective": "Preserve status and report the result.", "owner": "everyskill", "required_output": "coordinated response", "dependencies": ["target"]}
      ],
      "edges": [
        {"from": "route", "to": "target", "kind": "context"},
        {"from": "target", "to": "integrate", "kind": "data"}
      ],
      "topology_regions": [
        {"id": "ordered-handoff", "primitive": "SEQUENTIAL", "task_ids": ["route", "target", "integrate"]},
        {"id": "owner-transfer", "primitive": "HANDOFF", "source_task": "route", "target_task": "target", "source_owner": "everyskill", "target_owner": "selected-skill", "context_contract": ["canonical request", "authority facts", "required output", "relevant constraints"], "acceptance_oracle": "The target owns the requested outcome and returns an explicit downstream status.", "failure_mode": "Preserve target failure; do not silently substitute another permission boundary."}
      ],
      "budget": {"max_workers": 1, "max_parallel_branches": 1, "max_delegation_depth": 1, "max_review_rounds": 0}
    }
  ]
}
```

The outer task graph remains acyclic. Conditional quorum readiness, cooperative cancellation, and dynamic worker creation are region semantics, not unbounded back-edges or hidden tasks.
