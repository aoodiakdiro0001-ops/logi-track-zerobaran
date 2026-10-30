"""
============================================================
  Logi-Track ZeroBaran - طبقة قاعدة البيانات (Supabase)
  المؤلف: Baran Avisat
============================================================
  كل عمليات الإدخال/الإخراج على قاعدة البيانات تمر من هنا.
  تستخدم Supabase Postgres كمخزن مركزي.
============================================================
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from supabase import create_client, Client

from config.settings import settings


# ============================================================
#  حالات الشحنة القياسية
# ============================================================
SHIPMENT_STATUS = {
    "pending": "بانتظار التتبع",
    "in_transit": "في الطريق",
    "out_for_delivery": "خرجت للتوصيل",
    "delivered": "تم التسليم",
    "delayed": "متأخرة",
    "exception": "حالة استثنائية",
    "returned": "مُرجعة",
}


class Database:
    """طبقة قاعدة البيانات المركزية - Logi-Track ZeroBaran."""

    _instance: Optional["Database"] = None
    _client: Optional[Client] = None

    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._client is None and settings.has_supabase:
            try:
                # نستخدم service_role key للوصول الكامل من الخادم
                key = settings.supabase_service_key or settings.supabase_key
                self._client = create_client(settings.supabase_url, key)
                logger.info("✅ تم الاتصال بقاعدة بيانات Supabase بنجاح")
            except Exception as e:
                logger.error(f"❌ فشل الاتصال بـ Supabase: {e}")
                self._client = None

    # ============================================================
    #  خصائص
    # ============================================================
    @property
    def client(self) -> Optional[Client]:
        return self._client

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    # ============================================================
    #  العمليات على جدول العملاء
    # ============================================================
    def upsert_customer(
        self,
        name: str,
        phone: str,
        telegram_id: Optional[int] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """إضافة أو تحديث عميل."""
        if not self.is_connected:
            logger.warning("⚠️ قاعدة البيانات غير متصلة - تخطي upsert_customer")
            return None

        payload = {
            "customer_name": name,
            "phone": phone,
            "telegram_id": telegram_id,
            "email": email,
            "notes": notes,
        }
        try:
            res = (
                self._client.table("customers")
                .upsert(payload, on_conflict="phone")
                .execute()
            )
            logger.info(f"✅ تم حفظ/تحديث العميل: {name} ({phone})")
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ العميل {phone}: {e}")
            return None

    def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        try:
            res = (
                self._client.table("customers")
                .select("*")
                .eq("phone", phone)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب العميل {phone}: {e}")
            return None

    def get_customer_by_telegram(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        try:
            res = (
                self._client.table("customers")
                .select("*")
                .eq("telegram_id", telegram_id)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب العميل بـ telegram_id={telegram_id}: {e}")
            return None

    def list_customers(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        try:
            res = (
                self._client.table("customers")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"❌ خطأ في قائمة العملاء: {e}")
            return []

    # ============================================================
    #  العمليات على جدول الشحنات
    # ============================================================
    def add_shipment(
        self,
        tracking_number: str,
        customer_id: str,
        carrier: str = "unknown",
        origin_address: Optional[str] = None,
        destination_address: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            logger.warning("⚠️ قاعدة البيانات غير متصلة - تخطي add_shipment")
            return None

        payload = {
            "tracking_number": tracking_number,
            "customer_id": customer_id,
            "carrier": carrier,
            "origin_address": origin_address,
            "destination_address": destination_address,
            "status": "pending",
            "status_ar": SHIPMENT_STATUS["pending"],
            "notes": notes,
            "is_active": True,
        }
        try:
            res = self._client.table("shipments").insert(payload).execute()
            logger.info(f"📦 تم تسجيل شحنة جديدة: {tracking_number}")
            # سجل الحدث
            if res.data:
                self.add_event(
                    res.data[0]["id"],
                    "status_change",
                    "تسجيل الشحنة في النظام",
                    {"initial_status": "pending"},
                )
            return res.data[0] if res.data else None
        except Exception as e:
            # قد تكون الشحنة موجودة مسبقاً (unique constraint)
            if "duplicate" in str(e).lower() or "23505" in str(e):
                logger.warning(f"⚠️ الشحنة {tracking_number} موجودة مسبقاً")
                return self.get_shipment(tracking_number)
            logger.error(f"❌ خطأ في إضافة شحنة {tracking_number}: {e}")
            return None

    def get_shipment(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        try:
            res = (
                self._client.table("shipments")
                .select("*")
                .eq("tracking_number", tracking_number)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الشحنة {tracking_number}: {e}")
            return None

    def get_shipment_by_id(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        try:
            res = (
                self._client.table("shipments")
                .select("*")
                .eq("id", shipment_id)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الشحنة {shipment_id}: {e}")
            return None

    def list_active_shipments(self) -> List[Dict[str, Any]]:
        """إرجاع كل الشحنات النشطة (غير المُسلمة بعد)."""
        if not self.is_connected:
            return []
        try:
            res = (
                self._client.table("shipments")
                .select("*, customers(*)")
                .eq("is_active", True)
                .neq("status", "delivered")
                .order("created_at", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الشحنات النشطة: {e}")
            return []

    def list_all_shipments(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        try:
            res = (
                self._client.table("shipments")
                .select("*, customers(*)")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"❌ خطأ في قائمة الشحنات: {e}")
            return []

    def update_shipment_status(
        self,
        shipment_id: str,
        status: str,
        status_ar: Optional[str] = None,
        last_location: Optional[str] = None,
        eta: Optional[str] = None,
    ) -> bool:
        if not self.is_connected:
            return False
        if status not in SHIPMENT_STATUS:
            logger.error(f"❌ حالة غير معروفة: {status}")
            return False
        payload: Dict[str, Any] = {
            "status": status,
            "status_ar": status_ar or SHIPMENT_STATUS[status],
            "last_polled_at": datetime.now(timezone.utc).isoformat(),
        }
        if last_location is not None:
            payload["last_location"] = last_location
        if eta is not None:
            payload["eta"] = eta
        if status == "delivered":
            payload["is_active"] = False
        try:
            self._client.table("shipments").update(payload).eq("id", shipment_id).execute()
            logger.info(f"🔄 تم تحديث الشحنة {shipment_id}: {status_ar or SHIPMENT_STATUS[status]}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الشحنة {shipment_id}: {e}")
            return False

    def deactivate_shipment(self, shipment_id: str) -> bool:
        try:
            self._client.table("shipments").update({"is_active": False}).eq(
                "id", shipment_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف الشحنة: {e}")
            return False

    # ============================================================
    #  العمليات على جدول الأحداث
    # ============================================================
    def add_event(
        self,
        shipment_id: str,
        event_type: str,
        description: str,
        raw_payload: Optional[Dict] = None,
        location: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            return None
        payload = {
            "shipment_id": shipment_id,
            "event_type": event_type,
            "event_description": description,
            "raw_payload": json.dumps(raw_payload, ensure_ascii=False)
            if raw_payload
            else None,
            "location": location,
        }
        try:
            res = self._client.table("shipment_events").insert(payload).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة حدث: {e}")
            return None

    def list_events(self, shipment_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        try:
            res = (
                self._client.table("shipment_events")
                .select("*")
                .eq("shipment_id", shipment_id)
                .order("occurred_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الأحداث: {e}")
            return []

    # ============================================================
    #  العمليات على جدول الإشعارات
    # ============================================================
    def log_notification(
        self,
        shipment_id: str,
        customer_id: str,
        message_text: str,
        channel: str = "telegram",
        ai_generated: bool = True,
        delivery_status: str = "sent",
        error_message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            return None
        payload = {
            "shipment_id": shipment_id,
            "customer_id": customer_id,
            "channel": channel,
            "message_text": message_text,
            "ai_generated": ai_generated,
            "delivery_status": delivery_status,
            "error_message": error_message,
            "sent_at": datetime.now(timezone.utc).isoformat()
            if delivery_status == "sent"
            else None,
        }
        try:
            res = self._client.table("notifications_log").insert(payload).execute()
            # أضف حدث في سجل الشحنة
            self.add_event(
                shipment_id,
                "notification_sent",
                f"تم إرسال إشعار عبر {channel}",
                {"channel": channel, "status": delivery_status},
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الإشعار: {e}")
            return None

    def list_notifications(self, shipment_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        try:
            q = self._client.table("notifications_log").select(
                "*, shipments(tracking_number), customers(customer_name, phone)"
            )
            if shipment_id:
                q = q.eq("shipment_id", shipment_id)
            res = q.order("created_at", desc=True).limit(limit).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"❌ خطأ في قائمة الإشعارات: {e}")
            return []

    # ============================================================
    #  العمليات على جدول الإعدادات
    # ============================================================
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if not self.is_connected:
            return default
        try:
            res = (
                self._client.table("system_settings")
                .select("value")
                .eq("key", key)
                .limit(1)
                .execute()
            )
            return res.data[0]["value"] if res.data else default
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإعداد {key}: {e}")
            return default

    def set_setting(self, key: str, value: str, description: Optional[str] = None) -> bool:
        if not self.is_connected:
            return False
        payload = {"key": key, "value": value}
        if description:
            payload["description"] = description
        try:
            self._client.table("system_settings").upsert(
                payload, on_conflict="key"
            ).execute()
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الإعداد {key}: {e}")
            return False

    # ============================================================
    #  إحصائيات لوحة التحكم
    # ============================================================
    def get_dashboard_stats(self) -> Dict[str, int]:
        """إحصائيات سريعة للوحة التحكم."""
        if not self.is_connected:
            return {
                "total_shipments": 0,
                "in_transit": 0,
                "out_for_delivery": 0,
                "delivered": 0,
                "delayed": 0,
                "exceptions": 0,
                "total_customers": 0,
                "notifications_sent": 0,
                "notifications_24h": 0,
            }
        try:
            res = self._client.rpc("get_dashboard_stats").execute()
            if res.data:
                return res.data if isinstance(res.data, dict) else res.data[0]
        except Exception as e:
            logger.debug(f"⚠️ RPC غير متاح، نحسب الإحصائيات يدوياً: {e}")
        # حساب يدوي
        return self._compute_stats_manually()

    def _compute_stats_manually(self) -> Dict[str, int]:
        stats = {
            "total_shipments": 0,
            "in_transit": 0,
            "out_for_delivery": 0,
            "delivered": 0,
            "delayed": 0,
            "exceptions": 0,
            "total_customers": 0,
            "notifications_sent": 0,
            "notifications_24h": 0,
        }
        if not self.is_connected:
            return stats
        try:
            stats["total_shipments"] = (
                self._client.table("shipments").select("id", count="exact").execute().count or 0
            )
            stats["in_transit"] = (
                self._client.table("shipments")
                .select("id", count="exact")
                .eq("status", "in_transit")
                .execute()
                .count
                or 0
            )
            stats["out_for_delivery"] = (
                self._client.table("shipments")
                .select("id", count="exact")
                .eq("status", "out_for_delivery")
                .execute()
                .count
                or 0
            )
            stats["delivered"] = (
                self._client.table("shipments")
                .select("id", count="exact")
                .eq("status", "delivered")
                .execute()
                .count
                or 0
            )
            stats["delayed"] = (
                self._client.table("shipments")
                .select("id", count="exact")
                .eq("status", "delayed")
                .execute()
                .count
                or 0
            )
            stats["exceptions"] = (
                self._client.table("shipments")
                .select("id", count="exact")
                .eq("status", "exception")
                .execute()
                .count
                or 0
            )
            stats["total_customers"] = (
                self._client.table("customers").select("id", count="exact").execute().count or 0
            )
            stats["notifications_sent"] = (
                self._client.table("notifications_log")
                .select("id", count="exact")
                .eq("delivery_status", "sent")
                .execute()
                .count
                or 0
            )
        except Exception as e:
            logger.error(f"❌ خطأ في الحساب اليدوي للإحصائيات: {e}")
        return stats


# ============================================================
#  نسخة مشتركة (Singleton)
# ============================================================
db = Database()
