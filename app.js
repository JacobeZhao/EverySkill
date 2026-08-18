const EXAMPLES = {
  diagnosis: "分析线上 API 偶发超时的根因，比较三个可能原因，给出证据充分且不修改生产环境的诊断结论。",
  research: "调研三种企业知识库方案，比较成本、准确性、权限能力和迁移风险，推荐最适合 200 人团队的一种。",
  software: "修复订单服务的重复扣款问题，先定位触发条件，再实现改动、补充回归测试并完成独立审查。",
  artifact: "为季度经营复盘创建一份管理层 PDF，整理关键数据、设计叙事结构、生成制品并逐页检查视觉质量。"
};

const TOPOLOGIES = {
  diagnosis: {
    name: "证据并行 · 诊断汇合",
    kind: "HYBRID",
    primitives: "SEQUENTIAL · PARALLEL_SAMPLE · PARALLEL_SECTION",
    baseSuccess: 92.4,
    baseLatency: 71,
    tokens: 18.6,
    authority: "只读分析，不修改生产状态",
    failure: "保留失败分支，证据不足时降级输出",
    stop: "两轮无置信提升或耗时预算耗尽",
    reasons: [
      ["未知根因需要多假设竞争", "三个证据 Agent 独立验证，避免首个猜测形成锚定。"],
      ["证据必须在汇合点统一校准", "协调器按解释力和可证伪性排序，不采用简单多数票。"],
      ["只读权限决定停止边界", "需要变更状态的检查会立即停止，并标记为证据缺口。"]
    ],
    nodes: [
      { id: "intake", label: "问题定界", role: "Coordinator", type: "coordinator", x: 10, y: 48, duration: 4, detail: "固定现象、期望、时间窗和只读权限。" },
      { id: "h1", label: "依赖延迟假设", role: "Evidence Agent", type: "worker", x: 34, y: 20, duration: 31, detail: "检查下游依赖的延迟分布和相关性。" },
      { id: "h2", label: "资源耗尽假设", role: "Evidence Agent", type: "worker", x: 34, y: 48, duration: 27, detail: "核对连接池、线程池和资源水位证据。" },
      { id: "h3", label: "流量模式假设", role: "Evidence Agent", type: "worker", x: 34, y: 76, duration: 24, detail: "比较异常样本与流量特征，寻找共同条件。" },
      { id: "join", label: "证据汇合", role: "Synthesis Agent", type: "coordinator", x: 61, y: 48, duration: 15, detail: "保留冲突与来源，按证据强度给假设排序。" },
      { id: "review", label: "反证审查", role: "Verifier", type: "verifier", x: 80, y: 29, duration: 17, detail: "主动寻找能推翻首选结论的证据。" },
      { id: "output", label: "诊断结论", role: "Authoritative Output", type: "output", x: 91, y: 62, duration: 4, detail: "输出结论、置信度、未知项和下一步。" }
    ],
    edges: [["intake", "h1", true], ["intake", "h2", false], ["intake", "h3", false], ["h1", "join", true], ["h2", "join", false], ["h3", "join", false], ["join", "review", true], ["review", "output", true], ["join", "output", false]]
  },
  research: {
    name: "多源研究 · 决策校准",
    kind: "PARALLEL + REVIEW",
    primitives: "SEQUENTIAL · PARALLEL_SECTION · REVIEW_LOOP",
    baseSuccess: 90.8,
    baseLatency: 83,
    tokens: 23.4,
    authority: "只读取公开或已授权资料",
    failure: "单一来源失败不阻断，降低相关判断置信度",
    stop: "证据覆盖验收维度或达到研究预算",
    reasons: [
      ["比较维度可以并行取证", "成本、能力和风险分别收集，减少关键路径耗时。"],
      ["推荐必须建立在统一量纲上", "汇合阶段标准化来源质量和评价口径。"],
      ["反方审查降低确认偏差", "Critic Agent 专门挑战推荐结论和缺失证据。"]
    ],
    nodes: [
      { id: "brief", label: "决策框架", role: "Coordinator", type: "coordinator", x: 10, y: 48, duration: 7, detail: "明确选项、受众、评价维度和权重。" },
      { id: "cost", label: "成本证据", role: "Research Agent", type: "worker", x: 34, y: 20, duration: 34, detail: "核对价格、迁移和长期维护成本。" },
      { id: "cap", label: "能力证据", role: "Research Agent", type: "worker", x: 34, y: 48, duration: 38, detail: "按统一场景比较功能和约束。" },
      { id: "risk", label: "风险证据", role: "Research Agent", type: "worker", x: 34, y: 76, duration: 31, detail: "评估权限、锁定、成熟度和退出成本。" },
      { id: "matrix", label: "证据矩阵", role: "Synthesis Agent", type: "coordinator", x: 61, y: 48, duration: 18, detail: "标准化证据并显式保留未知项。" },
      { id: "critic", label: "反方审查", role: "Critic Agent", type: "verifier", x: 80, y: 29, duration: 16, detail: "挑战排名对权重和证据缺口的敏感性。" },
      { id: "output", label: "推荐报告", role: "Authoritative Output", type: "output", x: 91, y: 62, duration: 4, detail: "给出可追溯推荐、条件和替代方案。" }
    ],
    edges: [["brief", "cost", true], ["brief", "cap", false], ["brief", "risk", false], ["cost", "matrix", false], ["cap", "matrix", true], ["risk", "matrix", false], ["matrix", "critic", true], ["critic", "output", true], ["matrix", "output", false]]
  },
  software: {
    name: "受控变更 · 审查闭环",
    kind: "SEQUENTIAL + REVIEW",
    primitives: "SEQUENTIAL · PARALLEL_SECTION · REVIEW_LOOP",
    baseSuccess: 94.1,
    baseLatency: 116,
    tokens: 27.2,
    authority: "仅修改批准范围内的代码和测试",
    failure: "验证失败返回修订节点，最多两轮",
    stop: "验收证据通过、两轮无进展或范围漂移",
    reasons: [
      ["代码变更存在真实依赖链", "先建立问题证据，再实施、审查和验证，不能跳阶段。"],
      ["探索任务可安全并行", "调用链和测试基线分开读取，写入阶段保持单一所有者。"],
      ["审查结论必须能触发修订", "显式 Review Loop 避免发现问题后直接进入验证。"]
    ],
    nodes: [
      { id: "scope", label: "范围与验收", role: "Coordinator", type: "coordinator", x: 9, y: 48, duration: 8, detail: "锁定批准范围、风险等级和验收标准。" },
      { id: "trace", label: "调用链探索", role: "Explorer", type: "worker", x: 29, y: 26, duration: 24, detail: "定位所有者、调用方和稳定扩展点。" },
      { id: "baseline", label: "测试基线", role: "Test Analyst", type: "worker", x: 29, y: 70, duration: 21, detail: "确认独立测试预言和现有行为。" },
      { id: "implement", label: "实现变更", role: "Implementation Agent", type: "worker", x: 51, y: 48, duration: 42, detail: "单一写入所有者完成代码与测试修改。" },
      { id: "review", label: "独立审查", role: "Review Agent", type: "verifier", x: 72, y: 27, duration: 21, detail: "检查调用方、失败路径、契约和债务增量。" },
      { id: "verify", label: "验收验证", role: "Verifier", type: "verifier", x: 72, y: 70, duration: 25, detail: "执行成功、失败和兼容路径验证。" },
      { id: "output", label: "已验证变更", role: "Authoritative Output", type: "output", x: 92, y: 48, duration: 5, detail: "报告变更、证据、风险和未运行检查。" }
    ],
    edges: [["scope", "trace", true], ["scope", "baseline", false], ["trace", "implement", true], ["baseline", "implement", false], ["implement", "review", true], ["review", "verify", true], ["review", "implement", false], ["verify", "output", true]]
  },
  artifact: {
    name: "并行预制 · 视觉验收",
    kind: "PARALLEL + REVIEW",
    primitives: "SEQUENTIAL · PARALLEL_SECTION · REVIEW_LOOP",
    baseSuccess: 91.6,
    baseLatency: 102,
    tokens: 25.8,
    authority: "仅创建请求的本地制品及必要资源",
    failure: "渲染失败保留源文件并报告可恢复状态",
    stop: "视觉标准通过或两轮修改无实质进展",
    reasons: [
      ["结构和素材可并行准备", "两条预制分支在创建前汇合，缩短关键路径。"],
      ["真实渲染是独立验收预言", "不能只检查文本或源结构，需要逐页视觉检查。"],
      ["唯一制品所有者防止覆盖", "创建与修订由同一 Agent 承担，协调器只做汇合。"]
    ],
    nodes: [
      { id: "brief", label: "制品简报", role: "Coordinator", type: "coordinator", x: 9, y: 48, duration: 7, detail: "固定受众、格式、内容和视觉验收标准。" },
      { id: "structure", label: "叙事结构", role: "Structure Agent", type: "worker", x: 30, y: 26, duration: 27, detail: "规划信息层级、章节和页面节奏。" },
      { id: "assets", label: "素材准备", role: "Asset Agent", type: "worker", x: 30, y: 70, duration: 31, detail: "收集可用数据、图片与来源说明。" },
      { id: "create", label: "制品生成", role: "Artifact Agent", type: "worker", x: 52, y: 48, duration: 38, detail: "生成唯一权威源文件和目标格式。" },
      { id: "render", label: "真实渲染", role: "Renderer", type: "verifier", x: 72, y: 27, duration: 18, detail: "渲染最终格式以发现布局和资源问题。" },
      { id: "inspect", label: "视觉审查", role: "Visual Reviewer", type: "verifier", x: 72, y: 70, duration: 20, detail: "检查可读性、分页、溢出和视觉一致性。" },
      { id: "output", label: "验收制品", role: "Authoritative Output", type: "output", x: 92, y: 48, duration: 5, detail: "交付最终制品和视觉检查结果。" }
    ],
    edges: [["brief", "structure", true], ["brief", "assets", false], ["structure", "create", true], ["assets", "create", false], ["create", "render", true], ["render", "inspect", true], ["inspect", "create", false], ["inspect", "output", true]]
  }
};

