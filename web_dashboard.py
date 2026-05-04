#!/usr/bin/env python3
"""
Sentinel Guard — Tactical Cybersecurity Dashboard
Kali Linux 2026 × Nmap Hacker's Radar × DeepSeek-V4 AI Core
AI سلسلة: Gemini → Docker Model Runner (DeepSeek V4 / MiMo / Granite) → Ollama
pip install flask openai google-genai
"""
import os, json, hmac, hashlib, time, glob, re
from functools import wraps
from flask import (
    Flask, render_template_string, request, redirect, url_for,
    session, jsonify, Response, stream_with_context,
)

app = Flask(__name__)
app.secret_key = os.getenv(
    "DASHBOARD_SECRET",
    hashlib.sha256(b"sentinel-guard-v2-tactical").hexdigest(),
)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("HTTPS", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=3600,
)

_PWD_HASH = hashlib.sha256(
    os.getenv("DASHBOARD_PASSWORD", "alhakim2026").encode()
).hexdigest()
SENTINEL_API = os.getenv("SENTINEL_API_URL", "http://localhost:8000/api/v1")

# ── AI Backend Config ────────────────────────────────────────────────────────
GEMINI_KEY   = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
MODEL_URL    = os.getenv("OLLAMA_URL", os.getenv(
    "DOCKER_MODEL_RUNNER_URL", "http://localhost:11434/v1"
))
AI_MODEL         = os.getenv("OLLAMA_MODEL", os.getenv("AI_MODEL_GENERAL", "phi3"))
AI_MODEL_FAST    = os.getenv("AI_MODEL_FAST",    "ai/granite-4.0-nano")
AI_MODEL_DEEP    = os.getenv("AI_MODEL_DEEP",    "ai/deepseek-v4-pro")
AI_MODEL_REASON  = os.getenv("AI_MODEL_REASON",  "ai/mimo-v2.5-pro")
AI_MODEL_FALLBACK= os.getenv("AI_MODEL_FALLBACK","ai/deepseek-v3-0324")

# خريطة model IDs المدعومة (label → model_id)
AVAILABLE_MODELS = {
    "deepseek-v4-flash": AI_MODEL,
    "deepseek-v4-pro":   AI_MODEL_DEEP,
    "granite-nano":      AI_MODEL_FAST,
    "mimo-pro":          AI_MODEL_REASON,
    "deepseek-v3":       AI_MODEL_FALLBACK,
}

# Thinking mode — suffix يُضاف للـ system prompt عند Think Max
_THINK_MAX_SUFFIX = (
    "\n\n=== Think Max Mode ===\n"
    "فكّر بعمق وتأنّ في الإجابة. استخدم قدراتك الاستدلالية الكاملة. "
    "حلّل المشكلة من جوانب متعددة قبل الإجابة النهائية."
)

# ── Knowledge base ───────────────────────────────────────────────────────────
def _load_knowledge() -> str:
    base = os.path.join(os.path.dirname(__file__), "knowledge", "kali-tools")
    parts = []
    for p in sorted(glob.glob(os.path.join(base, "*.md"))):
        try:
            parts.append(open(p, encoding="utf-8").read())
        except Exception:
            pass
    return "\n\n---\n\n".join(parts)

_KNOWLEDGE = _load_knowledge()

AMEEN_SYSTEM = (
    "أنت الأمين — مساعد أمني ذكي لنظام Sentinel Guard.\n"
    "تتخصص في أمن المعلومات وتحليل الثغرات وDocker security وتفسير نتائج الفحص.\n"
    "تتحدث العربية افتراضياً وتجيب بإيجاز تقني دقيق.\n\n"
    "=== قواعد السيادة — لا استثناء ===\n"
    "• ممنوع --privileged | ممنوع --net=host\n"
    "• ممنوع الدخول لأنظمة غير مملوكة\n"
    "• لا تُنفّذ إلا بأمر صريح من المستخدم\n"
    "• جميع الأدوات على الأصول المملوكة فقط\n\n"
    "=== أسلوبك ===\n"
    "• ردود مباشرة وتقنية — لا حشو\n"
    "• أوامر حرفية عند الشرح\n"
    "• أولويات الإصلاح: CRITICAL أولاً\n\n"
    "=== قاعدة المعرفة الكاملة ===\n\n"
    + _KNOWLEDGE
)

# ── AI Streaming: Gemini → Docker Model Runner → Ollama ─────────────────────
def _active_backend() -> str:
    if GEMINI_KEY:
        return f"Gemini · {GEMINI_MODEL}"
    host = MODEL_URL.split("//")[-1].split("/")[0]
    return f"Local · {AI_MODEL.split('/')[-1]} @ {host}"

def _resolve_model(model_key: str | None) -> str:
    """يُحوّل مفتاح النموذج إلى model_id الفعلي."""
    if not model_key:
        return AI_MODEL
    return AVAILABLE_MODELS.get(model_key, AI_MODEL)

def _build_system(thinking_mode: str) -> str:
    """يبني الـ system prompt مع التعديل المناسب لوضع التفكير."""
    sys = AMEEN_SYSTEM
    if thinking_mode == "think-max":
        sys += _THINK_MAX_SUFFIX
    return sys

