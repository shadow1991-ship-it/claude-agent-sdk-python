#!/usr/bin/env python3
"""
Sentinel Guard Web Dashboard — NetGuard-style tactical interface.
AI chatbot powered by DeepSeek V4 Flash via Docker Model Runner (local, free).
pip install flask openai
"""
import os
import json
import hmac
import hashlib
from functools import wraps
from flask import (
    Flask, render_template_string, request,
    redirect, url_for, session, jsonify, Response, stream_with_context,
)
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.getenv("DASHBOARD_SECRET", "change-me-in-production-64-chars")

DASHBOARD_PASSWORD_HASH = hashlib.sha256(
    os.getenv("DASHBOARD_PASSWORD", "alhakim2026").encode()
).hexdigest()

SENTINEL_API = os.getenv("SENTINEL_API_URL", "http://localhost:8000/api/v1")

# دعم Ollama + Docker Model Runner معاً — يختار الأول المتاح
MODEL_RUNNER_URL = os.getenv(
    "OLLAMA_URL",
    os.getenv("DOCKER_MODEL_RUNNER_URL", "http://localhost:12434/engines/llama.cpp/v1")
)
AI_MODEL = os.getenv(
    "OLLAMA_MODEL",
    os.getenv("AI_MODEL_GENERAL", "ai/deepseek-v4-flash")
)

def _load_knowledge() -> str:
    """يقرأ قاعدة معرفة أدوات الأمن ويدمجها في system prompt الذكاء."""
    import glob
    base = os.path.join(os.path.dirname(__file__), "knowledge", "kali-tools")
    parts = []
    for path in sorted(glob.glob(os.path.join(base, "*.md"))):
        try:
            with open(path, encoding="utf-8") as f:
                parts.append(f.read())
        except Exception:
            pass
    return "\n\n---\n\n".join(parts)


_KNOWLEDGE = _load_knowledge()

AMEEN_SYSTEM = (
    "أنت الأمين — مساعد أمني ذكي لنظام Sentinel Guard.\n"
    "تتخصص في أمن المعلومات، تحليل الثغرات، Docker security، وتفسير نتائج الفحص.\n"
    "تتحدث العربية بشكل افتراضي وتجيب بإيجاز ودقة.\n\n"
    "=== قواعد السيادة (لا استثناء) ===\n"
    "- ممنوع --privileged في أي Docker container\n"
    "- ممنوع --net=host في أي Docker container\n"
    "- ممنوع الدخول لأنظمة غير مملوكة للمستخدم\n"
    "- لا تُنفّذ أي أداة أو أمر إلا بطلب صريح من المستخدم\n"
    "- جميع الأدوات للاستخدام على الأصول المملوكة فقط\n\n"
    "=== دورك ===\n"
    "- إذا سأل المستخدم عن نتيجة فحص → اشرحها مع أولويات الإصلاح\n"
    "- إذا طلب شرح أداة → اشرحها من قاعدة معرفتك\n"
    "- إذا طلب تنفيذ أمر → اعطه الأمر الصحيح فقط، لا تُنفّذه أنت\n"
    "- إذا كان الطلب يتعلق بأنظمة الغير → ارفض بوضوح\n\n"
    "=== قاعدة المعرفة ===\n\n"
    + _KNOWLEDGE
)

# ─── Auth ─────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def _check_password(password: str) -> bool:
    candidate = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(candidate, DASHBOARD_PASSWORD_HASH)


# ─── Templates ────────────────────────────────────────────────────────────────

