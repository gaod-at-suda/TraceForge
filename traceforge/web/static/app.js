const $ = (id) => document.getElementById(id);

const taskInput = $("task");
const runButton = $("run");
const resetButton = $("reset");
const restoreButton = $("restore-run");
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
let runStartedAt = null;
let runFinishedAt = null;
let restoreState = {available: false, used: false, reason: ""};

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
  rollback_finished: "自动回滚完成",
  manual_restore_started: "手动恢复开始",
  manual_restore_finished: "手动恢复完成",
  acceptance_failed: "验收失败",
  run_finished: "任务完成",
  run_failed: "任务失败",
  run_stopped: "任务停止"
};

const markerIcons = {
  run_started: "R",
  step_started: "S",
  model_started: "AI",
  model_finished: "AI",
  tool_started: ">_",
  tool_finished: "✓",
  tool_failed: "!",
  file_changed: "Δ",
  verification_started: "V",
  verification_finished: "V",
  finalization_started: "F",
  finalization_finished: "F",
  rollback_started: "↩",
  rollback_finished: "↩",
  manual_restore_started: "↶",
  manual_restore_finished: "↶",
  acceptance_failed: "!",
  run_finished: "✓",
  run_failed: "!",
  run_stopped: "■"
};

function short(value, limit = 100) {
  const text = String(value ?? "");
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

function setStatus(kind, text) {
  $("status-dot").className = `dot ${kind}`;
  $("status-text").textContent = text;
}

function setChip(id, key, value) {
  const element = $(id);
  element.innerHTML = "";
  const keySpan = document.createElement("span");
  keySpan.className = "chip-key";
  keySpan.textContent = key;
  const valueSpan = document.createElement("span");
  valueSpan.textContent = value;
  element.append(keySpan, valueSpan);
}

function setResultBadge(kind, text) {
  const badge = $("result-badge");
  badge.className = `result-badge ${kind}`;
  badge.innerHTML = "<i></i>";
  badge.append(document.createTextNode(text));
}

function updateRestoreUi(busy = false) {
  const available = Boolean(restoreState && restoreState.available);
  const used = Boolean(restoreState && restoreState.used);
  restoreButton.disabled = busy || !available;
  restoreButton.textContent = used ? "✓ 已恢复" : "↩ 恢复本次修改";
  restoreButton.title = (restoreState && restoreState.reason)
    || "仅在本次任务存在安全 Git Checkpoint 且工作区未被再次修改时可用";
}

function setRunningUi(running) {
  runButton.disabled = running;
  resetButton.disabled = running;
  browseWorkspaceButton.disabled = running;
  applyWorkspaceButton.disabled = running;
  runButton.classList.toggle("running", running);
  $("run-label").textContent = running ? "Agent 运行中" : "运行 Agent";
  updateRestoreUi(running);
}

function markerClass(type, data = {}) {
  if (["tool_failed", "run_failed", "acceptance_failed", "run_stopped"].includes(type)) return "bad";
  if (["verification_finished", "rollback_finished", "manual_restore_finished"].includes(type)) return data.success ? "good" : "bad";
  if (["tool_finished", "run_finished", "file_changed", "finalization_finished"].includes(type)) return "good";
  if (["step_started", "model_started", "tool_started", "verification_started", "rollback_started", "manual_restore_started", "finalization_started"].includes(type)) return "warn";
  return "info";
}

function formatClock(timestamp) {
  if (!timestamp) return "";
  return new Date(timestamp * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function formatElapsed(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "-";
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`;
  const minutes = Math.floor(seconds / 60);
  const remain = Math.floor(seconds % 60);
  return `${minutes}m ${String(remain).padStart(2, "0")}s`;
}

function updateDuration() {
  if (!runStartedAt) {
    $("metric-duration").textContent = "-";
    return;
  }
  const end = runFinishedAt || Date.now() / 1000;
  $("metric-duration").textContent = formatElapsed(end - runStartedAt);
}

function eventLabel(event) {
  const d = event.data || {};
  switch (event.event_type) {
    case "run_started":
      return ["任务开始", `${short(d.task, 88)} · ${modeNames[d.mode] || d.mode || "-"}模式 · Git ${d.checkpoint_enabled ? "Checkpoint Ready" : "Checkpoint Off"}`];
    case "step_started":
      return [`步骤 ${event.step}`, `执行预算 ${d.max_steps} steps`];
    case "model_started":
      return [d.finalization ? "模型收尾" : "模型思考", `${d.message_count ?? "-"} 条上下文消息`];
    case "model_finished":
      return [d.finalization ? "收尾响应" : "模型响应", d.content ? short(d.content, 94) : `${d.tool_call_count ?? 0} 个工具调用`];
    case "tool_started":
      return [`调用 ${d.tool || "tool"}`, short(JSON.stringify(d.arguments || {}), 96)];
    case "tool_finished":
      return [`完成 ${d.tool || "tool"}`, `${Number(d.duration_ms || 0).toFixed(1)} ms · ${short(d.output, 82)}`];
    case "tool_failed":
      return [`工具失败 · ${d.tool || "tool"}`, short(d.error, 92)];
    case "file_changed":
      return ["文件已修改", d.path || "-"];
    case "verification_started":
      return ["宿主自动验证", "独立于模型执行真实项目测试"];
    case "verification_finished":
      return [d.success ? "自动验证通过" : "自动验证失败", d.command || d.reason || "-"];
    case "finalization_started":
      return ["进入收尾阶段", "关闭工具，仅允许输出最终总结"];
    case "finalization_finished":
      return [d.success ? "收尾完成" : "收尾失败", short(d.message || "-")];
    case "rollback_started":
      return ["Git 回滚开始", d.reason || "恢复任务开始前的 Checkpoint"];
    case "rollback_finished":
      return [d.success ? "Git 自动回滚完成" : "Git 自动回滚失败", d.revision || "-"];
    case "manual_restore_started":
      return ["恢复本次修改", d.reason || "恢复任务开始前的 Git Checkpoint"];
    case "manual_restore_finished":
      return [d.success ? "本次修改已恢复" : "手动恢复失败", d.message || d.revision || "-"];
    case "acceptance_failed":
      return ["最终验收失败", d.reason || "-"];
    case "run_finished":
      return ["任务完成", short(d.message, 96)];
    case "run_failed":
      return ["任务失败", short(d.error || d.message, 96)];
    case "run_stopped":
      return ["任务停止", short(d.reason || d.error || d.message || "-", 96)];
    default:
      return [eventNames[event.event_type] || event.event_type, short(JSON.stringify(d), 96)];
  }
}

function selectEvent(event, element = null) {
  document.querySelectorAll(".event.selected").forEach((item) => item.classList.remove("selected"));
  if (element) element.classList.add("selected");

  const d = event.data || {};
  $("detail-seq").textContent = `#${event.seq ?? "-"}`;
  $("detail-type").textContent = eventNames[event.event_type] || event.event_type || "-";
  $("detail-tool").textContent = d.tool || "-";
  $("detail-duration").textContent = d.duration_ms != null ? `${Number(d.duration_ms).toFixed(1)} ms` : "-";
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

  const marker = document.createElement("span");
  marker.className = `marker ${markerClass(event.event_type, d)}`;
  marker.textContent = markerIcons[event.event_type] || "·";

  const content = document.createElement("span");
  content.className = "event-content";
  const titleRow = document.createElement("span");
  titleRow.className = "event-title-row";
  const titleSpan = document.createElement("span");
  titleSpan.className = "event-title";
  titleSpan.textContent = title;
  const typeSpan = document.createElement("span");
  typeSpan.className = "event-type";
  typeSpan.textContent = event.event_type;
  titleRow.append(titleSpan, typeSpan);
  const subSpan = document.createElement("span");
  subSpan.className = "event-sub";
  subSpan.textContent = sub;
  content.append(titleRow, subSpan);

  const eventTime = document.createElement("span");
  eventTime.className = "event-time";
  eventTime.textContent = formatClock(event.timestamp) || `#${event.seq}`;

  button.append(marker, content, eventTime);
  button.addEventListener("click", () => selectEvent(event, button));
  timeline.appendChild(button);
  timeline.scrollTop = timeline.scrollHeight;

  if (event.event_type === "run_started") {
    runStartedAt = event.timestamp || Date.now() / 1000;
    runFinishedAt = null;
    updateDuration();
  }
  if (["run_finished", "run_failed", "run_stopped"].includes(event.event_type)) {
    runFinishedAt = event.timestamp || Date.now() / 1000;
    updateDuration();
  }
  if (event.step) $("step-label").textContent = `步骤 ${event.step}`;

  if (event.event_type === "file_changed") {
    const path = d.path || "unknown";
    const history = changedFiles.get(path) || [];
    history.push(d.diff || "");
    changedFiles.set(path, history);
    renderChanges();
    selectEvent(event, button);
  }

  if (event.event_type === "verification_finished") {
    latestVerification = d;
    $("metric-verify").textContent = d.success ? "通过" : "失败";
    selectEvent(event, button);
  }

  if (["tool_failed", "run_failed", "run_stopped", "rollback_finished", "manual_restore_finished", "acceptance_failed"].includes(event.event_type)) {
    selectEvent(event, button);
  }
}

function diffStats(text) {
  let additions = 0;
  let deletions = 0;
  for (const line of String(text || "").split("\n")) {
    if (line.startsWith("+") && !line.startsWith("+++")) additions += 1;
    if (line.startsWith("-") && !line.startsWith("---")) deletions += 1;
  }
  return {additions, deletions};
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
    const fullDiff = diffs.filter(Boolean).join("\n\n");
    const stats = diffStats(fullDiff);
    const item = document.createElement("div");
    item.className = "change-item";

    const head = document.createElement("div");
    head.className = "change-head";
    const nameWrap = document.createElement("div");
    nameWrap.className = "change-name";
    const name = document.createElement("strong");
    name.textContent = path;
    const stat = document.createElement("span");
    stat.className = "change-stat";
    stat.innerHTML = `<span class="add">+${stats.additions}</span> &nbsp; <span class="del">-${stats.deletions}</span>`;
    nameWrap.append(name, stat);

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = "查看 Diff";
    const pre = document.createElement("pre");
    pre.hidden = true;
    pre.textContent = fullDiff || "未记录文本 Diff。";
    toggle.addEventListener("click", () => {
      pre.hidden = !pre.hidden;
      toggle.textContent = pre.hidden ? "查看 Diff" : "收起 Diff";
    });

    head.append(nameWrap, toggle);
    item.append(head, pre);
    changesEl.appendChild(item);
  }
}

function resetView(message = "") {
  timeline.innerHTML = `
    <div class="empty-state">
      <div class="empty-orbit"><span>⌁</span></div>
      <strong>${message ? "已就绪" : "Agent 启动中"}</strong>
      <p>${message || "执行时间线将实时更新。"}</p>
    </div>`;

  events = [];
  changedFiles = new Map();
  latestVerification = null;
  restoreState = {available: false, used: false, reason: ""};
  updateRestoreUi(false);
  lastSeq = 0;
  runStartedAt = null;
  runFinishedAt = null;
  $("step-label").textContent = "步骤 -";
  $("metric-steps").textContent = "-";
  $("metric-verify").textContent = "-";
  $("metric-changes").textContent = "0";
  $("metric-duration").textContent = "-";
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
    // 本地服务短暂不可用时保留当前页面，不打断任务展示。
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
    setChip("model-chip", "MODEL", data.model || "-");
    setChip("mode-chip", "MODE", modeNames[data.mode] || data.mode || "-");
    restoreState = data.restore || {available: false, used: false, reason: ""};
    setRunningUi(Boolean(data.running));

    if (data.running) {
      setStatus("running", "运行中");
      setResultBadge("running", "运行中");
      return;
    }

    if (data.result) {
      const success = Boolean(data.result.success);
      const restored = Boolean(data.restore && data.restore.used);
      setStatus(restored ? "idle" : (success ? "done" : "failed"), restored ? "已恢复" : (success ? "已完成" : "失败"));
      setResultBadge(restored ? "restored" : (success ? "good" : "bad"), restored ? "已恢复" : (success ? "通过" : "失败"));
      $("metric-steps").textContent = data.result.steps ?? "-";
      $("final-answer").textContent = data.result.message || "任务结束，但没有返回总结。";
      $("message").textContent = restored
        ? (data.restore.reason || "本次 Agent 修改已恢复。")
        : (success ? `运行 ${data.result.run_id || ""} 已完成。` : (data.result.message || "任务失败"));

      if (!latestVerification) {
        $("metric-verify").textContent = success && changedFiles.size === 0 ? "无需额外" : (success ? "未记录" : "失败");
      }
      if (!runFinishedAt && runStartedAt) runFinishedAt = Date.now() / 1000;
      updateDuration();
      return;
    }

    setStatus("idle", "空闲");
    setResultBadge("neutral", "等待中");
  } catch (_) {
    setRunningUi(false);
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
  setRunningUi(true);
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
      setRunningUi(false);
      return;
    }
    $("message").textContent = "任务已提交，TraceForge 正在执行。";
    await pollEvents();
    await pollStatus();
  } catch (err) {
    setResultBadge("bad", "错误");
    $("message").textContent = `无法连接本地服务：${err}`;
    setRunningUi(false);
  }
}

