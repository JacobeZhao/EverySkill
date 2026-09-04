# Topology Selection

Use this reference after intent and visible-skill ownership are known and before instantiating a workflow. Select the smallest topology whose benefit is supported by the request graph. Complexity alone never requires more agents.

## Decision Order

1. Apply authority and capability gates. Forbidden work is `blocked`; a human gate cannot cure a prohibition.
2. Use `DIRECT` when the coordinator can produce the complete result without a specialist or material decomposition.
3. Use `ROUTE_ONE` when one visible specialist owns the complete outcome and no cross-owner join is needed.
4. Add `SEQUENTIAL` only where one task consumes another task's output or requires its control decision.
5. Add parallelism only for branches that can start from immutable shared inputs and do not write the same state.
6. Add review or sampling only when it improves a named acceptance property enough to justify its budget.
7. Add `HUMAN_GATE` only when a human decision can resolve conditional or unknown authority, compatibility, or product judgment.
8. Add `HANDOFF` only when ownership actually transfers to a visible target with a bounded context contract and explicit return status.

## Primitive Decision Table

| Primitive | Required evidence | Use when | Do not use when | Required controls |
| --- | --- | --- | --- | --- |
| `DIRECT` | One atomic outcome; coordinator has capability and authority | The answer or action is self-contained | A named specialist is mandatory or a real dependency exists | Record the direct-result oracle |
| `ROUTE_ONE` | One visible owner covers the outcome | One specialist can complete and verify the work | Multiple owners must exchange outputs or reconcile results | Define input, required output, authority, and failure result |
| `HANDOFF` | A selected target owns the next procedure | Ownership transfers in the same Agent context or across a declared host boundary | The coordinator is still the complete owner or the target is unavailable | Declare source and target owners/tasks, minimized context, acceptance oracle, and failure status |
| `SEQUENTIAL` | A data or control dependency between stages | A later task cannot start correctly before an earlier result | Ordering is only cosmetic | Declare the dependency edge and handoff output |
| `PARALLEL_SECTION` | Two or more independent branches from immutable inputs | All branches are required or useful and a join can reconcile them | Branches share mutable ownership or one consumes another | Declare branches, join task, join mode, branch budget, and failure propagation |
| `PARALLEL_SAMPLE` | Independent attempts can reduce uncertainty | Diverse hypotheses, evaluations, or candidate solutions improve confidence | The task has one deterministic answer or attempts would contaminate each other | Isolate prompts/context, define diversity requirement and evidence-based adjudication |
| `ORCHESTRATOR_WORKERS` | Required branches cannot be known reliably at planning time | Discovery must create bounded follow-up tasks | A fixed DAG is already known | Define worker creation rule, depth/worker cap, join rule, and stop condition |
| `REVIEW_LOOP` | Explicit evaluator, repair owner, pass rule, and bounded improvement opportunity | Review findings can trigger an in-scope correction | Acceptance is subjective without criteria or no writer can revise | Keep the outer graph acyclic; define region tasks, max rounds, pass and no-progress exits |
| `HUMAN_GATE` | A human answer can resolve the pending decision | Authority is conditional/unknown or consequential judgment is reserved for a person | An action is forbidden or no user answer can supply the missing capability | State the question, allowed answers, resume state, and blocked fallback |

## Parallel Independence Test

Branches may run concurrently only when all conditions hold:

- neither branch consumes the other's output;
- both can start from the same immutable upstream version;
- they do not mutate the same artifact, record, or external state;
- their failures can be represented independently at the join;
- running both stays within worker, context, token, time, and cost budgets.

If any condition fails, use a sequential edge or split read-only discovery from single-owner mutation.

## Edge Semantics

- `data`: the target consumes the source output. The source must settle successfully or the join policy must explicitly allow a partial result.
- `control`: the source grants ordering or permission; its full output is not automatically forwarded.
- `context`: the target receives a declared, minimized context slice derived from the source.

Every edge is also a startup dependency. A task becomes eligible only after its declared dependencies reach states accepted by the applicable join policy.

## Join Modes

- `all`: every branch must succeed.
- `all_settled`: wait for every branch, then preserve successes, failures, and missing evidence separately.
- `quorum`: continue after a declared minimum number of acceptable independent results; never use majority as proof by itself.
- `first_acceptable`: continue after the first result meeting a predeclared oracle and cancel or ignore remaining disposable branches safely.

A `quorum` region declares `min_acceptable`, an `acceptance_oracle`, the basis for branch independence, and behavior when quorum is not reached. The threshold must not exceed branch count.

A `first_acceptable` region declares its acceptance oracle, whether remaining branches are cancelled or ignored, evidence that cancellation is cooperative and disposable when cancellation is selected, and behavior when no result qualifies.

Every parallel region declares exactly one join task and one join mode. The join records conflicts and failed branches instead of erasing them.

## Dynamic Workers

`ORCHESTRATOR_WORKERS` is a bounded discovery region, not permission for recursive delegation. Declare the planner task, worker template, creation rule, deduplication key, join task and mode, worker cap, stop conditions, and failure behavior. EverySkill contracts cap dynamic delegation at depth 1; workers cannot create workers.

## Handoff Semantics

A handoff transfers procedure ownership, not request ownership or authority. The coordinator retains the canonical request and passes only the target's required context slice. The target returns an explicit downstream status and evidence for the handoff acceptance oracle. Failure remains visible; a fallback target requires a new compatible routing decision and may not cross the original permission boundary.

## Graph Measures

Use structural measures unless real observations exist:

- structural critical path: the longest dependency chain through the outer DAG;
- parallel width: the largest number of simultaneously eligible branches;
- fan-out: the number of independent branches opened by a node or region;
- fan-in: the number of branches reconciled by a join.

Do not claim numeric latency, success probability, or token savings without measured inputs. Review rounds and retries are bounded region costs, not back-edges in the outer DAG.

## Selection Record

For every non-direct topology, record:

```text
selected primitives; task and edge evidence; expected benefit;
rejected simpler topology and reason; join mode; authority state;
budget; stop conditions; capability fallback; acceptance oracle
```
