# تحليل بيانات الاعتماد — Credential Analysis & Hash Identification

> ⛔ للاستخدام على أنظمة مملوكة أو مرخَّص اختبارها فقط
> الذكاء يشرح المفاهيم — لا يُنفّذ إلا بأمر صريح منك

---

## تحديد نوع الـ Hash

### أداة hashid / hash-identifier

```bash
# تحديد نوع hash مجهول
hashid '$2a$12$R9h/cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jWMUW'
# → [+] Blowfish(OpenBSD) [+] Woltlab Burning Board 4.x [+] bcrypt

hashid '5d41402abc4b2a76b9719d911017c592'
# → [+] MD5 [+] MD4 [+] Double MD5

# أو hash-identifier (تفاعلي)
hash-identifier
```

### صيغ Hash الشائعة

| الصيغة | المثال | الأداة |
|--------|--------|--------|
| MD5 | `5d41402abc4b2a76b9719d911017c592` | md5sum |
| SHA-1 | `7c2a55657d911109dbc930836e7a770fb946e8ef` | shasum |
| SHA-256 | `2cf24dba5fb0a30...` | sha256sum |
| bcrypt | `$2a$12$R9h/cIPz0gi...` | passlib |
| MD5crypt | `$1$salt$hash` | /etc/shadow |
| SHA-512crypt | `$6$salt$hash` | /etc/shadow Linux |
| NTLM | `AAD3B435B51404EEAAD3...` | Windows SAM |
| NTLMv2 | `username::domain:...` | Responder التقاط |

---

## Gerrit — استطلاع بيانات الاعتماد (تقنية أمنية)

### كيف يخزن Gerrit External IDs

**المشكلة الأمنية**: Gerrit يخزن external IDs باستخدام SHA-1 لمسار الملف، مما يسمح باستنتاج المسار من اسم المستخدم المعروف.

```bash
# حساب SHA-1 من external ID (username معروف)
echo -n 'gerrit:jdoe' | shasum
# → 7c2a55657d911109dbc930836e7a770fb946e8ef

echo -n 'username:jdoe' | shasum
# → e0b751ae90ef039f320e097d7d212f490e933706

# المسار في git refs: 7c/2a55657d911109dbc930836e7a770fb946e8ef
# أول حرفان → subdirectory / باقي الـ hash → اسم الملف
```

**البنية المخزّنة:**
```ini
[externalId "username:jdoe"]
  accountId = 1003407
  email = jdoe@example.com
  password = bcrypt:4:LCbmSBDivK/hhGVQMfkDpA==:XcWn0pKYSVU/UJgOvhidkEtmqCp6oKB7
```

### صيغة Gerrit bcrypt (مختلفة عن Standard bcrypt)

```
Standard bcrypt:  $2a$COST$SALTandHASH     (60 chars)
Gerrit bcrypt:    bcrypt:COST:BASE64SALT:BASE64HASH
```

```python
# كيفية التحقق (على نظامك فقط — للتشخيص)
import bcrypt, base64

stored = "bcrypt:4:LCbmSBDivK/hhGVQMfkDpA==:XcWn0pKYSVU/UJgOvhidkEtmqCp6oKB7"
parts = stored.split(":")
cost = int(parts[1])
salt_b64 = parts[2]
hash_b64 = parts[3]

# تحويل Salt → standard bcrypt format للتحقق
salt_bytes = base64.b64decode(salt_b64 + "==")
```

### قراءة Gerrit external ID (لمن يملك صلاحية git)

```bash
# عرض ملف external ID مباشرة
git show refs/meta/external-ids:7c/2a55657d911109dbc930836e7a770fb946e8ef

# استخراج جميع external IDs (إذا ملكت repo)
git ls-tree refs/meta/external-ids -r --name-only | head -20

# البحث عن حساب محدد
git grep "email = target@example.com" refs/meta/external-ids
```

---

## اكتشاف Hash في ملفات النظام

### Linux — ملفات الـ Hash

```bash
# /etc/shadow — hashes المستخدمين (يحتاج root)
cat /etc/shadow | grep -v '*' | grep -v '!'
# المستخدمون الذين لديهم password فعلي

# استخراج hash مستخدم محدد
getent shadow username

# التحقق من نوع الـ hash
# $1$  = MD5crypt
# $5$  = SHA-256crypt
# $6$  = SHA-512crypt (Linux default)
# $2a$ = bcrypt
# $y$  = yescrypt (Ubuntu 21.04+)
```