async function restoreLastRun() {
  if (!restoreState.available) {
    $("message").textContent = restoreState.reason || "当前没有可恢复的 Agent 修改。";
    return;
  }

  const confirmed = window.confirm(
    "将把当前工作区恢复到本次 Agent 任务开始前的 Git Checkpoint，并删除本次任务创建的未跟踪文件。\n\n"
    + "只有在任务结束后工作区没有新的人工修改时才会执行。是否继续？"
  );
  if (!confirmed) return;

  restoreButton.disabled = true;
  $("message").textContent = "正在安全恢复本次 Agent 修改…";
  try {
    const res = await fetch("/api/restore", {method: "POST"});
    const data = await res.json();
    if (!res.ok || !data.ok) {
      $("message").textContent = data.error || "恢复失败";
      await pollStatus();
      return;
    }

    $("message").textContent = data.message || "本次修改已恢复。";
    await pollEvents();
    await pollStatus();
  } catch (err) {
    $("message").textContent = `恢复失败：${err}`;
    await pollStatus();
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

function clearFolderSelection() {
  document.querySelectorAll(".folder-row.selected").forEach((el) => el.classList.remove("selected"));
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
      list.innerHTML = '<div class="empty-state" style="min-height:240px"><strong>空目录</strong><p>当前目录没有可进入的子文件夹。</p></div>';
    }

    for (const folder of data.children || []) {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "folder-row";

      const icon = document.createElement("span");
      icon.className = "folder-icon";
      icon.textContent = "▰";
      const name = document.createElement("span");
      name.className = "folder-name";
      name.textContent = folder.name;
      const folderPath = document.createElement("span");
      folderPath.className = "folder-path";
      folderPath.textContent = folder.path;
      row.append(icon, name, folderPath);

      row.addEventListener("click", () => {
        clearFolderSelection();
        row.classList.add("selected");
        $("browser-path").value = folder.path;
      });
      row.addEventListener("dblclick", () => loadDirectory(folder.path));
      list.appendChild(row);
    }
  } catch (err) {
    $("browser-message").textContent = `目录读取失败：${err}`;
  }
}

function openWorkspaceModal() {
  workspaceModal.hidden = false;
  document.body.style.overflow = "hidden";
  loadDirectory(workspaceInput.value.trim());
}

function closeWorkspaceModal() {
  workspaceModal.hidden = true;
  document.body.style.overflow = "";
}

runButton.addEventListener("click", startRun);
restoreButton.addEventListener("click", restoreLastRun);
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
setInterval(updateDuration, 250);
pollStatus();
