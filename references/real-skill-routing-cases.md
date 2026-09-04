# Real Skill Routing Cases

These fixtures validate ownership and orchestration boundaries for visible Skills without copying their implementation or claiming downstream execution succeeded.

## Development And Repository Debt

Use [the development and debt cases](development-debt-suite-cases.md) for explicit guided development, comprehensive cleanup, active-workflow continuation, and their ordered combination. Shared-worktree writes stay serial.

## Architecture And Development

- A request that explicitly asks `architecture-decision` for a decision record, with no implementation, hands off only to that Skill.
- A request for an architecture decision followed by implementation uses `SEQUENTIAL(HANDOFF,HANDOFF)`: the accepted decision is a data/control dependency of `guided-multi-agent-development`.
- An ordinary local edit does not acquire an architecture phase merely because architecture analysis might be interesting.

The decision and implementation retain separate acceptance criteria. Architecture approval is not mutation authority.

## Development And Deployment

- A read-only deployment-readiness assessment hands off to `server-service-deploy-standard` without implying release authority.
- Local implementation and remote deployment are separate intent nodes. Development may proceed under local authority while an unauthorized deployment node remains blocked at a `HUMAN_GATE`.
- A successful build or test never grants server, credential, production, release, or rollback authority.

## Fixture Rules

- Refer only to visible Skill names and stable public responsibilities, never local installation paths.
- Require `UNRUN(missing_capability)` when a target Skill is unavailable to the evaluation host.
- Compare owners, topology primitives, ordered handoffs, authority, route state, and fallback. Do not compare free-text reasoning.
- Add a case only when it protects a new ownership, continuation, authority, or over-orchestration boundary.
