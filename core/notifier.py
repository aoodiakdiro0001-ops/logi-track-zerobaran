"""
============================================================
  Logi-Track ZeroBaran - محرك التنبيهات (Notifier)
  المؤلف: Baran Avisat
============================================================
  هذه الوحدة مسؤولة عن:
  - إرسال الإشعارات للعملاء عبر Telegram
  - إرسال تقارير لوجستية للمدير
  - تسجيل كل إشعار في قاعدة البيانات
============================================================
"""

from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger

from config.settings import settings
from core.database import db


class TelegramNotifier:
    """محرك التنبيهات عبر Telegram - Logi-Track ZeroBaran."""

    def __init__(self) -> None:
        self.bot_token = settings.telegram_bot_token
        self.admin_chat_id = settings.telegram_admin_chat_id
        self._bot = None
        self._app = None

    async def _get_bot(self):
        """تهيئة lazy-load للبوت."""
        if self._bot is None and settings.has_telegram:
            try:
                from telegram import Bot
                self._bot = Bot(token=self.bot_token)
                logger.info("🤖 تم تهيئة بوت تليجرام بنجاح")
            except Exception as e:
                logger.error(f"❌ فشل تهيئة بوت تليجرام: {e}")
        return self._bot

    # ============================================================
    #  إرسال إشعار للعميل
    # ============================================================
    async def send_customer_notification(
        self,
        customer_telegram_id: Optional[int],
        customer_name: str,
        tracking_number: str,
        shipment_id: str,
        message: str,
        customer_id: Optional[str] = None,
    ) -> bool:
        """إرسال إشعار للعميل عبر تليجرام."""
        bot = await self._get_bot()
        if bot is None:
            logger.warning("⚠️ بوت تليجرام غير مُهيأ - تسجيل الإشعار فقط في قاعدة البيانات")
            db.log_notification(
                shipment_id=shipment_id,
                customer_id=customer_id or "",
                message_text=message,
                channel="telegram",
                delivery_status="failed",
                error_message="bot_not_initialized",
            )
            return False

        if not customer_telegram_id:
            logger.warning(f"⚠️ العميل {customer_name} ليس لديه telegram_id - تسجيل الإشعار فقط")
            db.log_notification(
                shipment_id=shipment_id,
                customer_id=customer_id or "",
                message_text=message,
                channel="telegram",
                delivery_status="failed",
                error_message="no_telegram_id",
            )
            return False

        try:
            await bot.send_message(
                chat_id=customer_telegram_id,
                text=message,
                parse_mode="HTML",
            )
            logger.info(f"✅ تم إرسال إشعار للعميل {customer_name} ({customer_telegram_id})")

            db.log_notification(
                shipment_id=shipment_id,
                customer_id=customer_id or "",
                message_text=message,
                channel="telegram",
                delivery_status="sent",
            )
            return True
        except Exception as e:
            logger.error(f"❌ فشل إرسال إشعار للعميل {customer_name}: {e}")
            db.log_notification(
                shipment_id=shipment_id,
                customer_id=customer_id or "",
                message_text=message,
                channel="telegram",
                delivery_status="failed",
                error_message=str(e),
            )
            return False

    # ============================================================
    #  إرسال تقرير للمدير
    # ============================================================
    async def send_admin_report(
        self, title: str, body: str, level: str = "info"
    ) -> bool:
        """إرسال تقرير للمدير عبر تليجرام."""
        bot = await self._get_bot()
        if bot is None or not self.admin_chat_id:
            logger.info(f"📊 [ADMIN] {title}: {body}")
            return False

        emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(
            level, "ℹ️"
        )
        text = f"{emoji} <b>{title}</b>\n\n{body}"

        try:
            await bot.send_message(
                chat_id=self.admin_chat_id,
                text=text,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"❌ فشل إرسال تقرير للمدير: {e}")
            return False

    # ============================================================
    #  إرسال إشعار متزامن (للاستخدام من سكريبتات sync)
    # ============================================================
    def send_sync(
        self,
        customer_telegram_id: Optional[int],
        customer_name: str,
        tracking_number: str,
        shipment_id: str,
        message: str,
        customer_id: Optional[str] = None,
    ) -> bool:
        """نسخة متزامنة لإرسال الإشعار (للاستخدام من GitHub Actions)."""
        try:
            return asyncio.run(
                self.send_customer_notification(
                    customer_telegram_id=customer_telegram_id,
                    customer_name=customer_name,
                    tracking_number=tracking_number,
                    shipment_id=shipment_id,
                    message=message,
                    customer_id=customer_id,
                )
            )
        except RuntimeError:
            # قد يكون هناك loop نشط
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self.send_customer_notification(
                    customer_telegram_id=customer_telegram_id,
                    customer_name=customer_name,
                    tracking_number=tracking_number,
                    shipment_id=shipment_id,
                    message=message,
                    customer_id=customer_id,
                )
            )

    def send_admin_sync(self, title: str, body: str, level: str = "info") -> bool:
        try:
            return asyncio.run(self.send_admin_report(title, body, level))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self.send_admin_report(title, body, level)
            )


# ============================================================
#  نسخة مشتركة
# ============================================================
notifier = TelegramNotifier()
