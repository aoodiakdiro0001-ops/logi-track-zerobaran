"""
============================================================
  Logi-Track ZeroBaran - بوت تليجرام (التسجيل والإشعارات)
  المؤلف: Baran Avisat
============================================================
  هذا البوت يتيح:
  - تسجيل شحنة جديدة برقم التتبع وبيانات العميل
  - الاستعلام عن حالة الشحنات
  - ربط حساب العميل بـ Telegram ID
  - استقبال التنبيهات الإدارية

  أوامر البوت:
    /start       - بدء التفاعل وتسجيل العميل
    /register    - تسجيل شحنة جديدة
    /track       - تتبع شحنة برقم التتبع
    /myshipments - عرض شحناتي
    /help        - المساعدة
    /admin       - لوحة المدير (للمسؤولين فقط)
============================================================
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

from loguru import logger
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config.settings import settings, AUTHOR, PROJECT_META
from core.database import db
from core.tracker import tracker, TrackingResult
from core.ai_engine import ai_brain
from core.notifier import notifier


# ============================================================
#  قوائم لوحة المفاتيح
# ============================================================
def main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        ["📦 تسجيل شحنة جديدة", "🔍 تتبع شحنة"],
        ["📋 شحناتي", "❓ مساعدة"],
    ]
    if is_admin:
        buttons.append(["📊 لوحة المدير", "🔄 فحص فوري"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# ============================================================
#  أمر /start
# ============================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    welcome = (
        f"🌟 <b>أهلاً بك في {PROJECT_META['name']}</b> 🌟\n\n"
        f"نظام ذكي لتتبع الشحنات وإرسال إشعارات فورية لحظة بلحظة.\n\n"
        f"👤 <b>المؤلف:</b> {AUTHOR['name']}\n"
        f"📧 <b>البريد:</b> {AUTHOR['email']}\n"
        f"📱 <b>واتساب:</b> {AUTHOR['whatsapp']}\n\n"
        f"أنا هنا لمساعدتك في متابعة شحناتك بكل سهولة.\n"
        f"اختر من القائمة أدناه أو استخدم الأوامر.\n\n"
        f"• /register - لتسجيل شحنة جديدة\n"
        f"• /track - لتتبع شحنة\n"
        f"• /myshipments - لعرض شحناتك\n"
        f"• /help - للمساعدة"
    )

    # تسجيل العميل في قاعدة البيانات (إذا لم يكن مسجلاً)
    if db.is_connected:
        existing = db.get_customer_by_telegram(chat_id)
        if not existing:
            db.upsert_customer(
                name=user.full_name or "عميل",
                phone=f"tg_{chat_id}",
                telegram_id=chat_id,
            )

    await update.message.reply_text(
        welcome,
        parse_mode="HTML",
        reply_markup=main_keyboard(is_admin=str(chat_id) == settings.telegram_admin_chat_id),
    )


# ============================================================
#  أمر /register - تسجيل شحنة جديدة
# ============================================================
# حالة المحادثة: tracking → name → phone → carrier
REGISTRATION_STATES = {}

async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    REGISTRATION_STATES[chat_id] = {"step": "tracking"}
    await update.message.reply_text(
        "📦 <b>تسجيل شحنة جديدة</b>\n\n"
        "أرسل رقم التتبع (Tracking Number):",
        parse_mode="HTML",
    )


async def handle_registration_step(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """معالجة خطوات التسجيل التدريجية. يرجع True إذا تمت المعالجة."""
    chat_id = update.effective_chat.id
    if chat_id not in REGISTRATION_STATES:
        return False

    text = update.message.text.strip()
    state = REGISTRATION_STATES[chat_id]

    if state["step"] == "tracking":
        if not text or len(text) < 5:
            await update.message.reply_text("❌ رقم التتبع غير صالح. حاول مرة أخرى:")
            return True
        state["tracking"] = text
        state["step"] = "name"
        await update.message.reply_text(
            "👤 اسم العميل (المستلم):\n"
            "(أرسل اسم العميل كاملاً)"
        )
        return True

    if state["step"] == "name":
        state["name"] = text
        state["step"] = "phone"
        await update.message.reply_text(
            "📱 رقم هاتف العميل (مع رمز الدولة، مثال: 00905313263722):"
        )
        return True

    if state["step"] == "phone":
        # تنظيف الرقم
        phone = re.sub(r"[^\d+]", "", text)
        if len(phone) < 8:
            await update.message.reply_text("❌ رقم الهاتف غير صالح. حاول مرة أخرى:")
            return True
        state["phone"] = phone
        state["step"] = "carrier"

        # أزرار اختيار شركة الشحن
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🚚 Aramex", callback_data="car_aramex"),
                    InlineKeyboardButton("📦 DHL", callback_data="car_dhl"),
                ],
                [
                    InlineKeyboardButton("✈️ FedEx", callback_data="car_fedex"),
                    InlineKeyboardButton("🏠 UPS", callback_data="car_ups"),
                ],
                [
                    InlineKeyboardButton("🇹🇷 PTT Kargo", callback_data="car_ptt"),
                    InlineKeyboardButton("🇹🇷 Yurtiçi", callback_data="car_yurtici"),
                ],
                [
                    InlineKeyboardButton("🇹🇷 MNG Kargo", callback_data="car_mng"),
                    InlineKeyboardButton("❓ كشف تلقائي", callback_data="car_auto"),
                ],
            ]
        )
        await update.message.reply_text(
            "🚚 اختر شركة الشحن:",
            reply_markup=kb,
        )
        return True

    return False


async def handle_carrier_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """اختيار شركة الشحن من القائمة."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    if chat_id not in REGISTRATION_STATES:
        await query.edit_message_text("⏰ انتهت الجلسة. ابدأ من جديد باستخدام /register")
        return

    carrier = query.data.replace("car_", "")
    state = REGISTRATION_STATES[chat_id]
    state["carrier"] = carrier

    # === حفظ الشحنة في قاعدة البيانات ===
    tracking = state["tracking"]
    name = state["name"]
    phone = state["phone"]

    if not db.is_connected:
        await query.edit_message_text(
            "❌ قاعدة البيانات غير متصلة. تأكد من إعداد Supabase."
        )
        REGISTRATION_STATES.pop(chat_id, None)
        return

    # 1. حفظ/تحديث العميل
    customer = db.upsert_customer(
        name=name,
        phone=phone,
        telegram_id=chat_id,
    )
    if not customer:
        await query.edit_message_text("❌ فشل تسجيل العميل. حاول مرة أخرى.")
        REGISTRATION_STATES.pop(chat_id, None)
        return

    # 2. حفظ الشحنة
    shipment = db.add_shipment(
        tracking_number=tracking,
        customer_id=customer["id"],
        carrier=carrier,
        notes=f"مسجلة عبر تليجرام بواسطة {name}",
    )
    if not shipment:
        await query.edit_message_text(
            f"❌ فشل تسجيل الشحنة {tracking}.\n"
            "قد تكون مسجلة مسبقاً. استخدم /track للاستعلام."
        )
        REGISTRATION_STATES.pop(chat_id, None)
        return

    await query.edit_message_text(
        f"✅ <b>تم تسجيل الشحنة بنجاح!</b>\n\n"
        f"📦 رقم التتبع: <code>{tracking}</code>\n"
        f"👤 العميل: {name}\n"
        f"📱 الهاتف: {phone}\n"
        f"🚚 شركة الشحن: {carrier}\n\n"
        f"🤖 سيبدأ النظام بمتابعة شحنتك تلقائياً.\n"
        f"ستصلك إشعارات فورية عند كل تحديث.",
        parse_mode="HTML",
        reply_markup=main_keyboard(
            is_admin=str(chat_id) == settings.telegram_admin_chat_id
        ),
    )

    # إشعار المدير
    await notifier.send_admin_report(
        title="شحنة جديدة مسجلة",
        body=(
            f"📦 رقم التتبع: {tracking}\n"
            f"👤 العميل: {name} ({phone})\n"
            f"🚚 الشركة: {carrier}\n"
            f"🆔 معرّف الشحنة: {shipment.get('id', '')[:8]}"
        ),
        level="success",
    )

    # محاولة تتبع فوري
    try:
        result = tracker.track(tracking, carrier)
        if result.success and result.status != "pending":
            db.update_shipment_status(
                shipment["id"],
                status=result.status,
                status_ar=result.status_ar,
                last_location=result.last_location,
                eta=result.eta.isoformat() if result.eta else None,
            )
    except Exception as e:
        logger.debug(f"ℹ️ لم نتمكن من التتبع الفوري: {e}")

    REGISTRATION_STATES.pop(chat_id, None)


