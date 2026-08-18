---
name: everyskill
description: "Use for every user request and conversation turn as a best-effort universal router: preserve explicit skill choices, classify one or more intents, assess six task-complexity dimensions, and hand a compact Route Packet to the best visible specialized skill(s) or core handling. Apply implicitly whenever available. Do not override higher-priority instructions, user authority, an explicitly invoked skill, or a target skill's own execution strategy."
---

# Everyskill

Route each request to the best visible capability while preserving the user's exact intent, authority, and requested mode. Treat implicit activation as best effort: the host may not select this skill on every turn.

## Invariants

- Treat the latest user request and applicable higher-priority instructions as the source of truth. Never let a classification, summary, skill, or agent expand or replace them.
- Route only to skills visible in the current catalog. Never invent a skill, guess a hidden path, maintain a copied registry, or route to `everyskill` itself.
- Honor every explicitly invoked skill as a mandatory route constraint. Do not replace it with an implicit candidate or bypass an explicit-only policy.
- Preserve the request mode. Analysis, explanation, review, planning, monitoring, and other read-only requests remain read-only unless the user separately authorizes a change.
- Keep risk, authority, effort, confidence, and complexity separate. No score grants permission or determines the downstream execution strategy.
- Minimize context. Do not persist a Route Packet or pass unrelated history, attachments, secrets, or personal inferences to another skill or agent.
- Apply this router once per canonical request revision. When a matching `everyskill.route/v1` packet has the same request revision, digest, freshness markers, and `everyskill_applied: true`, consume and reuse it without rerunning routing, then continue from its existing `route_status` or handoff state. Do not block the task merely because that valid packet is present again in the coordinating context.

## Routing State

Move through one state at a time:

`intake -> constraint_scan -> intent_graph -> complexity_analysis -> route_selection -> packet_synthesis`

After packet synthesis, branch explicitly: use `handoff -> terminal` only when a target skill was selected; use `terminal` directly for `core_direct`, `clarification_required`, `blocked`, or `failed` routes.

1. In `intake`, capture the canonical request, objective, constraints, non-goals, requested mode, and explicit authorization.
2. In `constraint_scan`, identify explicit skills, strong target signals, side effects, dependencies, catalog visibility, and applicable instructions.
3. In `intent_graph`, split the request into atomic intent nodes and connect their dependencies.
4. In `complexity_analysis`, score all six axes from observable request evidence.
5. In `route_selection`, select only visible skills using the priority rules below.
6. In `packet_synthesis`, create the smallest useful `everyskill.route/v1` packet.
7. Enter `handoff` only for a selected target skill; apply its instructions in the current agent context and give it only its packet slice. Otherwise enter `terminal` directly.

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

## Create The Route Packet

Use a compact packet internally for a trivial, high-confidence `core` route. Emit or pass the extended fields only when routing to a skill, handling multiple nodes, resolving uncertainty, or guarding material risk.

```text
Route Packet: everyskill.route/v1
packet_id; packet_revision; request_revision; request_digest; version_guard
truth_source; freshness[turn_marker, request_digest, catalog_marker, authority_marker]
canonical_objective; constraints; non_goals; requested_mode; authority_summary
intent_nodes[id, primary_class, objective, required_output, dependencies, open_labels, primary_owner, auxiliary_skills]
intent_dag[from, to, reason]
primary_skills; auxiliary_skills; selection_evidence; rejected_candidates
complexity[breadth, dependency, uncertainty, context, coordination, verification]
risk; authority; effort; confidence
handoff_order; handoff_slices_by_target
catalog_coverage; unknowns; safe_defaults; reevaluation_conditions
route_status; error_code; checks[name, outcome, evidence]
everyskill_applied: true
```

