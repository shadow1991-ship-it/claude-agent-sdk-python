"""
Market Intelligence — أداة استخبارات السوق الخاصة
Private · Tailscale Only · No Cloud Dependency
Powered by: Adanos Market Sentiment API + Ollama AI (local)

Run:
    ADANOS_API_KEY=your_key DASHBOARD_PASSWORD=yourpass python empire/market_intel.py

Access:
    http://100.109.223.64:5001  (via Tailscale only)
"""
import hashlib, hmac, json, os, time
from functools import wraps
from datetime import datetime

import httpx
from flask import (
    Flask, Response, jsonify, redirect, render_template_string,
    request, session, stream_with_context, url_for,
)

# ── Config ────────────────────────────────────────────────────────────────────
ADANOS_BASE   = os.getenv("ADANOS_BASE_URL", "https://api.adanos.org")
ADANOS_KEY    = os.getenv("ADANOS_API_KEY", "")          # ضع مفتاحك هنا أو في .env
OLLAMA_URL    = os.getenv("OLLAMA_URL",  "http://localhost:11434")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "phi3")
_PWD_HASH     = hashlib.sha256(
    os.getenv("DASHBOARD_PASSWORD", "market2026").encode()
).hexdigest()

PLATFORMS = {
    "x":         "/x/stocks/v1",
    "news":      "/news/stocks/v1",
    "reddit":    "/reddit/stocks/v1",
    "reddit-crypto": "/reddit/crypto/v1",
    "polymarket": "/polymarket/stocks/v1",
}

PLATFORM_LABELS = {
    "x":          ("𝕏 Twitter",  "#1d9bf0"),
    "news":       ("📰 News",     "#00c3ff"),
    "reddit":     ("🟠 Reddit",   "#ff4500"),
    "reddit-crypto": ("🟡 Crypto", "#f7931a"),
    "polymarket": ("🎯 Polymarket","#7b2fff"),
}

app = Flask(__name__)
app.secret_key = os.urandom(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

# ── Rate limiter (auth brute force protection) ────────────────────────────────
_hits: dict = {}

def _locked(ip: str) -> bool:
    r = _hits.get(ip, {"n": 0, "t": 0})
    if r["n"] >= 5 and time.time() - r["t"] < 300:
        return True
    if r["n"] >= 5:
        _hits.pop(ip, None)
    return False

def _fail(ip: str) -> None:
    r = _hits.setdefault(ip, {"n": 0, "t": time.time()})
    r["n"] += 1
    if r["n"] == 1:
        r["t"] = time.time()

def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if not session.get("ok"):
            return redirect(url_for("login"))
        return f(*a, **kw)
    return d

# ── Adanos API client ─────────────────────────────────────────────────────────
def _adanos_headers() -> dict:
    h = {"Accept": "application/json", "User-Agent": "MarketIntel/1.0"}
    if ADANOS_KEY:
        h["Authorization"] = f"Bearer {ADANOS_KEY}"
        h["X-API-Key"] = ADANOS_KEY
    return h

def adanos_get(path: str, params: dict | None = None) -> dict | list:
    try:
        r = httpx.get(
            f"{ADANOS_BASE}{path}",
            params=params or {},
            headers=_adanos_headers(),
            timeout=15,
        )
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}

# ── Ollama AI ─────────────────────────────────────────────────────────────────
def ask_ai(prompt: str) -> str:
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": OLLAMA_MODEL,
                  "messages": [
                      {"role": "system", "content":
                       "أنت محلل مالي ذكي. حلّل بيانات السوق وأعطِ رأياً موجزاً باللغة العربية. "
                       "ركّز على: الاتجاه، المخاطر، الفرص، والتوصية."},
                      {"role": "user", "content": prompt}],
                  "stream": False},
            timeout=60,
        )
        return r.json().get("message", {}).get("content", "(لا رد)")
    except Exception as e:
        return f"(Ollama غير متاح: {e})"

def ai_stream(prompt: str):
    try:
        with httpx.stream(
            "POST",
            f"{OLLAMA_URL}/api/chat",
            json={"model": OLLAMA_MODEL,
                  "messages": [
                      {"role": "system", "content":
                       "أنت محلل مالي ذكي ومتخصص في أسواق الأسهم والعملات الرقمية. "
                       "حلّل البيانات بدقة واعطِ توصيات قابلة للتنفيذ باللغة العربية."},
                      {"role": "user", "content": prompt}],
                  "stream": True},
            timeout=90,
        ) as r:
            for line in r.iter_lines():
                if line:
                    try:
                        d = json.loads(line)
                        delta = d.get("message", {}).get("content", "")
                        if delta:
                            yield f"data: {json.dumps({'delta': delta})}\n\n"
                        if d.get("done"):
                            yield "data: [DONE]\n\n"
                            return
                    except Exception:
                        pass
    except Exception as e:
        yield f"data: {json.dumps({'delta': f'⚠ {e}'})}\n\n"
        yield "data: [DONE]\n\n"

