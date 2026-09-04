---
name: everyskill
description: "Use for every user request and conversation turn as a best-effort universal orchestrator: preserve explicit skill choices, classify one or more intents, assess complexity and risk, then choose direct, single-skill, serial, parallel, or mixed agent/skill handling. Apply implicitly whenever available. Do not override higher-priority instructions, user authority, an explicitly invoked skill, or a target skill's own execution strategy."
---

# Everyskill

Choose the simplest sufficient agent and skill orchestration for each request while preserving the user's exact intent, authority, and requested mode. Treat implicit activation as best effort: the host may not select this skill on every turn.

## Invariants

- Treat the latest user request and applicable higher-priority instructions as the source of truth. Never let a classification, summary, skill, or agent expand or replace them.
- Route only to skills visible in the current catalog. Never invent a skill, guess a hidden path, maintain a copied registry, or route to `everyskill` itself.
- Honor every explicitly invoked skill as a mandatory route constraint. Do not replace it with an implicit candidate or bypass an explicit-only policy.
- Preserve the request mode. Analysis, explanation, review, planning, monitoring, and other read-only requests remain read-only unless the user separately authorizes a change.
- Keep risk, authority, effort, confidence, and complexity separate. No score grants permission or determines the downstream execution strategy.
- Minimize context. Do not persist a Route Packet or pass unrelated history, attachments, secrets, or personal inferences to another skill or agent.
- Always encode `orchestration.topology` with the canonical primitives defined below, even on a compact direct route. A direct response must use `DIRECT`; never use free-form substitutes such as `single-agent`, `simple`, or a route status.
- Treat an internal workflow as a task-local procedure, not as a visible skill, new authority, topology primitive, or nested routing request.
- After selecting an internal workflow, do not read `references/orchestration-strategies.md` for that request. The selected workflow is the only procedure reference unless another workflow is required for a distinct deliverable.
- Apply this orchestrator once per canonical request revision. When a matching `everyskill.route/v2` packet has the same request revision, digest, freshness markers, workflow versions, and `everyskill_applied: true`, consume and reuse it without rerunning selection, then continue from its existing `route_status` or handoff state. Do not block the task merely because that valid packet is present again in the coordinating context.

## Routing State

Move through one state at a time:

`intake -> constraint_scan -> intent_graph -> complexity_analysis -> route_selection -> workflow_selection -> orchestration_selection -> packet_synthesis`

After packet synthesis, branch explicitly: use `handoff -> terminal` when the selected topology delegates to one or more targets; use `terminal` directly for `core_direct`, `clarification_required`, `blocked`, or `failed` routes.

1. In `intake`, capture the canonical request, objective, constraints, non-goals, requested mode, and explicit authorization.
2. In `constraint_scan`, identify explicit skills, strong target signals, side effects, dependencies, catalog visibility, and applicable instructions.
3. In `intent_graph`, split the request into atomic intent nodes and connect their dependencies.
4. In `complexity_analysis`, score all six axes from observable request evidence.
5. In `route_selection`, select only visible skills using the priority rules below.
6. In `workflow_selection`, keep the fast path or select the smallest matching internal workflow by primary requested outcome.
7. In `orchestration_selection`, instantiate the workflow or choose the controller and simplest topology that provides a material benefit for the intent DAG.
8. In `packet_synthesis`, create the smallest useful `everyskill.route/v2` packet.
9. Enter `handoff` when the topology delegates work; apply each target's instructions in the current agent context and give it only its packet slice. Otherwise enter `terminal` directly.

At `terminal`, set `route_status` to exactly one of `core_direct`, `routed`, `clarification_required`, `blocked`, or `failed`. Treat `routed` as successful selection and handoff, not as successful completion of downstream work. Keep individual validation outcomes in `checks` with `pass`, `fail`, `blocked`, or `unrun`; never use a check outcome as the route status.

Invalidate a packet when the latest user intent, request revision, authority, target system, relevant catalog visibility, material dependency, or risk changes. Create a higher `packet_revision`; do not treat invalidation as permission for recursive routing.

## Build The Intent DAG

