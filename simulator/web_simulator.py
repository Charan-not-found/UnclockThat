"""PROMETHEUS-X Web Line Simulator (runs on port 5180).

Serves a browser UI at http://127.0.0.1:5180 with a dropdown to pick any ZIP file
inside simulator/sample_data/ (or loose images), stream images one-by-one to the
PROMETHEUS-X backend, and display live True/False results & heatmaps.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from stream_simulator import (
    DEFAULT_SAMPLE_DIR,
    IMAGE_EXTS,
    check_bytes_async,
    check_bytes_sync,
    list_images_in_zip,
    list_scanner_units,
    list_zip_archives,
    read_image_bytes,
)

HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>PROMETHEUS-X — Production Line Simulator</title>
  <style>
    :root {
      --bg: #0b1120; --surface: #111827; --card: #1e293b; --border: #334155;
      --text: #f1f5f9; --muted: #94a3b8; --blue: #2563eb; --green: #22c55e; --red: #ef4444; --amber: #f59e0b;
    }
    * { box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
    .wrap { max-width: 1180px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 12px; flex-wrap: wrap; }
    .brand { display: flex; align-items: center; gap: 10px; }
    .badge { background: var(--blue); color: #fff; font-weight: 700; font-size: 12px; padding: 6px 8px; border-radius: 6px; }
    h1 { font-size: 19px; margin: 0; }
    .sub { color: #94a3b8; font-size: 12px; margin-top: 2px; }
    .pill { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border); background: var(--card); }
    .pill.live { border-color: #22c55e66; color: var(--green); background: #22c55e18; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
    .grid-kpi { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 16px; }
    .kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }
    .kpi .lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
    .kpi .val { font-size: 22px; font-weight: 700; margin-top: 4px; font-variant-numeric: tabular-nums; }
    .row { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; }
    label { display: flex; flex-direction: column; font-size: 12px; color: var(--muted); gap: 4px; }
    input, select { background: var(--bg); color: var(--text); border: 1px solid #475569; border-radius: 6px; padding: 7px 10px; font-size: 13px; }
    .chk { flex-direction: row; align-items: center; gap: 6px; padding-bottom: 6px; color: var(--text); cursor: pointer; }
    button { background: var(--blue); color: #fff; border: 0; border-radius: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; cursor: pointer; }
    button.sec { background: var(--card); border: 1px solid var(--border); }
    button.danger { background: #dc2626; }
    button:disabled { opacity: 0.45; cursor: not-allowed; }
    .prog-bg { height: 6px; background: #1e293b; border-radius: 999px; overflow: hidden; margin-top: 12px; }
    .prog-bar { height: 100%; background: var(--blue); width: 0%; transition: width .15s ease; }
    .split { display: grid; grid-template-columns: 360px 1fr; gap: 16px; }
    @media (max-width: 900px) { .split { grid-template-columns: 1fr; } }
    .preview-box { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; aspect-ratio: 4/3; display: flex; align-items: center; justify-content: center; overflow: hidden; }
    .preview-box img { width: 100%; height: 100%; object-fit: contain; }
    .verdict { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; }
    .verdict.true { background: #22c55e22; color: var(--green); border: 1px solid #22c55e55; }
    .verdict.false { background: #ef444422; color: var(--red); border: 1px solid #ef444455; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; }
    .mono { font-family: ui-monospace, monospace; }
    a { color: #60a5fa; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .tbl-wrap { max-height: 430px; overflow-y: auto; }
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="brand">
      <div class="badge">PX</div>
      <div>
        <h1>PROMETHEUS-X — Production Line Simulator</h1>
        <div class="sub">Pick a ZIP archive from <code>simulator/sample_data/</code> to stream images one-by-one and receive <strong>True</strong> (PASS) / <strong>False</strong> (FAIL or REVIEW_REQUIRED).</div>
      </div>
    </div>
    <span id="statusPill" class="pill">IDLE</span>
  </div>

  <div class="grid-kpi">
    <div class="kpi"><div class="lbl">Checked</div><div class="val" id="kTotal">0</div></div>
    <div class="kpi"><div class="lbl">True (PASS)</div><div class="val" style="color:var(--green)" id="kPass">0</div></div>
    <div class="kpi"><div class="lbl">False (FAIL/REVIEW)</div><div class="val" style="color:var(--red)" id="kFail">0</div></div>
    <div class="kpi"><div class="lbl">Pass Rate</div><div class="val" id="kRate">—</div></div>
    <div class="kpi"><div class="lbl">Avg Latency</div><div class="val" id="kLat">—</div></div>
  </div>

  <div class="card">
    <div class="row">
      <label>Server API
        <input id="apiUrl" value="http://127.0.0.1:8000/api/v1" size="25" />
      </label>
      <label>Scanner Unit
        <select id="unitId"></select>
      </label>
      <label>Dataset ZIP (simulator/sample_data)
        <select id="zipSource"></select>
      </label>
      <label>Mode
        <select id="mode">
          <option value="sync">sync (/inspections)</option>
          <option value="async">async (/jobs)</option>
        </select>
      </label>
      <label>Threshold
        <input id="threshold" type="number" value="0.5" min="0" max="1" step="0.05" style="width:74px" />
      </label>
      <label>Delay (ms)
        <input id="delayMs" type="number" value="200" min="0" style="width:78px" />
      </label>
      <label class="chk"><input type="checkbox" id="loopChk" /> Loop</label>
    </div>
    <div class="row" style="margin-top:12px;">
      <button class="sec" onclick="refreshAll()">Refresh Units &amp; ZIPs</button>
      <button id="startBtn" onclick="startStream()">Start Stream</button>
      <button id="stopBtn" class="danger" onclick="stopStream()" disabled>Stop</button>
      <button class="sec" onclick="clearResults()">Clear</button>
      <button class="sec" onclick="exportCsv()">Export CSV</button>
      <label style="margin-left:auto; flex-direction:row; align-items:center; gap:6px;">Filter:
        <select id="filterSel" onchange="renderTable()">
          <option value="all">All</option>
          <option value="true">True (PASS)</option>
          <option value="false">False (FAIL/REVIEW)</option>
        </select>
      </label>
    </div>
    <div class="prog-bg"><div class="prog-bar" id="progBar"></div></div>
  </div>

  <div class="split">
    <div class="card">
      <div style="font-size:13px;font-weight:600;margin-bottom:8px;">Live Sample Preview</div>
      <div class="preview-box" id="prevOrigBox"><span class="sub">Waiting for stream…</span></div>
      <div style="font-size:12px;color:var(--muted);margin-top:6px;" id="prevCaption">No image scanned yet</div>
      <div style="font-size:13px;font-weight:600;margin:12px 0 8px;">After Scan (Heatmap / Defects)</div>
      <div class="preview-box" id="prevHeatBox"><span class="sub">No heatmap yet</span></div>
    </div>

    <div class="card">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Image File</th>
              <th>Result (True/False)</th>
              <th>Decision</th>
              <th>Score</th>
              <th>Inspection</th>
              <th>Latency</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<script>
let stopped = false;
let allRows = [];

async function loadUnits() {
  const api = encodeURIComponent(document.getElementById('apiUrl').value);
  const res = await fetch('/sim/units?api=' + api);
  const units = await res.json();
  const sel = document.getElementById('unitId');
  sel.innerHTML = '';
  for (const u of units) {
    const opt = document.createElement('option');
    opt.value = u.id;
    opt.textContent = `${u.id}: ${u.name} (${u.status})`;
    sel.appendChild(opt);
  }
}

async function loadSources() {
  const res = await fetch('/sim/sources');
  const sources = await res.json();
  const sel = document.getElementById('zipSource');
  const prev = sel.value;
  sel.innerHTML = '';
  for (const s of sources) {
    const opt = document.createElement('option');
    opt.value = s.value;
    opt.textContent = s.label;
    sel.appendChild(opt);
  }
  if (prev && sources.some(s => s.value === prev)) {
    sel.value = prev;
  }
}

async function refreshAll() {
  await Promise.all([loadUnits(), loadSources()]);
}

function stopStream() {
  stopped = true;
  document.getElementById('statusPill').textContent = 'STOPPING…';
  document.getElementById('statusPill').className = 'pill';
}

function clearResults() {
  allRows = [];
  document.getElementById('progBar').style.width = '0%';
  updateKpis();
  renderTable();
}

function updateKpis() {
  const total = allRows.length;
  const pass = allRows.filter(r => r.passed).length;
  const fail = total - pass;
  const lats = allRows.map(r => Number(r.latency_ms)).filter(n => !Number.isNaN(n));
  const avg = lats.length ? Math.round(lats.reduce((a, b) => a + b, 0) / lats.length) : null;
  document.getElementById('kTotal').textContent = total;
  document.getElementById('kPass').textContent = pass;
  document.getElementById('kFail').textContent = fail;
  document.getElementById('kRate').textContent = total ? ((pass / total * 100).toFixed(1) + '%') : '—';
  document.getElementById('kLat').textContent = avg != null ? (avg + ' ms') : '—';
}

function renderTable() {
  const f = document.getElementById('filterSel').value;
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  const filtered = allRows.filter(r => f === 'all' ? true : (f === 'true' ? r.passed : !r.passed));
  for (const d of filtered.slice().reverse()) {
    const tr = document.createElement('tr');
    const insLink = d.inspection_id
      ? `<a href="http://localhost:5173/inspections/${d.inspection_id}" target="_blank">${d.inspection_id}</a>`
      : '—';
    tr.innerHTML = `
      <td class="mono">${d.seq}</td>
      <td>${d.file}</td>
      <td><span class="verdict ${d.passed ? 'true' : 'false'}">${d.passed}</span></td>
      <td>${d.decision}</td>
      <td class="mono">${d.score ?? '—'}</td>
      <td class="mono">${insLink}</td>
      <td class="mono">${d.latency_ms} ms</td>
    `;
    tbody.appendChild(tr);
  }
}

function exportCsv() {
  if (!allRows.length) return;
  const lines = ['seq,file,passed,decision,score,inspection_id,latency_ms']
    .concat(allRows.map(r => `${r.seq},"${r.file}",${r.passed},${r.decision},${r.score},${r.inspection_id},${r.latency_ms}`));
  const blob = new Blob([lines.join('\\n')], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'simulator_results.csv';
  a.click();
}

async function startStream() {
  const unitId = document.getElementById('unitId').value;
  if (!unitId) { alert('Select a Scanner Unit first'); return; }
  const source = document.getElementById('zipSource').value;
  if (!source) { alert('Add a .zip file to simulator/sample_data/ first'); return; }
  const apiUrl = document.getElementById('apiUrl').value;
  const mode = document.getElementById('mode').value;
  const threshold = Number(document.getElementById('threshold').value) || 0.5;
  const delayMs = Number(document.getElementById('delayMs').value) || 0;

  const listRes = await fetch('/sim/files?source=' + encodeURIComponent(source));
  const files = await listRes.json();
  if (!files.length) { alert('No images found in selected ZIP / folder'); return; }

  stopped = false;
  document.getElementById('startBtn').disabled = true;
  document.getElementById('stopBtn').disabled = false;
  document.getElementById('statusPill').textContent = 'STREAMING';
  document.getElementById('statusPill').className = 'pill live';

  const apiHost = apiUrl.replace(/\\/api\\/v1\\/?$/, '');

  do {
    for (let i = 0; i < files.length; i++) {
      if (stopped) break;
      const f = files[i];
      document.getElementById('prevOrigBox').innerHTML =
        `<img src="/sim/image?source=${encodeURIComponent(source)}&filename=${encodeURIComponent(f)}" />`;

      const r = await fetch('/sim/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_url: apiUrl, unit_id: Number(unitId), source, filename: f, mode, threshold }),
      });
      const d = await r.json();
      d.seq = allRows.length + 1;
      allRows.push(d);

      document.getElementById('prevCaption').textContent =
        `${d.file} → ${d.passed} (${d.decision}, score ${d.score})`;
      if (d.heatmap_url) {
        document.getElementById('prevHeatBox').innerHTML = `<img src="${apiHost}${d.heatmap_url}" />`;
      } else {
        document.getElementById('prevHeatBox').innerHTML = `<span class="sub">No heatmap generated</span>`;
      }

      document.getElementById('progBar').style.width = `${Math.round(((i + 1) / files.length) * 100)}%`;
      updateKpis();
      renderTable();

      if (delayMs > 0 && !stopped) await new Promise(res => setTimeout(res, delayMs));
    }
  } while (document.getElementById('loopChk').checked && !stopped);

  document.getElementById('startBtn').disabled = false;
  document.getElementById('stopBtn').disabled = true;
  document.getElementById('statusPill').textContent = stopped ? 'STOPPED' : 'COMPLETED';
  document.getElementById('statusPill').className = 'pill';
}

refreshAll().catch(() => {});
</script>
</body>
</html>
"""


