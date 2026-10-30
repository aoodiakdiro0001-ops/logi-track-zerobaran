# 📦 دليل التثبيت الكامل - Logi-Track ZeroBaran

> **المؤلف:** Baran Avisat | **البريد:** Baranavisat@gmail.com | **واتساب:** 00905313263722

دليل تفصيلي خطوة بخطوة لإعداد وتشغيل نظام Logi-Track ZeroBaran من الصفر.

---

## 📋 المتطلبات الأساسية

| المتطلب | الإصدار | رابط الحصول عليه |
|---|---|---|
| Python | 3.11 أو أحدث | https://python.org |
| Git | أحدث إصدار | https://git-scm.com |
| حساب GitHub | مجاني | https://github.com |
| حساب Supabase | مجاني (Free Tier) | https://supabase.com |
| Google Gemini API | مجاني (Free Tier) | https://aistudio.google.com |
| Groq API (بديل) | مجاني (Free Tier) | https://console.groq.com |
| Telegram Bot | مجاني | عبر BotFather على تليجرام |

---

## 🛠️ الخطوة 1: إعداد قاعدة البيانات (Supabase)

### 1.1 إنشاء مشروع Supabase

1. اذهب إلى https://supabase.com وسجّل حساب مجاني.
2. اضغط **New Project** واختر اسماً وكلمة مرور قوية لقاعدة البيانات.
3. اختر المنطقة الأقرب إليك (eu-central لأوروبا، me-central-1 للشرق الأوسط).
4. انتظر حتى يكتمل الإعداد (يستغرق 2-3 دقائق).

### 1.2 الحصول على مفاتيح الاتصال

1. اذهب إلى **Project Settings** → **API**.
2. انسخ القيم التالية:
   - **Project URL** → سيكون `SUPABASE_URL`
   - **anon public** key → سيكون `SUPABASE_KEY`
   - **service_role** key → سيكون `SUPABASE_SERVICE_KEY` (احتفظ به سرياً!)

### 1.3 تنفيذ مخطط قاعدة البيانات

1. في لوحة تحكم Supabase، اذهب إلى **SQL Editor**.
2. اضغط **New Query**.
3. افتح ملف `scripts/setup_database.sql` من المشروع.
4. انسخ كامل المحتوى والصقه في SQL Editor.
5. اضغط **Run** لتنفيذ المخطط.

✅ سترى رسالة "Success. No rows returned." عند النجاح.

### 1.4 التحقق من الجداول

اذهب إلى **Table Editor** وتأكد من وجود الجداول التالية:
- `customers`
- `shipments`
- `shipment_events`
- `notifications_log`
- `system_settings`
- `audit_log`

---

## 🤖 الخطوة 2: إعداد Google Gemini API

### 2.1 الحصول على مفتاح API

1. اذهب إلى https://aistudio.google.com.
2. سجّل الدخول بحساب Google.
3. اضغط **Get API Key** → **Create API Key**.
4. اختر مشروع Google Cloud أو أنشئ واحداً جديداً.
5. انسخ مفتاح API.

### 2.2 تفعيل النموذج

- النموذج الافتراضي: `gemini-1.5-flash` (مجاني وسريع).
- للاستخدام المكثف: `gemini-1.5-pro` (له حدوده في الفئة المجانية).

---

## 🚀 الخطوة 3: إنشاء بوت تليجرام

### 3.1 إنشاء البوت

1. افتح تليجرام وابحث عن `@BotFather`.
2. أرسل الأمر `/newbot`.
3. اتبع التعليمات:
   - اختر اسماً للبوت (مثال: `Logi-Track ZeroBaran`).
   - اختر معرّفاً فريداً (مثال: `logi_track_zerobaran_bot`).
4. ستحصل على **Bot Token** — انسخه.

### 3.2 الحصول على معرّف الدردشة الخاص بك (Admin Chat ID)

1. ابحث عن `@userinfobot` على تليجرام.
2. أرسل أي رسالة، وسيُردّ بـ `Id: 123456789`.
3. هذا هو `TELEGRAM_ADMIN_CHAT_ID`.

### 3.3 (اختياري) تفعيل Bot Mode

لجعل البوت متاحاً للعملاء، يمكن تركه في **Inline Mode** أو إضافته لمجموعة. اقرأ توثيق Telegram Bot API للمزيد.

---

## 💻 الخطوة 4: إعداد المشروع محلياً

### 4.1 تنزيل المشروع

```bash
git clone <repository-url>
cd Logi-Track-ZeroBaran
```

