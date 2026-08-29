"""生成一键测试的静态可视化 HTML 报告。

报告完全由本地生成，不需要额外 Web 框架或服务器。
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _escape(value: Any) -> str:
    return html.escape(str(value))


def build_html_report(
    output_path: Path,
    scenario_name: str,
    scenario_description: str,
    task: str,
    agent_success: bool,
    agent_message: str,
    agent_steps: int,
    verification_success: bool,
    verification_output: str,
    events: list[dict],
    diffs: dict[str, str],
) -> Path:
    """把 Agent 事件、最终验证结果和文件 Diff 写入 HTML。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    event_rows = []
    for event in events:
        event_type = _escape(event.get("event_type", ""))
        step = event.get("step")
        data = event.get("data", {})
        event_rows.append(
            "<div class='event'>"
            f"<div class='event-head'><span class='type'>{event_type}</span>"
            f"<span class='step'>Step {_escape(step if step is not None else '-')}</span></div>"
            f"<pre>{_escape(json.dumps(data, ensure_ascii=False, indent=2))}</pre>"
            "</div>"
        )

    diff_blocks = []
    if diffs:
        for path, diff in diffs.items():
            diff_blocks.append(
                "<section class='diff-card'>"
                f"<h3>{_escape(path)}</h3>"
                f"<pre class='diff'>{_escape(diff)}</pre>"
                "</section>"
            )
    else:
        diff_blocks.append("<p class='muted'>Agent 没有修改任何文本文件。</p>")

    agent_status = "PASS" if agent_success else "FAIL"
    verify_status = "PASS" if verification_success else "FAIL"

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TraceForge Direct Test Report</title>
<style>
body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    background: #f6f7f9;
    color: #20242a;
}}
main {{ max-width: 1180px; margin: 0 auto; padding: 28px 18px 48px; }}
h1 {{ margin-bottom: 8px; }}
h2 {{ margin-top: 30px; }}
.card {{
    background: white;
    border: 1px solid #dfe3e8;
    border-radius: 12px;
    padding: 18px;
    margin-top: 14px;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 12px;
}}
.metric {{ font-size: 13px; color: #69707a; }}
.metric strong {{ display: block; color: #20242a; font-size: 22px; margin-top: 4px; }}
.pass {{ color: #197a42 !important; }}
.fail {{ color: #b42318 !important; }}
pre {{
    white-space: pre-wrap;
    word-break: break-word;
    background: #f8f9fb;
    border-radius: 8px;
    padding: 12px;
    overflow-x: auto;
}}
.event {{
    border-left: 3px solid #9098a3;
    padding: 8px 12px;
    margin: 10px 0;
    background: white;
}}
.event-head {{ display: flex; gap: 12px; justify-content: space-between; }}
.type {{ font-weight: 700; }}
.step {{ color: #69707a; }}
.diff-card {{
    background: white;
    border: 1px solid #dfe3e8;
    border-radius: 12px;
    padding: 16px;
    margin-top: 12px;
}}
.diff {{ background: #15181d; color: #e8ebef; }}
.muted {{ color: #69707a; }}
</style>
</head>
<body>
<main>
<h1>TraceForge 一键自动测试报告</h1>
<p class="muted">{_escape(scenario_description)}</p>

<div class="grid">
  <div class="card metric">Agent 结果<strong class="{'pass' if agent_success else 'fail'}">{agent_status}</strong></div>
  <div class="card metric">独立 pytest 验证<strong class="{'pass' if verification_success else 'fail'}">{verify_status}</strong></div>
  <div class="card metric">Agent Steps<strong>{agent_steps}</strong></div>
  <div class="card metric">场景<strong style="font-size:16px">{_escape(scenario_name)}</strong></div>
</div>

<h2>预设任务</h2>
<div class="card"><pre>{_escape(task)}</pre></div>

<h2>Agent 最终回答</h2>
<div class="card"><pre>{_escape(agent_message)}</pre></div>

<h2>独立 pytest 验证</h2>
<div class="card"><pre>{_escape(verification_output)}</pre></div>

<h2>代码修改 Diff</h2>
{''.join(diff_blocks)}

<h2>Agent Timeline</h2>
<div class="card">
{''.join(event_rows) if event_rows else '<p class="muted">没有记录到事件。</p>'}
</div>
</main>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
    return output_path