def _resolve_safe_source(source_val: str) -> Path:
    if source_val == "__loose__":
        return DEFAULT_SAMPLE_DIR
    candidate = (DEFAULT_SAMPLE_DIR / Path(source_val).name).resolve()
    if candidate.parent == DEFAULT_SAMPLE_DIR.resolve() and candidate.is_file() and candidate.suffix.lower() == ".zip":
        return candidate
    p = Path(source_val)
    return p if p.exists() else DEFAULT_SAMPLE_DIR


class SimHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass

    def _send_json(self, code: int, payload: object) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            html = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        qs = parse_qs(parsed.query)
        if parsed.path == "/sim/units":
            api = qs.get("api", ["http://127.0.0.1:8000/api/v1"])[0]
            try:
                self._send_json(200, list_scanner_units(api))
            except Exception as exc:
                self._send_json(502, {"error": str(exc)})
            return

        if parsed.path == "/sim/sources":
            sources = []
            for zp in list_zip_archives(DEFAULT_SAMPLE_DIR):
                cnt = len(list_images_in_zip(zp))
                sources.append({"value": zp.name, "label": f"{zp.name} ({cnt} images)"})
            loose = [p for p in DEFAULT_SAMPLE_DIR.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS] if DEFAULT_SAMPLE_DIR.is_dir() else []
            if loose:
                sources.append({"value": "__loose__", "label": f"Loose images in sample_data ({len(loose)} images)"})
            self._send_json(200, sources)
            return

        if parsed.path == "/sim/files":
            source = _resolve_safe_source(qs.get("source", ["__loose__"])[0])
            if source.is_file() and source.suffix.lower() == ".zip":
                self._send_json(200, list_images_in_zip(source))
            elif source.is_dir():
                files = [p.name for p in sorted(source.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
                self._send_json(200, files)
            else:
                self._send_json(200, [])
            return

        if parsed.path == "/sim/image":
            source = _resolve_safe_source(qs.get("source", ["__loose__"])[0])
            member = qs.get("filename", [""])[0]
            try:
                fname, data = read_image_bytes(source, member)
            except Exception:
                self.send_error(404)
                return
            ctype, _ = mimetypes.guess_type(fname)
            self.send_response(200)
            self.send_header("Content-Type", ctype or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/sim/check":
            self._send_json(404, {"error": "Not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        source = _resolve_safe_source(body.get("source", "__loose__"))
        member = body["filename"]
        threshold = float(body.get("threshold", 0.5))
        api_url = body["api_url"].rstrip("/")
        try:
            fname, raw = read_image_bytes(source, member)
            if body.get("mode") == "async":
                res = check_bytes_async(api_url, int(body["unit_id"]), fname, raw, threshold=threshold)
            else:
                res = check_bytes_sync(api_url, int(body["unit_id"]), fname, raw, threshold=threshold)
            if res.get("inspection_id"):
                try:
                    import requests
                    d_resp = requests.get(f"{api_url}/inspections/{quote(res['inspection_id'])}", timeout=5)
                    if d_resp.ok:
                        ars = d_resp.json().get("anomaly_results", [])
                        hm = next((a.get("heatmap_url") for a in ars if a.get("heatmap_url")), None)
                        if hm:
                            res["heatmap_url"] = hm
                except Exception:
                    pass
            self._send_json(200, res)
        except Exception as exc:
            self._send_json(500, {
                "file": Path(member).name,
                "passed": False,
                "decision": f"ERROR: {exc}",
                "score": 0,
                "inspection_id": "",
                "latency_ms": 0,
            })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PROMETHEUS-X Web Simulator UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5180)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), SimHandler)
    print(f"[Simulator UI] Listening on http://{args.host}:{args.port}")
    server.serve_forever()
