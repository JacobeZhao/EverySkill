# Diagnosis Workflow

The coordinator keeps the investigation read-only, preserves the observed facts separately from inference, and owns the causal report. Independent candidates and evidence checks are bounded; disagreement and unknowns survive the join instead of being averaged away. Any repair or state mutation requires separate authorization outside this workflow.

<!-- workflow-contract -->
```json
{
  "id": "diagnosis",
  "version": "1",
  "controller": "hybrid",
  "topology": "SEQUENTIAL(PARALLEL_SAMPLE,PARALLEL_SECTION)",
  "tasks": [
    {
      "id": "frame",
      "objective": "Define the observed behavior, expected behavior, investigation boundary, and evidence quality requirements.",
      "owner": "coordinator",
      "required_output": "A neutral problem statement with known facts, unknowns, and read-only constraints.",
      "dependencies": []
    },
    {
      "id": "hypothesis_a",
      "objective": "Propose a falsifiable causal hypothesis from the scoped observations.",
      "owner": "hypothesis-worker",
      "required_output": "One candidate cause with predictions, supporting clues, and disconfirming evidence to seek.",
      "dependencies": ["frame"]
    },
    {
      "id": "hypothesis_b",
      "objective": "Independently propose an alternative falsifiable causal hypothesis.",
      "owner": "hypothesis-worker",
      "required_output": "One distinct candidate cause with predictions, supporting clues, and disconfirming evidence to seek.",
      "dependencies": ["frame"]
    },
    {
      "id": "hypothesis_c",
      "objective": "Independently challenge likely assumptions with a third falsifiable hypothesis when evidence warrants it.",
      "owner": "hypothesis-worker",
      "required_output": "A distinct candidate or an explicit statement that a defensible third candidate is unavailable.",
      "dependencies": ["frame"]
    },
    {
      "id": "evidence_a",
      "objective": "Test the predictions of the first hypothesis using bounded read-only inspection.",
      "owner": "evidence-worker",
      "required_output": "Observations with provenance and their support, contradiction, or ambiguity for the hypothesis.",
      "dependencies": ["hypothesis_a"]
    },
    {
      "id": "evidence_b",
      "objective": "Test the predictions of the second hypothesis using bounded read-only inspection.",
      "owner": "evidence-worker",
      "required_output": "Observations with provenance and their support, contradiction, or ambiguity for the hypothesis.",
      "dependencies": ["hypothesis_b"]
    },
    {
      "id": "evidence_c",
      "objective": "Test the third hypothesis or document why it could not be tested within the evidence boundary.",
      "owner": "evidence-worker",
      "required_output": "Observations with provenance, or an explicit evidence gap.",
      "dependencies": ["hypothesis_c"]
    },
    {
      "id": "judge",
      "objective": "Compare predictions with evidence, reject contradicted candidates, rank surviving causes, and preserve unresolved alternatives.",
      "owner": "judge",
      "required_output": "An evidence matrix, causal assessment, confidence statement, and unresolved unknowns.",
      "dependencies": ["evidence_a", "evidence_b", "evidence_c"]
    },
    {
      "id": "report",
      "objective": "Explain the observed behavior from the judged evidence without implying repair authority or certainty beyond the record.",
      "owner": "coordinator",
      "required_output": "A user-facing diagnosis with evidence, confidence, alternatives, unknowns, and bounded next checks.",
      "dependencies": ["judge"]
    }
  ],
  "edges": [
    {"from": "frame", "to": "hypothesis_a", "kind": "control"},
    {"from": "frame", "to": "hypothesis_b", "kind": "control"},
    {"from": "frame", "to": "hypothesis_c", "kind": "control"},
    {"from": "hypothesis_a", "to": "evidence_a", "kind": "data"},
    {"from": "hypothesis_b", "to": "evidence_b", "kind": "data"},
    {"from": "hypothesis_c", "to": "evidence_c", "kind": "data"},
    {"from": "evidence_a", "to": "judge", "kind": "data"},
    {"from": "evidence_b", "to": "judge", "kind": "data"},
    {"from": "evidence_c", "to": "judge", "kind": "data"},
    {"from": "judge", "to": "report", "kind": "data"}
  ],
  "join_policy": {
    "hypotheses": "Keep candidates independent until evidence collection begins and deduplicate only logically equivalent claims.",
    "evidence": "Wait for available branches, preserve contradictions and provenance, and never treat majority agreement as proof.",
    "judge": "Rank by explanatory and predictive support; retain ties, ambiguity, and untested candidates explicitly."
  },
  "context_policy": {
    "coordinator": "Retains the canonical observations, investigation boundary, authority constraints, and aggregate evidence.",
    "hypothesis_workers": "Receive the neutral frame without other workers' candidate conclusions.",
    "evidence_workers": "Receive only the frame, assigned hypothesis, permitted read-only sources, and required evidence format.",
    "state": "All investigation tasks are read-only; do not modify code, configuration, data, services, or external systems."
  },
  "budget": {
    "max_workers": 3,
    "max_parallel_branches": 3,
    "max_delegation_depth": 2,
    "max_review_rounds": 2,
    "max_evidence_passes_per_hypothesis": 2
  },
  "stop_conditions": [
    "Stop successfully when one cause has sufficient direct evidence and material alternatives have been addressed.",
    "Stop with an inconclusive result when remaining evidence is unavailable, unsafe to obtain, or outside the authorized boundary.",
    "Stop after two evidence passes without material confidence improvement.",
    "Stop on cancellation, exhausted budget, or discovery that further investigation would require mutation."
  ],
  "failure_policy": {
    "branch_failure": "Continue with surviving branches only when their evidence can still support a useful assessment; preserve the failed branch and its missing evidence.",
    "conflicting_evidence": "Do not force consensus; report competing explanations and the observation that would distinguish them.",
    "insufficient_evidence": "Return an inconclusive diagnosis with verified facts, rejected candidates, live hypotheses, and bounded next checks.",
    "partial_result": "A partial report must separate observed facts, inferences, confidence, unavailable evidence, and unknowns."
  },
  "verification": {
    "checks": [
      "Every causal claim cites observed evidence or is labeled as a hypothesis.",
      "Material competing hypotheses were tested or retained with an explicit evidence gap.",
      "Evidence provenance and contradictions are preserved.",
      "No investigation task mutated target state and all budget limits were respected."
    ],
    "evaluator": "coordinator",
    "acceptance": "The report is evidence-traceable and calibrated, including when the defensible result is inconclusive."
  },
  "output": {
    "owner": "coordinator",
    "required_sections": ["observations", "causal_assessment", "evidence", "alternatives", "confidence", "unknowns", "next_checks"],
    "completion_rule": "State confirmed, probable, possible, or inconclusive according to the evidence and preserve unresolved alternatives."
  }
}
```

The coordinator may use fewer than three branches when the evidence cannot support distinct candidates. Unused capacity does not weaken an otherwise sufficient diagnosis.
