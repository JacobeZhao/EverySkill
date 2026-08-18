# Agent Orchestration Strategies

Use this background reference when designing or extending workflows, or when no internal workflow fits an orchestration problem. During ordinary handling, load only the selected workflow reference. `SKILL.md` is the normative owner of primitive names, packet fields, risk, authority, statuses, and errors.

## Contents

- Selection principles
- Decision dimensions
- Foundational strategies
- Canonical primitives
- Selection heuristics
- Orchestration plan contract
- Failure modes
- Sources

## Selection Principles

1. Choose the simplest topology that can meet the required quality and safety level.
2. Add an agent only when specialization, independence, diversity, dynamic decomposition, or independent verification provides a concrete benefit.
3. Keep authority, risk, complexity, and orchestration separate. None of them alone selects a topology.
4. Prefer deterministic control for known workflows and bounded LLM control for open-ended decomposition.
5. Define data flow, context visibility, join behavior, budget, and stop conditions before execution.
6. Compare expected quality gain against latency, token cost, coordination overhead, and new failure modes.

## Decision Dimensions

Evaluate these dimensions before choosing a strategy:

- **Decomposability:** Can the objective be split into clear subtasks?
- **Dependency:** Which outputs are required before other work can start?
- **Independence:** Can subtasks run concurrently without shared mutable state?
- **Predictability:** Are the required subtasks known before execution?
- **Specialization:** Do visible skills or agents have materially different expertise or tools?
- **Diversity value:** Would independent attempts or perspectives improve confidence?
- **Verification:** Are there explicit criteria for judging and improving an output?
- **Control ownership:** Should a manager retain the user-facing conversation or transfer it?
- **Context isolation:** What is the minimum context each worker needs?
- **Budget:** What are the maximum calls, workers, rounds, tokens, latency, and cost?
- **Authority:** Which steps may act, which require confirmation, and which are forbidden?

## Foundational Strategies

### Direct Handling

The primary agent answers without delegation. Use it for a single clear outcome when specialist capability, decomposition, or independent verification would not materially improve the result.

Benefits: lowest latency, cost, and coordination risk.

Avoid it when the task crosses distinct domains, has meaningful independent subtasks, or requires separation between execution and verification.

### Routing and Dispatch

A router classifies the request and chooses one specialist or workflow. Use it when categories are distinct and classification can be performed reliably.

Routing normally selects one path. Dispatch may select multiple targets, in which case it becomes an orchestration decision and requires a join policy.

### Handoff

One agent transfers control and relevant conversation state to another agent. Use it when the specialist should own the remainder of the interaction.

Do not use handoff for a bounded supporting task when the original agent must synthesize the final answer. In that case, retain manager control and invoke the specialist as a tool or worker.

### Manager With Agents as Tools

A manager retains control, invokes specialists for bounded tasks, and owns synthesis and the final response. Use it when outputs must share one policy boundary, one user-facing voice, or one aggregation point.

The manager can become a bottleneck and may distort specialist results. Require structured worker outputs when aggregation correctness matters.

### Sequential Pipeline

Agents execute in a fixed order and each stage consumes selected outputs from earlier stages. Use it for real data or control dependencies such as research, outline, draft, review, and revision.

Add gates between fragile stages. Do not serialize tasks that are independent, because latency and error propagation increase with every stage.

### Parallel Fan-Out and Gather

Split an objective into independent sections, execute them concurrently, then gather results. Use it to reduce latency or isolate attention across distinct considerations.

Every branch needs a unique output contract. The gather step must define how to merge, rank, deduplicate, or report conflicts. Parallel workers should not mutate the same state without an explicit consistency model.

### Parallel Sampling and Voting

Run the same task through multiple independent attempts, then select or synthesize the result. Use it when diversity has measurable value, such as uncertain reasoning, candidate generation, or safety checks.

Voting is not an external truth oracle. Correlated models can repeat the same error, so prefer evidence-based judging over majority count.

### Orchestrator-Workers

A central LLM dynamically decomposes an open-ended task, delegates workers, and synthesizes their results. Use it when the number and shape of subtasks cannot be predicted reliably before seeing the request or intermediate evidence.

Bound worker count, recursion depth, context, and execution rounds. Require the orchestrator to state task boundaries, expected outputs, dependencies, and join behavior before delegation.

### Hierarchical Decomposition

Higher-level agents recursively delegate to lower-level coordinators or workers. Use it for large tasks with natural layers of ownership.

Avoid unnecessary hierarchy. Each level adds context loss, latency, cost, and ambiguity about responsibility.

### Group Chat or Blackboard

Specialists share a common message thread or workspace, and a manager or policy selects speakers until a termination condition is reached. Use it when participants must react to each other's evolving work.

Shared context is expensive and encourages convergence, repetition, and distraction. Prefer isolated workers plus explicit artifacts when peer interaction is not required.

### Generate and Review

One agent generates an artifact and another reviews it against explicit criteria. Use it when role separation can expose defects in code, writing, plans, or factual claims.

