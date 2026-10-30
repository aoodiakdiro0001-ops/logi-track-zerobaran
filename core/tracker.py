"""
============================================================
  Logi-Track ZeroBaran - محرك التتبع اللوجستي (Tracker)
  المؤلف: Baran Avisat
============================================================
  هذه الوحدة مسؤولة عن:
  - سحب بيانات الشحن من APIs شركات الشحن
  - تحويل الحالات التقنية إلى حالات موحدة
  - رصد التغيرات في حالة الشحنة
  - حساب أوقات التوصيل المتوقعة (ETA)
============================================================
"""

from __future__ import annotations

import httpx
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, field

from loguru import logger

from config.settings import settings


# ============================================================
#  نماذج البيانات
# ============================================================
@dataclass
class TrackingEvent:
    """حدث واحد في خط سير الشحنة."""

    event_type: str
    description: str
    location: Optional[str] = None
    timestamp: Optional[datetime] = None
    raw_data: Dict = field(default_factory=dict)


@dataclass
class TrackingResult:
    """نتيجة الاستعلام عن شحنة من شركة الشحن."""

    tracking_number: str
    carrier: str
    status: str  # pending, in_transit, out_for_delivery, delivered, delayed, exception, returned
    status_ar: str
    last_location: Optional[str] = None
    eta: Optional[datetime] = None
    events: list[TrackingEvent] = field(default_factory=list)
    raw_response: Dict = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


