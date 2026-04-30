# تحليل الشبكة — Network Analysis (Defensive)

> جميع الأدوات هنا للمراقبة الدفاعية لشبكتك أنت.

---

## Tcpdump — التقاط حزم الشبكة

```bash
# التقاط كل حركة المرور
tcpdump -i eth0

# فلترة بـ IP
tcpdump -i eth0 host 192.168.1.1

# فلترة بـ Port
tcpdump -i eth0 port 443
tcpdump -i eth0 port 80 or port 443

# حفظ لملف
tcpdump -i eth0 -w capture.pcap

# قراءة من ملف
tcpdump -r capture.pcap

# بدون DNS resolution (أسرع)
tcpdump -n -i eth0

# عرض hex + ASCII
tcpdump -XX -i eth0 port 80
```

---

## ss / netstat — اتصالات الشبكة

```bash
# كل الاتصالات المفتوحة
ss -tuln

# اتصالات TCP فقط
ss -tn

# مع اسم البرنامج
ss -tulnp

# المنافذ التي تستمع
ss -lntp

# netstat (قديمة لكن شائعة)
netstat -an | grep LISTEN
netstat -an | grep ESTABLISHED
```

---

## iptables — جدار الحماية

```bash
# عرض القواعد الحالية
iptables -L -n -v

# السماح لـ SSH فقط من IP محدد
iptables -A INPUT -p tcp --dport 22 -s 192.168.1.100 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j DROP

# حجب IP مشبوه
iptables -A INPUT -s 1.2.3.4 -j DROP

# السماح فقط بالمنافذ المطلوبة
iptables -P INPUT DROP
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# حفظ القواعد
iptables-save > /etc/iptables/rules.v4
```

---

## UFW — جدار ناري مبسط (Ubuntu)

```bash
# تفعيل
ufw enable

# السياسة الافتراضية
ufw default deny incoming
ufw default allow outgoing

# السماح بمنافذ محددة
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# السماح من IP محدد
ufw allow from 192.168.1.0/24 to any port 3306

# عرض الحالة
ufw status verbose

# حذف قاعدة
ufw delete allow 22/tcp
```

---

## Fail2ban — حماية من Brute Force

```bash
# حالة كل الـ jails
fail2ban-client status

# حالة SSH jail
fail2ban-client status sshd

# حجب IP يدوياً
fail2ban-client set sshd banip 1.2.3.4

# رفع الحجب
fail2ban-client set sshd unbanip 1.2.3.4
```

**إعداد `/etc/fail2ban/jail.local`:**
```ini
[sshd]
enabled = true
maxretry = 3
findtime = 600
bantime = 3600

[nginx-http-auth]
enabled = true
maxretry = 5
```

---

## تحليل Logs الشبكة

```bash
# أكثر IPs تحاول الاتصال
grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn | head -20

# محاولات SSH الفاشلة
grep "Failed password" /var/log/auth.log | tail -50

# فحص Nginx logs
cat /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10

# حركة المرور غير العادية
awk '$9 >= 400' /var/log/nginx/access.log | tail -20
```

---

## Speedtest-cli — قياس سرعة الشبكة

```bash
speedtest-cli
speedtest-cli --json | python3 -m json.tool
```

---

## مؤشرات الاختراق (IOC) — ماذا تراقب

```
🔴 اتصالات على منافذ غير معتادة
🔴 حركة مرور خارجة ليلاً
🔴 DNS queries لـ domains جديدة
🔴 محاولات SSH/RDP متكررة
🔴 ملفات جديدة في /tmp أو /var/tmp
🔴 processes غريبة في top/ps
🔴 cron jobs جديدة غير معروفة
🔴 مستخدمون جدد في /etc/passwd
```
