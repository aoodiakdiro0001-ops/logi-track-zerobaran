"""
============================================================
  Logi-Track ZeroBaran - نقطة الدخول الرئيسية
  المؤلف: Baran Avisat (Baranavisat@gmail.com)
  واتساب: 00905313263722
============================================================
  هذا الملف يسمح بتشغيل أي مكون من النظام عبر سطر الأوامر:

  python main.py api       → تشغيل خادم FastAPI
  python main.py bot       → تشغيل بوت تليجرام
  python main.py dashboard  → تشغيل لوحة تحكم Streamlit
  python main.py poll      → تشغيل دورة فحص واحدة
  python main.py status    → عرض حالة النظام
============================================================
"""

import sys
import os
import subprocess
from pathlib import Path

# إضافة جذر المشروع إلى المسار
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings, AUTHOR, PROJECT_META
from core.logger import logger


BANNER = r"""
============================================================
                                                           
    ██╗      █████╗  ██╗  ██╗██╗   ██╗██████╗  ██████╗ ██╗  ██╗
    ██║     ██╔══██╗╚██╗██╔╝██║   ██║██╔══██╗██╔═══██╗╚██╗██╔╝
    ██║     ███████║ ╚███╔╝ ██║   ██║██████╔╝██║   ██║ ╚███╔╝ 
    ██║     ██╔══██║ ██╔██╗ ██║   ██║██╔══██╗██║   ██║ ██╔██╗ 
    ███████╗██║  ██║██╔╝ ██╗╚██████╔╝██████╔╝╚██████╔╝██╔╝ ██╗
    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
                                                           
    ZeroBaran - المنظومة الذاتية الذكية لتتبع الشحنات
                                                           
    المؤلف: Baran Avisat
    البريد: Baranavisat@gmail.com
    واتساب: 00905313263722
============================================================
"""


def print_banner() -> None:
    """طباعة شعار المشروع."""
    print(BANNER)
    print(f"  📦 المشروع: {PROJECT_META['name']} v{PROJECT_META['version']}")
    print(f"  📝 الوصف: {PROJECT_META['description']}")
    print(f"  👨‍💻 المؤلف: {AUTHOR['name']} ({AUTHOR['email']})")
    print(f"  📱 واتساب: {AUTHOR['whatsapp']}")
    print("=" * 60 + "\n")


def show_status() -> None:
    """عرض حالة النظام."""
    print_banner()
    print("📊 حالة النظام:")
    print(f"  • البيئة: {settings.environment}")
    print(f"  • Supabase: {'✅ متصل' if settings.has_supabase else '❌ غير متصل'}")
    print(f"  • AI Provider: {settings.ai_provider.upper() if settings.ai_provider != 'none' else '❌ غير مُفعّل'}")
    print(f"  • Telegram: {'✅ مُفعّل' if settings.has_telegram else '❌ غير مُفعّل'}")
    print(f"  • فترة الفحص: كل {settings.poll_interval_hours} ساعة")
    print(f"  • المنطقة الزمنية: {settings.timezone}")
    print()

    # فحص قاعدة البيانات
    if settings.has_supabase:
        try:
            from core.database import db
            if db.is_connected:
                stats = db.get_dashboard_stats()
                print("📈 إحصائيات سريعة:")
                for k, v in stats.items():
                    print(f"  • {k}: {v}")
        except Exception as e:
            print(f"⚠️ تعذّر جلب الإحصائيات: {e}")


def run_api() -> None:
    """تشغيل خادم FastAPI."""
    print_banner()
    print("🚀 تشغيل خادم FastAPI على المنفذ 8000...")
    print("📖 توثيق API: http://localhost:8000/docs\n")
    try:
        import uvicorn
        uvicorn.run(
            "api.server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
        )
    except ImportError:
        logger.error("❌ uvicorn غير مثبت. شغّل: pip install uvicorn")
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف الخادم")


def run_bot() -> None:
    """تشغيل بوت تليجرام."""
    print_banner()
    print("🤖 تشغيل بوت تليجرام...\n")
    from bot.telegram_bot import run_bot
    run_bot()


def run_dashboard() -> None:
    """تشغيل لوحة تحكم Streamlit."""
    print_banner()
    print("📊 تشغيل لوحة التحكم Streamlit على المنفذ 8501...")
    print("🌐 الرابط: http://localhost:8501\n")
    dashboard_path = PROJECT_ROOT / "dashboard" / "app.py"
    try:
        subprocess.run(
            ["streamlit", "run", str(dashboard_path), "--server.port=8501"],
            check=True,
        )
    except FileNotFoundError:
        logger.error("❌ streamlit غير مثبت. شغّل: pip install streamlit")
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف لوحة التحكم")


def run_poll() -> None:
    """تشغيل دورة فحص واحدة."""
    print_banner()
    print("🔄 تشغيل دورة فحص واحدة...\n")
    from scripts.poll_shipments import main as poll_main
    poll_main()


def show_help() -> None:
    """عرض المساعدة."""
    print_banner()
    print("📖 الأوامر المتاحة:")
    print()
    print("  python main.py api         تشغيل خادم FastAPI (المنفذ 8000)")
    print("  python main.py bot         تشغيل بوت تليجرام")
    print("  python main.py dashboard   تشغيل لوحة تحكم Streamlit (المنفذ 8501)")
    print("  python main.py poll        تشغيل دورة فحص شحنات واحدة")
    print("  python main.py status      عرض حالة النظام")
    print("  python main.py help        عرض هذه المساعدة")
    print()
    print("🔧 ملفات التوثيق:")
    print("  README.md                  دليل الاستخدام الكامل")
    print("  INSTALL.md                 دليل التثبيت")
    print("  .env.example               مثال على متغيرات البيئة")
    print()
    print("👨‍💻 المؤلف: " + AUTHOR["name"])
    print("📧 البريد: " + AUTHOR["email"])
    print("📱 واتساب: " + AUTHOR["whatsapp"])


def main() -> None:
    """نقطة الدخول الرئيسية."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    command = sys.argv[1].lower().strip("-")

    commands = {
        "api": run_api,
        "server": run_api,
        "bot": run_bot,
        "telegram": run_bot,
        "dashboard": run_dashboard,
        "streamlit": run_dashboard,
        "poll": run_poll,
        "track": run_poll,
        "status": show_status,
        "help": show_help,
        "--help": show_help,
        "-h": show_help,
    }

    handler = commands.get(command)
    if handler:
        handler()
    else:
        print(f"❌ أمر غير معروف: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