### Windows — استخراج NTLM Hashes

```bash
# من Impacket (على نظام مملوك)
python3 secretsdump.py DOMAIN/admin:password@target-ip

# من Metasploit (post-exploitation)
run post/windows/gather/credentials/credential_collector

# hashdump من Meterpreter session
hashdump
# → Administrator:500:AABBCC...:DDEEFF...
#   الجزء الثالث = LM hash (قديم)
#   الجزء الرابع = NTLM hash
```

---

## كسر الـ Hash — Hashcat

### أوامر Hashcat الأساسية

```bash
# كسر MD5
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt

# كسر SHA-1
hashcat -m 100 hash.txt /usr/share/wordlists/rockyou.txt

# كسر bcrypt (بطيء — GPU مطلوب)
hashcat -m 3200 hash.txt /usr/share/wordlists/rockyou.txt

# كسر NTLM (سريع جداً)
hashcat -m 1000 hash.txt /usr/share/wordlists/rockyou.txt

# كسر NTLMv2
hashcat -m 5600 hash.txt /usr/share/wordlists/rockyou.txt

# كسر SHA-512crypt (/etc/shadow)
hashcat -m 1800 hash.txt /usr/share/wordlists/rockyou.txt

# مع Rules (تولّد تنويعات من الكلمات)
hashcat -m 0 hash.txt wordlist.txt -r /usr/share/hashcat/rules/best64.rule

# Brute force (أرقام 8 أحرف)
hashcat -m 0 hash.txt -a 3 ?d?d?d?d?d?d?d?d
```

### جدول Hash Types في Hashcat

```
0     → MD5
100   → SHA-1
1400  → SHA-256
1700  → SHA-512
3200  → bcrypt
1000  → NTLM
5600  → NTLMv2
1800  → sha512crypt ($6$)
500   → md5crypt ($1$)
7400  → sha256crypt ($5$)
```

---

## John the Ripper — كسر Shadow File مباشرة

```bash
# دمج passwd + shadow
unshadow /etc/passwd /etc/shadow > hashes.txt

# كسر تلقائي
john hashes.txt

# مع wordlist
john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt

# عرض النتائج
john --show hashes.txt

# كسر bcrypt من Gerrit
echo 'user:bcrypt:4:SALT:HASH' > gerrit_hash.txt
john --format=bcrypt gerrit_hash.txt
```

---

## Python — توليد وفحص الـ Hash

```python
import hashlib, hmac

# MD5
hashlib.md5(b"password").hexdigest()

# SHA-1 (مكسور — لا تستخدمه للأمان)
hashlib.sha1(b"gerrit:jdoe").hexdigest()
# → 7c2a55657d911109dbc930836e7a770fb946e8ef

# SHA-256 (موصى به)
hashlib.sha256(b"password").hexdigest()

# HMAC-SHA256 (للتحقق الآمن)
hmac.new(b"secret_key", b"message", hashlib.sha256).hexdigest()

# bcrypt (الأقوى للكلمات السر)
import bcrypt
hashed = bcrypt.hashpw(b"password", bcrypt.gensalt(rounds=12))
bcrypt.checkpw(b"password", hashed)  # True

# مقارنة آمنة ضد Timing Attacks
hmac.compare_digest(candidate_hash, stored_hash)
```

---

## الأتمتة — Python build.py Pattern (من Chromium)

نمط مُلهِم من Chromium's build.py لأتمتة مهام المشروع:

```python
import sys, inspect

def task_scan(target: str):
    """يُطلق فحص على target محدد."""
    ...

def task_status():
    """يعرض حالة جميع الخدمات."""
    ...

def main(args):
    # اكتشاف تلقائي لجميع الـ tasks
    tasks = {
        name.removeprefix("task_"): fn
        for name, fn in globals().items()
        if name.startswith("task_")
    }
    fn = tasks.get(args[0])
    fn(*args[1:])

# الاستخدام: python manage.py scan 192.168.1.1
# الاستخدام: python manage.py status
```

---

## قواعد الاستخدام

```
✅ تحليل hashes من أنظمة تملكها (server خاص، VM، Docker)
✅ CTF: HackTheBox, TryHackMe, VulnHub
✅ اختبار كلمات مرور النظام الخاص بك
✅ تعلم الأنماط والصيغ
❌ استخراج credentials من أنظمة الغير
❌ استخدام external IDs لاختراق Gerrit instances غير مملوكة
❌ الذكاء لا يُنفّذ أي أمر إلا بطلبك الصريح
```