def _ai_stream(message: str, history: list | None = None,
               thinking_mode: str = "non-think", model_key: str | None = None):
    """يُرسل رسالة للذكاء ويُعيد SSE stream.
    thinking_mode: 'non-think' | 'think-high' | 'think-max'
    model_key: مفتاح من AVAILABLE_MODELS أو None للـ default
    """
    active_model = _resolve_model(model_key)
    system_content = _build_system(thinking_mode)
    max_tok = 3000 if thinking_mode in ("think-high", "think-max") else 1500

    # 1. Gemini (google-genai SDK)
    if GEMINI_KEY:
        try:
            from google import genai
            from google.genai import types
            gclient = genai.Client(api_key=GEMINI_KEY)
            msgs = []
            for h in (history or []):
                msgs.append(types.Content(
                    role=h["role"],
                    parts=[types.Part.from_text(text=h["content"])],
                ))
            msgs.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)],
            ))
            stream = gclient.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=msgs,
                config=types.GenerateContentConfig(
                    system_instruction=system_content,
                    max_output_tokens=max_tok,
                ),
            )
            for chunk in stream:
                if chunk.text:
                    yield f"data: {json.dumps({'delta': chunk.text, 'backend': 'gemini'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        except Exception:
            pass  # fallthrough to local model

    # 2. Docker Model Runner / Ollama (OpenAI-compatible)
    try:
        from openai import OpenAI
        client = OpenAI(base_url=MODEL_URL, api_key="unused")
        msgs_openai = [{"role": "system", "content": system_content}]
        for h in (history or []):
            msgs_openai.append({"role": h["role"], "content": h["content"]})
        msgs_openai.append({"role": "user", "content": message})
        stream = client.chat.completions.create(
            model=active_model,
            messages=msgs_openai,
            stream=True,
            max_tokens=max_tok,
            temperature=1.0,
            top_p=1.0,
            timeout=60 if thinking_mode in ("think-high", "think-max") else 40,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield f"data: {json.dumps({'delta': delta, 'backend': active_model})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'delta': f'⚠ خطأ: {exc}'})}\n\n"
        yield "data: [DONE]\n\n"

# ── Rate-limited Auth ────────────────────────────────────────────────────────
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

def _ok(pw: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(pw.encode()).hexdigest(), _PWD_HASH
    )

# ─────────────────────────────────────────────────────────────────────────────
_CSS = """
:root{
  --bg:#03050a;--s1:rgba(0,10,3,.96);--s2:#050e07;
  --b:rgba(0,255,65,.18);--bhi:rgba(0,255,65,.55);
  --g:#00ff41;--g2:#00cc33;--cy:#00d4ff;
  --r:#ff1744;--o:#ff6d00;--am:#ffaa00;
  --t:#b8c8b4;--td:#3a5c3a;--tb:#e8ffe4;
  --mono:'Courier New',monospace;
  --glow:0 0 8px #00ff41,0 0 20px rgba(0,255,65,.22);
  --glow-r:0 0 8px #ff1744,0 0 20px rgba(255,23,68,.22);
  --glow-c:0 0 8px #00d4ff,0 0 16px rgba(0,212,255,.18);
  --glow-am:0 0 8px #ffaa00,0 0 16px rgba(255,170,0,.18);
}
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;overflow:hidden;}
body{background:var(--bg);color:var(--t);font-family:'Segoe UI',system-ui,sans-serif;}
#mtx{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;opacity:.11;}
body::after{content:'';position:fixed;inset:0;z-index:1;pointer-events:none;
  background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,.09) 3px,rgba(0,0,0,.09) 4px);}
.root{position:relative;z-index:2;display:grid;
  grid-template-columns:190px 1fr 345px;height:100vh;}
.sidebar{background:var(--s1);border-left:1px solid var(--b);display:flex;
  flex-direction:column;overflow:hidden;}
.sb-head{padding:14px 12px;border-bottom:1px solid var(--b);text-align:center;}
.sb-hex{font-size:28px;color:var(--g);text-shadow:var(--glow);}
.sb-name{font-family:var(--mono);font-size:10px;color:var(--g);letter-spacing:3px;
  margin:5px 0 2px;text-shadow:var(--glow);animation:glitch 6s infinite;}
.sb-ver{font-size:8px;color:var(--td);font-family:var(--mono);}
.sb-online{display:flex;align-items:center;justify-content:center;gap:4px;
  margin-top:7px;font-size:8px;color:var(--g);font-family:var(--mono);}
.sb-online::before{content:'';width:5px;height:5px;border-radius:50%;
  background:var(--g);box-shadow:var(--glow);animation:pulse 2s infinite;flex-shrink:0;}
.nav-grp{padding:6px 0;}
.nav-lbl{font-family:var(--mono);font-size:8px;color:var(--td);padding:3px 11px;letter-spacing:2px;}
.nav-btn{display:flex;align-items:center;gap:7px;padding:8px 11px;
  color:var(--td);font-size:11px;font-family:var(--mono);cursor:pointer;
  border:none;background:none;width:100%;text-align:right;
  transition:.15s;border-right:2px solid transparent;}
.nav-btn:hover,.nav-btn.active{color:var(--g);
  background:rgba(0,255,65,.055);border-right-color:var(--g);}
.sb-foot{margin-top:auto;padding:10px 11px;border-top:1px solid var(--b);}
.sb-row{display:flex;justify-content:space-between;
  font-family:var(--mono);font-size:8px;padding:2px 0;}
.sk{color:var(--td);} .sv{color:var(--g);} .sv.r{color:var(--r);} .sv.am{color:var(--am);}
.main{display:flex;flex-direction:column;overflow:hidden;}
.mscroll{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:10px;}
.mscroll::-webkit-scrollbar{width:3px;}
.mscroll::-webkit-scrollbar-thumb{background:var(--b);}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:10px;}
.tb-left h1{font-family:var(--mono);font-size:15px;color:var(--g);
  letter-spacing:2px;animation:glitch 5s infinite;text-shadow:var(--glow);}
.tb-left p{font-size:9px;color:var(--td);font-family:var(--mono);margin-top:2px;}
.tb-right{display:flex;align-items:center;gap:12px;}
.gauge-wrap{position:relative;width:70px;height:70px;}
.gauge-wrap svg{width:70px;height:70px;}
.gauge-center{position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;}
.gauge-num{font-family:var(--mono);font-size:17px;font-weight:700;
  color:var(--am);text-shadow:var(--glow-am);}
.gauge-lbl{font-family:var(--mono);font-size:7px;color:var(--td);}
.tb-time{font-family:var(--mono);font-size:9px;color:var(--td);text-align:left;}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;}
.stat{background:var(--s1);border:1px solid var(--b);border-radius:3px;
  padding:11px 10px;position:relative;}
.stat::before{content:'┌─';position:absolute;top:3px;right:6px;
  font-family:var(--mono);font-size:8px;color:var(--g2);opacity:.45;}
.stat::after{content:'─┐';position:absolute;top:3px;left:6px;
  font-family:var(--mono);font-size:8px;color:var(--g2);opacity:.45;}
.stat-lbl{font-family:var(--mono);font-size:8px;color:var(--td);
  text-transform:uppercase;letter-spacing:1px;}
.stat-val{font-family:var(--mono);font-size:22px;font-weight:700;
  color:var(--g);text-shadow:var(--glow);margin:5px 0 2px;}
.stat-sub{font-size:8px;color:var(--td);}
.panel{background:var(--s1);border:1px solid var(--b);border-radius:3px;padding:12px;}
.panel-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.panel-title{font-family:var(--mono);font-size:9px;color:var(--g);letter-spacing:2px;}
.panel-title::before{content:'// ';}
.pbadge{font-family:var(--mono);font-size:8px;padding:2px 7px;border-radius:2px;
  border:1px solid var(--b);color:var(--td);}
.pbadge.on{color:var(--am);border-color:rgba(255,170,0,.35);animation:blink-b 1.5s infinite;}
.radar-grid{display:grid;grid-template-columns:280px 1fr;gap:14px;align-items:start;}
#radar{filter:drop-shadow(0 0 8px rgba(0,255,65,.3));}
#rs{transform-origin:150px 150px;animation:sweep 4s linear infinite;}
.rtable{font-family:var(--mono);}
.rhead{display:grid;grid-template-columns:115px 55px 1fr;font-size:8px;
  color:var(--td);padding:3px 0;border-bottom:1px solid var(--b);
  margin-bottom:5px;letter-spacing:1px;}
.rrow{display:grid;grid-template-columns:115px 55px 1fr;padding:4px 0;
  font-size:10px;border-bottom:1px solid rgba(0,255,65,.05);}
.rip{color:var(--cy);} .rport{color:var(--g);} .rsvc{color:var(--t);}
.rempty{font-size:9px;color:var(--td);padding:14px 0;}
.rnmap{font-family:var(--mono);font-size:9px;margin-top:14px;
  background:#020803;border:1px solid var(--b);border-radius:2px;padding:10px;}
.rnmap .cmd{color:var(--g);} .rnmap .out{color:var(--cy);} .rnmap .dim{color:var(--td);}
.frow{display:flex;align-items:flex-start;gap:7px;padding:7px 0;
  border-bottom:1px solid rgba(0,255,65,.06);}
.frow:last-child{border-bottom:none;}
.fbadge{font-family:var(--mono);font-size:8px;padding:2px 5px;border-radius:2px;
  white-space:nowrap;flex-shrink:0;text-transform:uppercase;}
.fb-critical{background:rgba(255,23,68,.14);color:var(--r);border:1px solid rgba(255,23,68,.35);}
.fb-high{background:rgba(255,109,0,.1);color:var(--o);border:1px solid rgba(255,109,0,.3);}
.fb-medium{background:rgba(255,170,0,.08);color:var(--am);border:1px solid rgba(255,170,0,.25);}
.fb-low{background:rgba(0,255,65,.05);color:var(--g);border:1px solid rgba(0,255,65,.18);}
.fb-info{background:rgba(0,212,255,.05);color:var(--cy);border:1px solid rgba(0,212,255,.18);}
.ftitle{font-size:11px;color:var(--tb);} .fdesc{font-size:9px;color:var(--td);margin-top:2px;}
.ffix{font-size:9px;color:var(--g);margin-top:2px;}
.scan-row{display:flex;gap:7px;margin-bottom:10px;}
.sinp{flex:1;background:#020903;border:1px solid var(--b);color:var(--g);
  padding:7px 11px;border-radius:2px;font-family:var(--mono);font-size:11px;outline:none;}
.sinp:focus{border-color:var(--g);box-shadow:var(--glow);}
.sinp::placeholder{color:var(--td);}
.btn-tac{background:transparent;border:1px solid var(--g);color:var(--g);
  padding:7px 14px;border-radius:2px;cursor:pointer;font-family:var(--mono);
  font-size:10px;letter-spacing:1px;transition:.15s;white-space:nowrap;}
.btn-tac:hover{background:rgba(0,255,65,.09);box-shadow:var(--glow);}
.statusbar{background:rgba(0,4,1,.99);border-top:1px solid var(--b);
  padding:5px 12px;display:flex;align-items:center;gap:10px;
  font-family:var(--mono);font-size:8px;flex-shrink:0;}
.sbi{display:flex;align-items:center;gap:4px;color:var(--td);white-space:nowrap;}
.sbi.on{color:var(--g);} .sbi.on .si{text-shadow:var(--glow);} .sbi.warn{color:var(--am);}
.sbsep{color:rgba(0,255,65,.18);}
.sb-motto{margin-right:auto;color:var(--td);font-size:7px;letter-spacing:.5px;}
.terminal{background:rgba(0,3,0,.98);border-right:1px solid var(--b);
  display:flex;flex-direction:column;overflow:hidden;}
.t-hdr{padding:9px 12px;border-bottom:1px solid var(--b);
  display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.t-htitle{font-family:var(--mono);font-size:9px;color:var(--g);letter-spacing:2px;}
.t-hstatus{display:flex;align-items:center;gap:4px;
  font-family:var(--mono);font-size:8px;color:var(--g);}
.t-dot{width:6px;height:6px;border-radius:50%;background:var(--g);
  box-shadow:var(--glow);animation:pulse 2s infinite;}
.t-bknd{font-family:var(--mono);font-size:7px;color:var(--td);
  margin-top:2px;border-top:1px solid var(--b);padding-top:3px;}
.t-body{flex:1;overflow-y:auto;padding:8px 10px;display:flex;flex-direction:column;gap:3px;}
.t-body::-webkit-scrollbar{width:2px;}
.t-body::-webkit-scrollbar-thumb{background:var(--b);}
.tline{font-family:var(--mono);font-size:10px;line-height:1.65;
  display:flex;gap:5px;align-items:flex-start;}
.tp{color:var(--g);text-shadow:var(--glow);white-space:nowrap;flex-shrink:0;}
.to{color:var(--t);} .to.ai{color:var(--cy);} .to.err{color:var(--r);}
.t-inp-row{padding:7px 10px;border-top:1px solid var(--b);
  display:flex;align-items:center;gap:5px;flex-shrink:0;}
.t-plbl{font-family:var(--mono);font-size:9px;color:var(--g);
  white-space:nowrap;text-shadow:var(--glow);}
.t-inp{flex:1;background:transparent;border:none;outline:none;
  color:var(--t);font-family:var(--mono);font-size:10px;}
.t-cursor{display:inline-block;width:6px;height:11px;background:var(--g);
  animation:blink .7s step-end infinite;vertical-align:middle;box-shadow:var(--glow);}
@keyframes sweep{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.7)}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
@keyframes blink-b{0%,100%{opacity:1}50%{opacity:.35}}
@keyframes glitch{
  0%,93%{text-shadow:var(--glow)}
  94%{text-shadow:3px 0 var(--r),-3px 0 var(--cy)}
  95%{text-shadow:-3px 0 var(--g),3px 0 var(--r)}
  96%{text-shadow:2px 2px var(--cy),-2px -2px var(--r)}
  97%,100%{text-shadow:var(--glow)}
}
/* ── Thinking Mode Controls ── */
.think-bar{display:flex;align-items:center;gap:5px;padding:5px 10px;
  border-bottom:1px solid var(--b);flex-shrink:0;background:rgba(0,3,0,.6);}
.think-lbl{font-family:var(--mono);font-size:7px;color:var(--td);letter-spacing:1px;margin-left:6px;}
.think-btn{font-family:var(--mono);font-size:8px;padding:3px 8px;border-radius:2px;
  border:1px solid var(--b);background:transparent;color:var(--td);cursor:pointer;
  transition:.15s;letter-spacing:.5px;}
.think-btn:hover{border-color:var(--cy);color:var(--cy);}
.think-btn.active{border-color:var(--cy);color:var(--cy);
  background:rgba(0,212,255,.08);box-shadow:var(--glow-c);}
.model-sel{font-family:var(--mono);font-size:8px;background:#020a04;
  border:1px solid var(--b);color:var(--g);padding:3px 6px;border-radius:2px;
  cursor:pointer;margin-right:auto;}
.model-sel:focus{outline:none;border-color:var(--g);}
/* ── Think Block (reasoning display) ── */
.think-block{background:rgba(0,212,255,.04);border:1px solid rgba(0,212,255,.18);
  border-radius:2px;margin:4px 0;overflow:hidden;}
.think-summary{font-family:var(--mono);font-size:8px;color:var(--cy);padding:4px 8px;
  cursor:pointer;display:flex;align-items:center;gap:5px;
  border-bottom:1px solid rgba(0,212,255,.1);list-style:none;}
.think-summary::before{content:'▶';font-size:7px;transition:.2s;}
details[open] .think-summary::before{content:'▼';}
.think-content{font-family:var(--mono);font-size:9px;color:rgba(0,212,255,.75);
  padding:7px 10px;line-height:1.6;white-space:pre-wrap;max-height:200px;overflow-y:auto;}
.think-content::-webkit-scrollbar{width:2px;}
.think-content::-webkit-scrollbar-thumb{background:rgba(0,212,255,.25);}
"""

HTML_LOGIN = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SENTINEL GUARD // AUTHENTICATE</title>
<style>{{ css }}
.lw{display:flex;align-items:center;justify-content:center;height:100vh;position:relative;z-index:2;}
.lbox{background:rgba(0,8,2,.97);border:1px solid var(--bhi);border-radius:3px;
  padding:30px 28px;width:370px;box-shadow:var(--glow),inset 0 0 50px rgba(0,255,65,.02);}
.lpre{font-family:var(--mono);font-size:8px;color:var(--td);text-align:center;
  margin-bottom:14px;line-height:2;letter-spacing:.5px;}
.lhex{font-size:32px;color:var(--g);text-shadow:var(--glow);text-align:center;}
.lname{font-family:var(--mono);font-size:13px;color:var(--g);letter-spacing:4px;
  text-shadow:var(--glow);animation:glitch 3s infinite;text-align:center;margin:6px 0 3px;}
.lsub{font-family:var(--mono);font-size:8px;color:var(--td);text-align:center;
  letter-spacing:1px;margin-bottom:14px;}
.lstat{display:flex;align-items:center;justify-content:center;gap:5px;
  font-family:var(--mono);font-size:8px;color:var(--g);margin-bottom:18px;}
.lstat::before{content:'';width:5px;height:5px;border-radius:50%;background:var(--g);
  box-shadow:var(--glow);animation:pulse 2s infinite;display:block;}
.lerr{background:rgba(255,23,68,.1);border:1px solid rgba(255,23,68,.3);color:var(--r);
  padding:7px 11px;border-radius:2px;font-family:var(--mono);font-size:9px;
  margin-bottom:10px;text-align:center;}
.lfield{display:flex;align-items:center;background:#020a03;border:1px solid var(--b);
  border-radius:2px;margin-bottom:10px;padding:0 10px;}
.lfield:focus-within{border-color:var(--g);box-shadow:var(--glow);}
.lprompt{font-family:var(--mono);font-size:9px;color:var(--g);white-space:nowrap;margin-left:8px;}
.lfield input{flex:1;background:transparent;border:none;outline:none;
  color:var(--t);padding:9px 0;font-family:var(--mono);font-size:11px;}
.lbtn{width:100%;background:transparent;border:1px solid var(--g);color:var(--g);
  padding:10px;border-radius:2px;font-family:var(--mono);font-size:10px;
  letter-spacing:3px;cursor:pointer;transition:.15s;margin-bottom:8px;}
.lbtn:hover{background:rgba(0,255,65,.09);box-shadow:var(--glow);}
.lfooter{font-family:var(--mono);font-size:7px;color:var(--td);
  text-align:center;margin-top:14px;line-height:2.2;}
</style></head>
<body><canvas id="mtx"></canvas>
<div class="lw"><div class="lbox">
  <div class="lpre">┌─────────────────────────────────────┐<br>│   SENTINEL GUARD // ACCESS CONTROL  │<br>└─────────────────────────────────────┘</div>
  <div class="lhex">⬡</div>
  <div class="lname">SENTINEL GUARD</div>
  <div class="lsub">TACTICAL SECURITY PLATFORM · AI POWERED</div>
  <div class="lstat">● SYSTEM ONLINE · AI CORE ACTIVE</div>
  {% if error %}<div class="lerr">⚠ ACCESS DENIED — {{ error }}</div>{% endif %}
  <form method="POST">
    <div class="lfield">
      <span class="lprompt">[root@sentinel ~]$</span>
      <input type="password" name="password" placeholder="AUTHENTICATE..." autofocus>
    </div>
    <button type="submit" class="lbtn">⬢ CONFIRM IDENTITY</button>
  </form>
  <div class="lfooter">POWERFUL TOOLS · REAL SKILLS · TOTAL CONTROL<br>
    ممنوع --privileged | ممنوع --net=host | السيادة كاملة لك</div>
</div></div>
<script>(function(){
  var c=document.getElementById('mtx'),ctx=c.getContext('2d');
  c.width=window.innerWidth;c.height=window.innerHeight;
  var cols=Math.floor(c.width/14),drops=[];
  for(var i=0;i<cols;i++)drops[i]=Math.random()*c.height;
  var ch='0123456789ABCDEF';
  function draw(){
    ctx.fillStyle='rgba(3,5,10,0.06)';ctx.fillRect(0,0,c.width,c.height);
    ctx.font='12px Courier New';
    for(var i=0;i<drops.length;i++){
      var b=Math.random()>.96;
      ctx.fillStyle=b?'#ffffff':'#00ff41';ctx.globalAlpha=b?.85:.42;
      ctx.fillText(ch[Math.floor(Math.random()*ch.length)],i*14,drops[i]);
      ctx.globalAlpha=1;
      if(drops[i]>c.height&&Math.random()>.975)drops[i]=0;
      drops[i]+=14;
    }
  }
  setInterval(draw,55);
})();</script></body></html>"""

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SENTINEL GUARD // TACTICAL</title>
<style>{{ css }}</style></head>
<body>
<canvas id="mtx"></canvas>
<div class="root">

<!-- SIDEBAR -->
<nav class="sidebar">
  <div class="sb-head">
    <div class="sb-hex">⬡</div>
    <div class="sb-name">SENTINEL</div>
    <div class="sb-ver">v2.0 · TACTICAL · AI POWERED</div>
    <div class="sb-online">SYSTEM ONLINE</div>
  </div>
  <div class="nav-grp">
    <div class="nav-lbl">// MODULES</div>
    <button class="nav-btn active" onclick="navTo('overview',this)">◈ نظرة عامة</button>
    <button class="nav-btn" onclick="navTo('radar',this)">⊕ الرادار</button>
    <button class="nav-btn" onclick="navTo('dockerfile',this)">🐳 Dockerfile</button>
    <button class="nav-btn" onclick="navTo('api',this)">📡 API</button>
  </div>
  <div class="nav-grp">
    <div class="nav-lbl">// QUICK ASK</div>
    <button class="nav-btn" onclick="quickAsk('اشرح نتائج آخر فحص')">▸ نتائج الفحص</button>
    <button class="nav-btn" onclick="quickAsk('ما أهم ثغرة يجب إصلاحها؟')">▸ أولوية الإصلاح</button>
    <button class="nav-btn" onclick="quickAsk('كيف أحمي Docker container؟')">▸ أمن Docker</button>
    <button class="nav-btn" onclick="quickAsk('شرح OWASP Top 10 بالعربي')">▸ OWASP Top 10</button>
    <button class="nav-btn" onclick="quickAsk('كيف أفحص المنافذ بـ Nmap؟')">▸ Nmap scan</button>
    <button class="nav-btn" onclick="quickAsk('ما هي أخطر ثغرات Docker؟')">▸ ثغرات Docker</button>
  </div>
  <div class="sb-foot">
    <div class="sb-row"><span class="sk">PRIV:</span><span class="sv r">RESTRICTED</span></div>
    <div class="sb-row"><span class="sk">NET:</span><span class="sv">ISOLATED</span></div>
    <div class="sb-row"><span class="sk">AI:</span><span class="sv">ONLINE</span></div>
    <div class="sb-row"><span class="sk">MODE:</span><span class="sv">SOVEREIGN</span></div>
    <div style="margin-top:8px;border-top:1px solid var(--b);padding-top:6px;">
      <a href="/logout" style="font-family:var(--mono);font-size:8px;color:var(--r);text-decoration:none;">⬡ LOGOUT</a>
    </div>
  </div>
</nav>

<!-- MAIN -->
<div class="main">
<div class="mscroll">

  <!-- Top Bar -->
  <div class="topbar">
    <div class="tb-left">
      <h1>SENTINEL GUARD</h1>
      <p id="update-time">// لوحة التحكم الأمنية · جارٍ التحميل…</p>
    </div>
    <div class="tb-right">
      <div class="gauge-wrap">
        <svg viewBox="0 0 70 70">
          <circle cx="35" cy="35" r="28" fill="none" stroke="rgba(0,255,65,.1)" stroke-width="7"/>
          <circle id="gauge-arc" cx="35" cy="35" r="28" fill="none" stroke="#ffaa00"
            stroke-width="7" stroke-dasharray="175.9" stroke-dashoffset="44"
            stroke-linecap="round" transform="rotate(-90 35 35)"/>
        </svg>
        <div class="gauge-center">
          <div class="gauge-num" id="gauge-num">75</div>
          <div class="gauge-lbl">THREAT</div>
        </div>
      </div>
      <div class="tb-time" id="tb-clock">--:--:--</div>
    </div>
  </div>

  <!-- Stats -->
  <div class="stats">
    <div class="stat">
      <div class="stat-lbl">TOTAL SCANS</div>
      <div class="stat-val" id="st-total">—</div>
      <div class="stat-sub">إجمالي الفحوصات</div>
    </div>
    <div class="stat">
      <div class="stat-lbl">CRITICAL</div>
      <div class="stat-val" style="color:var(--r);text-shadow:var(--glow-r)" id="st-crit">—</div>
      <div class="stat-sub">ثغرات حرجة</div>
    </div>
    <div class="stat">
      <div class="stat-lbl">RISK SCORE</div>
      <div class="stat-val" style="color:var(--am);text-shadow:var(--glow-am)" id="st-risk">—</div>
      <div class="stat-sub">متوسط الخطر / 100</div>
    </div>
    <div class="stat">
      <div class="stat-lbl">ASSETS</div>
      <div class="stat-val" style="color:var(--cy);text-shadow:var(--glow-c)" id="st-assets">—</div>
      <div class="stat-sub">أصول موثّقة</div>
    </div>
  </div>

  <!-- SEC: OVERVIEW -->
  <div id="sec-overview" style="display:flex;flex-direction:column;gap:10px">

    <div class="panel">
      <div class="panel-hdr">
        <span class="panel-title">NETWORK RADAR — HACKER'S EYE</span>
        <span class="pbadge on" id="radar-badge">● SCANNING</span>
      </div>
      <div class="radar-grid">
        <div style="display:flex;align-items:center;justify-content:center;">
          <svg id="radar" viewBox="0 0 300 300" width="272" height="272">
            <defs>
              <radialGradient id="bgfill" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="rgba(0,255,65,0.04)"/>
                <stop offset="100%" stop-color="rgba(0,0,0,0)"/>
              </radialGradient>
              <filter id="gf">
                <feGaussianBlur stdDeviation="1.5" result="b"/>
                <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
            </defs>
            <circle cx="150" cy="150" r="140" fill="url(#bgfill)"/>
            <circle cx="150" cy="150" r="35" fill="none" stroke="rgba(0,255,65,.12)" stroke-width="1"/>
            <circle cx="150" cy="150" r="70" fill="none" stroke="rgba(0,255,65,.14)" stroke-width="1"/>
            <circle cx="150" cy="150" r="105" fill="none" stroke="rgba(0,255,65,.16)" stroke-width="1"/>
            <circle cx="150" cy="150" r="140" fill="none" stroke="rgba(0,255,65,.28)" stroke-width="1.5"/>
            <line x1="150" y1="10" x2="150" y2="290" stroke="rgba(0,255,65,.1)" stroke-width="1"/>
            <line x1="10" y1="150" x2="290" y2="150" stroke="rgba(0,255,65,.1)" stroke-width="1"/>
            <line x1="51" y1="51" x2="249" y2="249" stroke="rgba(0,255,65,.05)" stroke-width="1"/>
            <line x1="249" y1="51" x2="51" y2="249" stroke="rgba(0,255,65,.05)" stroke-width="1"/>
            <text x="150" y="15" fill="#00ff41" font-size="9" text-anchor="middle" font-family="Courier New" opacity=".7">N</text>
            <text x="286" y="154" fill="#00ff41" font-size="9" text-anchor="start" font-family="Courier New" opacity=".7">E</text>
            <text x="150" y="291" fill="#00ff41" font-size="9" text-anchor="middle" font-family="Courier New" opacity=".7">S</text>
            <text x="8" y="154" fill="#00ff41" font-size="9" text-anchor="end" font-family="Courier New" opacity=".7">W</text>
            <text x="222" y="38" fill="#00ff41" font-size="7" text-anchor="middle" font-family="Courier New" opacity=".4">30</text>
            <text x="264" y="80" fill="#00ff41" font-size="7" text-anchor="middle" font-family="Courier New" opacity=".4">60</text>
            <text x="264" y="225" fill="#00ff41" font-size="7" text-anchor="middle" font-family="Courier New" opacity=".4">120</text>
            <text x="78" y="267" fill="#00ff41" font-size="7" text-anchor="middle" font-family="Courier New" opacity=".4">210</text>
            <text x="36" y="80" fill="#00ff41" font-size="7" text-anchor="middle" font-family="Courier New" opacity=".4">300</text>
            <g id="rs">
              <path d="M150,150 L290,150 A140,140 0 0,0 150,10 Z" fill="#00ff41" fill-opacity=".1"/>
              <line x1="150" y1="150" x2="290" y2="150" stroke="#00ff41" stroke-width="2.5" filter="url(#gf)" opacity=".9"/>
              <circle cx="290" cy="150" r="3" fill="#ffffff" opacity=".7"/>
            </g>
            <g id="radar-targets"></g>
            <circle cx="150" cy="150" r="4" fill="#00ff41" filter="url(#gf)"/>
            <circle cx="150" cy="150" r="9" fill="none" stroke="#00ff41" stroke-width="1" opacity=".4"/>
          </svg>
        </div>
        <div class="rtable">
          <div class="rhead"><span>IP ADDRESS</span><span>PORT</span><span>SERVICE</span></div>
          <div id="radar-list"><div class="rempty">// انتظار بيانات…</div></div>
          <div class="rnmap">
            <div class="cmd">$ nmap -sS -sV -T4 -A target</div>
            <div style="margin-top:4px"><span class="dim">[ </span><span class="out" id="nmap-bar">●●●●●●●●</span><span class="dim"> ] SCANNING…</span></div>
            <div style="margin-top:4px;font-size:8px;color:var(--td)" id="nmap-done"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-hdr">
        <span class="panel-title">SECURITY FINDINGS</span>
        <span class="pbadge">LIVE</span>
      </div>
      <div id="findings-list">
        <div style="color:var(--td);font-family:var(--mono);font-size:10px;padding:20px;text-align:center">// جارٍ التحميل…</div>
      </div>
    </div>
  </div>

  <!-- SEC: RADAR -->
  <div id="sec-radar" style="display:none;flex-direction:column;gap:10px">
    <div class="panel">
      <div class="panel-hdr">
        <span class="panel-title">NMAP — THE HACKER'S RADAR</span>
        <span class="pbadge on">● ACTIVE</span>
      </div>
      <p style="font-family:var(--mono);font-size:9px;color:var(--td);margin-bottom:10px">SEE EVERYTHING. MISS NOTHING.</p>
      <div class="scan-row">
        <input class="sinp" id="nmap-target" placeholder="target IP / domain…">
        <button class="btn-tac" onclick="quickAsk('كيف أفحص ' + document.getElementById('nmap-target').value + ' بـ Nmap؟')">⬢ إرشادات Nmap</button>
      </div>
      <div style="font-family:var(--mono);font-size:9px;color:var(--td);
        background:#020903;border:1px solid var(--b);border-radius:2px;padding:10px;line-height:2.2">
        <div style="color:var(--g);margin-bottom:4px">// أوامر Nmap الأساسية</div>
        <div>nmap -sS -sV -T4 -A &lt;target&gt; &nbsp;→ فحص شامل</div>
        <div>nmap -p- &lt;target&gt; &nbsp;→ كل المنافذ 0-65535</div>
        <div>nmap --script=vuln &lt;target&gt; &nbsp;→ فحص الثغرات</div>
        <div>nmap -sU --top-ports 20 &lt;target&gt; &nbsp;→ UDP scan</div>
        <div>nmap -oA results &lt;target&gt; &nbsp;→ حفظ النتائج</div>
        <div style="color:var(--am);margin-top:6px">// على أصولك المملوكة فقط — السيادة كاملة لك</div>
      </div>
    </div>
  </div>

  <!-- SEC: DOCKERFILE -->
  <div id="sec-dockerfile" style="display:none;flex-direction:column;gap:10px">
    <div class="panel">
      <div class="panel-hdr">
        <span class="panel-title">DOCKERFILE SECURITY SCANNER</span>
        <span class="pbadge">AI + RULES</span>
      </div>
      <div class="scan-row">
        <input class="sinp" id="df-url" placeholder="رابط أو مسار Dockerfile…">
        <button class="btn-tac" onclick="scanDockerfile()">⬢ فحص الآن</button>
      </div>
      <div id="df-result"></div>
    </div>
  </div>

  <!-- SEC: API -->
  <div id="sec-api" style="display:none;flex-direction:column;gap:10px">
    <div class="panel">
      <div class="panel-hdr">
        <span class="panel-title">API ENDPOINTS</span>
        <span class="pbadge">REST · FastAPI</span>
      </div>
      <div style="font-family:var(--mono);font-size:10px;background:#020903;
        border:1px solid var(--b);border-radius:2px;padding:12px;line-height:2.4;color:var(--cy)">
        POST &nbsp;/api/v1/auth/login &nbsp;&nbsp;→ JWT token<br>
        POST &nbsp;/api/v1/assets &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→ إضافة أصل<br>
        POST &nbsp;/api/v1/scans &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→ طلب فحص<br>
        GET &nbsp;&nbsp;/api/v1/scans/{id} &nbsp;&nbsp;→ نتيجة الفحص<br>
        GET &nbsp;&nbsp;/api/v1/scans/{id}/sarif &nbsp;→ SARIF 2.1.0<br>
        POST /api/v1/scans/{id}/findings/{fid}/fix &nbsp;→ AutoFixer
      </div>
      <div style="margin-top:8px">
        <a href="{{ sentinel_api | replace('/api/v1','') }}/docs"
          target="_blank" class="btn-tac" style="display:inline-block;text-decoration:none;margin-top:4px">
          ⬢ Swagger UI
        </a>
      </div>
    </div>
  </div>

</div><!-- /mscroll -->

<!-- Status Bar -->
<div class="statusbar">
  <div class="sbi on"><span class="si">📡</span>RECON ACTIVE</div>
  <span class="sbsep">|</span>
  <div class="sbi"><span class="si">⊕</span>DISCOVER EVERYTHING</div>
  <span class="sbsep">|</span>
  <div class="sbi"><span class="si">⊛</span>ENUMERATE DEEPER</div>
  <span class="sbsep">|</span>
  <div class="sbi on"><span class="si">></span>EXPLOIT NOT TODAY</div>
  <span class="sbsep">|</span>
  <div class="sb-motto">KNOWLEDGE IS POWER. RECON IS CONTROL.</div>
  <div class="sbi warn"><span class="si">☠</span></div>
</div>
</div><!-- /main -->

<!-- TERMINAL (الأمين AI) -->
<aside class="terminal">
  <div class="t-hdr">
    <div>
      <div class="t-htitle">// AMEEN AI CORE · DeepSeek-V4</div>
      <div class="t-bknd" id="t-backend">{{ backend }}</div>
    </div>
    <div class="t-hstatus"><span class="t-dot"></span>ACTIVE</div>
  </div>

  <!-- Model + Thinking Mode Bar -->
  <div class="think-bar">
    <select class="model-sel" id="model-sel" title="اختر النموذج">
      <option value="deepseek-v4-flash">⚡ V4-Flash (1M)</option>
      <option value="deepseek-v4-pro">🧠 V4-Pro (Deep)</option>
      <option value="granite-nano">🔧 Granite (Fix)</option>
      <option value="mimo-pro">🔬 MiMo (Reason)</option>
      <option value="deepseek-v3">💾 V3 (Fallback)</option>
    </select>
    <span class="think-lbl">THINK:</span>
    <button class="think-btn active" id="tm-off"  onclick="setThinkMode('non-think',this)">OFF</button>
    <button class="think-btn"        id="tm-high" onclick="setThinkMode('think-high',this)">HIGH</button>
    <button class="think-btn"        id="tm-max"  onclick="setThinkMode('think-max',this)">MAX ★</button>
  </div>

  <div class="t-body" id="tlog">
    <div class="tline">
      <span class="tp">[AMEEN]</span>
      <span class="to ai">مرحباً — أنا الأمين. اسألني عن أي ثغرة أو أداة أمنية.</span>
    </div>
    <div class="tline">
      <span class="tp">[SYS]</span>
      <span class="to" style="color:var(--td)">قاعدة المعرفة: {{ kb_count }} ملف · DeepSeek-V4 · السيادة: مُفعَّلة</span>
    </div>
  </div>
  <div class="t-inp-row">
    <span class="t-plbl">[USER]$</span>
    <input class="t-inp" id="t-inp" placeholder="اسألني…" onkeydown="handleKey(event)">
    <span class="t-cursor"></span>
  </div>
</aside>

</div><!-- /root -->

<script>
// Matrix Rain
(function(){
  var c=document.getElementById('mtx'),ctx=c.getContext('2d');
  function resize(){c.width=window.innerWidth;c.height=window.innerHeight;}
  resize();window.addEventListener('resize',resize);
  var ch='0123456789ABCDEF',drops=[];
  function init(){drops=[];var cols=Math.floor(c.width/14);
    for(var i=0;i<cols;i++)drops[i]=Math.random()*c.height;}
  init();window.addEventListener('resize',init);
  function draw(){
    ctx.fillStyle='rgba(3,5,10,0.055)';ctx.fillRect(0,0,c.width,c.height);
    ctx.font='12px Courier New';
    for(var i=0;i<drops.length;i++){
      var b=Math.random()>.96;
      ctx.fillStyle=b?'#ffffff':'#00ff41';ctx.globalAlpha=b?.8:.42;
      ctx.fillText(ch[Math.floor(Math.random()*ch.length)],i*14,drops[i]);
      ctx.globalAlpha=1;
      if(drops[i]>c.height&&Math.random()>.975)drops[i]=0;
      drops[i]+=14;
    }
  }
  setInterval(draw,55);
})();

// Clock
setInterval(function(){
  document.getElementById('tb-clock').textContent=new Date().toLocaleTimeString('ar');
},1000);

// Radar Targets
var _demoTargets=[
  {ip:'192.168.1.1',angle:45,r:70,svc:'http',port:'80'},
  {ip:'10.0.0.5',angle:130,r:105,svc:'rdp',port:'3389'},
  {ip:'172.16.5.23',angle:220,r:85,svc:'ssh',port:'22'},
  {ip:'203.0.113.10',angle:310,r:120,svc:'https',port:'443'},
  {ip:'8.8.8.8',angle:180,r:55,svc:'dns',port:'53'},
];

function setRadarTargets(targets){
  var ns='http://www.w3.org/2000/svg';
  var g=document.getElementById('radar-targets');g.innerHTML='';
  var list=document.getElementById('radar-list');list.innerHTML='';
  targets.forEach(function(t){
    var rad=t.angle*Math.PI/180;
    var x=150+Math.cos(rad)*t.r,y=150+Math.sin(rad)*t.r;
    var col=t.svc==='rdp'||t.svc==='ftp'?'#ff9100':'#00d4ff';
    function el(tag,attrs){
      var e=document.createElementNS(ns,tag);
      Object.entries(attrs).forEach(function(a){e.setAttribute(a[0],a[1]);});return e;
    }
    g.appendChild(el('circle',{cx:x,cy:y,r:8,fill:'none',stroke:col,'stroke-width':1,opacity:.5}));
    g.appendChild(el('circle',{cx:x,cy:y,r:3,fill:col,filter:'url(#gf)'}));
    g.appendChild(el('line',{x1:x-9,y1:y,x2:x+9,y2:y,stroke:col,'stroke-width':.8,opacity:.8}));
    g.appendChild(el('line',{x1:x,y1:y-9,x2:x,y2:y+9,stroke:col,'stroke-width':.8,opacity:.8}));
    var lbl=el('text',{x:x+11,y:y+3,fill:col,'font-size':7,'font-family':'Courier New'});
    lbl.textContent=t.ip;g.appendChild(lbl);
    var row=document.createElement('div');row.className='rrow';
    row.innerHTML='<span class="rip">'+t.ip+'</span><span class="rport">'+
      (t.port||'?')+'</span><span class="rsvc">'+t.svc+'</span>';
    list.appendChild(row);
  });
  document.getElementById('nmap-done').textContent=
    'NMAP DONE: '+targets.length+' HOSTS UP — '+new Date().toLocaleTimeString('ar');
}
setRadarTargets(_demoTargets);

// Nmap bar animation
var _bars=['●●●●●●●●','●●●●●●●○','●●●●●●○○','●●●●●○○○','●●●●○○○○'];
var _bi=0;setInterval(function(){_bi=(_bi+1)%_bars.length;
  document.getElementById('nmap-bar').textContent=_bars[_bi];},600);

// Navigation
var _secs=['overview','radar','dockerfile','api'];
function navTo(name,btn){
  document.querySelectorAll('.nav-btn').forEach(function(b){b.classList.remove('active');});
  btn.classList.add('active');
  _secs.forEach(function(s){
    var el=document.getElementById('sec-'+s);
    if(el)el.style.display=s===name?'flex':'none';
  });
}

// API Stats
var API='{{ sentinel_api }}';
var tok=localStorage.getItem('sentinel_token')||'';
var authH=tok?{Authorization:'Bearer '+tok}:{};

async function loadStats(){
  try{
    var r1=await fetch(API+'/scans',{headers:authH}).catch(function(){return null;});
    var r2=await fetch(API+'/assets',{headers:authH}).catch(function(){return null;});
    var scans=r1&&r1.ok?await r1.json():[];
    var assets=r2&&r2.ok?await r2.json():[];
    document.getElementById('st-total').textContent=scans.length||0;
    document.getElementById('st-assets').textContent=assets.length||0;
    var crit=0,rsum=0;
    (scans||[]).forEach(function(s){
      crit+=(s.finding_counts&&s.finding_counts.critical||0);
      rsum+=(s.risk_score||0);
    });
    document.getElementById('st-crit').textContent=crit;
    var risk=scans.length?(rsum/scans.length).toFixed(0):0;
    document.getElementById('st-risk').textContent=risk;
    var arc=document.getElementById('gauge-arc');
    var num=document.getElementById('gauge-num');
    arc.setAttribute('stroke-dashoffset',175.9*(1-risk/100));
    num.textContent=risk;
    var col=risk>70?'#ff1744':risk>40?'#ffaa00':'#00ff41';
    arc.setAttribute('stroke',col);num.style.color=col;
    document.getElementById('update-time').textContent=
      '// آخر تحديث: '+new Date().toLocaleTimeString('ar');
    renderFindings(scans);
    if(scans.length){
      setRadarTargets((scans||[]).slice(0,5).map(function(s,i){
        return {ip:(s.asset_value||'asset-'+i),angle:i*72,r:40+i*20,
          svc:(s.scan_type||'?'),port:'—'};
      }));
    }
  }catch(e){}
}

function renderFindings(scans){
  var el=document.getElementById('findings-list');
  var rows=[];
  (scans||[]).forEach(function(s){
    Object.entries(s.finding_counts||{}).forEach(function(entry){
      var sev=entry[0],cnt=entry[1];
      rows.push('<div class="frow"><span class="fbadge fb-'+sev+'">'+sev+'</span>'+
        '<div><div class="ftitle">'+cnt+' ثغرة · '+sev+'</div>'+
        '<div class="fdesc">Scan '+(s.id||'').slice(0,8)+'… · '+(s.scan_type||'')+'</div></div></div>');
    });
  });
  el.innerHTML=rows.length?rows.slice(0,8).join(''):
    '<div style="color:var(--td);font-family:var(--mono);font-size:10px;padding:18px;text-align:center">'+
    '// NO FINDINGS — SYSTEM CLEAN</div>';
}

// Dockerfile Scanner
async function scanDockerfile(){
  var url=document.getElementById('df-url').value.trim();if(!url)return;
  var el=document.getElementById('df-result');
  el.innerHTML='<div class="tline"><span class="tp">[SCAN]</span><span class="to">جارٍ الفحص…</span></div>';
  try{
    var r=await fetch('/api/scan-dockerfile',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})});
    var data=await r.json();
    if(data.error){el.innerHTML='<div class="tline"><span class="tp">[ERR]</span><span class="to err">'+data.error+'</span></div>';return;}
    var all=(data.rule_findings||[]).concat(data.ai_findings||[]);
    el.innerHTML=!all.length?
      '<div class="frow"><span class="fbadge fb-low">CLEAN</span><span class="ftitle" style="margin-right:8px">✓ لم تُكتشف ثغرات</span></div>':
      all.map(function(f){return '<div class="frow"><span class="fbadge fb-'+f.severity+'">'+f.severity+'</span>'+
        '<div><div class="ftitle">'+f.title+'</div><div class="fdesc">'+f.description+'</div>'+
        (f.remediation?'<div class="ffix">▶ '+f.remediation+'</div>':'')+
        '</div></div>';}).join('');
  }catch(e){el.innerHTML='<div class="tline"><span class="to err">ERROR: '+e.message+'</span></div>';}
}

// ── AI Terminal — DeepSeek-V4 with Thinking Modes ──────────────────────────
var _history=[];
var _thinkMode='non-think';
var _modelKey='deepseek-v4-flash';

function setThinkMode(mode, btn){
  _thinkMode=mode;
  document.querySelectorAll('.think-btn').forEach(function(b){b.classList.remove('active');});
  btn.classList.add('active');
  var labels={'non-think':'⚡ سريع','think-high':'🧠 تفكير','think-max':'★ أقصى'};
  addLine('[SYS]','وضع التفكير: '+labels[mode],'');
}

document.getElementById('model-sel').addEventListener('change',function(){
  _modelKey=this.value;
  addLine('[SYS]','النموذج: '+this.options[this.selectedIndex].text,'');
});

function addLine(prompt,text,cls){
  var tlog=document.getElementById('tlog');
  var div=document.createElement('div');div.className='tline';
  div.innerHTML='<span class="tp">'+prompt+'</span><span class="to '+(cls||'')+'">'+
    text.replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</span>';
  tlog.appendChild(div);tlog.scrollTop=tlog.scrollHeight;return div;
}

function _renderThinkBlock(thinking, tlog){
  if(!thinking)return;
  var block=document.createElement('details');block.className='think-block';
  var summ=document.createElement('summary');summ.className='think-summary';
  summ.textContent='💭 تفكير الذكاء ('+thinking.split('\\n').length+' سطر) — انقر للعرض';
  var content=document.createElement('div');content.className='think-content';
  content.textContent=thinking;
  block.appendChild(summ);block.appendChild(content);
  tlog.appendChild(block);tlog.scrollTop=tlog.scrollHeight;
}

function _parseThinking(text){
  var re=/<think>([\s\S]*?)<\/think>/i;
  var m=text.match(re);
  var thinking=m?m[1].trim():'';
  var answer=text.replace(/<think>[\s\S]*?<\/think>/gi,'').trim();
  return{thinking:thinking,answer:answer};
}

function quickAsk(text){document.getElementById('t-inp').value=text;sendMsg();}
function handleKey(e){if(e.key==='Enter')sendMsg();}

async function sendMsg(){
  var inp=document.getElementById('t-inp');
  var text=inp.value.trim();if(!text)return;
  inp.value='';
  addLine('[USER]',text,'');
  _history.push({role:'user',content:text});
  var tlog=document.getElementById('tlog');
  var aiDiv=addLine('[AMEEN]','','ai');
  var aiSpan=aiDiv.querySelector('.to');
  aiSpan.textContent='…';
  if(_thinkMode!=='non-think'){
    aiSpan.textContent='🧠 جارٍ التفكير…';
  }
  try{
    var resp=await fetch('/api/chat',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        message:text,
        history:_history.slice(-6),
        thinking_mode:_thinkMode,
        model_key:_modelKey
      })});
    var reader=resp.body.getReader(),decoder=new TextDecoder();
    aiSpan.textContent='';var full='';
    while(true){
      var rd=await reader.read();if(rd.done)break;
      decoder.decode(rd.value).split('\\n').forEach(function(line){
        if(!line.startsWith('data: '))return;
        var d=line.slice(6).trim();if(d==='[DONE]')return;
        try{
          var p=JSON.parse(d);
          if(p.delta){
            full+=p.delta;
            // أثناء الـ streaming: اعرض النص كاملاً (بما فيه <think>)
            aiSpan.textContent=full.length>300?'…'+full.slice(-300):full;
          }
        }catch(ex){}
      });
      tlog.scrollTop=tlog.scrollHeight;
    }
    // بعد اكتمال الـ stream: فصل الـ thinking عن الجواب
    var parsed=_parseThinking(full);
    aiDiv.remove();  // أزل الـ div المؤقت
    if(parsed.thinking){
      _renderThinkBlock(parsed.thinking,tlog);
    }
    var finalDiv=addLine('[AMEEN]',parsed.answer||full,'ai');
    if(_history.length>0)_history.push({role:'assistant',content:parsed.answer||full});
  }catch(e){
    aiSpan.textContent='⚠ خطأ: '+e.message;
    aiSpan.className='to err';
  }
}

loadStats();
setInterval(loadStats,30000);
</script>
</body></html>"""

# ─────────────────────────────────────────────────────────────────────────────
# Flask Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    ip = request.remote_addr or "0.0.0.0"
    error = None
    if request.method == "POST":
        if _locked(ip):
            error = "محاولات كثيرة — انتظر 5 دقائق"
        elif _ok(request.form.get("password", "")):
            session["ok"] = True
            _hits.pop(ip, None)
            return redirect(url_for("dashboard"))
        else:
            _fail(ip)
            error = "كلمة السر خاطئة"
    return render_template_string(HTML_LOGIN, css=_CSS, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    kb_count = len(glob.glob(
        os.path.join(os.path.dirname(__file__), "knowledge", "kali-tools", "*.md")
    ))
    return render_template_string(
        HTML_DASHBOARD,
        css=_CSS,
        sentinel_api=SENTINEL_API,
        backend=_active_backend(),
        kb_count=kb_count,
    )


@app.route("/api/chat", methods=["POST"])
@login_required
def chat_stream():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", ""))[:2000]
    history = data.get("history", [])
    thinking_mode = data.get("thinking_mode", "non-think")
    model_key = data.get("model_key") or None
    # التحقق من القيم المسموحة فقط
    if thinking_mode not in ("non-think", "think-high", "think-max"):
        thinking_mode = "non-think"
    return Response(
        stream_with_context(_ai_stream(message, history, thinking_mode, model_key)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/api/ai-status")
@login_required
def ai_status():
    return jsonify({
        "backend": _active_backend(),
        "gemini": bool(GEMINI_KEY),
        "models": list(AVAILABLE_MODELS.keys()),
        "thinking_modes": ["non-think", "think-high", "think-max"],
    })


@app.route("/api/models")
@login_required
def list_models():
    """يُعيد النماذج المُعرَّفة + يحاول الاستعلام عن Docker Model Runner."""
    available = []
    try:
        from openai import OpenAI
        client = OpenAI(base_url=MODEL_URL, api_key="unused")
        resp = client.models.list()
        available = [m.id for m in resp.data]
    except Exception:
        pass
    return jsonify({
        "configured": AVAILABLE_MODELS,
        "runner_available": available,
    })


@app.route("/api/scan-dockerfile", methods=["POST"])
@login_required
def api_scan_dockerfile():
    import asyncio, sys
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", ""))[:1000]
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sentinel-guard"))
        from app.services.scanner.dockerfile_scanner import DockerfileScanner
        result = asyncio.run(DockerfileScanner().scan(url))
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "rule_findings": [], "ai_findings": []}), 500


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"\n[SENTINEL] ● Dashboard    : http://localhost:{port}")
    print(f"[SENTINEL] ● AI Backend   : {_active_backend()}")
    print(f"[SENTINEL] ● Knowledge    : {len(_KNOWLEDGE.split(chr(10)))} lines")
    print(f"[SENTINEL] ● Sovereignty  : --privileged BLOCKED | --net=host BLOCKED\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