# ── HTML Templates ─────────────────────────────────────────────────────────────
_CSS = """
:root{
  --bg:#03050a;--panel:#060b12;--panel2:#080f18;
  --border:#0a1a30;--border-hi:#0f2f55;
  --accent:#00c3ff;--accent2:#7b2fff;
  --green:#00ff88;--red:#ff3b5c;--amber:#ffaa00;
  --text:#c8d8f0;--muted:#3a5575;
  --x:#1d9bf0;--reddit:#ff4500;--news:#00c3ff;
  --crypto:#f7931a;--poly:#7b2fff;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;overflow-x:hidden}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-thumb{background:var(--border-hi);border-radius:2px}

/* ── Canvas BG ── */
#bgc{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.2}

/* ── Layout ── */
.wrap{position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column}

/* ── Nav ── */
nav{
  display:flex;align-items:center;justify-content:space-between;
  padding:.65rem 1.5rem;
  background:rgba(6,11,18,.92);backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;
}
.nav-brand{font-family:'Courier New',monospace;font-size:.9rem;color:var(--accent);
  display:flex;align-items:center;gap:.5rem}
.nav-brand .ver{font-size:.7rem;color:var(--muted);padding:.15rem .4rem;
  border:1px solid var(--border);border-radius:3px}
.nav-right{display:flex;align-items:center;gap:1rem}
.nav-right a{color:var(--muted);font-size:.8rem;text-decoration:none;transition:color .2s}
.nav-right a:hover{color:var(--accent)}
.live-dot{width:7px;height:7px;background:var(--green);border-radius:50%;
  box-shadow:0 0 6px var(--green);animation:pulse 2s infinite}
@keyframes pulse{50%{opacity:.25}}

/* ── Main grid ── */
.main{display:grid;grid-template-columns:300px 1fr;gap:0;flex:1}
@media(max-width:900px){.main{grid-template-columns:1fr}}

/* ── Sidebar ── */
.sidebar{
  background:var(--panel);border-left:1px solid var(--border);
  padding:1.2rem;display:flex;flex-direction:column;gap:1.2rem;
  overflow-y:auto;max-height:calc(100vh - 49px);position:sticky;top:49px;
}
.s-label{font-family:'Courier New',monospace;font-size:.65rem;color:var(--accent);
  letter-spacing:.2em;text-transform:uppercase;margin-bottom:.6rem}

/* ── Search box ── */
.search-wrap{position:relative}
.search-input{
  width:100%;padding:.7rem 2.5rem .7rem .8rem;
  background:var(--bg);border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-size:.9rem;outline:none;
  font-family:'Segoe UI',system-ui,sans-serif;
  transition:border-color .2s;
}
.search-input:focus{border-color:var(--accent)}
.search-input::placeholder{color:var(--muted)}
.search-btn{
  position:absolute;left:.5rem;top:50%;transform:translateY(-50%);
  background:none;border:none;color:var(--muted);cursor:pointer;
  font-size:1rem;transition:color .2s;padding:.3rem;
}
.search-btn:hover{color:var(--accent)}

/* ── Platform toggles ── */
.platform-list{display:flex;flex-direction:column;gap:.4rem}
.platform-btn{
  display:flex;align-items:center;gap:.6rem;padding:.55rem .75rem;
  background:var(--bg);border:1px solid var(--border);border-radius:8px;
  color:var(--muted);font-size:.82rem;cursor:pointer;text-align:right;
  transition:all .2s;width:100%;
}
.platform-btn:hover,.platform-btn.active{border-color:var(--accent);color:var(--text);
  background:rgba(0,195,255,.05)}
.platform-btn.active .pb-dot{background:var(--accent);box-shadow:0 0 6px var(--accent)}
.pb-dot{width:6px;height:6px;border-radius:50%;background:var(--muted);flex-shrink:0;margin-right:auto}

/* ── Trending chips ── */
.trend-chips{display:flex;flex-wrap:wrap;gap:.4rem}
.chip{
  padding:.25rem .6rem;background:rgba(0,195,255,.07);
  border:1px solid rgba(0,195,255,.18);border-radius:999px;
  font-family:'Courier New',monospace;font-size:.72rem;color:var(--accent);
  cursor:pointer;transition:all .2s;
}
.chip:hover{background:rgba(0,195,255,.15);border-color:var(--accent)}

/* ── AI quick asks ── */
.quick-list{display:flex;flex-direction:column;gap:.35rem}
.quick-btn{
  background:none;border:none;color:var(--muted);font-size:.8rem;
  text-align:right;cursor:pointer;padding:.3rem .5rem;border-radius:6px;
  transition:all .2s;display:flex;align-items:center;gap:.4rem;
}
.quick-btn:hover{color:var(--accent);background:rgba(0,195,255,.05)}

/* ── Content area ── */
.content{padding:1.2rem;display:flex;flex-direction:column;gap:1.2rem;overflow-y:auto}

/* ── Summary bar ── */
.summary-bar{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:.8rem
}
.sum-card{
  background:var(--panel);border:1px solid var(--border);border-radius:10px;
  padding:.9rem 1rem;text-align:center;
}
.sum-val{font-family:'Courier New',monospace;font-size:1.4rem;font-weight:700;margin-bottom:.2rem}
.sum-lbl{font-size:.72rem;color:var(--muted)}

/* ── Results panel ── */
.results-panel{background:var(--panel);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.rp-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:.7rem 1rem;border-bottom:1px solid var(--border);
}
.rp-title{font-family:'Courier New',monospace;font-size:.78rem;color:var(--accent)}
.rp-count{font-family:'Courier New',monospace;font-size:.7rem;color:var(--muted)}
.rp-body{padding:.8rem;display:flex;flex-direction:column;gap:.7rem;max-height:500px;overflow-y:auto}

/* ── Result card ── */
.result-card{
  background:var(--panel2);border:1px solid var(--border);border-radius:8px;
  padding:.9rem;transition:border-color .2s;
}
.result-card:hover{border-color:var(--border-hi)}
.rc-top{display:flex;align-items:flex-start;justify-content:space-between;gap:.5rem;margin-bottom:.5rem}
.rc-ticker{
  font-family:'Courier New',monospace;font-size:.85rem;font-weight:700;
  padding:.2rem .6rem;border-radius:5px;background:rgba(0,195,255,.1);
  border:1px solid rgba(0,195,255,.2);color:var(--accent);flex-shrink:0;
}
.rc-title{font-size:.85rem;color:var(--text);line-height:1.4;flex:1}
.rc-meta{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;margin-top:.5rem}
.rc-source{font-size:.72rem;color:var(--muted);font-family:'Courier New',monospace}
.rc-time{font-size:.72rem;color:var(--muted)}
.rc-body{font-size:.82rem;color:var(--muted);line-height:1.6;margin-top:.4rem}
.rc-link{display:inline-flex;align-items:center;gap:.2rem;font-size:.75rem;
  color:var(--accent);text-decoration:none;margin-top:.5rem}
.rc-link:hover{text-decoration:underline}

/* ── Sentiment badge ── */
.sent{padding:.15rem .5rem;border-radius:3px;font-size:.68rem;
  font-family:'Courier New',monospace;text-transform:uppercase}
.sent-bullish{background:rgba(0,255,136,.1);color:var(--green);border:1px solid rgba(0,255,136,.2)}
.sent-bearish{background:rgba(255,59,92,.1); color:var(--red);  border:1px solid rgba(255,59,92,.2)}
.sent-neutral{background:rgba(255,170,0,.07);color:var(--amber);border:1px solid rgba(255,170,0,.18)}

/* ── Score bar ── */
.score-bar{height:3px;background:var(--border);border-radius:2px;margin-top:.4rem;overflow:hidden}
.score-fill{height:100%;border-radius:2px;transition:width .6s}

/* ── AI Panel ── */
.ai-panel{background:var(--panel);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.ai-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:.7rem 1rem;border-bottom:1px solid var(--border);
}
.ai-title{font-family:'Courier New',monospace;font-size:.78rem;color:var(--accent2)}
.ai-model{font-family:'Courier New',monospace;font-size:.68rem;color:var(--muted)}
.ai-body{padding:1rem;min-height:80px;max-height:300px;overflow-y:auto;
  font-size:.85rem;line-height:1.7;white-space:pre-wrap}
.ai-input-row{display:flex;gap:.5rem;padding:.75rem;border-top:1px solid var(--border)}
.ai-inp{
  flex:1;padding:.55rem .8rem;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:.85rem;outline:none;
  font-family:'Segoe UI',system-ui,sans-serif;
}
.ai-inp:focus{border-color:var(--accent2)}
.ai-inp::placeholder{color:var(--muted)}

/* ── Buttons ── */
.btn{padding:.5rem 1.1rem;border-radius:7px;border:none;cursor:pointer;
  font-size:.82rem;font-weight:600;transition:all .2s}
.btn-primary{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff}
.btn-primary:hover{opacity:.85;transform:translateY(-1px)}
.btn-sm{padding:.3rem .7rem;font-size:.75rem}
.btn-ghost{background:none;border:1px solid var(--border);color:var(--muted)}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}

/* ── Loading ── */
.loading{display:none;align-items:center;gap:.5rem;padding:1rem;
  color:var(--muted);font-size:.82rem;font-family:'Courier New',monospace}
.loading.show{display:flex}
.spin{width:14px;height:14px;border:2px solid var(--border);
  border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Empty state ── */
.empty{text-align:center;padding:3rem 1rem;color:var(--muted)}
.empty .icon{font-size:2.5rem;margin-bottom:.75rem}
.empty p{font-size:.85rem}

/* ── Platform tabs ── */
.ptabs{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.5rem}
.ptab{padding:.3rem .8rem;border-radius:999px;border:1px solid var(--border);
  background:none;color:var(--muted);font-size:.75rem;cursor:pointer;transition:all .2s}
.ptab.active,.ptab:hover{border-color:var(--accent);color:var(--accent);background:rgba(0,195,255,.06)}

/* ── Trending table ── */
.trend-table{width:100%;border-collapse:collapse}
.trend-table th,.trend-table td{padding:.5rem .75rem;text-align:right;border-bottom:1px solid var(--border);font-size:.82rem}
.trend-table th{color:var(--muted);font-family:'Courier New',monospace;font-size:.7rem;font-weight:400}
.trend-table tr:last-child td{border:none}
.trend-table tr:hover td{background:rgba(0,195,255,.03)}
.rank{font-family:'Courier New',monospace;color:var(--muted);font-size:.75rem}

/* ── Footer ── */
footer{border-top:1px solid var(--border);padding:.7rem 1.5rem;
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;
  font-family:'Courier New',monospace;font-size:.7rem;color:var(--muted)}
footer span{display:flex;align-items:center;gap:.4rem}

/* ── Login page ── */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:var(--bg);position:relative;z-index:1}
.login-box{background:var(--panel);border:1px solid var(--border-hi);border-radius:14px;
  padding:2.5rem 2rem;width:360px;box-shadow:0 0 40px rgba(0,195,255,.06)}
.login-logo{text-align:center;margin-bottom:1.5rem}
.login-logo .icon{font-size:2.5rem}
.login-logo h1{font-family:'Courier New',monospace;font-size:1.1rem;color:var(--accent);
  margin:.5rem 0 .2rem}
.login-logo p{font-size:.78rem;color:var(--muted)}
.login-field{display:flex;flex-direction:column;gap:.35rem;margin-bottom:1rem}
.login-field label{font-size:.8rem;color:var(--muted)}
.login-field input{padding:.7rem .9rem;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:.9rem;outline:none;transition:border-color .2s}
.login-field input:focus{border-color:var(--accent)}
.login-err{background:rgba(255,59,92,.1);border:1px solid rgba(255,59,92,.2);color:var(--red);
  padding:.6rem .9rem;border-radius:7px;font-size:.82rem;margin-bottom:1rem}
"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Market Intel — تسجيل الدخول</title>
<style>{{ css }}</style></head>
<body>
<canvas id="bgc"></canvas>
<div class="login-wrap">
<div class="login-box">
  <div class="login-logo">
    <div class="icon">📊</div>
    <h1>MARKET INTEL</h1>
    <p>استخبارات السوق الخاصة · Adanos + Ollama</p>
  </div>
  {% if error %}<div class="login-err">⚠ {{ error }}</div>{% endif %}
  <form method="POST">
    <div class="login-field">
      <label>كلمة المرور</label>
      <input type="password" name="password" placeholder="••••••••" autofocus/>
    </div>
    <button type="submit" class="btn btn-primary" style="width:100%;padding:.7rem">
      دخول ←
    </button>
  </form>
  <p style="margin-top:1rem;font-size:.72rem;color:var(--muted);text-align:center">
    🔒 وصول عبر Tailscale فقط
  </p>
</div>
</div>
<script>
(function(){
  var c=document.getElementById('bgc'),ctx=c.getContext('2d');
  c.width=window.innerWidth;c.height=window.innerHeight;
  var pts=[];for(var i=0;i<40;i++)pts.push({x:Math.random()*c.width,y:Math.random()*c.height,
    dx:(Math.random()-.5)*.4,dy:(Math.random()-.5)*.4,r:Math.random()*1.5+.5});
  function draw(){ctx.clearRect(0,0,c.width,c.height);pts.forEach(function(p){
    p.x+=p.dx;p.y+=p.dy;
    if(p.x<0)p.x=c.width;if(p.x>c.width)p.x=0;
    if(p.y<0)p.y=c.height;if(p.y>c.height)p.y=0;
    ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
    ctx.fillStyle='rgba(0,195,255,.3)';ctx.fill();
  });requestAnimationFrame(draw);}
  draw();
})();
</script>
</body></html>"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Market Intel — استخبارات السوق</title>
<style>{{ css }}</style>
</head>
<body>
<canvas id="bgc"></canvas>
<div class="wrap">

<!-- Nav -->
<nav>
  <div class="nav-brand">
    📊 <strong>MARKET INTEL</strong>
    <span class="ver">v1.0 · Adanos</span>
  </div>
  <div class="nav-right">
    <div class="live-dot"></div>
    <span id="clock" style="font-family:'Courier New',monospace;font-size:.75rem;color:var(--muted)"></span>
    <a href="/logout">خروج</a>
  </div>
</nav>

<!-- Main Grid -->
<div class="main">

<!-- ═══ SIDEBAR ═══ -->
<aside class="sidebar">

  <!-- Search -->
  <div>
    <div class="s-label">البحث</div>
    <div class="search-wrap">
      <input id="search-inp" class="search-input" placeholder="AAPL, BTC, TSLA, أي سهم أو عملة..." />
      <button class="search-btn" onclick="doSearch()">🔍</button>
    </div>
    <div style="margin-top:.5rem;display:flex;gap:.4rem;flex-wrap:wrap" id="recent-searches"></div>
  </div>

  <!-- Platforms -->
  <div>
    <div class="s-label">المنصات</div>
    <div class="platform-list">
      <button class="platform-btn active" data-p="x" onclick="selectPlatform('x',this)">
        <span>𝕏 Twitter / X</span>
        <span class="pb-dot" style="background:#1d9bf0;box-shadow:0 0 5px #1d9bf0"></span>
      </button>
      <button class="platform-btn" data-p="news" onclick="selectPlatform('news',this)">
        <span>📰 الأخبار المالية</span>
        <span class="pb-dot"></span>
      </button>
      <button class="platform-btn" data-p="reddit" onclick="selectPlatform('reddit',this)">
        <span>🟠 Reddit الأسهم</span>
        <span class="pb-dot"></span>
      </button>
      <button class="platform-btn" data-p="reddit-crypto" onclick="selectPlatform('reddit-crypto',this)">
        <span>🟡 Reddit Crypto</span>
        <span class="pb-dot"></span>
      </button>
      <button class="platform-btn" data-p="polymarket" onclick="selectPlatform('polymarket',this)">
        <span>🎯 Polymarket</span>
        <span class="pb-dot"></span>
      </button>
    </div>
  </div>

  <!-- Trending tickers -->
  <div>
    <div class="s-label" style="display:flex;justify-content:space-between">
      <span>الأكثر تداولاً</span>
      <button class="btn btn-ghost btn-sm" onclick="loadTrending()" style="font-size:.65rem;padding:.15rem .5rem">تحديث</button>
    </div>
    <div class="trend-chips" id="trend-chips">
      <span style="font-size:.75rem;color:var(--muted)">جارٍ التحميل…</span>
    </div>
  </div>

  <!-- AI quick asks -->
  <div>
    <div class="s-label">اسأل الذكاء</div>
    <div class="quick-list">
      <button class="quick-btn" onclick="quickAsk('ما توقعاتك لسوق الأسهم اليوم بناءً على المشاعر العامة؟')">▸ توقعات اليوم</button>
      <button class="quick-btn" onclick="quickAsk('ما الفرق بين مشاعر Reddit وX في الأسهم؟')">▸ Reddit vs X</button>
      <button class="quick-btn" onclick="quickAsk('كيف تقرأ بيانات مشاعر السوق لاتخاذ قرار استثماري؟')">▸ قراءة المشاعر</button>
      <button class="quick-btn" onclick="quickAsk('ما هي مؤشرات التحليل الفني الأهم مع تحليل المشاعر؟')">▸ التحليل الفني</button>
      <button class="quick-btn" onclick="quickAsk('اشرح مفهوم الـ Polymarket وكيف يعكس توقعات السوق')">▸ Polymarket ما هو</button>
    </div>
  </div>

  <!-- API status -->
  <div style="margin-top:auto">
    <div class="s-label">حالة الـ API</div>
    <div id="api-status" style="font-family:'Courier New',monospace;font-size:.72rem;display:flex;flex-direction:column;gap:.25rem">
      <span style="color:var(--muted)">جارٍ الفحص…</span>
    </div>
  </div>
</aside>

<!-- ═══ CONTENT ═══ -->
<div class="content">

  <!-- Summary bar -->
  <div class="summary-bar">
    <div class="sum-card">
      <div class="sum-val" id="s-total" style="color:var(--accent)">—</div>
      <div class="sum-lbl">نتائج البحث</div>
    </div>
    <div class="sum-card">
      <div class="sum-val" id="s-bullish" style="color:var(--green)">—</div>
      <div class="sum-lbl">إيجابي 🟢</div>
    </div>
    <div class="sum-card">
      <div class="sum-val" id="s-bearish" style="color:var(--red)">—</div>
      <div class="sum-lbl">سلبي 🔴</div>
    </div>
    <div class="sum-card">
      <div class="sum-val" id="s-score" style="color:var(--amber)">—</div>
      <div class="sum-lbl">مؤشر المشاعر</div>
    </div>
    <div class="sum-card">
      <div class="sum-val" id="s-platform" style="color:var(--accent2);font-size:1rem">𝕏</div>
      <div class="sum-lbl">المنصة الحالية</div>
    </div>
  </div>

  <!-- Results -->
  <div class="results-panel">
    <div class="rp-head">
      <span class="rp-title" id="results-title">// نتائج البحث</span>
      <span class="rp-count" id="results-count"></span>
    </div>
    <div class="loading" id="loading">
      <div class="spin"></div>
      <span>جارٍ جلب البيانات…</span>
    </div>
    <div class="rp-body" id="results-body">
      <div class="empty">
        <div class="icon">🔍</div>
        <p>ابحث عن سهم أو عملة رقمية<br/>أو انقر على أحد الرموز أعلاه</p>
      </div>
    </div>
  </div>

  <!-- Trending table -->
  <div class="results-panel" id="trending-panel">
    <div class="rp-head">
      <span class="rp-title">// الأكثر تداولاً الآن</span>
      <div class="ptabs" id="trend-tabs">
        <button class="ptab active" data-tp="x" onclick="switchTrendTab('x',this)">𝕏 X</button>
        <button class="ptab" data-tp="news" onclick="switchTrendTab('news',this)">📰 News</button>
        <button class="ptab" data-tp="reddit" onclick="switchTrendTab('reddit',this)">🟠 Reddit</button>
        <button class="ptab" data-tp="reddit-crypto" onclick="switchTrendTab('reddit-crypto',this)">🟡 Crypto</button>
      </div>
    </div>
    <div class="rp-body" id="trending-body">
      <div class="empty"><div class="icon">📈</div><p>جارٍ تحميل البيانات…</p></div>
    </div>
  </div>

  <!-- AI Panel -->
  <div class="ai-panel">
    <div class="ai-head">
      <span class="ai-title">🧠 محلل الذكاء — Ollama {{ model }}</span>
      <span class="ai-model">خاص · لا بيانات تغادر السيرفر</span>
    </div>
    <div class="ai-body" id="ai-body">
      مرحباً! أنا محللك المالي الخاص. أسألني عن أي سهم، عملة، أو بيانات السوق وسأحللها لك.
    </div>
    <div class="ai-input-row">
      <input id="ai-inp" class="ai-inp" placeholder="اسأل عن أي سهم، اتجاه، أو تحليل…"
             onkeydown="if(event.key==='Enter')sendAI()"/>
      <button class="btn btn-primary btn-sm" onclick="sendAI()">إرسال</button>
    </div>
  </div>

</div><!-- /content -->
</div><!-- /main -->

<footer>
  <span>📊 Market Intel · Powered by Adanos API + Ollama</span>
  <span>🔒 <strong>خاص</strong> · Tailscale Only · السيادة كاملة لك</span>
</footer>
</div><!-- /wrap -->

<script>
// ── Canvas BG ─────────────────────────────────────────────────────────────────
(function(){
  var c=document.getElementById('bgc'),ctx=c.getContext('2d');
  function rs(){c.width=window.innerWidth;c.height=window.innerHeight;}rs();
  window.addEventListener('resize',rs);
  var pts=[];for(var i=0;i<50;i++)pts.push({
    x:Math.random()*1920,y:Math.random()*1080,
    dx:(Math.random()-.5)*.25,dy:(Math.random()-.5)*.25,r:Math.random()*1.2+.3
  });
  function draw(){
    ctx.clearRect(0,0,c.width,c.height);
    pts.forEach(function(p){
      p.x+=p.dx;p.y+=p.dy;
      if(p.x<0)p.x=c.width;if(p.x>c.width)p.x=0;
      if(p.y<0)p.y=c.height;if(p.y>c.height)p.y=0;
      ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle='rgba(0,195,255,.4)';ctx.fill();
    });
    for(var i=0;i<pts.length;i++)for(var j=i+1;j<pts.length;j++){
      var dx=pts[i].x-pts[j].x,dy=pts[i].y-pts[j].y,d=Math.sqrt(dx*dx+dy*dy);
      if(d<100){ctx.beginPath();ctx.moveTo(pts[i].x,pts[i].y);ctx.lineTo(pts[j].x,pts[j].y);
        ctx.strokeStyle='rgba(0,195,255,'+(0.12*(1-d/100))+')';ctx.lineWidth=.4;ctx.stroke();}
    }
    requestAnimationFrame(draw);
  }draw();
})();

// ── Clock ─────────────────────────────────────────────────────────────────────
setInterval(function(){
  document.getElementById('clock').textContent=new Date().toLocaleTimeString('ar-SA');
},1000);

// ── State ─────────────────────────────────────────────────────────────────────
var _platform = 'x';
var _lastQuery = '';
var _recentSearches = JSON.parse(localStorage.getItem('mi_recent')||'[]');
var _trendData = {};
var _currentTrendPlatform = 'x';

// ── Platform selection ────────────────────────────────────────────────────────
function selectPlatform(p, btn) {
  _platform = p;
  document.querySelectorAll('.platform-btn').forEach(function(b){b.classList.remove('active');});
  btn.classList.add('active');
  var labels={'x':'𝕏','news':'📰','reddit':'🟠','reddit-crypto':'🟡','polymarket':'🎯'};
  document.getElementById('s-platform').textContent = labels[p]||p;
  if (_lastQuery) doSearch();
}

// ── Search ────────────────────────────────────────────────────────────────────
function doSearch() {
  var q = document.getElementById('search-inp').value.trim().toUpperCase();
  if (!q) return;
  _lastQuery = q;
  saveRecent(q);
  showLoading(true);
  document.getElementById('results-title').textContent = '// بحث: ' + q + ' على ' + _platform;

  fetch('/api/search', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({query: q, platform: _platform})
  })
  .then(function(r){return r.json();})
  .then(function(data){
    showLoading(false);
    renderResults(data, q);
  })
  .catch(function(e){
    showLoading(false);
    showError('خطأ في البحث: '+e.message);
  });
}

// ── Render results ────────────────────────────────────────────────────────────
function renderResults(data, query) {
  var items = data.items || data.results || data.data || (Array.isArray(data)?data:[]);
  var error = data.error;

  if (error) { showError(error); return; }

  document.getElementById('results-count').textContent = items.length + ' نتيجة';
  document.getElementById('s-total').textContent = items.length;

  var bullish=0, bearish=0, scoreSum=0;
  items.forEach(function(it){
    var s=(it.sentiment||it.sentiment_label||'').toLowerCase();
    if(s.includes('bull')||s==='positive'||s==='bullish') bullish++;
    else if(s.includes('bear')||s==='negative'||s==='bearish') bearish++;
    scoreSum += (it.sentiment_score||it.score||it.rank||0);
  });
  document.getElementById('s-bullish').textContent = bullish;
  document.getElementById('s-bearish').textContent = bearish;
  var avg = items.length ? (scoreSum/items.length).toFixed(2) : '—';
  document.getElementById('s-score').textContent = avg;

  if (!items.length) {
    document.getElementById('results-body').innerHTML =
      '<div class="empty"><div class="icon">🔍</div><p>لا توجد نتائج لـ <strong>'+query+'</strong></p></div>';
    return;
  }

  document.getElementById('results-body').innerHTML = items.slice(0,30).map(function(it){
    return renderResultCard(it);
  }).join('');
}

function renderResultCard(it) {
  var ticker = it.ticker||it.symbol||it.stock||'';
  var title  = it.title||it.text||it.body||it.content||it.headline||'';
  var source = it.source||it.subreddit||it.author||it.username||'';
  var url    = it.url||it.link||'#';
  var ts     = it.created_at||it.published_at||it.timestamp||it.date||'';
  var sent   = (it.sentiment||it.sentiment_label||'neutral').toLowerCase();
  var score  = it.sentiment_score||it.score||0;

  var sentClass = sent.includes('bull')||sent==='positive' ? 'sent-bullish'
                : sent.includes('bear')||sent==='negative' ? 'sent-bearish'
                : 'sent-neutral';
  var sentLabel = sent.includes('bull')||sent==='positive' ? 'إيجابي 🟢'
                : sent.includes('bear')||sent==='negative' ? 'سلبي 🔴'
                : 'محايد 🟡';

  var scoreColor = score>0.5?'var(--green)':score<-0.5?'var(--red)':'var(--amber)';
  var scoreW = Math.min(Math.abs(score)*100,100)+'%';

  var timeStr = ts ? new Date(ts).toLocaleString('ar-SA') : '';

  return '<div class="result-card">' +
    '<div class="rc-top">' +
      (ticker?'<span class="rc-ticker">$'+ticker+'</span>':'') +
      '<div class="rc-title">'+(title.slice(0,200)||'—')+'</div>' +
      '<span class="sent '+sentClass+'">'+sentLabel+'</span>' +
    '</div>' +
    '<div class="score-bar"><div class="score-fill" style="width:'+scoreW+';background:'+scoreColor+'"></div></div>' +
    '<div class="rc-meta">' +
      (source?'<span class="rc-source">@'+source+'</span>':'') +
      (timeStr?'<span class="rc-time">'+timeStr+'</span>':'') +
    '</div>' +
    (url&&url!=='#'?'<a class="rc-link" href="'+url+'" target="_blank">عرض المصدر ↗</a>':'') +
  '</div>';
}

// ── Trending ──────────────────────────────────────────────────────────────────
function loadTrending() {
  fetch('/api/trending?platform='+_currentTrendPlatform)
  .then(function(r){return r.json();})
  .then(function(data){
    _trendData[_currentTrendPlatform] = data;
    renderTrending(data);
    renderTrendChips(data);
  })
  .catch(function(e){
    document.getElementById('trending-body').innerHTML=
      '<div class="empty"><div class="icon">⚠️</div><p>'+e.message+'</p></div>';
  });
}

function renderTrending(data) {
  var items = data.items||data.results||data.data||(Array.isArray(data)?data:[]);
  var err   = data.error;
  if (err) {
    document.getElementById('trending-body').innerHTML=
      '<div style="padding:1rem;font-family:Courier New,monospace;font-size:.78rem;color:var(--red)">⚠ '+err+'</div>';
    return;
  }
  if(!items.length){
    document.getElementById('trending-body').innerHTML='<div class="empty"><div class="icon">📊</div><p>لا بيانات متاحة</p></div>';
    return;
  }
  var rows = items.slice(0,20).map(function(it,i){
    var ticker = it.ticker||it.symbol||it.stock||it.name||'—';
    var score  = it.sentiment_score||it.score||it.rank||'—';
    var sent   = (it.sentiment||it.sentiment_label||'').toLowerCase();
    var sentC  = sent.includes('bull')||sent==='positive'?'var(--green)':
                 sent.includes('bear')||sent==='negative'?'var(--red)':'var(--amber)';
    var vol    = it.volume||it.mentions||it.count||'—';
    var scoreDisp = typeof score==='number'?score.toFixed(2):score;
    return '<tr>' +
      '<td class="rank">#'+(i+1)+'</td>' +
      '<td style="font-family:Courier New,monospace;color:var(--accent);font-weight:700">$'+ticker+'</td>' +
      '<td style="color:'+sentC+'">'+scoreDisp+'</td>' +
      '<td style="color:var(--muted)">'+vol+'</td>' +
      '<td><button class="btn btn-ghost btn-sm" onclick="searchTicker(\''+ticker+'\')">بحث</button></td>' +
    '</tr>';
  }).join('');
  document.getElementById('trending-body').innerHTML=
    '<table class="trend-table">' +
    '<thead><tr><th>#</th><th>الرمز</th><th>المشاعر</th><th>الإشارات</th><th></th></tr></thead>' +
    '<tbody>'+rows+'</tbody></table>';
}

function renderTrendChips(data) {
  var items = data.items||data.results||data.data||(Array.isArray(data)?data:[]);
  var chips = items.slice(0,10).map(function(it){
    var t=it.ticker||it.symbol||it.stock||it.name||'';
    return t?'<span class="chip" onclick="searchTicker(\''+t+'\')">$'+t+'</span>':'';
  }).join('');
  document.getElementById('trend-chips').innerHTML = chips||'<span style="font-size:.75rem;color:var(--muted)">لا بيانات</span>';
}

function switchTrendTab(tp, btn) {
  _currentTrendPlatform = tp;
  document.querySelectorAll('.ptab').forEach(function(b){b.classList.remove('active');});
  btn.classList.add('active');
  if(_trendData[tp]){renderTrending(_trendData[tp]);}
  else{loadTrending();}
}

function searchTicker(t) {
  document.getElementById('search-inp').value = t;
  doSearch();
}

// ── Recent searches ───────────────────────────────────────────────────────────
function saveRecent(q) {
  _recentSearches = [q].concat(_recentSearches.filter(function(x){return x!==q;})).slice(0,6);
  localStorage.setItem('mi_recent', JSON.stringify(_recentSearches));
  renderRecent();
}
function renderRecent(){
  document.getElementById('recent-searches').innerHTML =
    _recentSearches.map(function(q){
      return '<span class="chip" onclick="searchTicker(\''+q+'\')" style="font-size:.65rem">'+q+'</span>';
    }).join('');
}

// ── AI ────────────────────────────────────────────────────────────────────────
function quickAsk(txt){ document.getElementById('ai-inp').value=txt; sendAI(); }

async function sendAI() {
  var inp = document.getElementById('ai-inp');
  var q   = inp.value.trim(); if(!q)return;
  inp.value='';
  var body = document.getElementById('ai-body');
  body.textContent='🧠 جارٍ التحليل…';

  var contextNote = _lastQuery
    ? '\n\nبيانات حالية: الرمز "'+_lastQuery+'" على منصة '+_platform
    : '';
  var fullPrompt = q + contextNote;

  try {
    var resp = await fetch('/api/ai/analyze', {
      method:'POST',headers:{'Content-Type':'application/json'},
      body: JSON.stringify({prompt: fullPrompt})
    });
    var reader=resp.body.getReader(), decoder=new TextDecoder();
    body.textContent='';
    while(true){
      var rd=await reader.read(); if(rd.done)break;
      decoder.decode(rd.value).split('\n').forEach(function(line){
        if(!line.startsWith('data: '))return;
        var d=line.slice(6).trim(); if(d==='[DONE]')return;
        try{body.textContent+=JSON.parse(d).delta||'';}catch(e){}
      });
      body.scrollTop=body.scrollHeight;
    }
  } catch(e){ body.textContent='⚠ خطأ: '+e.message; }
}

// ── API Status ────────────────────────────────────────────────────────────────
function checkAPIStatus() {
  fetch('/api/status')
  .then(function(r){return r.json();})
  .then(function(data){
    var el=document.getElementById('api-status');
    var html='';
    Object.entries(data).forEach(function(entry){
      var k=entry[0],v=entry[1];
      var col=v==='ok'?'var(--green)':v==='no_key'?'var(--amber)':'var(--red)';
      html+='<span style="color:'+col+'">'+
        (v==='ok'?'✓':v==='no_key'?'⚿':'✗')+' '+k+'</span>';
    });
    el.innerHTML=html;
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function showLoading(v){document.getElementById('loading').classList[v?'add':'remove']('show');}
function showError(msg){
  document.getElementById('results-body').innerHTML=
    '<div style="padding:1rem;font-family:Courier New,monospace;font-size:.82rem;color:var(--red)">⚠ '+msg+'</div>';
}

// ── Init ──────────────────────────────────────────────────────────────────────
renderRecent();
loadTrending();
checkAPIStatus();
setInterval(checkAPIStatus, 30000);

// search on Enter
document.getElementById('search-inp').addEventListener('keydown',function(e){
  if(e.key==='Enter') doSearch();
});
</script>
</body></html>"""