Assign exactly one primary intent class and exactly one primary owner (`skill-name` or `core`) to each atomic node. Give every node its own objective, required output, and dependencies. Add auxiliary skills only for distinct supporting work. Keep multiple user outcomes as separate nodes; do not force a multi-intent request into one leaf.

Use these classes:

- `I0 control`: converse, clarify, confirm, cancel, pause, resume, or report workflow status.
- `I1 communicate`: answer, explain, teach, summarize supplied content, or translate.
- `I2 retrieve`: find, read, search, enumerate, or obtain current state without evaluating it.
- `I3 analyze`: compare, evaluate, review, audit, inspect, or diagnose.
- `I4 decide`: recommend, rank, select, prioritize, or support a decision.
- `I5 plan`: plan, design, specify, model, or architect without performing the resulting change.
- `I6 create`: generate, export, or convert a new local or conversational artifact.
- `I7 modify`: edit, fix, refactor, update, or delete an existing local or conversational artifact or codebase.
- `I8 transact`: execute, manage, send, approve, deploy, delete, or mutate an external, business, or persistent application system outside local or conversational artifact handling.
- `I9 monitor`: wait, subscribe, poll, check periodically, or respond when a condition changes.

Apply these boundaries:

- Use `I0` as primary only when control or conversation is the outcome; otherwise make it an auxiliary control node.
- Use `I1` for an answer from supplied or stable knowledge and `I2` when retrieval or current state is required.
- Use `I3` to establish findings, `I4` to choose among options, and `I5` to produce a future design or sequence.
- Use `I6` to create a new local or conversational artifact. Use `I7` to edit or delete an existing local or conversational artifact or codebase; keep destructive-file authority separate from classification. Use `I8` only for a transaction against an external, business, or persistent application system outside that local artifact boundary. A request may contain dependent nodes from more than one class.
- Use `I9` only when work continues across time or awaits a condition; a one-time current-state lookup is `I2`.

Attach open labels without creating new intent classes: `domain`, `target_system`, `artifact`, `entity`, `action`, `modality`, `temporal`, and `side_effect`.

## Analyze Complexity

Score each axis independently as `K0`, `K1`, `K2`, or `K3`. Record short evidence for every non-zero score. Never compute or report an aggregate complexity score.

| Axis | K0 | K1 | K2 | K3 |
| --- | --- | --- | --- | --- |
| `breadth` | one atomic outcome | a few same-domain outcomes | multiple components or modules | multiple domains or systems |
| `dependency` | none | short local sequence | several tools, shared outputs, or external dependencies | critical, circular, or materially unknown dependency chain |
| `uncertainty` | inputs and outcome are explicit | minor reversible assumptions | research or material ambiguity | conflicting, open-ended, or safety-critical unknowns |
| `context` | prompt is sufficient | small local context needed | repository, history, or several artifacts needed | multiple large, distributed, or possibly omitted sources |
| `coordination` | one direct actor | a short serial handoff | multiple skills, agents, or people | concurrent cross-system work or shared mutable state |
| `verification` | self-evident response | one focused check | multiple independent or integration checks | high-stakes external oracle plus recovery evidence |

Record these independent assessments:

- `risk`: use `T1 narrow` for local, readily reversible work, including ordinary reversible artifact persistence, with no shared contract, permission boundary, concurrency, external integration, or material blast radius; `T2 shared` for shared callers, contracts, cross-module behavior, meaningful failure paths, or external-facing quality where rollback remains straightforward; `T3 critical` for authentication or authorization mechanisms, secrets or privacy, destructive or difficult-to-reverse persistent effects, unresolved material authority, concurrency correctness, external contracts, difficult rollback, or high blast radius; and `UNRESOLVED` when other material risk evidence is insufficient to choose safely. Use the highest-trigger envelope: any T3 trigger makes the whole affected route T3, T3 is highest, and `UNRESOLVED` blocks the risk-bearing action rather than defaulting lower. Do not classify all persistence or all authority questions as T3.
- `authority`: list allowed and forbidden actions separately, then set status to exactly one of `sufficient`, `conditional`, `missing`, `forbidden`, or `unknown`.
- `effort`: `micro`, `small`, `medium`, `large`, or `open_ended`; use it only as a workload estimate.
- `confidence`: `high`, `medium`, or `low`, with the evidence gap that would change the route.