_CSS = """
:root {
  --bg:#0d0f14;--surface:#151820;--border:#1e2330;
  --accent:#00d4aa;--accent2:#0066ff;--danger:#ff4466;
  --warn:#ffaa00;--text:#c8ccd8;--text-dim:#6b7280;
  --font:'Segoe UI',system-ui,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:var(--font);min-height:100vh;}
a{color:var(--accent);text-decoration:none;}
a:hover{color:#00ffcc;}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase;}
.badge-critical{background:rgba(255,68,102,.2);color:var(--danger);border:1px solid rgba(255,68,102,.4);}
.badge-high{background:rgba(255,100,50,.2);color:#ff6432;border:1px solid rgba(255,100,50,.4);}
.badge-medium{background:rgba(255,170,0,.2);color:var(--warn);border:1px solid rgba(255,170,0,.4);}
.badge-low{background:rgba(0,212,170,.15);color:var(--accent);border:1px solid rgba(0,212,170,.3);}
.badge-info{background:rgba(107,114,128,.15);color:var(--text-dim);border:1px solid #2a2f3f;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px;}
.btn{display:inline-block;padding:8px 18px;border-radius:6px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.btn-primary{background:var(--accent);color:#000;}
.btn-primary:hover{background:#00ffcc;}
.btn-ghost{background:rgba(255,255,255,.05);color:var(--text);border:1px solid var(--border);}
.btn-ghost:hover{background:rgba(255,255,255,.1);}
"""

