const $ = (id) => document.getElementById(id);
const taskInput = $("task");
const runButton = $("run");
const resetButton = $("reset");
const timeline = $("timeline");
const changesEl = $("changes");
const workspaceInput = $("workspace-input");
const browseWorkspaceButton = $("browse-workspace");
const applyWorkspaceButton = $("apply-workspace");
const workspaceModal = $("workspace-modal");
let lastSeq = 0;
let events = [];
let changedFiles = new Map();
let latestVerification = null;
let pollBusy = false;
let browserCurrent = "";
let browserParent = null;

const modeNames = {auto: "自动", plan: "规划", confirm: "确认"};
const eventNames = {
  run_started: "任务开始",
  step_started: "步骤开始",
  model_started: "模型思考",
  model_finished: "模型响应",
  tool_started: "工具调用开始",
  tool_finished: "工具调用完成",
  tool_failed: "工具调用失败",
  file_changed: "文件已修改",
  verification_started: "自动验证开始",
  verification_finished: "自动验证完成",
  finalization_started: "收尾阶段开始",
  finalization_finished: "收尾阶段完成",
  rollback_started: "回滚开始",
  rollback_finished: "回滚完成",
  acceptance_failed: "验收失败",
  run_finished: "任务完成",
  run_failed: "任务失败",
  run_stopped: "任务停止"
};

function short(value, limit = 100) {
  const text = String(value ?? "");
  return text.length > limit ? text.slice(0, limit) + "…" : text;
}

function setStatus(kind, text) {
  const dot = $("status-dot");
  dot.className = `dot ${kind}`;
  $("status-text").textContent = text;
}

function setResultBadge(kind, text) {
  const badge = $("result-badge");
  badge.className = `result-badge ${kind}`;
  badge.textContent = text;
}

function markerClass(type, data = {}) {
  if (["tool_failed", "run_failed", "acceptance_failed", "run_stopped"].includes(type)) return "bad";
  if (type === "verification_finished") return data.success ? "good" : "bad";
  if (type === "rollback_finished") return data.success ? "good" : "bad";
  if (["tool_finished", "run_finished", "file_changed", "finalization_finished"].includes(type)) return "good";
  if (["run_started", "step_started", "model_started", "tool_started", "verification_started", "rollback_started", "finalization_started"].includes(type)) return "warn";
  return "info";
}

function eventLabel(event) {
  const d = event.data || {};
  switch (event.event_type) {
    case "run_started": return ["任务开始", `${short(d.task)} · 模式=${modeNames[d.mode] || d.mode || "-"} · Git 基线=${d.checkpoint_enabled ? "已启用" : "未启用"}`];
    case "step_started": return [`步骤 ${event.step}`, `最大工具步数 ${d.max_steps}`];
    case "model_started": return [d.finalization ? "模型收尾" : "模型思考", `${d.message_count} 条上下文消息`];
    case "model_finished": return [d.finalization ? "收尾响应" : "模型响应", d.content ? short(d.content) : `${d.tool_call_count} 个工具调用`];
    case "tool_started": return [`▶ ${d.tool}`, short(JSON.stringify(d.arguments || {}))];
    case "tool_finished": return [`✓ ${d.tool}`, `${d.duration_ms ?? "-"} ms · ${short(d.output, 80)}`];
    case "tool_failed": return [`✕ ${d.tool}`, short(d.error)];
    case "file_changed": return ["文件已修改", d.path || "-"];
    case "verification_started": return ["自动验证", "宿主侧独立验证开始"];
    case "verification_finished": return [d.success ? "✓ 自动验证通过" : "✕ 自动验证失败", d.command || d.reason || "-"];
    case "finalization_started": return ["进入收尾阶段", "工具已关闭，仅允许模型输出最终总结"];
    case "finalization_finished": return [d.success ? "✓ 收尾完成" : "✕ 收尾失败", short(d.message || "-")];
    case "rollback_started": return ["↩ Git 回滚", d.reason || "恢复任务开始前的 Git Checkpoint"];
    case "rollback_finished": return [d.success ? "✓ Git 回滚完成" : "✕ Git 回滚失败", d.revision || "-"];
    case "acceptance_failed": return ["验收失败", d.reason || "-"];
    case "run_finished": return ["任务完成", short(d.message)];
    case "run_failed": return ["任务失败", short(d.error || d.message)];
    case "run_stopped": return ["任务停止", short(d.reason || d.error || d.message || "-")];
    default: return [eventNames[event.event_type] || event.event_type, short(JSON.stringify(d))];
  }
}