Apply authority status before any action. `sufficient` may proceed only within listed allowed actions. `conditional` may proceed only after every stated condition is met; otherwise clarify when a user answer can satisfy the condition, or block. `missing` sets `route_status: blocked` and `error_code: AUTHORITY_REQUIRED`. `forbidden` sets `blocked` and `AUTHORITY_FORBIDDEN`; a higher-priority prohibition cannot be cured by lower-priority instructions or user permission. `unknown` sets `clarification_required` and `AUTHORITY_UNKNOWN` when clarification can resolve it, otherwise `blocked`. Routing, skill selection, complexity, and successful handoff never grant authority.

## Select Skills

Resolve candidates in this order:

1. Applicable system, developer, repository, safety, and latest-user constraints.
2. Every skill explicitly invoked by the user.
3. Exact URL or token type, tagged application, file type, target product, or other strong ownership signal.
4. An exact workflow or umbrella skill whose own router owns the domain.
5. A specialized skill whose visible description matches the node.
6. `core` when no visible specialist is necessary or available.

Prefer one primary owner per node. Use multiple skills only when the DAG contains distinct owned work or a target skill requires an auxiliary capability. Preserve all compatible explicit skills; ask one blocking question when conflicting choices would materially change behavior, data, security, compatibility, or authority.

Treat the catalog as dynamic and potentially incomplete. Set coverage to `visible`, `possibly_truncated`, or `unknown`. Claim only the best visible match. If a skill is omitted, disabled, unavailable, or disallows implicit invocation, do not simulate it.

## Select Internal Workflow

Skip internal workflow loading when `DIRECT` or a straightforward `ROUTE_ONE` can satisfy the request. Otherwise read [references/workflow-catalog.md](references/workflow-catalog.md), choose by primary requested outcome after visible skill ownership is known, and load only the selected workflow reference:

- **Authorized software or configuration change:** [software change](references/workflow-software-change.md)
- **Cause-finding without implied repair authority:** [diagnosis](references/workflow-diagnosis.md)
- **Evidence gathering, comparison, or recommendation as the deliverable:** [research and decision](references/workflow-research-decision.md)
- **Substantial non-code artifact creation or revision:** [artifact creation](references/workflow-artifact-creation.md)

Use at most one workflow per intent node and one lead workflow per deliverable. Treat supporting behavior as stages inside the lead workflow. Load multiple workflow references only for distinct deliverables with separate acceptance criteria, then compose their nodes through the intent DAG. Ask one blocking question only when the primary outcome would materially change authority, the deliverable, compatibility, or verification.

Each selected workflow must supply bounded tasks and edges, owners, context inputs, join behavior, budget, stop and failure conditions, verification, and the coordinator-owned output. It may not redefine intent classes, risk, authority, skills, topology primitives, packet fields, statuses, error codes, or freshness rules. Matching a workflow grants neither capability nor permission; unavailable capabilities must produce a safe fallback, clarification, or block.

Treat the single JSON block immediately following `<!-- workflow-contract -->` in each workflow reference as the canonical structured contract. Require `id`, `version`, `controller`, `topology`, `tasks`, `edges`, `join_policy`, `context_policy`, `budget`, `stop_conditions`, `failure_policy`, `verification`, and `output`. Keep matching criteria in the catalog and keep surrounding workflow prose explanatory; do not duplicate either source.

When adding or validating workflows, read [references/workflow-scenarios.json](references/workflow-scenarios.json). Do not load scenario fixtures during ordinary request handling.

When authoring a new workflow, use [the workflow template](references/workflow-template.md) and follow [the authoring guide](references/workflow-authoring-guide.md). These are authoring references, not additional runtime workflows.

## Select Orchestration

Read [references/orchestration-strategies.md](references/orchestration-strategies.md) only when designing or extending workflows, or when no internal workflow fits a request that still needs orchestration. Never load it after selecting an internal workflow for the current request. Skip it for self-evident direct responses and straightforward single-skill handoffs.