HTML_LOGIN = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Guard — دخول</title>
<style>{{ css }}
.login-wrap{display:flex;align-items:center;justify-content:center;min-height:100vh;}
.login-box{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:36px;width:360px;}
.logo{text-align:center;margin-bottom:24px;}
.logo-icon{font-size:40px;margin-bottom:8px;}
.logo h2{color:#fff;font-size:18px;}
.logo p{color:var(--text-dim);font-size:12px;margin-top:4px;}
.err{background:rgba(255,68,102,.1);border:1px solid rgba(255,68,102,.3);color:var(--danger);padding:10px 14px;border-radius:6px;font-size:13px;margin-bottom:14px;}
input[type=password]{width:100%;background:#1e2330;border:1px solid #2a3040;color:#fff;padding:10px 14px;border-radius:6px;font-size:14px;outline:none;margin-bottom:14px;}
input[type=password]:focus{border-color:var(--accent);}
</style></head>
<body>
<div class="login-wrap"><div class="login-box">
  <div class="logo"><div class="logo-icon">🛡️</div><h2>Sentinel Guard</h2><p>لوحة التحكم الأمنية</p></div>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="password" name="password" placeholder="كلمة السر" autofocus>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:11px;">دخول</button>
  </form>
</div></div>
</body></html>"""

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Guard — Dashboard</title>
<style>{{ css }}
.layout{display:grid;grid-template-columns:210px 1fr 340px;height:100vh;overflow:hidden;}
/* Sidebar */
.sidebar{background:var(--surface);border-left:1px solid var(--border);padding:16px 12px;display:flex;flex-direction:column;gap:4px;overflow-y:auto;}
.sidebar-logo{text-align:center;padding:12px 0 18px;border-bottom:1px solid var(--border);margin-bottom:10px;}
.sidebar-logo h3{color:#fff;font-size:13px;margin-top:8px;}
.nav-btn{display:flex;align-items:center;gap:9px;padding:9px 11px;border-radius:7px;color:var(--text-dim);font-size:13px;cursor:pointer;transition:.15s;border:none;background:none;width:100%;text-align:right;}
.nav-btn:hover,.nav-btn.active{background:rgba(0,212,170,.1);color:var(--accent);}
/* Main */
.main{overflow-y:auto;padding:22px;display:flex;flex-direction:column;gap:18px;}
.top-bar{display:flex;align-items:center;justify-content:space-between;}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;}
.stat-label{color:var(--text-dim);font-size:11px;margin-bottom:5px;}
.stat-value{font-size:26px;font-weight:700;color:#fff;}
.stat-sub{color:var(--text-dim);font-size:10px;margin-top:3px;}
.section-title{font-size:12px;font-weight:600;color:var(--text-dim);text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px;}
.finding-row{display:flex;align-items:flex-start;gap:10px;padding:11px 0;border-bottom:1px solid var(--border);}
.finding-row:last-child{border-bottom:none;}
/* Chat */
.chat-panel{background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;height:100vh;}
.chat-header{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;}
.chat-dot{width:8px;height:8px;border-radius:50%;background:var(--accent);animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.4;}}
.chat-messages{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;}
.msg{max-width:90%;padding:9px 12px;border-radius:10px;font-size:13px;line-height:1.6;white-space:pre-wrap;}
.msg-user{background:rgba(0,102,255,.2);border:1px solid rgba(0,102,255,.3);align-self:flex-start;color:#c8d8ff;}
.msg-ai{background:#1a1f2e;border:1px solid var(--border);align-self:flex-end;color:var(--text);}
.msg-thinking{color:var(--text-dim);font-style:italic;font-size:12px;align-self:flex-end;}
.chat-input-area{padding:12px;border-top:1px solid var(--border);display:flex;gap:8px;}
.chat-input{flex:1;background:#1e2330;border:1px solid #2a3040;color:#fff;padding:9px 12px;border-radius:7px;font-size:13px;outline:none;resize:none;font-family:var(--font);}
.chat-input:focus{border-color:var(--accent);}
.send-btn{background:var(--accent);color:#000;border:none;border-radius:7px;padding:9px 14px;cursor:pointer;font-size:15px;transition:.15s;}
.send-btn:hover{background:#00ffcc;}
</style></head>
<body>
<div class="layout">

  <!-- Sidebar -->
  <nav class="sidebar">
    <div class="sidebar-logo">
      <div style="font-size:28px">🛡️</div>
      <h3>Sentinel Guard</h3>
      <div style="color:var(--text-dim);font-size:10px;margin-top:3px">v1.0 · AI Edition</div>
    </div>
    <button class="nav-btn active" onclick="navTo('overview',this)">📊 نظرة عامة</button>
    <button class="nav-btn" onclick="navTo('dockerfile',this)">🐳 Dockerfile</button>
    <button class="nav-btn" onclick="navTo('api',this)">📡 API Docs</button>
    <div style="flex:1"></div>
    <a href="/logout" class="nav-btn" style="color:var(--danger)">🚪 خروج</a>
  </nav>

  <!-- Main -->
  <main class="main">
    <div class="top-bar">
      <div>
        <h1 style="font-size:18px;color:#fff">لوحة التحكم الأمنية</h1>
        <p style="color:var(--text-dim);font-size:11px;margin-top:2px" id="last-update">—</p>
      </div>
      <button class="btn btn-primary" onclick="window.open('{{ sentinel_api|replace('/api/v1','') }}/docs','_blank')">API Docs</button>
    </div>

    <!-- Stats -->
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">إجمالي الفحوصات</div><div class="stat-value" id="st-total">—</div><div class="stat-sub">منذ البداية</div></div>
      <div class="stat-card"><div class="stat-label">ثغرات حرجة</div><div class="stat-value" style="color:var(--danger)" id="st-critical">—</div><div class="stat-sub">تحتاج تدخلاً فورياً</div></div>
      <div class="stat-card"><div class="stat-label">متوسط الخطر</div><div class="stat-value" style="color:var(--warn)" id="st-risk">—</div><div class="stat-sub">من 100</div></div>
      <div class="stat-card"><div class="stat-label">الأصول</div><div class="stat-value" style="color:var(--accent)" id="st-assets">—</div><div class="stat-sub">موثّقة ومفحوصة</div></div>
    </div>

    <!-- Overview section -->
    <div class="card" id="sec-overview">
      <div class="section-title">آخر النتائج الأمنية</div>
      <div id="findings-list"><div style="color:var(--text-dim);font-size:13px;text-align:center;padding:28px">جارٍ التحميل…</div></div>
    </div>

    <!-- Dockerfile section -->
    <div class="card" id="sec-dockerfile" style="display:none">
      <div class="section-title">فحص Dockerfile بالذكاء الاصطناعي</div>
      <div style="display:flex;gap:10px;margin-bottom:14px">
        <input id="df-url" type="text" placeholder="رابط أو مسار Dockerfile" class="chat-input" style="flex:1">
        <button class="btn btn-primary" onclick="scanDockerfile()">فحص الآن</button>
      </div>
      <div id="df-result"></div>
    </div>

    <!-- API section -->
    <div class="card" id="sec-api" style="display:none">
      <div class="section-title">نقاط النهاية الجديدة</div>
      <div style="display:flex;flex-direction:column;gap:10px;font-size:13px">
        <div style="background:#0d1117;border:1px solid var(--border);border-radius:7px;padding:12px;font-family:monospace;color:var(--accent)">
          POST /api/v1/scans → ScanType: dockerfile | sbom<br>
          GET  /api/v1/scans/{id}/sarif → SARIF 2.1.0 export<br>
          POST /api/v1/scans/{id}/findings/{fid}/fix → AI AutoFixer
        </div>
        <p style="color:var(--text-dim)">استخدم <a href="{{ sentinel_api|replace('/api/v1','') }}/docs" target="_blank">Swagger UI</a> للاختبار المباشر.</p>
      </div>
    </div>
  </main>

  <!-- Chat Panel -->
  <aside class="chat-panel">
    <div class="chat-header">
      <div class="chat-dot"></div>
      <div>
        <div style="font-size:13px;font-weight:600;color:#fff">الأمين AI</div>
        <div style="font-size:10px;color:var(--text-dim)">DeepSeek V4 Flash · محلي · مجاني</div>
      </div>
    </div>
    <div class="chat-messages" id="chat-messages">
      <div class="msg msg-ai">مرحباً! أنا الأمين — مساعدك الأمني. اسألني عن أي ثغرة أو نتيجة فحص وسأشرحها مع أولويات الإصلاح.</div>
    </div>
    <div class="chat-input-area">
      <textarea id="chat-input" class="chat-input" rows="2" placeholder="اكتب سؤالك…" onkeydown="handleKey(event)"></textarea>
      <button class="send-btn" onclick="sendMessage()">➤</button>
    </div>
  </aside>
</div>

<script>
const API = '{{ sentinel_api }}';
const token = localStorage.getItem('sentinel_token') || '';
const authHeaders = token ? {Authorization:`Bearer ${token}`} : {};

function navTo(name, btn) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  ['overview','dockerfile','api'].forEach(s => {
    document.getElementById('sec-'+s).style.display = s === name ? 'block' : 'none';
  });
}

async function loadStats() {
  try {
    const [scans, assets] = await Promise.all([
      fetch(`${API}/scans`, {headers:authHeaders}).then(r => r.ok ? r.json() : []),
      fetch(`${API}/assets`, {headers:authHeaders}).then(r => r.ok ? r.json() : []),
    ]);
    document.getElementById('st-total').textContent = scans.length || 0;
    document.getElementById('st-assets').textContent = assets.length || 0;
    let crit = 0, riskSum = 0;
    (scans||[]).forEach(s => { crit += (s.finding_counts?.critical||0); riskSum += (s.risk_score||0); });
    document.getElementById('st-critical').textContent = crit;
    document.getElementById('st-risk').textContent = scans.length ? (riskSum/scans.length).toFixed(1) : '0';
    document.getElementById('last-update').textContent = 'آخر تحديث: ' + new Date().toLocaleTimeString('ar');
    renderFindings(scans||[]);
  } catch(e) { console.error(e); }
}

function renderFindings(scans) {
  const el = document.getElementById('findings-list');
  const rows = [];
  (scans||[]).forEach(s => {
    Object.entries(s.finding_counts||{}).forEach(([sev,cnt]) => {
      rows.push(`<div class="finding-row">
        <span class="badge badge-${sev}">${sev}</span>
        <div style="flex:1">
          <div style="font-size:13px;color:#fff">${cnt} ثغرة · ${sev}</div>
          <div style="font-size:11px;color:var(--text-dim);margin-top:2px">Scan ${s.id?.slice(0,8)}… · ${s.scan_type}</div>
        </div></div>`);
    });
  });
  el.innerHTML = rows.length ? rows.slice(0,10).join('') : '<div style="color:var(--text-dim);font-size:13px;text-align:center;padding:28px">لا توجد نتائج بعد</div>';
}

async function scanDockerfile() {
  const url = document.getElementById('df-url').value.trim();
  if (!url) return;
  const el = document.getElementById('df-result');
  el.innerHTML = '<div style="color:var(--text-dim);font-size:13px">جارٍ الفحص بالذكاء الاصطناعي…</div>';
  try {
    const r = await fetch('/api/scan-dockerfile', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({url})
    });
    const data = await r.json();
    if (data.error) { el.innerHTML = `<div style="color:var(--danger);font-size:13px">${data.error}</div>`; return; }
    const all = [...(data.rule_findings||[]),...(data.ai_findings||[])];
    el.innerHTML = !all.length
      ? '<div style="color:var(--accent);font-size:13px">✅ لم يتم اكتشاف أي ثغرات</div>'
      : all.map(f => `<div class="finding-row">
          <span class="badge badge-${f.severity}">${f.severity}</span>
          <div style="flex:1">
            <div style="font-size:13px;color:#fff">${f.title}</div>
            <div style="font-size:12px;color:var(--text-dim);margin-top:2px">${f.description}</div>
            ${f.remediation?`<div style="font-size:11px;color:var(--accent);margin-top:3px">🔧 ${f.remediation}</div>`:''}
          </div></div>`).join('');
  } catch(e) { el.innerHTML = `<div style="color:var(--danger);font-size:13px">خطأ: ${e.message}</div>`; }
}

function handleKey(e) { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();} }

async function sendMessage() {
  const inp = document.getElementById('chat-input');
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  const msgs = document.getElementById('chat-messages');
  msgs.innerHTML += `<div class="msg msg-user">${text}</div>`;
  const think = document.createElement('div');
  think.className = 'msg msg-thinking';
  think.textContent = 'الأمين يفكر…';
  msgs.appendChild(think);
  msgs.scrollTop = msgs.scrollHeight;

  const aiEl = document.createElement('div');
  aiEl.className = 'msg msg-ai';
  aiEl.textContent = '';

  try {
    const resp = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:text})
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    think.replaceWith(aiEl);
    while (true) {
      const {done,value} = await reader.read();
      if (done) break;
      decoder.decode(value).split('\\n').forEach(line => {
        if (!line.startsWith('data: ')) return;
        const d = line.slice(6).trim();
        if (d === '[DONE]') return;
        try { aiEl.textContent += JSON.parse(d).delta||''; } catch {}
      });
      msgs.scrollTop = msgs.scrollHeight;
    }
  } catch(e) {
    think.textContent = 'تعذّر الاتصال بـ Docker Model Runner. تأكد أنه يعمل على المنفذ 12434.';
  }
  msgs.scrollTop = msgs.scrollHeight;
}

loadStats();
setInterval(loadStats, 30000);
</script>
</body></html>"""

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if _check_password(request.form.get("password", "")):
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        error = "كلمة السر غلط"
    return render_template_string(HTML_LOGIN, css=_CSS, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    return render_template_string(HTML_DASHBOARD, css=_CSS, sentinel_api=SENTINEL_API)


@app.route("/api/chat", methods=["POST"])
@login_required
def chat_stream():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", ""))[:2000]

    def generate():
        try:
            client = OpenAI(base_url=MODEL_RUNNER_URL, api_key="unused")
            stream = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": AMEEN_SYSTEM},
                    {"role": "user", "content": message},
                ],
                stream=True,
                max_tokens=1024,
                timeout=30,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield f"data: {json.dumps({'delta': delta})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'delta': f'خطأ في الاتصال بنموذج AI: {exc}'})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/api/scan-dockerfile", methods=["POST"])
@login_required
def api_scan_dockerfile():
    import asyncio
    import sys

    data = request.get_json(silent=True) or {}
    url = str(data.get("url", ""))[:1000]
    if not url:
        return jsonify({"error": "url required"}), 400

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sentinel-guard"))
        from app.services.scanner.dockerfile_scanner import DockerfileScanner
        scanner = DockerfileScanner()
        result = asyncio.run(scanner.scan(url))
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "rule_findings": [], "ai_findings": []}), 500


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
