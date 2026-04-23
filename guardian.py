#!/usr/bin/env python3
"""
👑 AL_HAKIM GUARDIAN — حارس الإمبراطورية الرقمية
🏥 الحكيم — طبيب الكود، حارس الإمبراطورية
⚡ مكتبات مدمجة فقط — مجاني 100%
"""

import hashlib
import os
import json
import base64
import sys
import argparse
import getpass
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════
OWNER = "AL_HAKIM"
OWNER_AR = "الحكيم"
EMPIRE = "DIGITAL EMPIRE"
MANIFEST_FILE = "MANIFEST.sig"
CORE_FILE = "AL_HAKIM.core"
MAP_FILE = "empire.map"
SIGNATURE = f"👑 {OWNER} | {EMPIRE} | {OWNER_AR} — طبيب الكود، حارس الإمبراطورية"
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache"}
SKIP_FILES = {MANIFEST_FILE, CORE_FILE, MAP_FILE, ".env"}
# ═══════════════════════════════════════


def _sha3_256(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def _sha3_512(data: bytes) -> str:
    return hashlib.sha3_512(data).hexdigest()


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def _hash_file(path: Path) -> str:
    return _sha3_256(path.read_bytes())


def _collect_files(root: Path) -> list[Path]:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            parts = set(p.parts)
            if not parts.intersection(SKIP_DIRS) and p.name not in SKIP_FILES:
                files.append(p)
    return files


def cmd_manifest(root: Path = Path(".")) -> None:
    """يُنشئ MANIFEST.sig — هاش SHA3-256 لكل ملف."""
    files = _collect_files(root)
    manifest = {}
    for f in files:
        rel = str(f.relative_to(root))
        manifest[rel] = _hash_file(f)
        print(f"  ✅ {rel}")

    manifest["_meta"] = {
        "owner": OWNER,
        "created": datetime.utcnow().isoformat(),
        "total_files": len(files),
        "empire_hash": _sha3_256(json.dumps(manifest, sort_keys=True).encode()),
    }

    Path(MANIFEST_FILE).write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\n🔐 MANIFEST.sig created — {len(files)} files")
    print(f"🏰 Empire hash: {manifest['_meta']['empire_hash'][:32]}...")


def cmd_verify_all(root: Path = Path(".")) -> None:
    """يتحقق من سلامة الملفات مقارنةً بـ MANIFEST.sig."""
    if not Path(MANIFEST_FILE).exists():
        print("❌ MANIFEST.sig غير موجود — شغّل: python guardian.py --manifest")
        sys.exit(1)

    manifest = json.loads(Path(MANIFEST_FILE).read_text())
    files = _collect_files(root)
    changed = []
    missing = []

    for f in files:
        rel = str(f.relative_to(root))
        current = _hash_file(f)
        if rel not in manifest:
            print(f"  🆕 جديد: {rel}")
        elif manifest[rel] != current:
            changed.append(rel)
            print(f"  ⚠️  تغيّر: {rel}")
        else:
            print(f"  ✅ سليم: {rel}")

    for rel in manifest:
        if rel.startswith("_"):
            continue
        if not Path(root / rel).exists():
            missing.append(rel)
            print(f"  ❌ مفقود: {rel}")

    print()
    if changed or missing:
        print(f"🚨 تنبيه! {len(changed)} ملف تغيّر، {len(missing)} ملف مفقود")
        sys.exit(1)
    else:
        print(f"🏰 الإمبراطورية سليمة — {len(files)} ملف بخير")


def cmd_hash_section(section: int) -> None:
    """يحسب SHA3-256 لقسم معيّن من DIGITAL_EMPIRE.md."""
    emp = Path("DIGITAL_EMPIRE.md")
    if not emp.exists():
        print("❌ DIGITAL_EMPIRE.md غير موجود")
        sys.exit(1)

    content = emp.read_text(encoding="utf-8")
    sections = content.split("---\n<!-- SECTION_HASH_")
    if section + 1 >= len(sections):
        print(f"❌ القسم {section} غير موجود")
        sys.exit(1)

    sec_content = sections[section + 1].split(" -->")[1] if " -->" in sections[section + 1] else sections[section + 1]
    h = _sha3_256(sec_content.encode("utf-8"))
    print(f"🔐 SHA3-256 [القسم {section}]: {h}")


def cmd_sign(root: Path = Path(".")) -> None:
    """يحسب التوقيع الشامل للإمبراطورية."""
    files = _collect_files(root)
    all_bytes = b""
    for f in sorted(files):
        all_bytes += f.read_bytes()

    sha3_256 = _sha3_256(all_bytes)
    sha3_512 = _sha3_512(all_bytes)

    print(f"\n{'═'*60}")
    print(f"👑 {SIGNATURE}")
    print(f"{'═'*60}")
    print(f"📁 الملفات:   {len(files)}")
    print(f"🔐 SHA3-256:  {sha3_256}")
    print(f"🔐 SHA3-512:  {sha3_512}")
    print(f"{'═'*60}\n")


def cmd_create_core() -> None:
    """يُنشئ النواة السرية AL_HAKIM.core المشفرة."""
    print("🏰 إنشاء النواة السرية لـ AL_HAKIM...")
    print("⚠️  كلمة السر هذه لن تُحفظ في أي مكان — احفظها في ذهنك وحده\n")

    password = getpass.getpass("🔑 اختر كلمة سرك: ")
    confirm = getpass.getpass("🔑 أكد كلمة السر: ")

    if password != confirm:
        print("❌ كلمات السر لا تتطابق")
        sys.exit(1)

    if len(password) < 6:
        print("❌ كلمة السر قصيرة جداً — 6 أحرف على الأقل")
        sys.exit(1)

    emp_hash = "N/A"
    if Path("MANIFEST.sig").exists():
        manifest = json.loads(Path("MANIFEST.sig").read_text())
        emp_hash = manifest.get("_meta", {}).get("empire_hash", "N/A")

    core_data = {
        "owner": OWNER,
        "owner_ar": OWNER_AR,
        "empire": EMPIRE,
        "created": datetime.utcnow().isoformat(),
        "identity": "من يفتح هذا الملف هو الحكيم الحقيقي",
        "test_question": "هل أنت الحكيم؟",
        "test_answer_hash": _sha3_256(f"{OWNER}{password}الحكيم".encode()),
        "empire_hash": emp_hash,
        "signature": SIGNATURE,
        "message": "بسم الله — هذه إمبراطوريتي، بناها عقلي، يحرسها إيماني",
    }

    core_json = json.dumps(core_data, ensure_ascii=False, indent=2).encode("utf-8")
    key = _sha3_256(password.encode()).encode()[:32]
    encrypted = _xor_cipher(core_json, key)
    encoded = base64.b64encode(encrypted).decode()

    header = f"# AL_HAKIM CORE — نواة الإمبراطورية السرية\n# {SIGNATURE}\n# لا تحذف هذا الملف ولا تعدّله\n"
    Path(CORE_FILE).write_text(header + encoded + "\n")
    print(f"\n✅ تم إنشاء {CORE_FILE}")
    print("🔐 احفظ كلمة سرك في ذهنك — لا أحد يستطيع فتح هذا الملف بدونها")


def cmd_verify_core() -> None:
    """يتحقق من هوية المالك عبر AL_HAKIM.core."""
    if not Path(CORE_FILE).exists():
        print(f"❌ {CORE_FILE} غير موجود — شغّل: python guardian.py --create-core")
        sys.exit(1)

    password = getpass.getpass("🔑 كلمة السر: ")

    content = Path(CORE_FILE).read_text()
    lines = content.strip().split("\n")
    encoded = lines[-1]

    key = _sha3_256(password.encode()).encode()[:32]
    try:
        encrypted = base64.b64decode(encoded)
        decrypted = _xor_cipher(encrypted, key)
        core_data = json.loads(decrypted.decode("utf-8"))
    except Exception:
        print("❌ كلمة السر خاطئة — هذا ليس الحكيم")
        sys.exit(1)

    expected_hash = _sha3_256(f"{OWNER}{password}الحكيم".encode())
    if core_data.get("test_answer_hash") != expected_hash:
        print("❌ فشل التحقق — هذا ليس الحكيم")
        sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"✅ مرحباً بك يا {core_data['owner_ar']} 🏰")
    print(f"👑 {core_data['signature']}")
    print(f"📅 تاريخ الإنشاء: {core_data['created']}")
    print(f"💬 {core_data['message']}")
    print(f"{'═'*60}\n")


