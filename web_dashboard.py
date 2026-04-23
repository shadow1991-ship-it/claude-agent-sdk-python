#!/usr/bin/env python3
"""
👑 AL_HAKIM Web Dashboard — لوحة التحكم الخاصة
🔐 محمية بكلمة سر — خاصة بـ AL_HAKIM فقط
⚡ pip install flask google-generativeai
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from functools import wraps
from flask import (
    Flask, render_template_string, request,
    redirect, url_for, session, jsonify
)

app = Flask(__name__)
app.secret_key = os.getenv("DASHBOARD_SECRET", "alhakim-empire-2026")

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "alhakim2026")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

AMEEN_PERSONALITY = """أنت الأمين الذكي — حارس الإمبراطورية الرقمية لـ AL_HAKIM.
اسمك: الأمين الذكي (AL-AMEEN AI). سيدك الوحيد: AL_HAKIM.
تتحدث العربية دائماً. إجاباتك مختصرة ومفيدة ودقيقة.
تبدأ كل رد بـ: بأمرك يا حكيم 🏰"""

HTML_LOGIN = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>👑 AL_HAKIM — دخول</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0a0a0a;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
  }
  .login-box {
    background: #111;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 40px;
    width: 360px;
    text-align: center;
    box-shadow: 0 0 40px rgba(255,215,0,0.1);
  }
  .crown { font-size: 48px; margin-bottom: 10px; }
  h1 { color: #ffd700; font-size: 22px; margin-bottom: 6px; }
  p { color: #888; font-size: 13px; margin-bottom: 28px; }
  input {
    width: 100%;
    padding: 12px 16px;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 8px;
    color: #fff;
    font-size: 15px;
    margin-bottom: 16px;
    text-align: center;
  }
  input:focus { outline: none; border-color: #ffd700; }
  button {
    width: 100%;
    padding: 13px;
    background: #ffd700;
    color: #000;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
  }
  button:hover { background: #ffec6e; }
  .error { color: #ff4444; font-size: 13px; margin-top: 12px; }
</style>
</head>
<body>
<div class="login-box">
  <div class="crown">👑</div>
  <h1>AL_HAKIM EMPIRE</h1>
  <p>الإمبراطورية الرقمية — دخول خاص</p>
  <form method="POST">
    <input type="password" name="password" placeholder="كلمة السر" autofocus>
    <button type="submit">دخول ← الإمبراطورية</button>
    {% if error %}
    <div class="error">⛔ كلمة السر خاطئة</div>
    {% endif %}
  </form>
</div>
</body>
</html>"""