# ============================================================
#  أمر /track - تتبع شحنة برقم التتبع
# ============================================================
TRACKING_STATES = {}

async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    TRACKING_STATES[chat_id] = True
    await update.message.reply_text(
        "🔍 <b>تتبع شحنة</b>\n\nأرسل رقم التتبع:",
        parse_mode="HTML",
    )


async def handle_tracking_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """معالجة إدخال رقم التتبع."""
    chat_id = update.effective_chat.id
    if chat_id not in TRACKING_STATES:
        return False

    text = update.message.text.strip()
    TRACKING_STATES.pop(chat_id, None)

    if not db.is_connected:
        await update.message.reply_text("❌ قاعدة البيانات غير متصلة.")
        return True

    # ابحث عن الشحنة في قاعدة البيانات
    shipment = db.get_shipment(text)
    if shipment:
        events = db.list_events(shipment["id"], limit=10)
        status_emoji = {
            "pending": "⏳", "in_transit": "🚚", "out_for_delivery": "🛵",
            "delivered": "✅", "delayed": "⏰", "exception": "⚠️", "returned": "↩️",
        }.get(shipment["status"], "📦")

        events_text = ""
        for e in events[:5]:
            events_text += f"\n  • {e.get('event_description', '')}"

        await update.message.reply_text(
            f"{status_emoji} <b>حالة الشحنة</b>\n\n"
            f"📦 رقم التتبع: <code>{shipment['tracking_number']}</code>\n"
            f"🚚 الشركة: {shipment.get('carrier', 'غير محدد')}\n"
            f"📌 الحالة: {shipment.get('status_ar', 'غير معروفة')}\n"
            f"📍 آخر موقع: {shipment.get('last_location', 'غير محدد')}\n"
            f"⏰ التسليم المتوقع: {shipment.get('eta', 'غير محدد')}\n\n"
            f"📋 <b>آخر الأحداث:</b>{events_text}",
            parse_mode="HTML",
        )
        return True

    # إن لم تكن مسجلة، نحاول تتبعها فوراً عبر النظام
    await update.message.reply_text(
        "🔍 لم نجد الشحنة في قاعدة بياناتنا. جاري البحث عبر شركة الشحن..."
    )
    result = tracker.track(text)
    if result.success:
        await update.message.reply_text(
            f"📦 <b>نتيجة التتبع المباشر</b>\n\n"
            f"رقم: <code>{result.tracking_number}</code>\n"
            f"الشركة: {result.carrier}\n"
            f"الحالة: {result.status_ar}\n"
            f"الموقع: {result.last_location or 'غير محدد'}\n\n"
            f"💡 لتسجيل هذه الشحنة في النظام، استخدم /register",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            f"❌ تعذّر العثور على بيانات للشحنة {text}.\n"
            f"تأكد من رقم التتبع أو سجّلها أولاً عبر /register"
        )

    return True


