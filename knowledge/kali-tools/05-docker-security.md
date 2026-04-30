# أمن Docker والـ Containers — Docker Security

---

## أكثر الأخطاء شيوعاً في Dockerfiles

### 1. الصورة غير مثبتة (Unpinned Image)
```dockerfile
# ❌ خطر — يتغير عند كل build
FROM ubuntu:latest

# ✅ آمن — ثابت دائماً
FROM ubuntu:22.04@sha256:a6d2b38300ce017add71440577d5b0a90460d269d9b7f0d01eb97b34abdc7f5a
```

### 2. تشغيل كـ root
```dockerfile
# ❌ خطر
RUN apt-get install -y nginx
CMD ["nginx"]

# ✅ آمن
RUN addgroup --system app && adduser --system --group app
USER app
CMD ["nginx"]
```

### 3. Secrets في Environment Variables
```dockerfile
# ❌ كارثة — تظهر في docker inspect
ENV DATABASE_PASSWORD=mysecret123

# ✅ استخدم Docker Secrets أو runtime injection
# docker run -e DATABASE_PASSWORD=$DB_PASS app
```

### 4. تثبيت أدوات غير ضرورية
```dockerfile
# ❌ يزيد attack surface
RUN apt-get install -y curl wget git vim netcat

# ✅ فقط ما تحتاجه
RUN apt-get install -y --no-install-recommends python3 && \
    rm -rf /var/lib/apt/lists/*
```

### 5. COPY بدل ADD
```dockerfile
# ❌ ADD يفك الضغط تلقائياً وقد يكون خطراً
ADD https://example.com/file.tar.gz /app/

# ✅ COPY واضح وآمن
COPY ./app /app/
```

---

## Multi-stage Builds — أفضل ممارسة

```dockerfile
# مرحلة البناء (فيها كل أدوات التطوير)
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# مرحلة الإنتاج (خفيفة ونظيفة)
FROM python:3.11-slim AS production
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
USER nobody
CMD ["python", "main.py"]
```

---

## Docker Compose — إعدادات آمنة

```yaml
services:
  api:
    image: myapp:1.0@sha256:abc123...
    read_only: true                    # filesystem للقراءة فقط
    security_opt:
      - no-new-privileges:true         # يمنع رفع الصلاحيات
    cap_drop:
      - ALL                            # إلغاء كل الـ capabilities
    cap_add:
      - NET_BIND_SERVICE               # فقط ما تحتاجه
    tmpfs:
      - /tmp                           # /tmp في RAM
    networks:
      - internal                       # شبكة داخلية فقط
    user: "1001:1001"                  # non-root user
```

---

## Trivy — فحص ثغرات Images

```bash
# فحص image
trivy image nginx:latest
trivy image --severity HIGH,CRITICAL myapp:latest

# فحص Dockerfile
trivy config ./Dockerfile

# فحص filesystem
trivy fs /path/to/project

# فحص repo
trivy repo https://github.com/myorg/myapp

# output SARIF
trivy image --format sarif -o results.sarif myapp:latest
```

---

## Syft — Software Bill of Materials (SBOM)

```bash
# توليد SBOM لـ image
syft nginx:latest

# توليد SBOM بصيغة SPDX
syft nginx:latest -o spdx-json > sbom.json

# توليد SBOM بصيغة CycloneDX
syft nginx:latest -o cyclonedx-json > sbom.cyclonedx.json

# فحص Dockerfile مباشرة
syft dir:/path/to/project
```

---

## Docker Bench Security

```bash
# تحليل إعدادات Docker daemon وـ containers
docker run --rm -it \
  --net host \
  --pid host \
  --userns host \
  --cap-add audit_control \
  -v /var/lib:/var/lib \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /usr/lib/systemd:/usr/lib/systemd \
  -v /etc:/etc \
  docker/docker-bench-security
```

---

## أوامر تشخيص يومية

```bash
# فحص الـ containers الشاغلة
docker ps --format "{{.Names}}: {{.Status}}"

# فحص الـ networks
docker network ls
docker network inspect bridge

# فحص الـ volumes
docker volume ls
docker volume inspect myvolume

# فحص logs
docker logs --tail=100 -f container_name

# فحص resource usage
docker stats --no-stream

# فحص metadata container
docker inspect container_name | jq '.[0].Config.Env'  # يكشف env vars

# تنظيف
docker system prune -f          # حذف المتوقفة
docker image prune -a -f        # حذف images غير المستخدمة
```

---

## قواعد الأمن الذهبية لـ Docker

```
✅ دائماً Pin الـ images بـ @sha256
✅ استخدم Multi-stage builds
✅ شغّل كـ non-root user
✅ read_only: true للـ filesystem
✅ cap_drop: ALL + أضف فقط ما تحتاجه
✅ no-new-privileges: true
✅ Networks منفصلة (لا تضع DB مع API في نفس الشبكة)
✅ فحص Trivy دورياً
✅ لا Secrets في ENV أو Dockerfile
❌ ممنوع --privileged في الإنتاج
❌ ممنوع --net=host
❌ ممنوع تشغيل كـ root
```
