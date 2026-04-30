# التشفير وكلمات السر — Cryptography & Password Security

> الهدف: اختبار قوة كلمات سرك أنت — ليس كسر كلمات سر الآخرين.

---

## أنواع التشفير الشائعة

| الخوارزمية | الحالة | ملاحظة |
|-----------|--------|--------|
| MD5 | ❌ مكسورة | لا تستخدم للكلمات السرية |
| SHA-1 | ❌ ضعيفة | متقاعدة من TLS |
| SHA-256 | ✅ آمنة | للملفات والتحقق |
| SHA-512 | ✅ آمنة | أقوى من SHA-256 |
| bcrypt | ✅ ممتازة | للكلمات السرية |
| Argon2 | ✅ الأفضل | modern password hashing |
| PBKDF2 | ✅ جيدة | مع iterations عالية |

---

## اختبار قوة كلمة السر (على كلماتك أنت)

```bash
# توليد hash
echo -n "MyPassword123!" | sha256sum
echo -n "MyPassword123!" | md5sum

# فحص قوة hash بـ John (على ملفاتك)
john --format=bcrypt --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt

# Hashcat (GPU-accelerated)
hashcat -m 3200 hash.txt /usr/share/wordlists/rockyou.txt   # bcrypt
hashcat -m 0 hash.txt wordlist.txt                           # MD5
hashcat -m 1000 hash.txt wordlist.txt                        # NTLM
```

### أوضاع Hashcat
| الوضع | الاسم | المثال |
|-------|-------|--------|
| -a 0 | Dictionary | قاموس كلمات |
| -a 1 | Combination | كلمتان معاً |
| -a 3 | Brute Force | `?l?l?l?l?l?l` |
| -a 6 | Hybrid | قاموس + mask |

---

## OpenSSL — توليد مفاتيح وشهادات

```bash
# توليد مفتاح RSA-2048
openssl genrsa -out private.key 2048

# توليد مفتاح RSA-4096 (أقوى)
openssl genrsa -out private.key 4096

# استخراج المفتاح العام
openssl rsa -in private.key -pubout -out public.key

# توليد شهادة self-signed
openssl req -new -x509 -key private.key -out cert.pem -days 365

# فحص شهادة
openssl x509 -in cert.pem -text -noout

# توليد CSR (طلب شهادة)
openssl req -new -key private.key -out request.csr

# التشفير المتماثل
openssl enc -aes-256-cbc -salt -in file.txt -out file.enc
openssl enc -d -aes-256-cbc -in file.enc -out file.txt

# توليد كلمة سر عشوائية
openssl rand -base64 32
openssl rand -hex 64
```

---

## GPG — تشفير الملفات

```bash
# توليد مفتاح
gpg --gen-key

# تشفير ملف
gpg -e -r "user@example.com" file.txt

# فك التشفير
gpg -d file.txt.gpg

# التوقيع الرقمي
gpg --sign file.txt
gpg --verify file.txt.gpg
```

---

## Python — أدوات التشفير

```python
import hashlib, secrets, base64
from cryptography.fernet import Fernet

# SHA-256
hashlib.sha256(b"password").hexdigest()

# bcrypt (للكلمات السرية)
import bcrypt
hashed = bcrypt.hashpw(b"password", bcrypt.gensalt(rounds=12))
bcrypt.checkpw(b"password", hashed)

# Fernet (تشفير متماثل)
key = Fernet.generate_key()
f = Fernet(key)
token = f.encrypt(b"secret data")
f.decrypt(token)

# توليد كلمة سر آمنة
secrets.token_urlsafe(32)

# PBKDF2
import hashlib
dk = hashlib.pbkdf2_hmac('sha256', b'password', b'salt', 100000)
```

---

## قواعد كلمات السر الآمنة

```
✅ 16+ حرف
✅ أرقام + حروف + رموز
✅ لا كلمات قاموسية
✅ مختلفة لكل حساب
✅ مدير كلمات سر (Bitwarden, KeePass)
✅ bcrypt أو Argon2 في التطبيقات
❌ MD5 أو SHA-1 للكلمات السرية
❌ تخزين بنص واضح
❌ كلمة سر < 8 أحرف
```

---

## تكامل مع Sentinel Guard

Sentinel Guard يستخدم في التوقيع:
```python
# RSA-2048/PSS في generator.py
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes
```