const state = {
  type: "diagnosis",
  objective: "balanced",
  weight: 68,
  budget: 90,
  selectedNode: null,
  running: false
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function classifyProblem(text) {
  const value = text.toLowerCase();
  if (/pdf|ppt|报告|演示|制品|海报|文档/.test(value)) return "artifact";
  if (/修复|实现|代码|重构|测试|功能|配置/.test(value)) return "software";
  if (/调研|比较|对比|推荐|选型|决策|research|compare/.test(value)) return "research";
  return "diagnosis";
}

function calculateMetrics(topology) {
  const objectiveAdjustments = {
    success: { success: 2.7, latency: 18, tokens: 5.2 },
    balanced: { success: 0, latency: 0, tokens: 0 },
    speed: { success: -4.2, latency: -22, tokens: -5.1 }
  }[state.objective];
  const weightFactor = (state.weight - 68) / 22;
  const success = Math.min(98.6, topology.baseSuccess + objectiveAdjustments.success + weightFactor * 1.4);
  const latency = Math.max(18, Math.round(topology.baseLatency + objectiveAdjustments.latency + weightFactor * 8));
  const tokens = Math.max(4.2, topology.tokens + objectiveAdjustments.tokens + weightFactor * 1.7);
  const budgetPenalty = Math.max(0, latency - state.budget) * 0.32;
  const timeScore = 100 - Math.min(100, latency / state.budget * 25);
  const score = Math.max(40, Math.min(98, Math.round(success * (state.weight / 100) + timeScore * ((100 - state.weight) / 100) - budgetPenalty)));
  return { success, latency, tokens, score };
}

function drawTopology() {
  const topology = TOPOLOGIES[state.type];
  const nodeLayer = $("#node-layer");
  const edgeLayer = $("#edge-layer");
  const isMobile = window.matchMedia("(max-width: 720px)").matches;
  const mobileLayouts = {
    branching: [[50, 9], [18, 29], [50, 29], [82, 29], [50, 52], [25, 71], [50, 90]],
    paired: [[50, 9], [24, 29], [76, 29], [50, 49], [24, 69], [76, 69], [50, 90]]
  };
  const mobileLayout = state.type === "diagnosis" || state.type === "research" ? mobileLayouts.branching : mobileLayouts.paired;
  const nodes = topology.nodes.map((node, index) => isMobile ? { ...node, x: mobileLayout[index][0], y: mobileLayout[index][1] } : node);
  nodeLayer.innerHTML = "";
  edgeLayer.innerHTML = "";
  edgeLayer.setAttribute("viewBox", "0 0 100 100");
  edgeLayer.setAttribute("preserveAspectRatio", "none");

  topology.edges.forEach(([fromId, toId, critical]) => {
    const from = nodes.find((node) => node.id === fromId);
    const to = nodes.find((node) => node.id === toId);
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const startX = from.x;
    const startY = from.y;
    const endX = to.x;
    const endY = to.y;
    const controlX = (startX + endX) / 2;
    path.setAttribute("d", `M ${startX} ${startY} C ${controlX} ${startY}, ${controlX} ${endY}, ${endX} ${endY}`);
    path.setAttribute("class", `edge${critical ? " critical" : ""}`);
    path.dataset.from = fromId;
    path.dataset.to = toId;
    edgeLayer.appendChild(path);
  });

  nodes.forEach((node) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `topology-node ${node.type}`;
    button.dataset.nodeId = node.id;
    button.style.left = `${node.x}%`;
    button.style.top = `${node.y}%`;
    button.innerHTML = `<span class="node-type"><i></i>${node.role}</span><strong>${node.label}</strong><small>~${node.duration}s</small>`;
    button.addEventListener("click", () => inspectNode(node));
    nodeLayer.appendChild(button);
  });
}