# ============================================================
#  محرك التتبع - يقوم بتنسيق سحب البيانات من شركات الشحن
# ============================================================
class ShipmentTracker:
    """المحرك المركزي لتتبع الشحنات - Logi-Track ZeroBaran."""

    def __init__(self) -> None:
        self.http = httpx.Client(timeout=30.0, follow_redirects=True)
        self.headers = {
            "User-Agent": "LogiTrack-ZeroBaran/1.0 (https://github.com/baranavisat)",
            "Accept": "application/json",
        }

    # ============================================================
    #  تتبع شحنة عبر شركة الشحن المناسبة
    # ============================================================
    def track(self, tracking_number: str, carrier: str = "auto") -> TrackingResult:
        """تتبع شحنة - يكتشف شركة الشحن تلقائياً إن لزم."""
        carrier = (carrier or "auto").lower().strip()
        logger.info(f"🔍 بدء تتبع الشحنة: {tracking_number} (الشركة: {carrier})")

        if carrier == "auto":
            carrier = self._detect_carrier(tracking_number)
            logger.info(f"🏷️ تم اكتشاف شركة الشحن: {carrier}")

        handlers = {
            "aramex": self._track_aramex,
            "dhl": self._track_dhl,
            "fedex": self._track_fedex,
            "ups": self._track_ups,
            "ptt": self._track_ptt,
            "yurtici": self._track_yurtici,
            "mng": self._track_mng,
            "ptt_kargo": self._track_ptt,
            "auto": self._track_generic,
        }

        handler = handlers.get(carrier, self._track_generic)
        try:
            result = handler(tracking_number)
            if not result.success:
                logger.warning(f"⚠️ لم يتم العثور على بيانات للشحنة {tracking_number}")
            return result
        except Exception as e:
            logger.error(f"❌ خطأ أثناء تتبع {tracking_number}: {e}")
            return TrackingResult(
                tracking_number=tracking_number,
                carrier=carrier,
                status="exception",
                status_ar="حالة استثنائية",
                success=False,
                error=str(e),
            )

    # ============================================================
    #  كشف شركة الشحن من رقم التتبع
    # ============================================================
    def _detect_carrier(self, tracking_number: str) -> str:
        """كشف شركة الشحن بناءً على نمط رقم التتبع."""
        tn = tracking_number.upper().strip()

        # DHL Express: عادةً 10 أرقام
        if tn.isdigit() and len(tn) == 10:
            return "dhl"

        # FedEx Express: 12 أو 15 أو 20 أو 22 رقماً
        if tn.isdigit() and len(tn) in (12, 15, 20, 22):
            return "fedex"

        # UPS: يبدأ بـ 1Z غالباً
        if tn.startswith("1Z"):
            return "ups"

        # Aramex: غالباً أحرف وأرقام بطول 11-15
        if any(tn.startswith(p) for p in ("AR", "ARAM", "AJ")) or (
            tn.isalnum() and 11 <= len(tn) <= 15 and not tn.isdigit()
        ):
            return "aramex"

        # PTT Kargo (تركيا): يبدأ بـ P عادةً أو أرقام
        if tn.startswith("P") or (tn.isdigit() and len(tn) == 13):
            return "ptt"

        # Yurtiçi Kargo
        if tn.startswith("YK") or tn.startswith("Y"):
            return "yurtici"

        # MNG Kargo
        if tn.startswith("MNG"):
            return "mng"

        return "generic"

    # ============================================================
    #  تتبع عبر Aramex
    # ============================================================
    def _track_aramex(self, tracking_number: str) -> TrackingResult:
        """تتبع شحنة Aramex عبر API الرسمي (إن توفر مفتاح) أو عبر صفحة التتبع."""
        if not settings.aramex_api_key:
            # وضع المحاكاة: نحاول سحب صفحة التتبع العامة
            return self._track_via_public_page(
                tracking_number, "aramex",
                url=f"https://www.aramex.com/track/results?ShipmentNumber={tracking_number}",
            )

        # API الرسمي - يُكمل لاحقاً بمفتاح API الحقيقي
        try:
            res = self.http.post(
                "https://www.aramex.com/api/track/v1/shipments",
                json={
                    "ClientInfo": {"APIKey": settings.aramex_api_key},
                    "Shipments": [tracking_number],
                },
                headers=self.headers,
            )
            res.raise_for_status()
            data = res.json()
            return self._parse_carrier_response(tracking_number, "aramex", data)
        except Exception as e:
            logger.error(f"❌ Aramex API error: {e}")
            return TrackingResult(
                tracking_number=tracking_number, carrier="aramex",
                status="exception", status_ar="حالة استثنائية",
                success=False, error=str(e),
            )

    # ============================================================
    #  تتبع عبر DHL
    # ============================================================
    def _track_dhl(self, tracking_number: str) -> TrackingResult:
        if not settings.dhl_api_key:
            return self._track_via_public_page(
                tracking_number, "dhl",
                url=f"https://www.dhl.com/global-en/home/tracking.html?tracking-id={tracking_number}",
            )
        try:
            res = self.http.get(
                f"https://api.dhl.com/track/shipments?trackingNumber={tracking_number}",
                headers={**self.headers, "DHL-API-Key": settings.dhl_api_key},
            )
            res.raise_for_status()
            data = res.json()
            return self._parse_carrier_response(tracking_number, "dhl", data)
        except Exception as e:
            logger.error(f"❌ DHL API error: {e}")
            return TrackingResult(
                tracking_number=tracking_number, carrier="dhl",
                status="exception", status_ar="حالة استثنائية",
                success=False, error=str(e),
            )

    # ============================================================
    #  تتبع عبر FedEx
    # ============================================================
    def _track_fedex(self, tracking_number: str) -> TrackingResult:
        if not settings.fedex_api_key:
            return self._track_via_public_page(
                tracking_number, "fedex",
                url=f"https://www.fedex.com/fedextrack/?trknbr={tracking_number}",
            )
        try:
            res = self.http.post(
                "https://apis.fedex.com/track/v2/shipments",
                json={
                    "includeDetailedScans": True,
                    "trackingInfo": [{"trackingNumberInfo": {"trackingNumber": tracking_number}}],
                },
                headers={**self.headers, "X-API-KEY": settings.fedex_api_key},
            )
            res.raise_for_status()
            data = res.json()
            return self._parse_carrier_response(tracking_number, "fedex", data)
        except Exception as e:
            logger.error(f"❌ FedEx API error: {e}")
            return TrackingResult(
                tracking_number=tracking_number, carrier="fedex",
                status="exception", status_ar="حالة استثنائية",
                success=False, error=str(e),
            )

    # ============================================================
    #  تتبع UPS
    # ============================================================
    def _track_ups(self, tracking_number: str) -> TrackingResult:
        return self._track_via_public_page(
            tracking_number, "ups",
            url=f"https://www.ups.com/track?tracknum={tracking_number}",
        )

    # ============================================================
    #  تتبع PTT Kargo (تركيا)
    # ============================================================
    def _track_ptt(self, tracking_number: str) -> TrackingResult:
        if not settings.turkey_ptt_api_key:
            return self._track_via_public_page(
                tracking_number, "ptt",
                url=f"https://www.ptt.gov.tr/tr/interaktif/kargo-sorgula.html?barkod={tracking_number}",
            )
        try:
            res = self.http.get(
                f"https://api.ptt.gov.tr/kargo/sorgula?barkod={tracking_number}",
                headers={**self.headers, "Authorization": f"Bearer {settings.turkey_ptt_api_key}"},
            )
            res.raise_for_status()
            data = res.json()
            return self._parse_carrier_response(tracking_number, "ptt", data)
        except Exception as e:
            logger.error(f"❌ PTT API error: {e}")
            return TrackingResult(
                tracking_number=tracking_number, carrier="ptt",
                status="exception", status_ar="حالة استثنائية",
                success=False, error=str(e),
            )

    # ============================================================
    #  Yurtiçi Kargo
    # ============================================================
    def _track_yurtici(self, tracking_number: str) -> TrackingResult:
        return self._track_via_public_page(
            tracking_number, "yurtici",
            url=f"https://www.yurticikargo.com/tr/online-servisler/gonderi-sorgula?code={tracking_number}",
        )

    # ============================================================
    #  MNG Kargo
    # ============================================================
    def _track_mng(self, tracking_number: str) -> TrackingResult:
        return self._track_via_public_page(
            tracking_number, "mng",
            url=f"https://www.mngkargo.com.tr/tr/gonderi-sorgulama?gk={tracking_number}",
        )

    # ============================================================
    #  تتبع عام - يستخدم صفحة التتبع العامة
    # ============================================================
    def _track_generic(self, tracking_number: str) -> TrackingResult:
        """تتبع عام عندما لا نعرف شركة الشحن."""
        return TrackingResult(
            tracking_number=tracking_number,
            carrier="unknown",
            status="pending",
            status_ar="بانتظار التتبع - شركة شحن غير معروفة",
            success=False,
            error="carrier_unknown",
        )

    # ============================================================
    #  تتبع عبر صفحة عامة (Fallback)
    # ============================================================
    def _track_via_public_page(
        self, tracking_number: str, carrier: str, url: str
    ) -> TrackingResult:
        """محاولة سحب بيانات من صفحة التتبع العامة بدون API."""
        try:
            res = self.http.get(url, headers=self.headers)
            if res.status_code == 200:
                # نحاول استخراج الحالة من النص (مبسط)
                text = res.text.lower()
                status = self._guess_status_from_text(text)
                return TrackingResult(
                    tracking_number=tracking_number,
                    carrier=carrier,
                    status=status,
                    status_ar=self._status_ar(status),
                    raw_response={"url": url, "http_status": res.status_code},
                )
        except Exception as e:
            logger.debug(f"ℹ️ لم نتمكن من سحب الصفحة العامة: {e}")

        return TrackingResult(
            tracking_number=tracking_number,
            carrier=carrier,
            status="pending",
            status_ar="بانتظار التتبع",
            success=False,
            error="no_api_key_no_public_data",
        )

    # ============================================================
    #  تحليل استجابة شركة الشحن
    # ============================================================
    def _parse_carrier_response(
        self, tracking_number: str, carrier: str, data: Dict
    ) -> TrackingResult:
        """تحويل استجابة شركة الشحن إلى نموذج موحد."""
        # هذا تحليل مبسط - كل شركة لها بنية مختلفة
        try:
            # محاولة استخراج الحالة من أعماق الاستجابة
            status_str = "pending"
            last_location = None
            eta = None

            # DHL structure
            if carrier == "dhl":
                shipments = data.get("shipments", [])
                if shipments:
                    s = shipments[0]
                    status_obj = s.get("status", {})
                    statusCode = status_obj.get("statusCode", "pending").lower()
                    status_str = self._map_status(statusCode)
                    if s.get("estimatedTimeOfDelivery"):
                        eta = datetime.fromisoformat(
                            s["estimatedTimeOfDelivery"].replace("Z", "+00:00")
                        )
                    events = s.get("events", [])
                    if events:
                        last_location = events[0].get("location", {}).get("address", {}).get("addressLocality")

            # FedEx structure
            elif carrier == "fedex":
                results = data.get("output", {}).get("completeTrackResults", [])
                if results:
                    tracks = results[0].get("trackResults", [])
                    if tracks:
                        latest = tracks[0].get("latestStatusDetail", {})
                        code = latest.get("code", "").lower()
                        status_str = self._map_status(code)
                        last_location = latest.get("scanLocation", {}).get("city")

            return TrackingResult(
                tracking_number=tracking_number,
                carrier=carrier,
                status=status_str,
                status_ar=self._status_ar(status_str),
                last_location=last_location,
                eta=eta,
                raw_response=data,
            )
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل استجابة {carrier}: {e}")
            return TrackingResult(
                tracking_number=tracking_number, carrier=carrier,
                status="exception", status_ar="حالة استثنائية",
                success=False, error=str(e),
            )

    # ============================================================
    #  دوال مساعدة لتحويل الحالات
    # ============================================================
    def _map_status(self, code: str) -> str:
        """تحويل رمز حالة شركة الشحن إلى حالة موحدة."""
        code = (code or "").lower()
        mapping = {
            # Delivered
            "dl": "delivered", "del": "delivered", "delivered": "delivered",
            "ok": "delivered", "completed": "delivered", "tamamlandi": "delivered",
            # Out for delivery
            "od": "out_for_delivery", "of": "out_for_delivery",
            "outfor": "out_for_delivery", "out_for_delivery": "out_for_delivery",
            "dağıtımaçıktı": "out_for_delivery",
            # In transit
            "it": "in_transit", "in_transit": "in_transit", "transit": "in_transit",
            "yolda": "in_transit", "transfer": "in_transit", "arrived": "in_transit",
            "departed": "in_transit", "inb": "in_transit",
            # Delayed
            "de": "delayed", "delay": "delayed", "delayed": "delayed",
            # Exception
            "ex": "exception", "exception": "exception", "undeliverable": "exception",
            # Returned
            "rt": "returned", "returned": "returned", "return": "returned",
            # Pending
            "pu": "pending", "pending": "pending", "ip": "pending", "picked": "pending",
        }
        return mapping.get(code, "pending")

    def _guess_status_from_text(self, text: str) -> str:
        """تخمين الحالة من نص الصفحة (عندما لا يتوفر API)."""
        if "delivered" in text or "تم التسليم" in text or "teslim edildi" in text:
            return "delivered"
        if "out for delivery" in text or "خرجت للتوصيل" in text or "dağıtıma çıktı" in text:
            return "out_for_delivery"
        if "in transit" in text or "في الطريق" in text or "yolda" in text:
            return "in_transit"
        if "delay" in text or "تأخير" in text or "gecikme" in text:
            return "delayed"
        if "exception" in text or "استثنائية" in text:
            return "exception"
        if "return" in text or "مرتجع" in text or "iade" in text:
            return "returned"
        return "pending"

    def _status_ar(self, status: str) -> str:
        mapping = {
            "pending": "بانتظار التتبع",
            "in_transit": "في الطريق",
            "out_for_delivery": "خرجت للتوصيل",
            "delivered": "تم التسليم",
            "delayed": "متأخرة",
            "exception": "حالة استثنائية",
            "returned": "مُرجعة",
        }
        return mapping.get(status, "بانتظار التتبع")

    # ============================================================
    #  حساب ETA التقديري
    # ============================================================
    def estimate_eta(self, carrier: str, created_at: Optional[datetime] = None) -> Optional[datetime]:
        """حساب وقت التسليم المتوقع بناءً على نوع شركة الشحن."""
        # تقديرات افتراضية بالأيام
        eta_days = {
            "dhl": 3, "fedex": 3, "ups": 3,
            "aramex": 4, "ptt": 5, "yurtici": 3, "mng": 4,
            "unknown": 7, "generic": 7,
        }
        days = eta_days.get(carrier, 7)
        base = created_at or datetime.now(timezone.utc)
        return base + timedelta(days=days)

    # ============================================================
    #  إغلاق
    # ============================================================
    def close(self) -> None:
        self.http.close()


# ============================================================
#  نسخة مشتركة
# ============================================================
tracker = ShipmentTracker()
