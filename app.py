#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直触深网 —— Web 前端服务
====================================
启动后自动打开浏览器，用户在页面中填写 API Key、Base URL、模型名称等关键信息，
点击「生成周报」即可运行 Agent 并查看 / 下载 Markdown 周报。

依赖：flask, markdown（均已随核心依赖安装）
运行：python app.py   （打包后即为 直触深网.exe）
"""

from __future__ import annotations

import datetime
import os
import sys
import threading
import uuid
import webbrowser

import markdown
from flask import Flask, jsonify, request, Response

from cybersecurity_weekly_agent import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_RSS_FEEDS,
    COPYRIGHT_TEXT,
    ReportConfig,
    generate_report,
    write_report,
    export_docx,
)

app = Flask(__name__)
app.json.ensure_ascii = False  # 中文原样返回，避免转义

# 任务登记表：task_id -> {status, progress[], result, html, filename, error}
TASKS: dict = {}
# 线程锁，保护 TASKS 字典的并发写入
TASKS_LOCK = threading.Lock()
HOST = "127.0.0.1"
PORT = 8029                               # 统一服务端口


# ----------------------------- 任务执行 -----------------------------

def _parse_feeds(text: str):
    if not text or not text.strip():
        return list(DEFAULT_RSS_FEEDS)
    feeds = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            name, url = line.split("|", 1)
            feeds.append((name.strip(), url.strip()))
    return feeds or list(DEFAULT_RSS_FEEDS)


def _append_progress(tid: str, msg: str) -> None:
    """线程安全地追加进度消息到任务记录。"""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    with TASKS_LOCK:
        if tid in TASKS:
            TASKS[tid].setdefault("progress", []).append(line)
            TASKS[tid]["last_update"] = ts
    # 同时输出到 stderr，方便打包后排查
    print(line, file=sys.stderr, flush=True)


def run_task(tid: str, payload: dict) -> None:
    try:
        _append_progress(tid, "[任务] 已接收，开始处理")
        _append_progress(tid, f"[任务] 线程ID={threading.get_ident()}")
        cfg = ReportConfig(
            api_key=(payload.get("api_key") or "").strip(),
            base_url=(payload.get("base_url") or DEFAULT_BASE_URL).strip(),
            model=(payload.get("model") or DEFAULT_MODEL).strip(),
            days=int(payload.get("days") or 7),
            start_date=payload.get("start_date") or None,
            end_date=payload.get("end_date") or None,
            max_events=int(payload.get("max_events") or 20),
            max_full_text=int(payload.get("max_full_text") or 20),
            rss_feeds=_parse_feeds(payload.get("feeds") or ""),
            selected_tags=payload.get("selected_tags") or [],
            selected_regions=payload.get("selected_regions") or [],
        )
        _append_progress(tid, f"[任务] 参数校验完成，days={cfg.days}, max_events={cfg.max_events}")
        _append_progress(tid, f"[任务] selected_tags={cfg.selected_tags}, selected_regions={cfg.selected_regions}")
        report = generate_report(cfg, on_progress=lambda m: _append_progress(tid, m))
        _append_progress(tid, "[任务] 周报生成完成，准备写入文件")
        out_path = write_report(report, cfg.output)
        html = markdown.markdown(
            report,
            extensions=["tables", "fenced_code", "toc"],
        )
        with TASKS_LOCK:
            TASKS[tid].update(
                status="done",
                result=report,
                html=html,
                filename=os.path.basename(out_path),
                saved_path=out_path,
                error="",
            )
        _append_progress(tid, f"[任务] 周报已保存：{out_path}")
    except Exception as exc:  # noqa: BLE001
        import traceback
        err_msg = f"{type(exc).__name__}: {exc}"
        _append_progress(tid, f"[错误] 任务异常: {err_msg}")
        _append_progress(tid, f"[错误] 堆栈:\n{traceback.format_exc()}")
        with TASKS_LOCK:
            TASKS[tid].update(status="error", error=err_msg)


# ----------------------------- 路由 -----------------------------

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>直触深网 - 网络安全周报生成器</title>
<style>
  :root{
    --bg:#f5f7fa; --card:#ffffff; --line:#e3e8ef; --text:#1f2933;
    --muted:#6b7280; --brand:#2563eb; --brand-d:#1d4ed8; --ok:#059669; --err:#dc2626;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
    background:var(--bg);color:var(--text);line-height:1.6}
  header{background:linear-gradient(120deg,#2563eb,#0ea5e9);color:#fff;padding:22px 28px}
  header h1{margin:0;font-size:20px;font-weight:700}
  header p{margin:6px 0 0;opacity:.9;font-size:13px}
  .wrap{max-width:1100px;margin:0 auto;padding:22px;display:grid;
    grid-template-columns:340px 1fr;gap:22px}
  @media(max-width:860px){.wrap{grid-template-columns:1fr}}
  .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;
    box-shadow:0 1px 3px rgba(0,0,0,.04)}
  .card h2{margin:0 0 14px;font-size:15px;border-left:3px solid var(--brand);padding-left:10px}
  label{display:block;font-size:12px;color:var(--muted);margin:12px 0 4px}
  input,textarea{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;
    font-size:13px;font-family:inherit;background:#fff;color:var(--text)}
  input:focus,textarea:focus{outline:none;border-color:var(--brand)}
  textarea{resize:vertical;min-height:70px}
  .row{display:flex;gap:10px}
  .row > div{flex:1}
  button{cursor:pointer;border:none;border-radius:8px;padding:10px 16px;font-size:14px;
    font-weight:600;color:#fff;background:var(--brand);transition:.15s}
  button:hover{background:var(--brand-d)}
  button.ghost{background:#eef2ff;color:var(--brand-d)}
  button:disabled{opacity:.5;cursor:not-allowed}
  .actions{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
  #progress{background:#0f172a;color:#cbd5e1;font-family:ui-monospace,Menlo,Consolas,monospace;
    font-size:12px;padding:12px;border-radius:8px;height:160px;overflow:auto;white-space:pre-wrap;margin-top:14px}
  #status{font-size:13px;margin-top:10px;font-weight:600}
  .badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600}
  .b-run{background:#fef3c7;color:#92400e}
  .b-ok{background:#d1fae5;color:#065f46}
  .b-err{background:#fee2e2;color:#991b1b}
  #report{margin-top:0}
  #report .md{padding:8px 18px;overflow:auto;max-height:70vh;
    border:1px solid var(--line);border-radius:8px;background:#fff}
  #report h1{font-size:22px} #report h2{font-size:18px;border-bottom:1px solid var(--line);
    padding-bottom:6px;margin-top:26px} #report h3{font-size:15px;color:var(--brand-d);margin-top:18px}
  #report table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
  #report th,#report td{border:1px solid var(--line);padding:7px 9px;text-align:left}
  #report th{background:#f1f5f9}
  #report blockquote{border-left:4px solid var(--brand);margin:10px 0;padding:6px 12px;
    background:#f8fafc;color:var(--muted)}
  #report a{color:var(--brand)}
  .empty{color:var(--muted);font-size:13px;padding:30px;text-align:center}
  .hint{font-size:11px;color:var(--muted);margin-top:3px}
  .copyright{text-align:center;font-size:13px;font-weight:700;color:var(--brand-d);
    padding:18px 16px;margin-top:18px;border-top:2px solid var(--brand);
    background:linear-gradient(180deg,#ffffff,#f1f5f9);letter-spacing:.3px}
  .filter-group{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}
  .filter-group label{display:flex;align-items:center;gap:4px;font-size:12px;
    padding:4px 8px;border:1px solid var(--line);border-radius:6px;cursor:pointer;
    color:var(--text);margin:0;transition:.15s;user-select:none}
  .filter-group label:hover{background:#f1f5f9}
  .filter-group input[type="checkbox"]{width:auto;margin:0;cursor:pointer}
  .filter-group label.selected{background:#dbeafe;border-color:var(--brand);color:var(--brand-d)}
</style>
</head>
<body>
<header>
  <h1>直触深网</h1>
  <p>自动抓取并整理全球安全热点详情，调用大模型生成《网络安全周报》</p>
</header>

<div class="wrap">
  <!-- 左侧配置 -->
  <div class="card">
    <h2>配置参数</h2>
    <label>API Key（留空则离线模式）</label>
    <input id="api_key" type="password" placeholder="sk-...">

    <label>API Base URL</label>
    <input id="base_url" value="https://api.deepseek.com/v1">
    <div class="hint">OpenAI 兼容接口，例如 DeepSeek / 通义 / 本地 Ollama 等</div>

    <label>模型名称</label>
    <input id="model" value="deepseek-v4-flash">

    <label>时间范围</label>
    <div class="row" style="gap:8px;margin-bottom:6px">
      <button type="button" class="ghost q" data-d="1">近一天</button>
      <button type="button" class="ghost q" data-d="7">近一周</button>
      <button type="button" class="ghost q" data-d="30">近一月</button>
    </div>
    <div class="row">
      <div>
        <label>开始日期</label>
        <input id="start_date" type="date">
      </div>
      <div>
        <label>结束日期</label>
        <input id="end_date" type="date">
      </div>
    </div>
    <div class="hint">留空则按「统计天数」回退；结束日期不超过今天。</div>

    <div class="row" style="margin-top:12px">
      <div>
        <label>统计天数（未选日期时生效）</label>
        <input id="days" type="number" value="7" min="1" max="365">
      </div>
      <div>
        <label>最大事件数</label>
        <input id="max_events" type="number" value="20" min="1" max="60">
      </div>
      <div>
        <label>抓取全文条数</label>
        <input id="max_full_text" type="number" value="20" min="0" max="40">
      </div>
    </div>

    <label>自定义 RSS 源（可选，每行一个：名称|URL）</label>
    <textarea id="feeds" placeholder="例如：&#10;FreeBuf|https://www.freebuf.com/feed"></textarea>

    <label>标签筛选（可多选，不选则显示全部）</label>
    <div class="filter-group" id="tag-filters">
      <label><input type="checkbox" name="tag" value="漏洞研究"> 漏洞研究</label>
      <label><input type="checkbox" name="tag" value="政策合规"> 政策合规</label>
      <label><input type="checkbox" name="tag" value="漏洞预警"> 漏洞预警</label>
      <label><input type="checkbox" name="tag" value="AI安全"> AI安全</label>
      <label><input type="checkbox" name="tag" value="攻防对抗"> 攻防对抗</label>
    </div>

    <label>地区筛选（可多选，不选则显示全部）</label>
    <div class="filter-group" id="region-filters">
      <label><input type="checkbox" name="region" value="中国"> 中国</label>
      <label><input type="checkbox" name="region" value="亚洲（除中国）"> 亚洲（除中国）</label>
      <label><input type="checkbox" name="region" value="欧洲"> 欧洲</label>
      <label><input type="checkbox" name="region" value="美洲"> 美洲</label>
      <label><input type="checkbox" name="region" value="澳洲"> 澳洲</label>
      <label><input type="checkbox" name="region" value="非洲"> 非洲</label>
    </div>

    <div class="actions">
      <button id="btn-run">生成周报</button>
    </div>
    <div id="status"></div>
    <div id="progress"></div>
  </div>

  <!-- 右侧结果 -->
  <div class="card" id="report">
    <h2>周报预览</h2>
    <div id="report-body"><div class="empty">填写左侧参数后点击「生成周报」，结果将显示在这里。</div></div>
    <div class="actions" id="result-actions" style="display:none">
      <button id="btn-download">下载 Markdown</button>
      <button id="btn-docx">下载 Word</button>
      <button id="btn-copy" class="ghost">复制全文</button>
    </div>
  </div>
</div>

<footer class="copyright">【直触深网】版权所有：洪声越Jeff 联系邮箱：HongshengyueJeff@163.com</footer>

<script>
const $ = id => document.getElementById(id);
let timer = null, curTask = null, curMarkdown = "";

function setStatus(text, cls){
  const el = $('status');
  el.innerHTML = text ? `<span class="badge ${cls}">${text}</span>` : "";
}
function log(msg){
  const p = $('progress');
  p.textContent += msg + "\n";
  p.scrollTop = p.scrollHeight;
}
function ymd(d){ return d.toISOString().slice(0,10); }
function setRange(days){
  const end = new Date();
  const start = new Date(); start.setDate(start.getDate() - (days - 1));
  $('start_date').value = ymd(start);
  $('end_date').value = ymd(end);
}
// 初始化默认时间范围（近一周）
setRange(7);
// 快捷选项
document.querySelectorAll('button.q').forEach(b => {
  b.onclick = () => setRange(parseInt(b.dataset.d, 10));
});

$('btn-run').onclick = async () => {
  const start = $('start_date').value;
  const end = $('end_date').value;
  // 前端合法性校验
  if(start && end && start > end){
    alert('开始日期不能晚于结束日期');
    return;
  }
  if(end && end > ymd(new Date())){
    alert('结束日期不能晚于今天');
    return;
  }
  // 收集选中的标签
  const selectedTags = [];
  document.querySelectorAll('#tag-filters input:checked').forEach(cb => {
    selectedTags.push(cb.value);
  });
  // 收集选中的地区
  const selectedRegions = [];
  document.querySelectorAll('#region-filters input:checked').forEach(cb => {
    selectedRegions.push(cb.value);
  });
  const payload = {
    api_key: $('api_key').value,
    base_url: $('base_url').value,
    model: $('model').value,
    days: $('days').value,
    start_date: start || "",
    end_date: end || "",
    max_events: $('max_events').value,
    max_full_text: $('max_full_text').value,
    feeds: $('feeds').value,
    selected_tags: selectedTags,
    selected_regions: selectedRegions,
  };
  $('btn-run').disabled = true;
  $('progress').textContent = "";
  $('report-body').innerHTML = '<div class="empty">生成中，请稍候…</div>';
  $('result-actions').style.display = 'none';
  setStatus('运行中', 'b-run');
  log('[*] 已提交任务，等待服务端处理 …');

  const res = await fetch('/api/generate', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  curTask = data.task_id;
  poll();
};

function poll(){
  if(timer) clearInterval(timer);
  let pollCount = 0;
  let lastProgressLen = 0;
  timer = setInterval(async () => {
    pollCount++;
    try {
      const r = await fetch('/api/status/' + curTask);
      const s = await r.json();
      const prog = s.progress || [];
      const p = $('progress');
      // 仅追加新增进度行（按索引递增）
      if (prog.length > lastProgressLen) {
        const newLines = prog.slice(lastProgressLen).join("\n");
        p.textContent += newLines + "\n";
        p.scrollTop = p.scrollHeight;
        lastProgressLen = prog.length;
      }
      // 心跳：每10次轮询（约15秒）追加一行，确认客户端连接正常
      if (pollCount % 10 === 0 && s.status === 'running') {
        const now = new Date().toLocaleTimeString('zh-CN', {hour12:false});
        p.textContent += `[${now}] [心跳] 客户端轮询正常 (${pollCount}次)，等待服务端响应...\n`;
        p.scrollTop = p.scrollHeight;
      }

      if(s.status === 'done'){
        clearInterval(timer);
        $('btn-run').disabled = false;
        setStatus('完成', 'b-ok');
        curMarkdown = s.result || "";
        $('report-body').innerHTML = '<div class="md">' + s.html + '</div>';
        $('result-actions').style.display = 'flex';
        log('[+] 周报已生成：' + (s.filename||''));
      } else if(s.status === 'error'){
        clearInterval(timer);
        $('btn-run').disabled = false;
        setStatus('失败', 'b-err');
        log('[!] 错误：' + s.error);
        $('report-body').innerHTML = '<div class="empty">生成失败：' + s.error + '</div>';
      } else if(s.status === 'running' && pollCount === 1){
        log('[*] 任务运行中，等待服务端进度 ...');
      }
    } catch(e) {
      const p = $('progress');
      const now = new Date().toLocaleTimeString('zh-CN', {hour12:false});
      p.textContent += `[${now}] [!] 轮询异常: ${e.message}\n`;
      p.scrollTop = p.scrollHeight;
    }
  }, 1500);
}

$('btn-download').onclick = () => {
  if(!curTask) return;
  window.location.href = '/api/download/' + curTask;
};
$('btn-docx').onclick = () => {
  if(!curTask) return;
  window.location.href = '/api/export/docx/' + curTask;
};
$('btn-copy').onclick = async () => {
  try{ await navigator.clipboard.writeText(curMarkdown); alert('已复制全文到剪贴板'); }
  catch(e){ alert('复制失败，请手动选择文本复制'); }
};
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/api/generate", methods=["POST"])
def api_generate():
    payload = request.get_json(silent=True) or {}
    tid = uuid.uuid4().hex
    TASKS[tid] = {
        "status": "running",
        "progress": [],
        "result": "",
        "html": "",
        "filename": "",
        "saved_path": "",
        "error": "",
    }
    t = threading.Thread(target=run_task, args=(tid, payload), daemon=True)
    t.start()
    return jsonify({"task_id": tid})


@app.route("/api/status/<tid>")
def api_status(tid):
    task = TASKS.get(tid)
    if not task:
        return jsonify({"status": "error", "error": "任务不存在"}), 404
    return jsonify(task)


@app.route("/api/download/<tid>")
def api_download(tid):
    task = TASKS.get(tid)
    if not task or not task.get("result"):
        return jsonify({"error": "无可下载内容"}), 404
    md = task["result"]
    # 下载文件名使用 ASCII，避免 HTTP 头编码问题（磁盘文件仍为中文名）
    return Response(
        md,
        mimetype="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="CyberSecurity_Weekly_Report.md"'},
    )


@app.route("/api/export/docx/<tid>")
def api_export_docx(tid):
    import tempfile
    task = TASKS.get(tid)
    if not task or not task.get("result"):
        return jsonify({"error": "无可导出内容"}), 404
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_path = tmp.name
        tmp.close()
        export_docx(task["result"], tmp_path)
        with open(tmp_path, "rb") as f:
            data = f.read()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # 清理失败不影响导出（沙箱/权限等）
        # 文件名使用 ASCII，避免 HTTP 头 latin-1 编码问题
        return Response(
            data,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="CyberSecurity_Weekly_Report.docx"'},
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Word 导出失败：{exc}"}), 500


def main():
    import argparse
    import socket
    parser = argparse.ArgumentParser(description="网络安全周报生成器（后端服务）")
    parser.add_argument("--no-browser", action="store_true",
                        help="不自动打开浏览器（由 Electron 等宿主拉起时使用）")
    parser.add_argument("--port", type=int, default=PORT, help=f"监听端口（默认 {PORT}）")
    args = parser.parse_args()

    # 若默认端口被占用，自动尝试后续端口，避免启动失败
    port = args.port
    for cand in range(args.port, args.port + 11):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, cand)) != 0:
                port = cand
                break
    url = f"http://{HOST}:{port}/"
    print(f"[*] 网络安全周报生成器已启动：{url}")
    if not args.no_browser:
        print("[*] 正在打开浏览器 …（如未自动打开，请手动访问上述地址；Ctrl+C 退出）")
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    else:
        print("[*] 已跳过自动打开浏览器（--no-browser）。")
    # 使用 Flask threaded 模式（waitress 在 Python 3.14 + Windows 上存在已知线程池调度问题，
    # 导致子线程长期得不到调度，任务进度永远为 0）
    print(f"[*] 网络安全周报生成器已启动：{url}")
    if not args.no_browser:
        print("[*] 正在打开浏览器 …（如未自动打开，请手动访问上述地址；Ctrl+C 退出）")
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    else:
        print("[*] 已跳过自动打开浏览器（--no-browser）。")
    app.run(host=HOST, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
