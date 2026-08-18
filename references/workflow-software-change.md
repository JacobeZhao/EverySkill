# Software Change Workflow

The coordinator keeps the change bounded to the authorized objective, gives each worker only its task inputs, and owns the final report. Exploration may run concurrently, but implementation begins only after the plan and applicable authority checkpoint are satisfied. Review findings feed at most two repair rounds; verification records both successes and unresolved failures.

<!-- workflow-contract -->
```json
{
  "id": "software-change",
  "version": "1",
  "controller": "hybrid",
  "topology": "SEQUENTIAL(PARALLEL_SECTION,REVIEW_LOOP)",
  "tasks": [
    {
      "id": "scope",
      "objective": "Restate the authorized change boundary, acceptance criteria, and protected paths before delegating work.",
      "owner": "coordinator",
      "required_output": "A bounded scope statement with acceptance checks and explicit non-goals.",
      "dependencies": []
    },
    {
      "id": "explore_implementation",
      "objective": "Inspect the smallest relevant implementation surface and identify established local patterns.",
      "owner": "exploration-worker",
      "required_output": "Evidence-backed implementation locations, dependencies, and constraints.",
      "dependencies": ["scope"]
    },
    {
      "id": "explore_verification",
      "objective": "Inspect relevant tests and validation commands without changing state.",
      "owner": "verification-worker",
      "required_output": "Applicable checks, coverage gaps, and likely regression boundaries.",
      "dependencies": ["scope"]
    },
    {
      "id": "plan",
      "objective": "Synthesize exploration into the smallest implementation plan that meets the acceptance criteria.",
      "owner": "coordinator",
      "required_output": "Ordered edits, verification steps, rollback considerations, and remaining unknowns.",
      "dependencies": ["explore_implementation", "explore_verification"]
    },
    {
      "id": "authority_gate",
      "objective": "Confirm that every planned mutation is within current authority; pause for a human decision when it is not.",
      "owner": "coordinator",
      "required_output": "A proceed decision for authorized mutations or a precise blocked decision.",
      "dependencies": ["plan"]
    },
    {
      "id": "implement",
      "objective": "Apply only the approved edits while preserving unrelated work.",
      "owner": "implementation-worker",
      "required_output": "Changed artifacts plus a concise account of deviations from the plan.",
      "dependencies": ["authority_gate"]
    },
    {
      "id": "review",
      "objective": "Evaluate the current change against scope, correctness, regressions, and repository conventions.",
      "owner": "review-worker",
      "required_output": "Prioritized findings with evidence and an explicit pass or revise decision.",
      "dependencies": ["implement"]
    },
    {
      "id": "revise",
      "objective": "Apply only supported in-scope review corrections, or preserve the unchanged artifact when review passes.",
      "owner": "implementation-worker",
      "required_output": "A revised artifact with addressed findings, or an explicit no-change pass result.",
      "dependencies": ["review"]
    },
    {
      "id": "verify",
      "objective": "Run the planned focused checks and any justified integration checks against the reviewed artifact.",
      "owner": "verification-worker",
      "required_output": "Check outcomes, commands or evidence, and unresolved validation gaps.",
      "dependencies": ["revise"]
    },
    {
      "id": "report",
      "objective": "Report the delivered change, verification evidence, partial failures, and remaining risks without overstating completion.",
      "owner": "coordinator",
      "required_output": "A user-facing change and verification report.",
      "dependencies": ["verify"]
    }
  ],
  "edges": [
    {"from": "scope", "to": "explore_implementation", "kind": "control"},
    {"from": "scope", "to": "explore_verification", "kind": "control"},
    {"from": "explore_implementation", "to": "plan", "kind": "data"},
    {"from": "explore_verification", "to": "plan", "kind": "data"},
    {"from": "plan", "to": "authority_gate", "kind": "control"},
    {"from": "authority_gate", "to": "implement", "kind": "control"},
    {"from": "implement", "to": "review", "kind": "data"},
    {"from": "review", "to": "revise", "kind": "data"},
    {"from": "revise", "to": "verify", "kind": "data"},
    {"from": "verify", "to": "report", "kind": "data"}
  ],
  "join_policy": {
    "exploration": "Wait for both exploration branches when available; if one fails, continue only when the surviving evidence is sufficient and record the missing branch.",
    "review": "The coordinator preserves every supported finding; the implementation worker applies only in-scope corrections and the loop stops after a pass, no progress, or the review-round cap.",
    "report": "Merge implementation, review, and verification evidence while preserving conflicts and unknowns."
  },
  "context_policy": {
    "coordinator": "Retains the canonical request, current authority boundary, plan, and aggregate evidence.",
    "workers": "Receive only scoped paths, acceptance criteria, required inputs, and outputs from declared dependencies.",
    "state": "Workers preserve unrelated workspace changes and do not share mutable ownership of the same artifact concurrently."
  },
  "budget": {
    "max_workers": 3,
    "max_parallel_branches": 2,
    "max_delegation_depth": 2,
    "max_review_rounds": 2,
    "max_exploration_passes_per_branch": 1
  },
  "stop_conditions": [
    "Stop successfully when the authorized change meets acceptance criteria and planned verification passes.",
    "Pause before mutation when the authority checkpoint cannot produce a proceed decision.",
    "Stop iterative repair after two review rounds or one round with no material progress.",
    "Stop on cancellation, exhausted budget, or a failure that makes further work unsafe or misleading."
  ],
  "failure_policy": {
    "exploration_failure": "Use sufficient surviving evidence when safe; otherwise stop before planning and report the missing dependency.",
    "implementation_failure": "Preserve recoverable workspace state, do not broaden scope, and report completed and incomplete edits separately.",
    "review_or_verification_failure": "Do not claim completion; report passed checks, failed checks, unrun checks, and the authoritative artifact state.",
    "partial_result": "Return usable in-scope work only when its boundaries and unverified aspects are explicit."
  },
  "verification": {
    "checks": [
      "Changed artifacts stay within the authorized scope and unrelated work is preserved.",
      "Acceptance criteria have direct evidence from focused tests, static checks, inspection, or justified integration checks.",
      "The task graph, review cap, and budget limits were respected.",
      "Failures and unrun checks remain visible in the final report."
    ],
    "evaluator": "coordinator",
    "acceptance": "All required criteria pass, or the result is explicitly reported as partial or blocked with evidence."
  },
  "output": {
    "owner": "coordinator",
    "required_sections": ["changed_artifacts", "behavior", "verification", "partial_failures", "remaining_risks"],
    "completion_rule": "Distinguish complete, partial, blocked, and failed outcomes using the actual evidence."
  }
}
```

The coordinator may omit unused parallelism or review iterations. It must not invent work to consume the budget.