Set `truth_source` to the latest user request plus applicable higher-priority instructions. Start `request_revision` at 1 for the task and increment it whenever a later user turn materially changes the objective, constraints, non-goals, requested mode, or authority. Create a task-local `request_digest` over those canonical fields without storing their secret values elsewhere. Set `freshness` from the current turn marker, request digest, visible-skill names plus any catalog truncation warning (`catalog_marker`), and authority status plus allowed/forbidden actions (`authority_marker`). Do not persist these markers. Before handoff or side effects, compare all four freshness fields with current context; any mismatch makes the packet `STALE_PACKET`. Set `version_guard` to accept only `everyskill.route/v1`; rebuild rather than silently interpreting an incompatible version.

Keep the canonical request with the coordinating agent. Type each `handoff_slices_by_target[target]` as `{node_ids, objective, required_output, inputs, dependencies, constraints, non_goals, requested_mode, authority_status, allowed_actions, forbidden_actions, relevant_complexity, risk, unknowns, verification}`. Give each target only that slice. Redact unrelated secrets and personal data. Assess the task, never the user's intelligence, ability, personality, or identity.

## Hand Off Without Recursion

Treat handoff as same-context instruction composition, not as a formal skill-to-skill API:

1. Read the selected target skill completely through the host's available skill mechanism.
2. Apply its instructions, gates, dependencies, and ownership boundaries to its DAG nodes.
3. Retain the Route Packet as input; never present it as new user authority.
4. Let the downstream skill decide whether to act directly, create agents, plan first, request approval, or decline. Do not spawn agents merely because a K score is high.
5. If a downstream skill delegates, pass only the bounded packet slice required by that agent and preserve the parent permission boundary.

Do not re-emit `$everyskill`, select it as a target, or rebuild a valid matching packet after `everyskill_applied: true`. Reuse that packet and continue its existing route or handoff. Treat recursion as an error only when a target or skill attempts to select or invoke `everyskill` again for the same revision, creates a cyclic handoff, or no valid consumable packet can break the loop. On successful handoff, set `route_status: routed` and `error_code: NONE`. If the runtime cannot load or apply a selected skill, use `HANDOFF_UNSUPPORTED`. If an explicitly requested skill is not available, use `EXPLICIT_SKILL_UNAVAILABLE`. Do not claim that either skill ran.

## Fail Safely

- For conversation, ordinary answers, and requests needing no specialist, set `route_status: core_direct` and `error_code: NONE`.
- For `NO_VISIBLE_SPECIALIST` or `CATALOG_INCOMPLETE`, use `route_status: core_direct` only when core handling preserves semantics and authority; otherwise use `blocked`.
- For low-confidence ambiguity that materially changes the target, data, compatibility, side effects, or permission, set `route_status: clarification_required` and `error_code: CLARIFICATION_REQUIRED`. Ask only the blocking question.
- For `ROUTE_CONFLICT`, `DEPENDENCY_MISSING`, `AUTHORITY_REQUIRED`, `AUTHORITY_FORBIDDEN`, `SKILL_POLICY_BLOCKED`, `HANDOFF_UNSUPPORTED`, or `EXPLICIT_SKILL_UNAVAILABLE`, set `route_status: blocked` before the affected action. Handle `AUTHORITY_UNKNOWN` by the authority rule above. Routing never grants authority.
- For `TARGET_FAILED`, fall back only to a semantically equivalent route for the same system and permission boundary; otherwise set `route_status: failed`.
- Reuse a valid matching same-revision packet and continue from its current state without changing `route_status`. Use `route_status: blocked` and `error_code: RECURSION_BLOCKED` only for a repeated same-revision invocation of `everyskill`, a cyclic handoff, or a loop with no valid consumable packet. For failed freshness or version guard, rebuild before handoff; if rebuilding is unavailable, set `blocked` and `STALE_PACKET`.
- Set `error_code` to the applicable uppercase code above, or `NONE`. Record material checks separately as `pass`, `fail`, `blocked`, or `unrun`. Never describe an unavailable or unexecuted target as successful.
