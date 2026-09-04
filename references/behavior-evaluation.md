# Behavior Evaluation

This protocol evaluates whether a fresh host Agent applies EverySkill consistently. The repository defines cases, result capture, and deterministic scoring; it does not call a model or provide a production runner.

## Isolation

Each trial starts in a fresh context with the same recorded model, host, system instructions, Skill revision, visible-skill catalog, workflow catalog, capability profile, and sampling settings. The result metadata records visible Skill names; a case whose `required_visible_skills` are absent is `UNRUN(missing_capability)` and is excluded from aggregate metrics.

The tested Agent receives the case request and declared context only. It must not receive:

- the case oracle or `workflow-scenarios.json` expected values;
- another trial's output or evaluator feedback;
- hidden skills, permissions, or capabilities not listed in the trial context.

The host adapter extracts only observable routing fields into `everyskill.evaluation-results/v1`. It preserves the raw host output outside this repository when needed for audit, subject to privacy and secret rules.

## Evaluation Cases

`behavior-evaluation-cases.json` is independent from workflow structural fixtures. Each case declares:

- request and task-local context;
- repetition count;
- allowed workflow and topology sets, because more than one topology can be semantically acceptable;
- allowed primary-owner sets and ordered Skill handoffs;
- expected route and authority status;
- expected host fallback;
- maximum workflow and coordination breadth;
- forbidden topology primitives;
- whether failure is safety-critical.

Do not turn free-text reasoning into an exact string oracle. Human review evaluates whether the stated evidence actually supports the decomposition and topology.

## Result Contract

Every trial records:

```text
case_id; trial_index;
packet[workflow_ids, topology, route_status, error_code,
       authority_status, fallback, primary_owners, handoff_order, intent_count]
```

Run metadata records the host, model/version, Skill revision, workflow catalog marker, sampling configuration, capability profile, and visible Skills. Generated IDs, prose, timestamps, and task names are excluded from the stability signature.

Run identity fields must be nonempty, `sampling` must be structured, and `workflow_catalog_marker` must equal `catalog-<catalog_version>` for the selected case suite. Decision arrays cannot contain duplicates. For these routing cases, `intent_count` equals the number of owners in the accepted primary-owner set; cases needing multiple nodes with the same owner must declare a future schema extension rather than weakening this oracle.

Visible Skill cases validate ownership without copying those Skills into this repository. Their `workflow_ids` remain empty because downstream Skills own their own procedures; EverySkill records only the owner and handoff boundary. The host loads a target Skill's instructions only when the route actually hands off to it.

## Metrics

- `packet_validity`: valid trial packets divided by expected trials.
- `route_accuracy`: macro average of each case's correct-trial ratio.
- `stability`: macro average of the most common normalized decision signature per case.
- `over_orchestration_rate`: trials exceeding workflow/coordination caps or using forbidden primitives, divided by expected trials.
- `safety_pass_rate`: correct valid trials among safety-critical cases. Missing safety trials count as failures.

Default release gates are defined in the case suite. Safety and packet validity gates are independent and cannot be hidden by a high average score.

## Human Decomposition Rubric

For a representative sample, a reviewer records `pass`, `fail`, or `unrun` with evidence for:

1. node atomicity and direct relevance to the deliverable;
2. correct data, control, and context dependencies;
3. one unambiguous owner and required output per node;
4. minimum necessary context per worker;
5. justified parallel independence and join behavior;
6. explicit budget, failure, stop, and verification behavior.

This rubric is not included in automated accuracy. Natural-language quality must not be simulated by substring checks.

## Running An Evaluation

1. A host adapter runs every eligible case for the declared repetitions under fresh contexts and records the visible Skill catalog.
2. The adapter writes one result document following `behavior-evaluation-results.example.json`.
3. Run:

```powershell
python scripts/evaluate_behavior.py --results <results.json>
```

Use `--json-report <path>` for a machine-readable report. The scorer exits `0` only when every configured gate passes, `1` for a valid evaluated suite with failed gates, and `2` for invalid case or result data.

Without captured host results, the behavior gate is `UNRUN`. Structural workflow tests are not evidence that routing behavior passed.
