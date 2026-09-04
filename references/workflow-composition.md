# Workflow Composition

Compose workflows only for distinct deliverables with independent acceptance criteria. An instance references a catalog workflow by ID and version; instance IDs prevent two uses of the same workflow from collapsing into one state machine.

<!-- workflow-composition-examples -->
```json
{
  "schema_version": "1",
  "examples": [
    {
      "id": "software-and-publication",
      "instances": [
        {"instance_id": "implementation", "workflow_id": "software-change", "workflow_version": "2", "acceptance_oracle": "The requested behavior and regression tests pass."},
        {"instance_id": "publication", "workflow_id": "artifact-creation", "workflow_version": "2", "acceptance_oracle": "The standalone release guide is rendered and inspected."}
      ],
      "tasks": [
        {"id": "implementation.output", "instance_id": "implementation"},
        {"id": "publication.input", "instance_id": "publication"},
        {"id": "publication.output", "instance_id": "publication"}
      ],
      "edges": [
        {"from": "implementation.output", "to": "publication.input", "kind": "data"},
        {"from": "publication.input", "to": "publication.output", "kind": "control"}
      ],
      "join_policy": "The coordinator reports each workflow status independently; overall delivery requires both acceptance oracles."
    }
  ]
}
```

Cross-workflow edges may transfer only declared data, control, or minimized context. They do not grant authority, merge budgets, or permit one workflow to claim another workflow's acceptance result. Cyclic instance dependencies and dangling task references are invalid.