function inspectNode(node) {
  state.selectedNode = node.id;
  $$(".topology-node").forEach((element) => element.classList.toggle("selected", element.dataset.nodeId === node.id));
  $("#node-inspector").innerHTML = `<span>当前节点 · ${node.role}</span><strong>${node.label} · 预计 ${node.duration}s</strong><p>${node.detail}</p>`;
}

function renderReasons(topology) {
  $("#reason-list").innerHTML = topology.reasons.map((reason, index) => `
    <div class="reason-item">
      <span class="reason-index">0${index + 1}</span>
      <div><strong>${reason[0]}</strong><p>${reason[1]}</p></div>
    </div>
  `).join("");
}

function renderStrategies(metrics) {
  const options = [
    { name: "直接回答", note: "单 Agent，无复核", structure: 2, success: metrics.success - 14.8, latency: 18, tokens: 4.2, score: metrics.score - 16 },
    { name: "串行流水线", note: "逐阶段传递", structure: 4, success: metrics.success - 5.6, latency: metrics.latency + 24, tokens: metrics.tokens - 1.9, score: metrics.score - 7 },
    { name: "自适应混合拓扑", note: "并行取证，受控汇合", structure: 5, success: metrics.success, latency: metrics.latency, tokens: metrics.tokens, score: metrics.score, recommended: true },
    { name: "全量并行采样", note: "高冗余，多数复核", structure: 6, success: Math.min(99, metrics.success + 2.1), latency: metrics.latency + 38, tokens: metrics.tokens + 13.6, score: metrics.score - 4 }
  ];
  $("#strategy-rows").innerHTML = options.map((option) => `
    <div class="strategy-row${option.recommended ? " recommended" : ""}" role="row">
      <span class="strategy-name">${option.name}${option.recommended ? '<b class="recommend-tag">推荐</b>' : ""}<small>${option.note}</small></span>
      <span class="structure-mini">${Array.from({ length: option.structure }, () => "<i></i><b></b>").join("").replace(/<b><\/b>$/, "")}</span>
      <span>${option.success.toFixed(1)}%</span>
      <span>${Math.round(option.latency)}s</span>
      <span>${option.tokens.toFixed(1)}k</span>
      <span class="score-bar"><strong>${Math.max(0, option.score)}</strong><i style="--score:${Math.max(0, option.score)}%"></i></span>
    </div>
  `).join("");
}

