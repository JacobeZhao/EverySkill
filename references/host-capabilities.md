# Host Capability Contract

EverySkill proposes and constrains orchestration; the host performs it. Before handoff, record which capabilities are available instead of assuming a full multi-agent runtime.

## Minimum Capabilities

The host should be able to:

- read the selected Skill and workflow references;
- enumerate only currently visible Skills;
- retain the canonical request and authority boundary;
- execute or present one bounded task at a time;
- pass declared dependency outputs as minimized context;
- represent `complete`, `partial`, `blocked`, `failed`, and `unrun` outcomes;
- report actual checks without claiming unavailable execution.

## Optional Capabilities And Fallbacks

| Missing capability | Required fallback |
| --- | --- |
| Parallel execution | Preserve the DAG and execute eligible branches serially from the same immutable input version; report the loss of latency benefit |
| Multiple agents | Use one Agent with isolated task contexts and sequential execution, or return the proposed plan when independence cannot be preserved |
| Persistent workflow state | Complete within the current turn or return a resume record; do not promise automatic continuation |
| Human-gate/resume support | Stop as `blocked` with the exact unresolved decision and required authority |
| Required visible Skill | Use an equivalent visible owner only within the same system and authority boundary; otherwise clarify or block |
| Independent reviewer | Mark independent verification `unrun` and do not claim the associated quality gate passed |
| Structured Route Packet transport | Render the same fields in a clearly labeled textual handoff without dropping authority, dependencies, or stop conditions |

Fallback changes execution capability, not task meaning or authority. Never replace missing external capability with simulated success.

The machine-readable host modes and allowed fallback names are maintained in [validation-policy.json](validation-policy.json). Changing those names configures validation only; it does not add the corresponding capability to a host.

## Capability Record

```text
host mode; visible skills; parallel capacity; agent capacity;
state persistence; human-gate support; reviewer independence;
selected fallback; lost benefit; blocked requirements
```