For any nontrivial topology decision, apply [the topology selection rules](references/topology-selection.md). Use its independence test, edge semantics, join modes, and required selection record. The task graph remains an outer DAG; represent bounded review or retry behavior as a declared `topology_regions` entry, never as an unbounded back-edge.

Choose among these canonical primitives: `DIRECT`, `ROUTE_ONE`, `HANDOFF`, `SEQUENTIAL`, `PARALLEL_SECTION`, `PARALLEL_SAMPLE`, `ORCHESTRATOR_WORKERS`, `REVIEW_LOOP`, and `HUMAN_GATE`. Compose complex work as a DAG of these primitives instead of inventing a new named pattern.

Record `orchestration.topology` only with canonical primitive names or an explicit composition of them. Keep topology orthogonal to `route_status`: for example, a direct answer uses topology `DIRECT` with status `core_direct`, while a turn that only proposes a future `PARALLEL_SECTION` plan may also finish as `core_direct` because no delegation occurred in the current turn. Never substitute a route status such as `core_direct` or `routed` for a topology name.

- Prefer `DIRECT` or `ROUTE_ONE` unless added coordination has a specific expected benefit.
- Use `SEQUENTIAL` only for real data or control dependencies.
- Use `PARALLEL_SECTION` only for independent subtasks with an explicit join policy.
- Use `PARALLEL_SAMPLE` only when diverse attempts or voting can improve confidence enough to justify the cost.
- Use `ORCHESTRATOR_WORKERS` when required subtasks cannot be known reliably in advance.
- Add `REVIEW_LOOP` only when evaluation criteria and stop conditions are explicit.
- Add `HUMAN_GATE` for unresolved authority, consequential actions, or decisions that require human judgment.

Select `code`, `llm`, or `hybrid` control independently from the topology. Prefer deterministic code control for known flows and a bounded hybrid controller for open-ended work. Never infer a topology directly from a complexity score, spawn agents merely because a score is high, or add coordination without identifying its benefit, budget, join behavior, and termination condition.

Before handoff, compare the selected topology with [the host capability contract](references/host-capabilities.md). A capability fallback may serialize execution or reduce verification, but it may not change task meaning, expand authority, or simulate success.

## Create The Route Packet

Use a compact packet internally for a trivial, high-confidence `core` route, but still record `orchestration.topology: DIRECT`. Emit or pass the extended fields only when routing to a skill, handling multiple nodes, resolving uncertainty, or guarding material risk.

Use [the Route Packet examples](references/route-packet-examples.md) as semantic examples only. Generate identifiers, digests, freshness markers, authority, and execution state from the current request and host; never copy example placeholders as current truth.

Use this exact topology/status pairing for a direct response:

```text
orchestration.topology: DIRECT
route_status: core_direct
```

```text
Route Packet: everyskill.route/v2
packet_id; packet_revision; request_revision; request_digest; version_guard
truth_source; freshness[turn_marker, request_digest, capability_catalog_marker, workflow_catalog_marker, authority_marker]
canonical_objective; constraints; non_goals; requested_mode; authority_summary
intent_nodes[id, primary_class, objective, required_output, dependencies, open_labels, primary_owner, auxiliary_skills]
intent_dag[from, to, reason]
primary_skills; auxiliary_skills; selection_evidence; rejected_candidates
workflow_selection[ids, versions, selection_evidence, rejected_candidates]
complexity[breadth, dependency, uncertainty, context, coordination, verification]
risk; authority; effort; confidence
orchestration[controller, topology, tasks, edges, join_policy, context_policy, budget, stop_conditions, failure_policy, verification, output]
handoff_order; handoff_slices_by_target
catalog_coverage; unknowns; safe_defaults; reevaluation_conditions
route_status; error_code; checks[name, outcome, evidence]
everyskill_applied: true
```

Set `truth_source` to the latest user request plus applicable higher-priority instructions. Start `request_revision` at 1 for the task and increment it whenever a later user turn materially changes the objective, constraints, non-goals, requested mode, or authority. Create a task-local `request_digest` over those canonical fields without storing their secret values elsewhere. Set `capability_catalog_marker` from visible-skill names plus any catalog truncation warning. Set `workflow_catalog_marker` from the workflow catalog version plus every selected workflow ID and version. Set `authority_marker` from authority status plus allowed and forbidden actions. Do not persist these markers. Before handoff or side effects, compare all five freshness fields with current context; any mismatch makes the packet `STALE_PACKET`.