A single review produces feedback but does not guarantee correction. Add a revision stage only when the feedback is actionable.

### Evaluator-Optimizer Loop

A generator or optimizer revises an artifact based on evaluator feedback until it passes or reaches a limit. Use it when quality criteria are explicit and iterative feedback demonstrably improves results.

Always define pass criteria, maximum rounds, no-progress detection, and the artifact version that is authoritative.

### Multi-Agent Debate

Several agents exchange solutions and critiques over multiple rounds, followed by a judge or aggregation step. Use it selectively for competing hypotheses or decisions where exposing assumptions is valuable.

Debate is costly and can amplify persuasive but unsupported claims. Require evidence, bound rounds, preserve independent first answers, and use a separate decision rule.

### Mixture of Agents

Multiple workers generate candidates in layers, with later workers seeing earlier outputs and an orchestrator producing the final result. Use it only when quality is substantially more important than latency and cost.

Treat it as an advanced ensemble, not a default. It has high token usage and can propagate early-layer noise.

### Human in the Loop

Pause at a defined gate for clarification, approval, correction, or judgment. Use it for unresolved authority, consequential external actions, ambiguous preferences, and cases without a reliable automated oracle.

Retain enough task-local context to resume safely within the current host workflow. EverySkill does not provide durable persistence. Present the exact decision and consequences rather than asking for generic approval.

### Event-Driven Orchestration

Agents subscribe to typed events and respond asynchronously. Use it for long-running workflows, external triggers, or systems where tasks do not fit one synchronous request.

This is background for a future runtime and is outside the current supported scope. A future implementation must define idempotency, delivery semantics, correlation identifiers, timeouts, cancellation, recovery, and ownership of shared state.

## Canonical Primitives

Use only the canonical primitive vocabulary defined in `SKILL.md`. Model hierarchy, group chat, debate, and mixture-of-agents as explicit compositions of those primitives. Treat event-driven systems as future runtime work, not as a current extension. Do not add a primitive merely to rename an existing topology.

Keep topology and route status as separate fields. Topology describes how work is or would be executed; route status describes what happened in the current turn. A planning-only response can therefore have `topology: PARALLEL_SECTION(...)` and `route_status: core_direct`, while an executed delegation can use the same topology and finish with `route_status: routed`.

## Selection Heuristics

- One atomic, low-risk outcome with no specialist advantage: `DIRECT`.
- One clearly matched specialist: `ROUTE_ONE` or `HANDOFF`, depending on control ownership.
- Known dependent stages: `SEQUENTIAL`.
- Known independent subtasks: `PARALLEL_SECTION` followed by a gather node.
- Same task needs diverse candidates: `PARALLEL_SAMPLE` followed by a judge.
- Unknown subtasks that depend on the input or evidence: `ORCHESTRATOR_WORKERS`.
- Output can improve against explicit criteria: add `REVIEW_LOOP`.
- Authority or consequential judgment is unresolved: insert `HUMAN_GATE` before the affected action.

Prefer a mixed DAG when different regions have different needs. Example:

```text
ORCHESTRATOR_WORKERS
  -> PARALLEL_SECTION(research, code_analysis, risk_analysis)
  -> SEQUENTIAL(synthesis, implementation)
  -> REVIEW_LOOP
  -> HUMAN_GATE only if a consequential action remains
```

## Orchestration Plan Contract

Record at least:

```text
controller: code | llm | hybrid
topology: canonical primitive or explicit composition of canonical primitives
tasks: id, objective, owner, required_output, dependencies
edges: data and control dependencies
join_policy: merge, rank, vote, select, or preserve conflicts
context_policy: inputs and state visible to each task
budget: calls, workers, rounds, tokens, latency, and cost limits
stop_conditions: success, failure, no progress, timeout, and cancellation
verification: checks, evaluator, evidence, and acceptance criteria
authority: allowed actions, forbidden actions, and human gates
```

## Failure Modes

- **Over-orchestration:** extra agents add cost without a specific expected benefit.
- **False parallelism:** workers depend on each other or mutate shared state.
- **Weak joins:** synthesis hides disagreement or drops evidence.
- **Context flooding:** every worker receives the entire conversation or repository.
- **Recursive delegation:** workers create unbounded descendants or cycles.
- **Unbounded refinement:** evaluation loops lack pass criteria or progress checks.
- **Correlated consensus:** voting or debate mistakes repeated error for confidence.
- **Authority laundering:** delegation is treated as permission to perform a forbidden action.
- **Ownership ambiguity:** no agent owns the final artifact, decision, or user response.
- **Missing recovery:** timeouts, partial failures, and cancellation leave the workflow inconsistent.

## Sources

- Anthropic, [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- OpenAI Agents SDK, [Agent Orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
- Google Agent Development Kit, [Multi-agent Workflow Patterns](https://google.github.io/adk-docs/workflows/patterns/)
- Microsoft AutoGen, [Design Patterns](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/intro.html)
- LangGraph, [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