### 4.2 إنشاء بيئة افتراضية

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 4.3 تثبيت التبعيات

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.4 إعداد متغيرات البيئة

```bash
cp .env.example .env
```

افتح ملف `.env` بمحرر نصوص واملأ القيم الحقيقية:

```env
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...

GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-1.5-flash

TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIjKlMnOpQrStUvWxYz
TELEGRAM_ADMIN_CHAT_ID=123456789

POLL_INTERVAL_HOURS=1
TIMEZONE=Asia/Istanbul
DEFAULT_LANGUAGE=ar
```

---

## 🧪 الخطوة 5: التحقق من الإعداد

```bash
python main.py status
```

يجب أن ترى شيئاً مثل:

```
📊 حالة النظام:
  • البيئة: production
  • Supabase: ✅ متصل
  • AI Provider: GEMINI
  • Telegram: ✅ مُفعّل
  • فترة الفحص: كل 1 ساعة
  • المنطقة الزمنية: Asia/Istanbul
```

---

## 🚀 الخطوة 6: التشغيل الأول

### تشغيل خادم API

```bash
python main.py api
```

افتح المتصفح على: http://localhost:8000/docs

### تشغيل بوت تليجرام

في نافذة طرفية أخرى:

```bash
python main.py bot
```

افتح تليجرام، ابحث عن بوتك، وأرسل `/start`.

### تشغيل لوحة التحكم

في نافذة طرفية ثالثة:

```bash
python main.py dashboard
```

افتح المتصفح على: http://localhost:8501

### اختبار دورة فحص

```bash
python main.py poll
```

---

## ☁️ الخطوة 7: النشر على GitHub Actions

### 7.1 رفع المشروع إلى GitHub

```bash
git init
git add .
git commit -m "🚀 Initial commit - Logi-Track ZeroBaran"
git branch -M main
git remote add origin https://github.com/aoodiakdiro0001-ops/logi-track-zerobaran.git
git push -u origin main
```

### 7.2 إضافة الأسرار (Secrets)

اذهب إلى:
**Repository** → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

أضف الأسرار التالية:

| الاسم | القيمة |
|---|---|
| `SUPABASE_URL` | https://yourproject.supabase.co |
| `SUPABASE_KEY` | (anon key) |
| `SUPABASE_SERVICE_KEY` | (service_role key) |
| `GEMINI_API_KEY` | (مفتاح Gemini) |
| `TELEGRAM_BOT_TOKEN` | (Bot token) |
| `TELEGRAM_ADMIN_CHAT_ID` | (Chat ID للمدير) |

### 7.3 تفعيل الجدولة

ملف `.github/workflows/poll_shipments.yml` معدٌّ ليعمل **كل ساعة**. لتغيير الفترة، عدّل سطر `cron`:

```yaml
schedule:
  - cron: '0 */3 * * *'  # كل 3 ساعات
  - cron: '0 9 * * *'    # يومياً الساعة 9 صباحاً
```

### 7.4 التشغيل اليدوي

اذهب إلى **Actions** في المستودع، اختر **Logi-Track ZeroBaran - Poll Shipments**، واضغط **Run workflow** لاختبار التشغيل.

---

## 🔍 استكشاف الأخطاء وإصلاحها

### ❌ Supabase غير متصل

- تأكد من صحة `SUPABASE_URL` و `SUPABASE_KEY`.
- تأكد من تنفيذ مخطط SQL.
- تحقق من سياسات RLS (Row Level Security).

### ❌ AI Provider غير مفعّل

- للتأكد من صحة مفتاح Gemini:
  ```bash
  curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"
  ```
- إذا فشل Gemini، استخدم Groq كبديل.

### ❌ بوت تليجرام لا يستجيب

- تأكد من صحة `TELEGRAM_BOT_TOKEN`.
- تحقق من أن البوت ليس قيد التشغيل في نافذة أخرى (Bot محدود لمثيل واحد).
- أرسل `/start` للبوت لتفعيل المحادثة.

### ❌ GitHub Actions لا يعمل

- تحقق من أن الأسرار مُضافة بشكل صحيح.
- اذهب إلى تبويب Actions واقرأ السجلات.
- تأكد من أن الـ cron expression صحيح.

### ❌ خطأ في الـ dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

## 📞 الدعم

للمساعدة في الإعداد أو أي استفسار:

| القناة | البيان |
|---|---|
| 📧 البريد | Baranavisat@gmail.com |
| 📱 واتساب | 00905313263722 |

---

<div align="center">

**🚚 Logi-Track ZeroBaran** — تم التطوير بواسطة **Baran Avisat** © 2026

</div>
