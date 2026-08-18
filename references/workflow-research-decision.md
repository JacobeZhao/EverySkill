# Research And Decision Workflow

The coordinator owns the criteria, evidence ledger, comparison, and final decision record. Evidence lanes remain independent until normalization; synthesis preserves provenance, conflicts, missing evidence, and uncertainty rather than forcing agreement.

<!-- workflow-contract -->
```json
{
  "id": "research-decision",
  "version": "1",
  "controller": "hybrid",
  "topology": "SEQUENTIAL(PARALLEL_SECTION,REVIEW_LOOP)",
  "tasks": [
    {
      "id": "frame",
      "objective": "Define the decision, alternatives, constraints, evaluation criteria, evidence requirements, and decision deadline.",
      "owner": "coordinator",
      "required_output": "A decision frame with weighted or ordered criteria, exclusions, evidence standards, and known unknowns.",
      "dependencies": []
    },
    {
      "id": "evidence_fit",
      "objective": "Independently gather evidence about how each alternative satisfies the stated criteria.",
      "owner": "research-worker",
      "required_output": "Criterion-linked findings with source provenance, observation dates, and confidence.",
      "dependencies": ["frame"]
    },
    {
      "id": "evidence_cost_risk",
      "objective": "Independently gather evidence about costs, constraints, tradeoffs, and failure modes for each alternative.",
      "owner": "research-worker",
      "required_output": "Comparable cost, constraint, and risk findings with provenance, dates, and confidence.",
      "dependencies": ["frame"]
    },
    {
      "id": "evidence_counter",
      "objective": "Seek disconfirming evidence, omitted alternatives, and credible challenges to likely conclusions.",
      "owner": "research-worker",
      "required_output": "Counterevidence, coverage gaps, and challenged assumptions with provenance and dates.",
      "dependencies": ["frame"]
    },
    {
      "id": "normalize",
      "objective": "Normalize units, time horizons, definitions, source quality, and evidence freshness without erasing source-specific limitations.",
      "owner": "comparison-worker",
      "required_output": "A criterion-by-alternative comparison with normalized values, source dates, freshness judgments, and explicit non-comparable fields.",
      "dependencies": ["evidence_fit", "evidence_cost_risk", "evidence_counter"]
    },
    {
      "id": "synthesize",
      "objective": "Compare alternatives against the criteria, preserve material conflicts, and produce a supported recommendation or calibrated uncertainty.",
      "owner": "coordinator",
      "required_output": "A recommendation, ranking, or inconclusive result with rationale, conflicts, sensitivity, confidence, and missing evidence.",
      "dependencies": ["normalize"]
    },
    {
      "id": "review",
      "objective": "Review criterion coverage, comparison fairness, provenance, freshness, conflict preservation, and calibration.",
      "owner": "review-worker",
      "required_output": "Prioritized findings and a pass or revise decision against the decision frame.",
      "dependencies": ["synthesize"]
    },
    {
      "id": "report",
      "objective": "Apply supported review corrections and publish the authoritative decision record without overstating certainty.",
      "owner": "coordinator",
      "required_output": "A user-facing comparison and recommendation, or an explicit uncertainty result, with evidence and limitations.",
      "dependencies": ["review"]
    }
  ],
  "edges": [
    {"from": "frame", "to": "evidence_fit", "kind": "control"},
    {"from": "frame", "to": "evidence_cost_risk", "kind": "control"},
    {"from": "frame", "to": "evidence_counter", "kind": "control"},
    {"from": "evidence_fit", "to": "normalize", "kind": "data"},
    {"from": "evidence_cost_risk", "to": "normalize", "kind": "data"},
    {"from": "evidence_counter", "to": "normalize", "kind": "data"},
    {"from": "normalize", "to": "synthesize", "kind": "data"},
    {"from": "synthesize", "to": "review", "kind": "data"},
    {"from": "review", "to": "report", "kind": "data"}
  ],
  "join_policy": {
    "evidence": "Wait for available independent lanes, preserve provenance and contradictions, and continue with partial evidence only when its limits remain explicit.",
    "comparison": "Normalize only defensible dimensions; retain missing, stale, disputed, and non-comparable evidence as distinct states.",
    "decision": "Apply the stated criteria and sensitivity checks; preserve tied or conflicting outcomes and return uncertainty when evidence cannot support a recommendation."
  },
  "context_policy": {
    "coordinator": "Retains the canonical decision frame, criteria, constraints, and aggregate evidence ledger.",
    "research_workers": "Receive the decision frame and assigned evidence lane, but not other lanes' conclusions before submitting independent findings.",
    "comparison_and_review": "Receive criterion-linked findings with provenance, dates, confidence, and declared gaps; unrelated context is excluded.",
    "state": "Research stays within the current authority boundary and does not treat workflow selection as permission for external action."
  },
  "budget": {
    "max_workers": 4,
    "max_parallel_branches": 3,
    "max_delegation_depth": 2,
    "max_review_rounds": 2,
    "max_evidence_passes_per_lane": 2
  },
  "stop_conditions": [
    "Stop successfully when criteria are covered and the evidence supports a calibrated recommendation or defensible inconclusive result.",
    "Stop collection when added evidence no longer materially changes coverage, ranking, or confidence.",
    "Stop review after two rounds or one round with no material progress.",
    "Stop on cancellation, exhausted budget, unavailable decisive evidence, or a required action outside current authority."
  ],
  "failure_policy": {
    "lane_failure": "Continue only when surviving lanes support a useful comparison; identify the missing lane and affected criteria.",
    "stale_evidence": "Label stale evidence and reduce confidence or withhold a recommendation when freshness is decision-critical.",
    "conflicting_evidence": "Preserve competing findings, provenance, and the evidence needed to resolve them; do not average conflict away.",
    "partial_result": "Return covered criteria, available evidence, provisional comparisons, gaps, and the decision impact of each gap."
  },
  "verification": {
    "checks": [
      "Every material conclusion traces to criterion-linked evidence with provenance and an observation date or explicit freshness gap.",
      "Units, definitions, time horizons, and source quality are normalized or marked non-comparable.",
      "Counterevidence, conflicts, missing lanes, and sensitivity to assumptions remain visible.",
      "The recommendation strength matches the evidence and all budget limits were respected."
    ],
    "evaluator": "coordinator",
    "acceptance": "The decision record is traceable, comparable, freshness-aware, and calibrated; an inconclusive result is acceptable when uncertainty is irreducible."
  },
  "output": {
    "owner": "coordinator",
    "required_sections": ["decision_frame", "criteria", "evidence", "comparison", "conflicts", "recommendation_or_uncertainty", "confidence", "freshness", "gaps"],
    "completion_rule": "Publish the coordinator's reviewed decision record as authoritative and distinguish supported recommendation, provisional recommendation, and inconclusive result."
  }
}
```

The coordinator may use fewer lanes or review rounds when they add no material evidence or quality benefit.
