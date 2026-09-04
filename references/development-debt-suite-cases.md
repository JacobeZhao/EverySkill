# Development And Debt Skill Cases

These are real visible-Skill routing examples. The source Skills may be installed locally, but this repository refers only to their portable names and public ownership boundaries. It does not copy their instructions or depend on an installation path.

| Request shape | Owner topology | Required order | Boundary |
| --- | --- | --- | --- |
| Explicit bounded feature using `$guided-multi-agent-development` | `HANDOFF` to `guided-multi-agent-development` | one handoff | The target owns discovery, plan approval, implementation, review, and delivery acceptance. |
| Approval or continuation of an active guided run | `HANDOFF` to the active owner | preserve current owner | Do not rematch the short control message as a new request. |
| Ordinary scoped edit without guided execution | `DIRECT` or the ordinary specialist | no suite handoff | Do not select guided development merely because planning could help. |
| Explicit repository-wide repeated cleanup using `$continuous-technical-debt-cleanup` | `HANDOFF` to `continuous-technical-debt-cleanup` | one handoff | The target owns its durable run, fixed panels, cycles, and convergence criteria. |
| Local supporting refactor or review of a few findings | `DIRECT` or the ordinary specialist | no cleanup handoff | Do not expand a scoped request into repository-wide cleanup. |
| Feature defines a target architecture, then broad cleanup applies it | `SEQUENTIAL(HANDOFF,HANDOFF)` | guided, then cleanup | Each Skill retains separate authority, approval, budget, recovery, and completion state. |
| A proven behavior-preserving debt blocker prevents safe feature work | `SEQUENTIAL(HANDOFF,HANDOFF)` | cleanup, then guided | Reverse the normal order only with evidence for the blocker and no unresolved product decision. |
| Independent read-only discovery for both outcomes | `PARALLEL_SECTION(HANDOFF,HANDOFF)` | join before any write | Parallelism is allowed only with immutable inputs, separate context, and no shared mutable state. |

## Transfer Rules

- A development run that discovers systemic debt records a future cleanup candidate; it does not start cleanup automatically.
- A cleanup run that encounters a product-behavior decision blocks that finding; it may hand off only after the user defines a development outcome.
- Concurrent writers are forbidden in one shared worktree. Read-only discovery may run in parallel, but mutation stages are serialized through explicit control edges.
- The coordinator retains the canonical combined request and reports both downstream states independently.
- If a required target Skill is not visible, block or mark an evaluation case `UNRUN(missing_capability)`; core must not simulate the target protocol.

The matching fresh-agent fixtures and exact owner/handoff oracles live in [behavior-evaluation-cases.json](behavior-evaluation-cases.json).
