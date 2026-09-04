# Artifact Creation Workflow

The coordinator owns the brief, acceptance criteria, and authoritative output. Specialists create within a shared structure and asset plan; the produced artifact is rendered and inspected when applicable, then revised only through a bounded review loop.

<!-- workflow-contract -->
```json
{
  "id": "artifact-creation",
  "version": "2",
  "controller": "hybrid",
  "topology": "SEQUENTIAL(PARALLEL_SECTION,REVIEW_LOOP)",
  "tasks": [
    {
      "id": "brief",
      "objective": "Define the audience, purpose, format, delivery target, acceptance criteria, constraints, and required assets.",
      "owner": "coordinator",
      "required_output": "An artifact brief with audience needs, intended use, format requirements, asset inventory, and explicit non-goals.",
      "dependencies": []
    },
    {
      "id": "structure",
      "objective": "Design the artifact's information structure, sequence, hierarchy, and format-specific organization.",
      "owner": "structure-worker",
      "required_output": "A structured outline or layout specification mapped to the brief and acceptance criteria.",
      "dependencies": ["brief"]
    },
    {
      "id": "assets",
      "objective": "Inspect, select, or prepare authorized source assets and identify missing or unusable dependencies.",
      "owner": "asset-worker",
      "required_output": "An asset manifest with source, rights or authority constraints, intended placement, and missing-asset gaps.",
      "dependencies": ["brief"]
    },
    {
      "id": "create",
      "objective": "Create the complete artifact in its requested format using the approved structure and available assets.",
      "owner": "artifact-specialist",
      "required_output": "A coherent artifact candidate plus a list of substitutions, omissions, and unresolved production constraints.",
      "dependencies": ["structure", "assets"]
    },
    {
      "id": "render_inspect",
      "objective": "Render and inspect the actual produced artifact when the format supports rendering; otherwise inspect the authoritative native representation.",
      "owner": "inspection-worker",
      "required_output": "Rendered or native inspection evidence covering completeness, layout, legibility, assets, and format integrity, or an explicit renderer gap.",
      "dependencies": ["create"]
    },
    {
      "id": "review",
      "objective": "Evaluate content, audience fit, purpose, structure, visual or format quality, accessibility, and inspection findings against the brief.",
      "owner": "review-worker",
      "required_output": "Prioritized actionable findings with a pass or revise decision.",
      "dependencies": ["render_inspect"]
    },
    {
      "id": "finalize",
      "objective": "Apply supported revisions, render and inspect the revised artifact when applicable, recheck affected criteria, and designate exactly one authoritative output.",
      "owner": "artifact-specialist",
      "required_output": "The authoritative artifact with inspection evidence for its final version, revision notes, and any unresolved limitations.",
      "dependencies": ["review"]
    },
    {
      "id": "report",
      "objective": "Deliver the authoritative artifact and accurately report verification, substitutions, partial failures, and remaining limitations.",
      "owner": "coordinator",
      "required_output": "A user-facing artifact handoff with authoritative location or representation and quality status.",
      "dependencies": ["finalize"]
    }
  ],
  "edges": [
    {"from": "brief", "to": "structure", "kind": "control"},
    {"from": "brief", "to": "assets", "kind": "control"},
    {"from": "structure", "to": "create", "kind": "data"},
    {"from": "assets", "to": "create", "kind": "data"},
    {"from": "create", "to": "render_inspect", "kind": "data"},
    {"from": "render_inspect", "to": "review", "kind": "data"},
    {"from": "review", "to": "finalize", "kind": "data"},
    {"from": "finalize", "to": "report", "kind": "data"}
  ],
  "topology_regions": [
    {
      "id": "main",
      "primitive": "SEQUENTIAL",
      "task_ids": ["brief", "structure", "assets", "create", "render_inspect", "review", "finalize", "report"]
    },
    {
      "id": "preproduction",
      "primitive": "PARALLEL_SECTION",
      "branches": [["structure"], ["assets"]],
      "join_task": "create",
      "join_mode": "all_settled",
      "failure_mode": "preserve"
    },
    {
      "id": "artifact_review",
      "primitive": "REVIEW_LOOP",
      "task_ids": ["render_inspect", "review", "finalize"],
      "exit_task": "report",
      "max_rounds": 2,
      "exit_conditions": ["pass", "no_material_progress", "budget_exhausted"]
    }
  ],
  "join_policy": {
    "preproduction": "Join structure and asset outputs before creation; preserve missing assets and constraints instead of silently substituting them.",
    "inspection": "Review the actual rendered artifact when applicable and carry every supported defect or renderer limitation into revision and reporting.",
    "finalization": "Apply only brief-aligned corrections, stop at pass or the review cap, and designate one final artifact as authoritative."
  },
  "context_policy": {
    "coordinator": "Retains the canonical brief, acceptance criteria, authority boundary, and authoritative-output decision.",
    "specialists": "Receive the brief plus only declared dependency outputs and assets needed for their bounded task.",
    "reviewer": "Receives the brief, artifact candidate, and actual render or native inspection evidence without unrelated history.",
    "state": "Only the artifact specialist mutates the artifact candidate; parallel workers do not share mutable artifact ownership."
  },
  "budget": {
    "max_workers": 3,
    "max_parallel_branches": 2,
    "max_delegation_depth": 2,
    "max_review_rounds": 2,
    "max_render_attempts_per_round": 2
  },
  "stop_conditions": [
    "Stop successfully when the authoritative artifact meets the brief and applicable render or native inspection checks pass.",
    "Stop review after two rounds or one round with no material progress.",
    "Stop with a partial artifact when missing assets or renderer failure prevents full acceptance but the remaining output is usable and clearly bounded.",
    "Stop on cancellation, exhausted budget, unrecoverable format corruption, or a required action outside current authority."
  ],
  "failure_policy": {
    "missing_asset": "Use an authorized substitute only when it preserves the brief; otherwise retain a labeled placeholder or omit the affected element and report the impact.",
    "renderer_failure": "Attempt a bounded equivalent renderer or native inspection; if neither verifies presentation, return the artifact as unrendered and do not claim visual acceptance.",
    "review_failure": "Preserve the latest inspectable candidate, identify failed and unrun criteria, and do not promote it as fully accepted.",
    "partial_result": "Return a usable artifact only with its authoritative version, completed scope, substitutions, missing elements, and unverified qualities explicit."
  },
  "verification": {
    "checks": [
      "The artifact serves the stated audience and purpose in the requested format and structure.",
      "Required content and assets are present, authorized, and correctly placed, or their gaps and substitutions are explicit.",
      "The actual artifact was rendered and inspected when applicable, with layout, legibility, completeness, and format integrity checked.",
      "Exactly one authoritative output is identified and all review and budget limits were respected."
    ],
    "evaluator": "coordinator",
    "acceptance": "All required brief criteria pass against the actual artifact, or the output is explicitly partial with failed and unrun checks preserved."
  },
  "output": {
    "owner": "coordinator",
    "required_sections": ["authoritative_artifact", "audience_and_purpose", "format", "assets", "render_or_inspection", "review_status", "partial_failures", "limitations"],
    "completion_rule": "Deliver exactly one authoritative artifact and distinguish accepted, partial, blocked, and failed outcomes from actual inspection evidence."
  }
}
```

The coordinator may omit unused parallelism or revision rounds, but it may not skip applicable inspection of the produced artifact.
