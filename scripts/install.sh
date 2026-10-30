#!/bin/bash
# =============================================================
#  Logi-Track ZeroBaran - سكريبت التثبيت
#  المؤلف: Baran Avisat (Baranavisat@gmail.com)
# =============================================================

set -e

echo "============================================================"
echo "  🚚 Logi-Track ZeroBaran - Setup Script"
echo "  المؤلف: Baran Avisat"
echo "  البريد: Baranavisat@gmail.com"
echo "  واتساب: 00905313263722"
echo "============================================================"
echo ""

# 1. فحص Python
echo "🔍 [1/5] فحص Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 غير مُثبَّت. ثبّته أولاً."
    exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  ✅ Python $PY_VERSION"

# 2. إنشاء بيئة افتراضية
echo ""
echo "🔍 [2/5] إنشاء البيئة الافتراضية..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✅ تم إنشاء venv/"
else
    echo "  ℹ️ venv/ موجودة"
fi

# تفعيل البيئة
source venv/bin/activate

# 3. تحديث pip
echo ""
echo "🔍 [3/5] تحديث pip..."
pip install --upgrade pip --quiet
echo "  ✅ pip محدّث"

# 4. تثبيت التبعيات
echo ""
echo "🔍 [4/5] تثبيت التبعيات..."
pip install -r requirements.txt --quiet
echo "  ✅ تم تثبيت كل التبعيات"

# 5. إنشاء ملف .env
echo ""
echo "🔍 [5/5] إعداد ملف البيئة..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  ✅ تم إنشاء .env (عدّله بمفاتيحك الحقيقية)"
else
    echo "  ℹ️ .env موجود"
fi

# إنشاء مجلدات
mkdir -p logs data

echo ""
echo "============================================================"
echo "  ✅ اكتمل التثبيت بنجاح!"
echo "============================================================"
echo ""
echo "الخطوات التالية:"
echo "  1. عدّل ملف .env وأضف المفاتيح الحقيقية"
echo "  2. نفّذ مخطط قاعدة البيانات: scripts/setup_database.sql"
echo "  3. شغّل النظام: python main.py status"
echo ""
echo "الأوامر المتاحة:"
echo "  python main.py api        → تشغيل خادم API"
echo "  python main.py bot        → تشغيل بوت تليجرام"
echo "  python main.py dashboard  → تشغيل لوحة التحكم"
echo "  python main.py poll       → تشغيل فحص واحد"
echo ""
echo "👨‍💻 المؤلف: Baran Avisat"
echo "📧 Baranavisat@gmail.com"
echo "📱 00905313263722"
echo ""