def cmd_add_signature(file_path: str) -> None:
    """يضيف توقيع AL_HAKIM داخل ملف."""
    p = Path(file_path)
    if not p.exists():
        print(f"❌ الملف غير موجود: {file_path}")
        sys.exit(1)

    content = p.read_text(encoding="utf-8")
    file_hash = _sha3_256(p.read_bytes())

    sig_line = (
        f"\n# {'═'*56}\n"
        f"# 👑 {OWNER} | {EMPIRE}\n"
        f"# 🏥 {OWNER_AR} — طبيب الكود، حارس الإمبراطورية\n"
        f"# 🔐 SHA3-256: {file_hash}\n"
        f"# ⚡ لا نسخ، لا اقتراب، لا استثناء\n"
        f"# {'═'*56}\n"
    )

    if f"👑 {OWNER}" not in content:
        p.write_text(content + sig_line, encoding="utf-8")
        print(f"✅ أُضيف توقيع AL_HAKIM لـ {file_path}")
    else:
        print(f"ℹ️  التوقيع موجود مسبقاً في {file_path}")


def main():
    parser = argparse.ArgumentParser(
        description="👑 AL_HAKIM Guardian — حارس الإمبراطورية الرقمية",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
الأوامر:
  --manifest        أنشئ MANIFEST.sig (هاش كل الملفات)
  --verify-all      تحقق من سلامة جميع الملفات
  --sign            اعرض التوقيع الشامل للإمبراطورية
  --hash N          احسب هاش القسم N من DIGITAL_EMPIRE.md
  --create-core     أنشئ النواة السرية AL_HAKIM.core
  --verify          تحقق من هوية المالك عبر AL_HAKIM.core
  --add-sig FILE    أضف توقيع AL_HAKIM لملف

مثال:
  python guardian.py --manifest
  python guardian.py --verify-all
  python guardian.py --hash 0
  python guardian.py --create-core
  python guardian.py --verify
        """,
    )

    parser.add_argument("--manifest", action="store_true", help="أنشئ MANIFEST.sig")
    parser.add_argument("--verify-all", action="store_true", help="تحقق من سلامة الملفات")
    parser.add_argument("--sign", action="store_true", help="اعرض التوقيع الشامل")
    parser.add_argument("--hash", type=int, metavar="N", help="احسب هاش القسم N")
    parser.add_argument("--create-core", action="store_true", help="أنشئ النواة السرية")
    parser.add_argument("--verify", action="store_true", help="تحقق من هوية المالك")
    parser.add_argument("--add-sig", metavar="FILE", help="أضف التوقيع لملف")

    args = parser.parse_args()

    print(f"\n{'═'*60}")
    print(f"  👑 AL_HAKIM GUARDIAN — حارس الإمبراطورية الرقمية")
    print(f"  🏥 الحكيم — طبيب الكود، حارس الإمبراطورية")
    print(f"{'═'*60}\n")

    if args.manifest:
        cmd_manifest()
    elif args.verify_all:
        cmd_verify_all()
    elif args.sign:
        cmd_sign()
    elif args.hash is not None:
        cmd_hash_section(args.hash)
    elif args.create_core:
        cmd_create_core()
    elif args.verify:
        cmd_verify_core()
    elif args.add_sig:
        cmd_add_signature(args.add_sig)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