function renderWorkspace(showToast = false) {
  state.type = classifyProblem($("#problem").value);
  state.weight = Number($("#success-weight").value);
  state.budget = Number($("#time-budget").value);
  const topology = TOPOLOGIES[state.type];
  const metrics = calculateMetrics(topology);

  $("#topology-name").textContent = topology.name;
  $("#topology-kind").textContent = topology.kind;
  $("#primitive-list").textContent = topology.primitives;
  $("#critical-path").textContent = `4 阶段 / ${metrics.latency} 秒`;
  $("#parallel-width").textContent = `${topology.nodes.filter((node) => node.type === "worker").length} Agents`;
  $("#success-metric").innerHTML = `${metrics.success.toFixed(1)}<small>%</small>`;
  $("#latency-metric").innerHTML = `${metrics.latency}<small>s</small>`;
  $("#token-metric").innerHTML = `${metrics.tokens.toFixed(1)}<small>k</small>`;
  $("#balance-metric").innerHTML = `${metrics.score}<small>/100</small>`;
  $("#success-delta").textContent = `+${Math.max(3, metrics.success - (metrics.success - 14.8)).toFixed(1)}% vs 直接回答`;
  const difference = state.budget - metrics.latency;
  $("#budget-status").textContent = difference >= 0 ? `预算内 ${difference}s` : `超出预算 ${Math.abs(difference)}s`;
  $("#budget-status").style.color = difference >= 0 ? "var(--green)" : "var(--coral)";
  $("#agent-count").textContent = `${topology.nodes.length - 1} 个执行单元`;
  $("#authority-policy").textContent = topology.authority;
  $("#failure-policy").textContent = topology.failure;
  $("#stop-policy").textContent = topology.stop;
  $("#run-id").textContent = `ES-${String(Math.floor(1000 + Math.random() * 8999))}`;
  $("#node-inspector").innerHTML = "<span>当前节点</span><strong>选择任意节点查看责任边界</strong><p>节点之间只传递完成下一阶段所需的最小上下文。</p>";

  drawTopology();
  renderReasons(topology);
  renderStrategies(metrics);
  if (showToast) toast(`已生成：${topology.name}`);
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function runSimulation() {
  if (state.running) return;
  state.running = true;
  const topology = TOPOLOGIES[state.type];
  const runButton = $("#run-button");
  const trace = $("#trace-timeline");
  const indicator = $("#execution-indicator");
  runButton.disabled = true;
  runButton.innerHTML = "<span>■</span> 模拟运行中";
  indicator.className = "running";
  $("#execution-label").textContent = "拓扑执行中";
  trace.innerHTML = "";
  $$(".topology-node").forEach((node) => node.classList.remove("done", "running"));

  const groups = state.type === "diagnosis" || state.type === "research"
    ? [[topology.nodes[0]], topology.nodes.slice(1, 4), [topology.nodes[4]], [topology.nodes[5]], [topology.nodes[6]]]
    : [[topology.nodes[0]], topology.nodes.slice(1, 3), [topology.nodes[3]], topology.nodes.slice(4, 6), [topology.nodes[6]]];

  let elapsed = 0;
  for (const group of groups) {
    group.forEach((node) => {
      const element = $(`[data-node-id="${node.id}"]`);
      element.classList.add("running");
      topology.edges.filter((edge) => edge[1] === node.id).forEach((edge) => {
        const path = $(`.edge[data-from="${edge[0]}"][data-to="${edge[1]}"]`);
        if (path) path.classList.add("active");
      });
    });
    await sleep(group.length > 1 ? 900 : 650);
    const groupDuration = Math.max(...group.map((node) => node.duration));
    elapsed += groupDuration;
    group.forEach((node) => {
      const element = $(`[data-node-id="${node.id}"]`);
      element.classList.remove("running");
      element.classList.add("done");
      topology.edges.filter((edge) => edge[1] === node.id).forEach((edge) => {
        const path = $(`.edge[data-from="${edge[0]}"][data-to="${edge[1]}"]`);
        if (path) path.classList.remove("active");
      });
      trace.insertAdjacentHTML("beforeend", `
        <div class="trace-item">
          <span class="trace-time">+${String(elapsed).padStart(2, "0")}.0s</span>
          <i class="trace-marker"></i>
          <div class="trace-copy"><strong>${node.label}</strong><span>${node.detail}</span></div>
          <span class="trace-duration">${node.duration}s</span>
        </div>
      `);
    });
  }

  indicator.className = "done";
  $("#execution-label").textContent = `模拟完成 · ${elapsed}s 关键路径`;
  runButton.disabled = false;
  runButton.innerHTML = "<span>↻</span> 再次运行";
  state.running = false;
  toast("拓扑模拟完成，所有汇合条件已满足");
}

function exportPlan() {
  const topology = TOPOLOGIES[state.type];
  const metrics = calculateMetrics(topology);
  const payload = {
    schema: "everyskill.topology-plan/v1",
    problem: $("#problem").value.trim(),
    objective: state.objective,
    time_budget_seconds: state.budget,
    workflow: state.type,
    topology: topology.primitives.split(" · "),
    predicted: { success_rate: Number(metrics.success.toFixed(1)), p50_seconds: metrics.latency, tokens_k: Number(metrics.tokens.toFixed(1)) },
    nodes: topology.nodes.map(({ id, label, role, duration }) => ({ id, label, role, estimated_seconds: duration })),
    edges: topology.edges.map(([from, to, critical]) => ({ from, to, critical }))
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `everyskill-${state.type}-topology.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  toast("编排方案已导出为 JSON");
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove("show"), 2200);
}

$$('[data-objective]').forEach((button) => button.addEventListener("click", () => {
  $$('[data-objective]').forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  state.objective = button.dataset.objective;
  renderWorkspace();
}));

$$('[data-example]').forEach((button) => button.addEventListener("click", () => {
  $("#problem").value = EXAMPLES[button.dataset.example];
  renderWorkspace(true);
}));

$("#success-weight").addEventListener("input", (event) => {
  $("#weight-output").textContent = `${event.target.value}%`;
  renderWorkspace();
});
$("#time-budget").addEventListener("change", () => renderWorkspace());
$("#analyze-button").addEventListener("click", () => renderWorkspace(true));
$("#reset-view").addEventListener("click", () => {
  state.selectedNode = null;
  drawTopology();
  toast("拓扑视图已重置");
});
$("#run-button").addEventListener("click", runSimulation);
$("#export-button").addEventListener("click", exportPlan);
$("#theme-toggle").addEventListener("click", () => document.body.classList.toggle("dark"));

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(drawTopology, 120);
});

renderWorkspace();
