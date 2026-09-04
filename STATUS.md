# 项目现状

更新时间：2026-09-04

## 当前定位

EverySkill 当前是一个可配置的 Agent/Skill 编排 Skill 包，不是前后端应用，也不是生产级调度平台。

它通过 Markdown 协议、工作流契约和场景规范，指导宿主 Agent 针对具体问题选择合适的编排方式，并输出可解释、可验证、受权限和预算约束的任务拓扑。

当前迭代版本：v0.4，具备配置化校验、图结构分析、结构覆盖报告、工作流脚手架和离线质量闭环。

## 已完成

- 建立核心路由与编排协议：意图分类、复杂度、风险、权限、置信度和 Route Packet。
- 定义标准拓扑原语：`DIRECT`、`ROUTE_ONE`、`HANDOFF`、`SEQUENTIAL`、`PARALLEL_SECTION`、`PARALLEL_SAMPLE`、`ORCHESTRATOR_WORKERS`、`REVIEW_LOOP`、`HUMAN_GATE`。
- 建立工作流目录和版本机制。
- 提供四个示例工作流：软件变更、诊断、研究决策、制品创建。
- 为工作流定义任务节点、依赖边、上下文策略、汇合策略、预算、停止、失败和验证规则。
- 提供正例、近似误匹配、权限、失败、预算和版本兼容场景。
- 提供 Python 结构校验器和回归测试。
- 移除演示前端，仓库核心只保留 Skill 文档、契约、场景和校验工具。
- 新增 [TARGET.md](./TARGET.md)，明确项目要解决的问题、方法、边界和成功标准。
- 建立拓扑选择决策表，定义各原语的适用条件、禁止条件和必要证据。
- 定义并行独立性、`data`/`control`/`context` 边、四种汇合模式和结构关键路径。
- 将四个工作流升级到契约 v2，并用 `topology_regions` 把原语映射到具体任务子图。
- 增加工作流模板、作者指南和完整 Route Packet 语义示例。
- 定义宿主最小能力，以及无并行、多 Agent、持久化、人工门控和审查能力时的安全降级。
- 将场景 schema 升级到 v2，记录选择理由、权限状态、宿主模式和降级结果。
- 扩展校验器，检查类型化边、拓扑区域、并行汇合、有限复核和场景决策字段。
- 定义 `quorum` 与 `first_acceptable` 的验收、失败和安全取消语义，并提供可校验实例。
- 将动态 `ORCHESTRATOR_WORKERS` 限制为深度 1，要求规划任务、Worker 模板、创建规则、去重键、预算、汇合和停止条件。
- 完善 `HANDOFF` 的来源、目标、最小上下文、验收和失败契约。
- 增加多工作流组合契约，校验实例 ID、工作流版本、跨工作流任务引用、独立验收、悬空边和环。
- 增加 `$guided-multi-agent-development` 与 `$continuous-technical-debt-cleanup` 的真实 Skill 路由案例，覆盖显式路由、继续已有流程、负例、两种串行顺序和只读并行边界。
- 建立 fresh-agent 行为评估协议、独立案例集、结果格式和离线评分器，计算 Packet 有效率、路由准确率、稳定率、过度编排率和安全通过率。
- 行为 oracle 现在校验主 owner 与 handoff 顺序；目标 Skill 不可见时将相应案例记录为 `UNRUN(missing_capability)`，不模拟成功。
- 将简单 `DIRECT` 和单 owner 请求改为轻量 fast path，只有多意图、真实依赖、权限冲突或共享状态等情况才构建完整 DAG 和扩展 Packet。
- 新增 `validation-policy.json` 和严格加载器，统一两个校验入口使用的原语、状态、预算、宿主降级和必需覆盖配置；未知 schema、重复值和未实现语义会 fail closed。
- 新增确定性图分析工具，计算拓扑排序、结构关键路径、最大反链并行宽度、fan-in/fan-out、区域分支数和动态 Worker 上界。
- 新增结构覆盖报告，映射工作流正例/近似误匹配、必需标签、拓扑原语、route/authority/host/fallback 以及真实 Skill owner/handoff，并始终与行为正确率分离。
- 新增保守的工作流脚手架，支持 dry-run，拒绝非法 ID、仓库外路径和覆盖已有文件，不自动修改目录或生成复杂拓扑。
- 新增人工拆分评审 JSON 契约和离线校验，人工结果单独报告，不影响自动路由指标。
- 扩展真实 Skill 案例，增加 `architecture-decision` 到 guided development，以及本地开发到 `server-service-deploy-standard` 的决策、顺序和权限边界。
- 加固离线工具边界：拒绝非有限预算、未知内部 schema 和未实现分支策略；人工评审必须引用实际 trial；工作流案例类型、覆盖维度与脚手架独占创建均可校验。
- 新增 GitHub Actions 结构与离线门禁，不需要模型密钥、外部服务或真实 Skill 安装。

## 当前可用能力

使用者可以通过 Markdown/JSON 配置新增工作流，并通过脚手架生成最小骨架。共享策略文件可以调整已有校验语义的允许值、预算和覆盖要求；结构分析与覆盖报告提供确定性反馈。宿主仍可按标准结果格式采集 fresh-agent 试验，再由离线评分器确定行为门禁。

当前验证结果：

```text
Workflow validation passed.
69 passed, 10 subtests passed
Structural coverage: 25/25 required tags
Topology analysis: 4/4 catalog workflows analyzed
Fresh-agent behavior gate: UNRUN
Human decomposition review: UNRUN (format validation only)
```

## 尚未完成

- 基于真实宿主 Agent 的 fresh-agent 行为采集尚未执行；当前只完成协议、独立案例、结果校验和离线评分，不能据此声称真实 LLM 路由已通过。
- 人工拆分质量目前只有记录格式和示例，尚未产生真实独立评审结果。
- 真实 Skill 案例已覆盖开发、技术债、架构决策和部署治理；更多跨领域冲突应根据真实误路由反馈增加，而不是继续预设扩张。
- 真实 Agent 执行仍由宿主环境负责，本项目不实现模型调用、任务队列、持久化或外部系统操作。

## 现状判断

除真实执行与真实评审取样外，项目已经形成从配置、脚手架、结构校验、图指标、覆盖报告到 CI 的离线闭环。当前主要差距是尚未由真实宿主完成 fresh-agent 数据采集，因此路由准确性、稳定性、拆分质量和过度编排率仍无实测结论；项目仍不需要建设后端运行时。

## 下一步优先级

1. 在具备固定模型、宿主和可见 Skill 目录的环境中运行 fresh-agent 案例，采集首份真实评估结果。
2. 对预选 trial 执行独立人工拆分评审，并与自动指标并列保存。
3. 根据真实误路由补充 owner 冲突、流程继续和过度编排案例，而不是预先扩充抽象规则。
4. 根据实际宿主 Agent 的使用反馈迭代协议和示例工作流。
