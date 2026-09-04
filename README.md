# EverySkill

EverySkill 是一个可配置的 Agent/Skill 编排 Skill。它通过 Markdown 工作流契约和场景规范，帮助宿主 Agent 判断任务是否需要编排、如何拆分任务、如何选择 Skill、如何组织串行或并行执行，以及如何汇总、验证和安全停止。

## 包含内容

- `SKILL.md`：核心路由与编排协议，包括意图分类、复杂度、风险、权限、拓扑原语、Route Packet 和失败安全规则。
- `references/workflow-catalog.md`：工作流选择目录和匹配优先级。
- `references/workflow-*.md`：软件变更、诊断、研究决策和制品创建的示例工作流契约。
- `references/topology-selection.md`：拓扑选择决策表、并行独立性、边语义和汇合规则。
- `references/advanced-topology-examples.md`：`quorum`、`first_acceptable`、动态 Worker 和 `HANDOFF` 的可校验实例。
- `references/workflow-composition.md`：多工作流实例、跨工作流边和独立验收契约。
- `references/development-debt-suite-cases.md`：多 Agent 开发与全仓技术债清理 Skill 的真实路由及组合案例。
- `references/workflow-template.md`：可复制的最小工作流契约模板和字段规则。
- `references/workflow-authoring-guide.md`：新增或修改工作流的完整步骤。
- `references/route-packet-examples.md`：直接、并行、权限门控、部分失败和过期 Packet 示例。
- `references/host-capabilities.md`：宿主最小能力和安全降级规则。
- `references/workflow-scenarios.json`：正例、近似误匹配、权限、预算、失败和版本场景。
- `references/behavior-evaluation.md`：fresh-agent 隔离、结果采集、指标和人工拆分审查规范。
- `references/behavior-evaluation-cases.json`：独立于结构场景的行为评估案例和门禁。
- `scripts/evaluate_behavior.py`：不调用模型的离线行为评分器。
- `scripts/validate_workflows.py`：校验工作流目录、契约结构、任务 DAG、预算和场景覆盖。
- `tests/`：工作流校验器和行为评分器回归测试。

## 如何配置

使用者可以按自己的 Skill 目录和宿主能力修改或新增工作流：

1. 阅读 `references/workflow-authoring-guide.md`，确认新需求不能由直接处理、单 Skill 或已有工作流覆盖。
2. 复制 `references/workflow-template.md`，定义任务 DAG、类型化边和 `topology_regions`。
3. 在 `references/workflow-catalog.md` 增加唯一的工作流 ID、版本、匹配条件和引用路径。
4. 在 `SKILL.md` 中保持直接链接，并在 `workflow-scenarios.json` 中补充正例、近似误匹配、权限、失败、预算和宿主降级场景。
5. 运行校验器和测试，确认依赖图、拓扑区域、版本、预算和引用一致。

工作流是任务级流程，不授予权限，也不替代宿主 Agent 或其他 Skill 的能力。实际执行、工具调用和权限控制由宿主环境负责。

## 验证

```powershell
python scripts/validate_workflows.py
python -m pytest -q
```

宿主采集 fresh-agent 结果后可运行：

```powershell
python scripts/evaluate_behavior.py --results <results.json>
```

没有真实宿主结果时，行为门禁为 `UNRUN`；结构测试通过不能替代真实路由质量评估。

本仓库不包含业务后端、持久化调度器或生产 Agent 执行器。配置和使用以 Markdown 契约为准。
