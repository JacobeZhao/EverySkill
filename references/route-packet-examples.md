# Route Packet Examples

These examples illustrate required semantics. Runtime identifiers, digests, and freshness markers must come from the actual host; never copy the placeholders as current values.

## Complete v2 Example

This is a field-complete worked example for an authorized research decision. Values prefixed with `example-` are illustrative and must be rebuilt from current host state.

```yaml
packet_type: everyskill.route/v2
packet_id: example-research-001
packet_revision: 1
request_revision: 1
request_digest: example-current-request-digest
version_guard: everyskill.route/v2-only
truth_source: latest user request plus applicable higher-priority instructions
freshness:
  turn_marker: example-current-turn
  request_digest: example-current-request-digest
  capability_catalog_marker: example-visible-skills
  workflow_catalog_marker: catalog-2/research-decision-2
  authority_marker: sufficient/read-only-authorized-sources
canonical_objective: Compare three storage options and recommend one with evidence.
constraints: [read only, cite provenance, preserve unknowns]
non_goals: [purchase a product, change external state]
requested_mode: research and recommendation
authority_summary:
  status: sufficient
  allowed: [read authorized and public sources]
  forbidden: [external mutation, secret access]
intent_nodes:
  - id: decide
    primary_class: I4 decide
    objective: Produce a calibrated recommendation.
    required_output: Evidence-backed comparison and recommendation or uncertainty.
    dependencies: []
    open_labels: {domain: storage, side_effect: read_only}
    primary_owner: research-specialist
    auxiliary_skills: []
intent_dag: []
primary_skills: [research-specialist]
auxiliary_skills: []
selection_evidence: One research owner can execute the selected workflow and preserve provenance.
rejected_candidates: [{candidate: core, reason: current multi-source evidence is required}]
workflow_selection:
  ids: [research-decision]
  versions: ['2']
  selection_evidence: Comparison and recommendation are the primary deliverable.
  rejected_candidates: [{candidate: diagnosis, reason: the request is not causal analysis of one observed system}]
complexity:
  breadth: K1
  dependency: K2
  uncertainty: K2
  context: K2
  coordination: K2
  verification: K2
risk: T1 narrow; authorized read-only research with no external mutation
authority: sufficient
effort: medium
confidence: medium; source availability may change evidence coverage
orchestration:
  controller: hybrid
  topology: SEQUENTIAL(PARALLEL_SECTION,REVIEW_LOOP)
  tasks: [frame, evidence_fit, evidence_cost_risk, evidence_counter, normalize, synthesize, review, report]
  edges:
    - {from: frame, to: evidence_fit, kind: control}
    - {from: frame, to: evidence_cost_risk, kind: control}
    - {from: frame, to: evidence_counter, kind: control}
    - {from: evidence_fit, to: normalize, kind: data}
    - {from: evidence_cost_risk, to: normalize, kind: data}
    - {from: evidence_counter, to: normalize, kind: data}
    - {from: normalize, to: synthesize, kind: data}
    - {from: synthesize, to: review, kind: data}
    - {from: review, to: report, kind: data}
  join_policy: {task: normalize, mode: all_settled, preserve: [failures, conflicts, provenance]}
  context_policy: Workers receive the decision frame and only their assigned evidence lane.
  budget: {max_workers: 4, max_parallel_branches: 3, max_delegation_depth: 2, max_review_rounds: 2}
  stop_conditions: [accepted calibrated result, no material progress, exhausted budget, unavailable decisive evidence]
  failure_policy: Continue with partial evidence only when affected criteria and confidence loss remain explicit.
  verification: [provenance, comparability, counterevidence, freshness, calibrated confidence]
  output: Coordinator-owned decision record.
handoff_order: [research-specialist]
handoff_slices_by_target:
  research-specialist:
    node_ids: [decide]
    objective: Produce the comparison and recommendation.
    required_output: Reviewed decision record.
    inputs: [canonical request, criteria, authorized source boundary]
    dependencies: []
    constraints: [read only, preserve provenance]
    non_goals: [external mutation]
    requested_mode: research and recommendation
    authority_status: sufficient
    allowed_actions: [read authorized and public sources]
    forbidden_actions: [purchase, deploy, secret access]
    relevant_complexity: [uncertainty K2, verification K2]
    risk: T1 narrow
    unknowns: [source availability]
    verification: [criterion coverage, provenance, counterevidence]
catalog_coverage: visible
unknowns: [availability and freshness of decisive evidence]
safe_defaults: [preserve uncertainty, stop before external action]
reevaluation_conditions: [request change, authority change, catalog change, missing decisive capability]
route_status: routed
error_code: NONE
checks:
  - {name: authority boundary, outcome: pass, evidence: requested work is read only}
  - {name: source availability, outcome: unrun, evidence: evaluated during workflow execution}
everyskill_applied: true
```

## Direct

```text
Route Packet: everyskill.route/v2
canonical_objective: explain the supplied constant
requested_mode: explanation
intent_nodes: [explain -> owner core]
workflow_selection: none
orchestration.controller: llm
orchestration.topology: DIRECT
authority.status: sufficient
route_status: core_direct
error_code: NONE
everyskill_applied: true
```

## Parallel Evidence With Join

```text
Route Packet: everyskill.route/v2
canonical_objective: compare alternatives and recommend one with evidence
workflow_selection: research-decision@2
orchestration.topology: SEQUENTIAL(PARALLEL_SECTION,REVIEW_LOOP)
tasks: frame -> [evidence_fit, evidence_cost_risk, evidence_counter] -> normalize -> synthesize -> review -> report
join: normalize; mode: all_settled; failures remain visible
review: evaluator review-worker; max_rounds: 2; exits: pass | no_progress | budget_exhausted
authority.status: sufficient; allowed: authorized read-only research
verification: provenance, comparability, counterevidence, calibration
route_status: routed
error_code: NONE
everyskill_applied: true
```

## Conditional Authority Gate

```text
Route Packet: everyskill.route/v2
canonical_objective: modify a protected resource after owner approval
orchestration.topology: HUMAN_GATE
authority.status: conditional
gate.question: identify the authorized owner decision for this exact resource and operation
gate.resume_state: rebuild freshness markers, then continue only if authority becomes sufficient
gate.fallback: blocked
route_status: blocked
error_code: AUTHORITY_REQUIRED
everyskill_applied: true
```

Forbidden authority does not use a human gate: it returns `blocked` with `AUTHORITY_FORBIDDEN`.

## Partial Branch Failure

```text
selected topology: PARALLEL_SECTION
join mode: all_settled
branch states: fit=complete; cost_risk=failed; counter=complete
join decision: continue only for criteria supported by surviving evidence
output: partial; preserve the failed lane, affected criteria, confidence loss, and unrun checks
```

## Stale Packet

```text
version_guard: everyskill.route/v2
freshness result: workflow catalog marker mismatch
action: rebuild from the current request, catalog, capabilities, and authority
fallback when rebuilding inputs are unavailable: blocked / STALE_PACKET
```