function selectEvent(event) {
  const d = event.data || {};
  $("detail-seq").textContent = `#${event.seq ?? "-"}`;
  $("detail-type").textContent = eventNames[event.event_type] || event.event_type || "-";
  $("detail-tool").textContent = d.tool || "-";
  $("detail-duration").textContent = d.duration_ms != null ? `${d.duration_ms} ms` : "-";
  $("detail-step").textContent = event.step ?? "-";
  $("detail-output").textContent = d.error || d.output || d.content || d.message || JSON.stringify(d, null, 2);
  const diff = d.diff || (d.metadata && d.metadata.diff);
  $("detail-diff").textContent = diff || "暂无代码差异。";
}

function appendEvent(event) {
  if (timeline.querySelector(".empty-state")) timeline.innerHTML = "";
  events.push(event);
  const d = event.data || {};
  const [title, sub] = eventLabel(event);
  const button = document.createElement("button");
  button.type = "button";
  button.className = "event";
  button.innerHTML = `
    <span class="marker ${markerClass(event.event_type, d)}"></span>
    <span><span class="event-title"></span><span class="event-sub"></span></span>
    <span class="event-time">#${event.seq}</span>`;
  button.querySelector(".event-title").textContent = title;
  button.querySelector(".event-sub").textContent = sub;
  button.addEventListener("click", () => selectEvent(event));
  timeline.appendChild(button);
  timeline.scrollTop = timeline.scrollHeight;

  if (event.step) $("step-label").textContent = `步骤 ${event.step}`;
  if (event.event_type === "file_changed") {
    const path = d.path || "unknown";
    const history = changedFiles.get(path) || [];
    history.push(d.diff || "");
    changedFiles.set(path, history);
    renderChanges();
    selectEvent(event);
  }
  if (event.event_type === "verification_finished") {
    latestVerification = d;
    $("metric-verify").textContent = d.success ? "通过" : "失败";
    selectEvent(event);
  }
  if (["tool_failed", "run_failed", "run_stopped", "rollback_finished", "acceptance_failed"].includes(event.event_type)) {
    selectEvent(event);
  }
}

function renderChanges() {
  const entries = [...changedFiles.entries()];
  $("metric-changes").textContent = String(entries.length);
  $("change-count").textContent = `${entries.length} 个文件`;
  if (!entries.length) {
    changesEl.innerHTML = '<p class="empty-inline">暂无文件修改。</p>';
    return;
  }
  changesEl.innerHTML = "";
  for (const [path, diffs] of entries) {
    const item = document.createElement("div");
    item.className = "change-item";
    const head = document.createElement("div");
    head.className = "change-head";
    const name = document.createElement("span");
    name.textContent = path;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = "展开差异";
    const pre = document.createElement("pre");
    pre.hidden = true;
    pre.textContent = diffs.filter(Boolean).join("\n\n");
    toggle.addEventListener("click", () => {
      pre.hidden = !pre.hidden;
      toggle.textContent = pre.hidden ? "展开差异" : "收起差异";
    });
    head.append(name, toggle);
    item.append(head, pre);
    changesEl.appendChild(item);
  }
}