# ============================================================
#  أمر /myshipments - عرض شحناتي
# ============================================================
async def cmd_myshipments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if not db.is_connected:
        await update.message.reply_text("❌ قاعدة البيانات غير متصلة.")
        return

    customer = db.get_customer_by_telegram(chat_id)
    if not customer:
        await update.message.reply_text(
            "❌ أنت غير مسجّل في النظام. استخدم /register لتسجيل شحنتك الأولى."
        )
        return

    # استعلم عن شحنات هذا العميل
    try:
        res = (
            db.client.table("shipments")
            .select("*")
            .eq("customer_id", customer["id"])
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        shipments = res.data or []
    except Exception as e:
        logger.error(f"❌ خطأ في جلب شحنات العميل: {e}")
        shipments = []

    if not shipments:
        await update.message.reply_text("📭 ليس لديك شحنات مسجلة بعد. استخدم /register")
        return

    text = f"📋 <b>شحناتك ({len(shipments)})</b>\n\n"
    for s in shipments:
        emoji = {
            "pending": "⏳", "in_transit": "🚚", "out_for_delivery": "🛵",
            "delivered": "✅", "delayed": "⏰", "exception": "⚠️", "returned": "↩️",
        }.get(s["status"], "📦")
        text += (
            f"{emoji} <code>{s['tracking_number']}</code>\n"
            f"   الحالة: {s.get('status_ar', 'غير معروفة')}\n"
            f"   الشركة: {s.get('carrier', 'غير محدد')}\n\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")


# ============================================================
#  أمر /help
# ============================================================
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        f"❓ <b>المساعدة - {PROJECT_META['name']}</b>\n\n"
        "📖 <b>الأوامر المتاحة:</b>\n\n"
        "• /start - بدء التفاعل\n"
        "• /register - تسجيل شحنة جديدة\n"
        "• /track - تتبع شحنة برقم التتبع\n"
        "• /myshipments - عرض شحناتي\n"
        "• /help - عرض هذه المساعدة\n\n"
        "💡 <b>كيف يعمل النظام؟</b>\n"
        "1️⃣ سجّل رقم التتبع عبر /register\n"
        "2️⃣ يتابع النظام شحنتك تلقائياً\n"
        "3️⃣ تصلك إشعارات فورية عند كل تحديث\n"
        "4️⃣ استعلم عن حالتك في أي وقت عبر /track\n\n"
        f"👨‍💻 <b>المؤلف:</b> {AUTHOR['name']}\n"
        f"📧 {AUTHOR['email']}\n"
        f"📱 {AUTHOR['whatsapp']}"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


# ============================================================
#  أمر /admin - لوحة المدير
# ============================================================
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if str(chat_id) != settings.telegram_admin_chat_id:
        await update.message.reply_text("⛔ هذا الأمر مخصص للمدير فقط.")
        return

    stats = db.get_dashboard_stats()
    text = (
        "📊 <b>لوحة المدير - Logi-Track ZeroBaran</b>\n\n"
        f"📦 إجمالي الشحنات: {stats.get('total_shipments', 0)}\n"
        f"🚚 في الطريق: {stats.get('in_transit', 0)}\n"
        f"🛵 خرجت للتوصيل: {stats.get('out_for_delivery', 0)}\n"
        f"✅ تم التسليم: {stats.get('delivered', 0)}\n"
        f"⏰ متأخرة: {stats.get('delayed', 0)}\n"
        f"⚠️ حالات استثنائية: {stats.get('exceptions', 0)}\n\n"
        f"👥 العملاء: {stats.get('total_customers', 0)}\n"
        f"📨 إشعارات مُرسلة: {stats.get('notifications_sent', 0)}\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


# ============================================================
#  معالج الرسائل العامة (الأزرار)
# ============================================================
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    # معالجة خطوات التسجيل
    if await handle_registration_step(update, context):
        return

    # معالجة إدخال رقم التتبع
    if await handle_tracking_input(update, context):
        return

    # أزرار القائمة الرئيسية
    if text == "📦 تسجيل شحنة جديدة":
        await cmd_register(update, context)
    elif text == "🔍 تتبع شحنة":
        await cmd_track(update, context)
    elif text == "📋 شحناتي":
        await cmd_myshipments(update, context)
    elif text == "❓ مساعدة":
        await cmd_help(update, context)
    elif text == "📊 لوحة المدير":
        await cmd_admin(update, context)
    elif text == "🔄 فحص فوري":
        await update.message.reply_text(
            "🔄 جاري الفحص الفوري...\n"
            "(يتم التشغيل تلقائياً عبر GitHub Actions)"
        )
    else:
        await update.message.reply_text(
            "لم أفهم طلبك. استخدم القائمة أو /help للمساعدة."
        )


# ============================================================
#  تشغيل البوت
# ============================================================
def run_bot() -> None:
    """تشغيل بوت تليجرام."""
    if not settings.has_telegram:
        logger.error("❌ إعدادات تليجرام غير مكتملة. أضف TELEGRAM_BOT_TOKEN و TELEGRAM_ADMIN_CHAT_ID في .env")
        return

    logger.info(f"🤖 بدء تشغيل بوت تليجرام - {PROJECT_META['name']}")

    app = Application.builder().token(settings.telegram_bot_token).build()

    # تسجيل المعالجات
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("track", cmd_track))
    app.add_handler(CommandHandler("myshipments", cmd_myshipments))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CallbackQueryHandler(handle_carrier_selection, pattern="^car_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("✅ البوت جاهز للاستقبال. اضغط Ctrl+C للإيقاف.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
