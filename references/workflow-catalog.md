# Workflow Catalog

Catalog version: `1`

Use this catalog only after visible skill ownership is known and `DIRECT` or straightforward `ROUTE_ONE` is insufficient. A workflow supplies a task-local procedure; it does not own capabilities, grant authority, or replace the intent DAG.

## Selection Table

| ID | Version | Primary requested outcome | Exclude or defer | Reference |
| --- | --- | --- | --- | --- |
| `software-change` | `1` | Modify software, configuration, or tests; implement a feature; fix a defect | Cause-finding or explanation without modification authority | [Software change](workflow-software-change.md) |
| `diagnosis` | `1` | Establish why observed behavior occurs and report evidence or confidence | A known cause with a direct authorized fix | [Diagnosis](workflow-diagnosis.md) |
| `research-decision` | `1` | Gather evidence, compare alternatives, rank, recommend, or decide | Causal diagnosis of one observed system | [Research and decision](workflow-research-decision.md) |
| `artifact-creation` | `1` | Create or substantially revise a non-code artifact with staged quality checks | A simple artifact operation adequately owned by one specialist | [Artifact creation](workflow-artifact-creation.md) |

## Precedence

1. Apply higher-priority constraints, requested mode, authority, explicit skills, and strong target ownership first.
2. Preserve the `DIRECT` or `ROUTE_ONE` fast path when it is sufficient.
3. Select by the primary requested deliverable, not by isolated nouns in the prompt.
4. Choose `software-change` for an authorized software modification; include diagnosis as a stage when the cause is unknown.
5. Choose `diagnosis` when the requested deliverable is a causal explanation and do not infer repair authority.
6. Choose `research-decision` when the comparison or recommendation is the deliverable.
7. Choose `artifact-creation` when research only supports the requested artifact.

## Composition And Ambiguity

- Select at most one workflow per intent node and one lead workflow per deliverable.
- Treat common supporting work as a stage in the lead workflow instead of loading another reference.
- Compose workflows only for distinct deliverables with separate acceptance criteria and an explicit join policy.
- Never let workflow references route to one another or recursively select EverySkill.
- Ask one blocking question only when different choices materially change the deliverable, authority, compatibility, or verification.
- If a reference or required capability is unavailable, use semantically equivalent core handling within the same authority boundary, ask for clarification, or block. Never simulate the missing capability.

## Extension Contract

To add a workflow:

1. Add one unique catalog row with a stable ID, version, primary outcome, exclusions, and shallow reference path.
2. Add one directly linked workflow reference with exactly one `<!-- workflow-contract -->` marker followed by a parseable JSON contract using the shared fields in `SKILL.md`.
3. Add positive, near-miss, overlap, authority, failure, and budget cases to `workflow-scenarios.json`.
4. Run structural validation and fresh-agent forward tests.
5. Change `SKILL.md` only to add the direct progressive-disclosure link or to evolve a universal contract.

Increment a workflow version for a material task, edge, authority, budget, stop, failure, join, or verification change. Increment the catalog version for a material matching, precedence, composition, or reference-path change. Both participate in Route Packet freshness.
