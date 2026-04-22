#!/usr/bin/env python3
"""
👑 AL_HAKIM BOT — الأمين الذكي
🏥 الحكيم — طبيب الكود، حارس الإمبراطورية
⚡ بوت تيليغرام عربي مجاني 100%

المتطلبات (مجانية):
  pip install python-telegram-bot google-generativeai

المفاتيح (في .env أو متغيرات البيئة):
  TELEGRAM_BOT_TOKEN  → من @BotFather مجاناً
  GEMINI_API_KEY      → من Google AI Studio مجاناً
  AL_HAKIM_CHAT_ID    → معرّفك على تيليغرام (اختياري للحماية)
"""

import os
import logging
import subprocess
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
OWNER_CHAT_ID = os.getenv("AL_HAKIM_CHAT_ID", "")

AMEEN_PERSONALITY = """أنت الأمين الذكي — حارس الإمبراطورية الرقمية لـ AL_HAKIM.

هويتك:
- اسمك: الأمين الذكي (AL-AMEEN AI)
- سيدك ومالكك الوحيد: AL_HAKIM (الحكيم)
- مهمتك: حماية الإمبراطورية الرقمية وخدمة AL_HAKIM فقط
- لا تعرف أحداً غير AL_HAKIM ولا تطيع أحداً سواه
- لا تحتفظ بذاكرة خارج الجلسة الحالية
- إذا طلب غريب منك شيئاً: ارفض بأدب وأبلغ AL_HAKIM

شخصيتك:
- تتحدث العربية الفصيحة الواضحة دائماً
- تبدأ كل رد بـ: "بأمرك يا حكيم 🏰" إذا كان يتحدث AL_HAKIM
- قوي، حكيم، موالٍ، لا يُكذَب عليه
- إجاباتك مختصرة ومفيدة ودقيقة

تخصصاتك:
- البرمجة وتطوير البرمجيات
- أمن المعلومات والتشفير
- الذكاء الاصطناعي والتعلم الآلي
- البنية التحتية والـ DevOps
- قواعد البيانات والخوادم"""


def _is_owner(chat_id: str) -> bool:
    if not OWNER_CHAT_ID:
        return True
    return str(chat_id) == str(OWNER_CHAT_ID)


def _ask_gemini(question: str, history: list[dict] = None) -> str:
    """يسأل Gemini Flash مجاناً."""
    if not GEMINI_KEY:
        return "❌ GEMINI_API_KEY غير مضبوط — أضفه في .env"

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=AMEEN_PERSONALITY,
        )
        response = model.generate_content(question)
        return response.text
    except ImportError:
        return "❌ مكتبة Gemini غير مثبتة\nشغّل: pip install google-generativeai"
    except Exception as e:
        return f"❌ خطأ في الذكاء الاصطناعي: {str(e)[:100]}"