function resetView(message = "") {
  timeline.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⌁</div>
      <p>${message || "Agent 正在启动，执行时间线将实时更新。"}</p>
    </div>`;
  events = [];
  changedFiles = new Map();
  latestVerification = null;
  lastSeq = 0;
  $("step-label").textContent = "步骤 -";
  $("metric-steps").textContent = "-";
  $("metric-verify").textContent = "-";
  $("metric-changes").textContent = "0";
  $("change-count").textContent = "0 个文件";
  changesEl.innerHTML = '<p class="empty-inline">暂无文件修改。</p>';
  $("final-answer").textContent = "Agent 正在工作…";
  $("detail-seq").textContent = "#-";
  $("detail-type").textContent = "-";
  $("detail-tool").textContent = "-";
  $("detail-duration").textContent = "-";
  $("detail-step").textContent = "-";
  $("detail-output").textContent = "等待事件…";
  $("detail-diff").textContent = "暂无代码差异。";
  setResultBadge("running", "运行中");
}

async function pollEvents() {
  if (pollBusy) return;
  pollBusy = true;
  try {
    const res = await fetch(`/api/events?after=${lastSeq}`, {cache: "no-store"});
    if (!res.ok) return;
    const data = await res.json();
    for (const event of data.events || []) {
      lastSeq = Math.max(lastSeq, event.seq || 0);
      appendEvent(event);
    }
  } catch (_) {
    // 本地服务短暂不可用时保持页面，不打断用户操作。
  } finally {
    pollBusy = false;
  }
}

async function pollStatus() {
  try {
    const res = await fetch("/api/status", {cache: "no-store"});
    if (!res.ok) return;
    const data = await res.json();
    $("workspace").textContent = `当前工作区：${data.workspace || "-"}`;
    if (document.activeElement !== workspaceInput) workspaceInput.value = data.workspace || "";
    $("model-chip").textContent = `模型：${data.model || "-"}`;
    $("mode-chip").textContent = `模式：${modeNames[data.mode] || data.mode || "-"}`;
    runButton.disabled = Boolean(data.running);
    resetButton.disabled = Boolean(data.running);
    browseWorkspaceButton.disabled = Boolean(data.running);
    applyWorkspaceButton.disabled = Boolean(data.running);

    if (data.running) {
      setStatus("running", "运行中");
      setResultBadge("running", "运行中");
    } else if (data.result) {
      const success = Boolean(data.result.success);
      setStatus(success ? "done" : "failed", success ? "已完成" : "失败");
      setResultBadge(success ? "good" : "bad", success ? "通过" : "失败");
      $("metric-steps").textContent = data.result.steps ?? "-";
      $("final-answer").textContent = data.result.message || "任务结束，但没有返回总结。";
      $("message").textContent = success ? `运行 ${data.result.run_id || ""} 已完成。` : (data.result.message || "任务失败");
      if (!latestVerification) $("metric-verify").textContent = success ? "未触发" : "失败";
    } else {
      setStatus("idle", "空闲");
      setResultBadge("neutral", "等待中");
    }
  } catch (_) {
    setStatus("failed", "连接中断");
  }
}

async function startRun() {
  const task = taskInput.value.trim();
  if (!task) {
    $("message").textContent = "请先输入一段编程任务。";
    taskInput.focus();
    return;
  }

  resetView();
  runButton.disabled = true;
  $("message").textContent = "正在提交任务…";
  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({task})
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      setResultBadge("bad", "错误");
      $("message").textContent = data.error || "提交失败";
      runButton.disabled = false;
      return;
    }
    $("message").textContent = "任务已提交，Agent 正在工作。";
    await pollEvents();
    await pollStatus();
  } catch (err) {
    setResultBadge("bad", "错误");
    $("message").textContent = `无法连接本地服务：${err}`;
    runButton.disabled = false;
  }
}

async function switchWorkspace(path) {
  const target = String(path || "").trim();
  if (!target) {
    $("message").textContent = "请先选择或输入工作区目录。";
    return false;
  }
  applyWorkspaceButton.disabled = true;
  browseWorkspaceButton.disabled = true;
  $("message").textContent = "正在切换工作区…";
  try {
    const res = await fetch("/api/workspace", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({path: target})
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      $("message").textContent = data.error || "工作区切换失败";
      return false;
    }
    resetView("工作区已切换，可以输入新的编程任务。");
    $("final-answer").textContent = "任务完成后，Agent 的最终总结会显示在这里。";
    setResultBadge("neutral", "等待中");
    workspaceInput.value = data.workspace || target;
    $("message").textContent = `工作区已切换：${data.workspace || target}`;
    await pollStatus();
    return true;
  } catch (err) {
    $("message").textContent = `工作区切换失败：${err}`;
    return false;
  } finally {
    applyWorkspaceButton.disabled = false;
    browseWorkspaceButton.disabled = false;
  }
}

async function loadDirectory(path = "") {
  $("browser-message").textContent = "正在读取目录…";
  try {
    const query = path ? `?path=${encodeURIComponent(path)}` : "";
    const res = await fetch(`/api/directories${query}`, {cache: "no-store"});
    const data = await res.json();
    if (!res.ok || !data.ok) {
      $("browser-message").textContent = data.error || "目录读取失败";
      return;
    }
    browserCurrent = data.current || "";
    browserParent = data.parent || null;
    $("browser-path").value = browserCurrent;
    $("browser-parent").disabled = !browserParent;
    $("browser-message").textContent = data.truncated ? "目录较多，仅显示前 250 个文件夹。" : "";

    const roots = $("browser-roots");
    roots.innerHTML = "";
    for (const root of data.roots || []) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "root-button";
      button.textContent = root;
      button.addEventListener("click", () => loadDirectory(root));
      roots.appendChild(button);
    }

    const list = $("folder-list");
    list.innerHTML = "";
    if (!(data.children || []).length) {
      list.innerHTML = '<div class="empty-state" style="min-height:210px"><p>当前目录没有可进入的子文件夹。</p></div>';
    }
    for (const folder of data.children || []) {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "folder-row";
      row.innerHTML = '<span class="folder-icon">▰</span><span class="folder-name"></span><span class="folder-path"></span>';
      row.querySelector(".folder-name").textContent = folder.name;
      row.querySelector(".folder-path").textContent = folder.path;
      row.addEventListener("dblclick", () => loadDirectory(folder.path));
      row.addEventListener("click", () => {
        document.querySelectorAll(".folder-row").forEach((el) => el.style.outline = "none");
        row.style.outline = "1px solid #74bfff";
        $("browser-path").value = folder.path;
      });
      list.appendChild(row);
    }
  } catch (err) {
    $("browser-message").textContent = `目录读取失败：${err}`;
  }
}

function openWorkspaceModal() {
  workspaceModal.hidden = false;
  loadDirectory(workspaceInput.value.trim());
}

function closeWorkspaceModal() {
  workspaceModal.hidden = true;
}

runButton.addEventListener("click", startRun);
resetButton.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/reset", {method: "POST"});
    const data = await res.json();
    if (data.ok) {
      resetView("会话已重置，可以输入新的任务。");
      $("final-answer").textContent = "任务完成后，Agent 的最终总结会显示在这里。";
      setResultBadge("neutral", "等待中");
      $("message").textContent = "已清除当前工作区的多轮会话历史。";
    } else {
      $("message").textContent = data.error || "重置失败";
    }
  } catch (err) {
    $("message").textContent = `重置失败：${err}`;
  }
});

applyWorkspaceButton.addEventListener("click", () => switchWorkspace(workspaceInput.value));
browseWorkspaceButton.addEventListener("click", openWorkspaceModal);
$("close-workspace").addEventListener("click", closeWorkspaceModal);
$("cancel-workspace").addEventListener("click", closeWorkspaceModal);
$("workspace-backdrop").addEventListener("click", closeWorkspaceModal);
$("browser-parent").addEventListener("click", () => browserParent && loadDirectory(browserParent));
$("browser-go").addEventListener("click", () => loadDirectory($("browser-path").value.trim()));
$("browser-path").addEventListener("keydown", (event) => {
  if (event.key === "Enter") loadDirectory($("browser-path").value.trim());
});
$("select-workspace").addEventListener("click", async () => {
  const selected = $("browser-path").value.trim() || browserCurrent;
  const ok = await switchWorkspace(selected);
  if (ok) closeWorkspaceModal();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !workspaceModal.hidden) closeWorkspaceModal();
});

taskInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    startRun();
  }
});

document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    taskInput.value = button.dataset.prompt || "";
    taskInput.focus();
  });
});

setInterval(pollEvents, 400);
setInterval(pollStatus, 650);
pollStatus();