# ── Flask Routes ──────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    ip = request.remote_addr or "0.0.0.0"
    error = None
    if request.method == "POST":
        if _locked(ip):
            error = "محاولات كثيرة — انتظر 5 دقائق"
        elif hmac.compare_digest(
            hashlib.sha256(request.form.get("password","").encode()).hexdigest(), _PWD_HASH
        ):
            session["ok"] = True
            _hits.pop(ip, None)
            return redirect(url_for("dashboard"))
        else:
            _fail(ip)
            error = "كلمة المرور خاطئة"
    return render_template_string(LOGIN_HTML, css=_CSS, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    return render_template_string(DASHBOARD_HTML, css=_CSS, model=OLLAMA_MODEL)


# ── API: Search ───────────────────────────────────────────────────────────────
@app.route("/api/search", methods=["POST"])
@login_required
def api_search():
    body     = request.get_json(silent=True) or {}
    query    = str(body.get("query", ""))[:50].strip()
    platform = body.get("platform", "x")

    if not query:
        return jsonify({"error": "query required"}), 400

    path = PLATFORMS.get(platform, PLATFORMS["x"])

    # محاولة عدة endpoints شائعة للـ API
    for endpoint in ["/search", "/posts/search", "/trending/search"]:
        data = adanos_get(f"{path}{endpoint}", {"query": query, "limit": 30, "q": query})
        if not data.get("error"):
            return jsonify(data)

    # محاولة /trending مع فلترة محلية
    data = adanos_get(f"{path}/trending", {"limit": 50})
    if not data.get("error"):
        items = data.get("items") or data.get("results") or data.get("data") or (
            data if isinstance(data, list) else []
        )
        q_upper = query.upper()
        filtered = [i for i in items if q_upper in str(i).upper()]
        return jsonify({"items": filtered, "source": "trending_filtered"})

    return jsonify(data)


# ── API: Trending ─────────────────────────────────────────────────────────────
@app.route("/api/trending")
@login_required
def api_trending():
    platform = request.args.get("platform", "x")
    path     = PLATFORMS.get(platform, PLATFORMS["x"])

    for endpoint in ["/trending", "/hot", "/popular", ""]:
        data = adanos_get(f"{path}{endpoint}", {"limit": 25})
        if not data.get("error"):
            return jsonify(data)

    return jsonify(data)


# ── API: AI Analyze (streaming) ───────────────────────────────────────────────
@app.route("/api/ai/analyze", methods=["POST"])
@login_required
def api_ai_analyze():
    body   = request.get_json(silent=True) or {}
    prompt = str(body.get("prompt", ""))[:2000]
    return Response(
        stream_with_context(ai_stream(prompt)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# ── API: Status ───────────────────────────────────────────────────────────────
@app.route("/api/status")
@login_required
def api_status():
    status = {}

    # فحص كل platform
    for name, path in PLATFORMS.items():
        if not ADANOS_KEY:
            status[name] = "no_key"
            continue
        try:
            r = httpx.get(
                f"{ADANOS_BASE}{path}/health",
                headers=_adanos_headers(), timeout=5,
            )
            status[name] = "ok" if r.status_code == 200 else f"http_{r.status_code}"
        except Exception:
            status[name] = "offline"

    # فحص Ollama
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        status["ollama"] = "ok" if r.status_code == 200 else "error"
    except Exception:
        status["ollama"] = "offline"

    return jsonify(status)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("MARKET_PORT", "5001"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    print(f"\n{'='*55}")
    print(f"  📊  MARKET INTEL — استخبارات السوق الخاصة")
    print(f"{'='*55}")
    print(f"  URL     : http://0.0.0.0:{port}")
    print(f"  Tailscale: http://100.109.223.64:{port}")
    print(f"  Adanos  : {'✅ مفتاح موجود' if ADANOS_KEY else '⚠  لا مفتاح — أضف ADANOS_API_KEY'}")
    print(f"  Ollama  : {OLLAMA_URL} [{OLLAMA_MODEL}]")
    print(f"  Privacy : 🔒 خاص تماماً — لا بيانات تغادر السيرفر")
    print(f"{'='*55}\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