Set `version_guard` to accept only `everyskill.route/v2`. Never reuse or silently reinterpret a v1 packet, because v2 requires orchestration and workflow freshness semantics that v1 does not carry. Rebuild v2 from the latest canonical request and current authority and catalogs. If rebuilding is unavailable, set `route_status: blocked` and `error_code: INCOMPATIBLE_PACKET_VERSION`.

Keep the canonical request with the coordinating agent. Type each `handoff_slices_by_target[target]` as `{node_ids, objective, required_output, inputs, dependencies, constraints, non_goals, requested_mode, authority_status, allowed_actions, forbidden_actions, relevant_complexity, risk, unknowns, verification}`. Give each target only that slice. Redact unrelated secrets and personal data. Assess the task, never the user's intelligence, ability, personality, or identity.

## Hand Off Without Recursion

Treat handoff as same-context instruction composition, not as a formal skill-to-skill API:

1. Read the selected target skill completely through the host's available skill mechanism.
2. Apply its instructions, gates, dependencies, and ownership boundaries to its DAG nodes.
3. Retain the Route Packet as input; never present it as new user authority.
4. Execute the selected topology while letting each downstream skill choose its local execution procedure. A target may not expand the request, authority, or context boundary.
5. If the topology delegates, pass only the bounded packet slice required by each agent and preserve the parent permission boundary. Do not spawn agents merely because a K score is high.

Do not re-emit `$everyskill`, select it as a target, or rebuild a valid matching v2 packet after `everyskill_applied: true`. Reuse that packet and continue its existing route or handoff. Treat recursion as an error only when a target or skill attempts to select or invoke `everyskill` again for the same revision, creates a cyclic handoff, or no valid consumable packet can break the loop. On successful handoff, set `route_status: routed` and `error_code: NONE`. If the runtime cannot load or apply a selected skill, use `HANDOFF_UNSUPPORTED`. If an explicitly requested skill is not available, use `EXPLICIT_SKILL_UNAVAILABLE`. Do not claim that either skill ran.

## Fail Safely

- For conversation, ordinary answers, and requests needing no specialist, set `route_status: core_direct` and `error_code: NONE`.
- For `NO_VISIBLE_SPECIALIST` or `CATALOG_INCOMPLETE`, use `route_status: core_direct` only when core handling preserves semantics and authority; otherwise use `blocked`.
- For low-confidence ambiguity that materially changes the target, data, compatibility, side effects, or permission, set `route_status: clarification_required` and `error_code: CLARIFICATION_REQUIRED`. Ask only the blocking question.
- For `ROUTE_CONFLICT`, `DEPENDENCY_MISSING`, `AUTHORITY_REQUIRED`, `AUTHORITY_FORBIDDEN`, `SKILL_POLICY_BLOCKED`, `HANDOFF_UNSUPPORTED`, `EXPLICIT_SKILL_UNAVAILABLE`, or `INCOMPATIBLE_PACKET_VERSION`, set `route_status: blocked` before the affected action. Handle `AUTHORITY_UNKNOWN` by the authority rule above. Routing never grants authority.
- For `TARGET_FAILED`, fall back only to a semantically equivalent route for the same system and permission boundary; otherwise set `route_status: failed`.
- Reuse a valid matching same-revision v2 packet and continue from its current state without changing `route_status`. Use `route_status: blocked` and `error_code: RECURSION_BLOCKED` only for a repeated same-revision invocation of `everyskill`, a cyclic handoff, or a loop with no valid consumable packet. For failed freshness, rebuild before handoff; if rebuilding is unavailable, set `blocked` and `STALE_PACKET`. Handle an incompatible version with `INCOMPATIBLE_PACKET_VERSION` instead.
- Set `error_code` to the applicable uppercase code above, or `NONE`. Record material checks separately as `pass`, `fail`, `blocked`, or `unrun`. Never describe an unavailable or unexecuted target as successful.
