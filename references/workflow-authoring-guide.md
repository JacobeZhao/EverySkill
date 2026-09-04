# Workflow Authoring Guide

## Before Adding A Workflow

Confirm that the outcome is repeated, materially distinct from existing catalog entries, and not adequately served by `DIRECT`, `ROUTE_ONE`, or a stage inside an existing workflow. A workflow is a task-local procedure, not a new capability or permission grant.

## Authoring Steps

1. Write one sentence naming the primary deliverable and its exclusions.
2. Add a unique ID, version, matching outcome, exclusion, and shallow reference path to `workflow-catalog.md`.
3. Copy `workflow-template.md` into a new `workflow-<name>.md` file.
4. Define tasks before topology. Give every task one objective, owner, required output, and dependencies.
5. Add one typed edge for every dependency.
6. Apply `topology-selection.md` and choose the smallest justified primitives.
7. Map primitives to tasks with `topology_regions`; define join, handoff, bounded dynamic-worker, and bounded-loop semantics where applicable. Use the advanced topology examples as fixtures, not as a reason to add complexity.
8. Define context minimization, authority boundary, budgets, failure propagation, stop conditions, verification, and authoritative output.
9. Link the workflow directly from `SKILL.md` only when it is part of the supported catalog.
10. Add one positive case, one near-miss, and every triggered authority, failure, budget, degradation, and version case to `workflow-scenarios.json`.
11. Run the validator and tests.

## Review Questions

- Could a simpler topology produce the same accepted result?
- Does every parallel branch pass the independence test?
- Does every fan-in have one explicit join mode?
- Does every quorum define acceptable independent evidence rather than equating votes with truth?
- Can every first-acceptable cancellation stop disposable work without losing external state?
- Are dynamic workers deduplicated, capped, and unable to create another worker level?
- Does every handoff identify its target, context slice, acceptance oracle, and failure state?
- Does the outer task graph remain acyclic?
- Are review and retry regions bounded by rounds and no-progress exits?
- Can missing authority, capability, or evidence be reported without pretending execution succeeded?
- Is one coordinator the authoritative owner of the final result?
- Are positive and near-miss examples distinguishable by the primary deliverable rather than keywords?

## Versioning

Increment the workflow version when tasks, dependencies, topology regions, authority, budget, join, failure, stop, verification, or output semantics change. Increment the catalog version when matching, precedence, composition, or reference paths change. Increment the scenario schema when required scenario fields or meanings change.