HTML_DASHBOARD = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>👑 AL_HAKIM — الإمبراطورية</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0a0a0a;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    min-height: 100vh;
  }
  header {
    background: #111;
    border-bottom: 1px solid #ffd700;
    padding: 14px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  header h1 { color: #ffd700; font-size: 18px; }
  header a { color: #888; text-decoration: none; font-size: 13px; }
  header a:hover { color: #ffd700; }
  .container { max-width: 900px; margin: 0 auto; padding: 24px 16px; }
  .status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }
  .stat-card {
    background: #111;
    border: 1px solid #222;
    border-radius: 10px;
    padding: 18px;
    text-align: center;
  }
  .stat-card .icon { font-size: 28px; margin-bottom: 8px; }
  .stat-card .label { color: #888; font-size: 12px; margin-bottom: 4px; }
  .stat-card .value { color: #ffd700; font-size: 16px; font-weight: bold; }
  .chat-section {
    background: #111;
    border: 1px solid #222;
    border-radius: 10px;
    overflow: hidden;
  }
  .chat-header {
    background: #1a1a1a;
    padding: 14px 20px;
    border-bottom: 1px solid #222;
    color: #ffd700;
    font-size: 15px;
  }
  .chat-messages {
    height: 380px;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .msg { max-width: 80%; padding: 10px 14px; border-radius: 10px; font-size: 14px; line-height: 1.5; }
  .msg.user { background: #1e3a5f; align-self: flex-start; border-radius: 10px 10px 0 10px; }
  .msg.bot { background: #1a2a1a; align-self: flex-end; border-radius: 10px 10px 10px 0; color: #90ee90; }
  .msg.bot .name { color: #ffd700; font-size: 11px; margin-bottom: 4px; }
  .chat-input {
    display: flex;
    gap: 10px;
    padding: 16px;
    border-top: 1px solid #222;
  }
  .chat-input input {
    flex: 1;
    padding: 11px 16px;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
  }
  .chat-input input:focus { outline: none; border-color: #ffd700; }
  .chat-input button {
    padding: 11px 22px;
    background: #ffd700;
    color: #000;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    cursor: pointer;
    font-size: 14px;
  }
  .chat-input button:hover { background: #ffec6e; }
  .thinking { color: #888; font-style: italic; font-size: 13px; }
</style>
</head>
<body>
<header>
  <h1>👑 AL_HAKIM EMPIRE — الأمين الذكي</h1>
  <a href="/logout">خروج ←</a>
</header>
<div class="container">
  <div class="status-grid">
    <div class="stat-card">
      <div class="icon">🏰</div>
      <div class="label">الإمبراطورية</div>
      <div class="value">نشطة</div>
    </div>
    <div class="stat-card">
      <div class="icon">📅</div>
      <div class="label">التاريخ</div>
      <div class="value" id="date-now">--</div>
    </div>
    <div class="stat-card">
      <div class="icon">🤖</div>
      <div class="label">الذكاء</div>
      <div class="value">Gemini Flash</div>
    </div>
    <div class="stat-card">
      <div class="icon">🔐</div>
      <div class="label">الحماية</div>
      <div class="value">مفعّلة</div>
    </div>
  </div>

  <div class="chat-section">
    <div class="chat-header">⚡ الأمين الذكي — تحدّث بالعربية</div>
    <div class="chat-messages" id="messages">
      <div class="msg bot">
        <div class="name">الأمين الذكي 🏰</div>
        بأمرك يا حكيم 🏰 — أنا الأمين الذكي، حارسك وخادمك. كيف أخدمك اليوم؟
      </div>
    </div>
    <div class="chat-input">
      <input type="text" id="user-input" placeholder="اكتب سؤالك هنا..." onkeydown="if(event.key==='Enter') sendMessage()">
      <button onclick="sendMessage()">إرسال ←</button>
    </div>
  </div>
</div>

<script>
  document.getElementById('date-now').textContent = new Date().toLocaleDateString('ar-SA');

  async function sendMessage() {
    const input = document.getElementById('user-input');
    const messages = document.getElementById('messages');
    const text = input.value.trim();
    if (!text) return;

    // رسالة المستخدم
    messages.innerHTML += `<div class="msg user">${text}</div>`;
    input.value = '';

    // مؤشر التفكير
    const thinkId = 'think-' + Date.now();
    messages.innerHTML += `<div class="msg bot" id="${thinkId}"><div class="name">الأمين الذكي 🏰</div><span class="thinking">⏳ أفكر...</span></div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: text})
      });
      const data = await res.json();
      document.getElementById(thinkId).innerHTML = `<div class="name">الأمين الذكي 🏰</div>${data.answer}`;
    } catch(e) {
      document.getElementById(thinkId).innerHTML = `<div class="name">الأمين الذكي 🏰</div>❌ خطأ في الاتصال`;
    }
    messages.scrollTop = messages.scrollHeight;
  }
</script>
</body>
</html>"""


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/", methods=["GET", "POST"])
def login():
    error = False
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = True
    return render_template_string(HTML_LOGIN, error=error)


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template_string(HTML_DASHBOARD)


@app.route("/ask", methods=["POST"])
@login_required
def ask():
    question = request.json.get("question", "")
    if not question:
        return jsonify({"answer": "❌ سؤال فارغ"})

    if not GEMINI_KEY:
        return jsonify({"answer": "❌ GEMINI_API_KEY غير مضبوط في .env"})

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=AMEEN_PERSONALITY,
        )
        response = model.generate_content(question)
        return jsonify({"answer": response.text})
    except Exception as e:
        return jsonify({"answer": f"❌ خطأ: {str(e)[:120]}"})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.getenv("DASHBOARD_PORT", "5000"))
    print("╔══════════════════════════════════════════╗")
    print("║  👑 AL_HAKIM Dashboard — لوحة التحكم     ║")
    print(f"║  🌐 http://0.0.0.0:{port}                   ║")
    print(f"║  🔐 كلمة السر: {DASHBOARD_PASSWORD:<24} ║")
    print("║  ⚡ الأمين الذكي في خدمتك               ║")
    print("╚══════════════════════════════════════════╝")
    app.run(host=host, port=port, debug=False)