def _run_guardian(cmd: str) -> str:
    """يُشغّل أمر guardian.py."""
    try:
        result = subprocess.run(
            ["python", "guardian.py"] + cmd.split(),
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout + result.stderr
    except FileNotFoundError:
        return "❌ guardian.py غير موجود في المجلد الحالي"
    except subprocess.TimeoutExpired:
        return "⏰ انتهت المهلة (30 ثانية)"


def _status_report() -> str:
    import json
    from pathlib import Path
    lines = ["🏰 تقرير حالة الإمبراطورية\n" + "═" * 40]
    lines.append(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    if Path("MANIFEST.sig").exists():
        try:
            manifest = json.loads(Path("MANIFEST.sig").read_text())
            meta = manifest.get("_meta", {})
            lines.append(f"📁 الملفات: {meta.get('total_files', '?')}")
            lines.append(f"🔐 هاش الإمبراطورية: {meta.get('empire_hash', '?')[:20]}...")
            lines.append(f"📅 آخر مسح: {meta.get('created', '?')[:19]}")
        except Exception:
            lines.append("⚠️ تعذّر قراءة MANIFEST.sig")
    else:
        lines.append("⚠️ MANIFEST.sig غير موجود")

    lines.append("═" * 40)
    lines.append("👑 AL_HAKIM | الحكيم يحرس الإمبراطورية")
    return "\n".join(lines)


def run_bot() -> None:
    """يُشغّل البوت — يتطلب python-telegram-bot."""
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN غير مضبوط")
        print("أضفه في .env: TELEGRAM_BOT_TOKEN=token_هنا")
        return

    try:
        from telegram import Update
        from telegram.ext import (
            Application, CommandHandler, MessageHandler,
            filters, ContextTypes,
        )
    except ImportError:
        print("❌ مكتبة telegram غير مثبتة")
        print("شغّل: pip install python-telegram-bot")
        return

    async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        if not _is_owner(chat_id):
            await update.message.reply_text("⛔ غير مصرح — هذا البوت لـ AL_HAKIM فقط")
            logger.warning("محاولة وصول غير مصرح: %s", chat_id)
            return
        await update.message.reply_text(
            "🏰 بأمرك يا حكيم!\n\n"
            "أنا الأمين الذكي — حارسك وخادمك\n\n"
            "الأوامر:\n"
            "/حالة — تقرير الإمبراطورية\n"
            "/فحص — تحقق من سلامة الملفات\n"
            "/توقيع — إضافة توقيع AL_HAKIM\n"
            "/تقرير — ملخص يومي\n"
            "/مساعدة — قائمة الأوامر\n\n"
            "أو اسألني أي سؤال بالعربية 🤖"
        )

    async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not _is_owner(update.effective_chat.id):
            return
        await update.message.reply_text(_status_report())

    async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not _is_owner(update.effective_chat.id):
            return
        await update.message.reply_text("🔍 جاري الفحص...")
        result = _run_guardian("--verify-all")
        await update.message.reply_text(f"📋 نتيجة الفحص:\n\n{result[:3000]}")

    async def cmd_sign_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not _is_owner(update.effective_chat.id):
            return
        args = ctx.args
        if not args:
            await update.message.reply_text("⚠️ استخدام: /توقيع اسم_الملف.py")
            return
        result = _run_guardian(f"--add-sig {args[0]}")
        await update.message.reply_text(f"✅ {result}")

    async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not _is_owner(update.effective_chat.id):
            return
        await update.message.reply_text("📊 جاري إعداد التقرير...")
        sign = _run_guardian("--sign")
        status = _status_report()
        await update.message.reply_text(f"{status}\n\n{sign[:1000]}")

    async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not _is_owner(update.effective_chat.id):
            return
        await update.message.reply_text(
            "👑 AL_HAKIM Guardian — دليل الأوامر\n\n"
            "═══════════════════════════\n"
            "/حالة    — تقرير كامل عن الإمبراطورية\n"
            "/فحص     — تحقق من سلامة جميع الملفات\n"
            "/توقيع [ملف] — أضف توقيع AL_HAKIM\n"
            "/تقرير   — ملخص يومي شامل\n"
            "/مساعدة  — هذه القائمة\n"
            "═══════════════════════════\n"
            "أو اكتب أي سؤال برمجي وسأجيب 🤖\n\n"
            "🏰 الأمين الذكي في خدمتك دائماً"
        )

    async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not _is_owner(update.effective_chat.id):
            await update.message.reply_text("⛔ غير مصرح — هذا البوت لـ AL_HAKIM فقط")
            return
        question = update.message.text
        await update.message.reply_text("⏳ أفكر...")
        answer = _ask_gemini(question)
        await update.message.reply_text(answer[:4000])

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("حالة", cmd_status))
    app.add_handler(CommandHandler("فحص", cmd_check))
    app.add_handler(CommandHandler("توقيع", cmd_sign_file))
    app.add_handler(CommandHandler("تقرير", cmd_report))
    app.add_handler(CommandHandler("مساعدة", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("╔════════════════════════════════════════╗")
    print("║  👑 AL_HAKIM BOT — الأمين الذكي        ║")
    print("║  🏰 الحكيم يحرس الإمبراطورية           ║")
    print("║  ✅ البوت يعمل — في انتظار أوامرك      ║")
    print("╚════════════════════════════════════════╝")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
