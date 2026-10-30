"""
============================================================
  Logi-Track ZeroBaran - اختبارات الوحدة
  المؤلف: Baran Avisat
============================================================
  اختبارات أساسية للتحقق من صحة المكونات.
  التشغيل: pytest tests/ -v
============================================================
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from config.settings import settings, AUTHOR, PROJECT_META
from core.tracker import tracker, TrackingResult
from core.ai_engine import ai_brain, LogisticsBrain, NotificationMessage


# ============================================================
#  اختبارات الإعدادات
# ============================================================
class TestSettings:
    def test_project_meta(self):
        assert PROJECT_META["name"] == "Logi-Track ZeroBaran"
        assert PROJECT_META["version"] == "1.0.0"

    def test_author_info(self):
        assert AUTHOR["name"] == "Baran Avisat"
        assert AUTHOR["email"] == "Baranavisat@gmail.com"
        assert AUTHOR["whatsapp"] == "00905313263722"

    def test_settings_singleton(self):
        from config.settings import settings as s1
        from config.settings import settings as s2
        assert s1 is s2


# ============================================================
#  اختبارات محرك التتبع
# ============================================================
class TestTracker:
    def test_carrier_detection_dhl(self):
        # DHL: 10 أرقام
        assert tracker._detect_carrier("1234567890") == "dhl"

    def test_carrier_detection_fedex(self):
        # FedEx: 12 رقماً
        assert tracker._detect_carrier("123456789012") == "fedex"

    def test_carrier_detection_ups(self):
        # UPS: يبدأ بـ 1Z
        assert tracker._detect_carrier("1Z999AA10123456784") == "ups"

    def test_carrier_detection_aramex(self):
        # Aramex: يبدأ بـ AR
        assert tracker._detect_carrier("AR12345678901") == "aramex"

    def test_status_mapping(self):
        assert tracker._map_status("delivered") == "delivered"
        assert tracker._map_status("DL") == "delivered"
        assert tracker._map_status("in_transit") == "in_transit"
        assert tracker._map_status("unknown") == "pending"

    def test_status_ar(self):
        assert tracker._status_ar("delivered") == "تم التسليم"
        assert tracker._status_ar("in_transit") == "في الطريق"
        assert tracker._status_ar("unknown") == "بانتظار التتبع"

    def test_eta_estimation(self):
        from datetime import datetime, timezone
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        eta = tracker.estimate_eta("dhl", created)
        assert eta is not None
        assert eta > created


# ============================================================
#  اختبارات العقل الذكي
# ============================================================
class TestAIEngine:
    def test_local_compose_pending(self):
        msg = ai_brain.compose_notification(
            customer_name="أحمد",
            tracking_number="TEST123",
            status="pending",
            status_ar="بانتظار التتبع",
        )
        assert msg.success
        assert "أحمد" in msg.body
        assert "TEST123" in msg.body

    def test_local_compose_delivered(self):
        msg = ai_brain.compose_notification(
            customer_name="سارة",
            tracking_number="ABC456",
            status="delivered",
            status_ar="تم التسليم",
        )
        assert "سارة" in msg.body
        assert "تم تسليمها" in msg.body

    def test_local_compose_in_transit(self):
        msg = ai_brain.compose_notification(
            customer_name="محمد",
            tracking_number="XYZ789",
            status="in_transit",
            status_ar="في الطريق",
            last_location="إسطنبول",
        )
        assert "محمد" in msg.body
        assert "في طريقها" in msg.body


# ============================================================
#  اختبارات قاعدة البيانات (يتطلب اتصال)
# ============================================================
class TestDatabase:
    def test_singleton(self):
        from core.database import db, Database
        assert isinstance(db, Database)

    def test_shipment_status_dict(self):
        from core.database import SHIPMENT_STATUS
        assert "delivered" in SHIPMENT_STATUS
        assert "in_transit" in SHIPMENT_STATUS
        assert SHIPMENT_STATUS["delivered"] == "تم التسليم"


# ============================================================
#  تشغيل الاختبارات
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
