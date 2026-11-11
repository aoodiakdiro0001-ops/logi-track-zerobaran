"""
============================================================
  Logi-Track ZeroBaran - سكريبت الفحص الدوري
  المؤلف: Baran Avisat
============================================================
  يُشغَّل تلقائياً عبر GitHub Actions كل ساعة (أو حسب الجدول).
  يقوم بـ:
  1. سحب كل الشحنات النشطة من قاعدة البيانات
  2. تتبع كل شحنة عبر شركة الشحن
  3. اكتشاف التغيرات في الحالة
  4. توليد رسالة AI وإرسالها للعميل
  5. إرسال تقرير للمدير
============================================================
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# إضافة جذر المشروع
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings, AUTHOR, PROJECT_META
from core.database import db
from core.tracker import tracker
from core.ai_engine import ai_brain
from core.notifier import notifier
from core.logger import logger


async def poll_once() -> dict:
    """تنفيذ دورة فحص واحدة على كل الشحنات النشطة."""
    logger.info("=" * 60)
    logger.info(f"🔄 بدء دورة الفحص - {PROJECT_META['name']}")
    logger.info(f"⏰ الوقت: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    if not db.is_connected:
        logger.error("❌ قاعدة البيانات غير متصلة - لا يمكن متابعة الفحص")
        return {"success": False, "error": "database_disconnected", "polled": 0}

    active = db.list_active_shipments()
    logger.info(f"📦 عدد الشحنات النشطة: {len(active)}")

    if not active:
        logger.info("✅ لا توجد شحنات نشطة للفحص")
        return {
            "success": True,
            "polled": 0,
            "updated": 0,
            "notifications_sent": 0,
        }

    stats = {
        "polled": 0,
        "updated": 0,
        "notifications_sent": 0,
        "errors": 0,
        "details": [],
    }

    for shipment in active:
        tracking = shipment.get("tracking_number", "")
        carrier = shipment.get("carrier", "auto")
        old_status = shipment.get("status", "pending")
        shipment_id = shipment.get("id")

        logger.info(f"🔍 فحص الشحنة: {tracking} (السابقة: {old_status})")
        stats["polled"] += 1

        try:
            result = tracker.track(tracking, carrier)
            if not result.success:
                logger.warning(
                    f"⚠️ لم نتمكن من جلب بيانات {tracking}: {result.error}"
                )
                stats["details"].append({
                    "tracking": tracking,
                    "status": "no_data",
                    "error": result.error,
                })
                continue

            new_status = result.status

            # تحديث آخر موقع ووقت الفحص دائماً
            db.update_shipment_status(
                shipment_id=shipment_id,
                status=new_status,
                status_ar=result.status_ar,
                last_location=result.last_location,
                eta=result.eta.isoformat() if result.eta else None,
            )

            # إضافة حدث للسجل
            db.add_event(
                shipment_id=shipment_id,
                event_type="location_update",
                description=f"آخر موقع: {result.last_location or 'غير محدد'}",
                raw_payload={
                    "status": new_status,
                    "carrier": result.carrier,
                    "last_location": result.last_location,
                },
                location=result.last_location,
            )

            # إن تغيرت الحالة، نولّد إشعاراً ونرسله
            if new_status != old_status:
                logger.info(
                    f"🔄 تغيّرت حالة {tracking}: {old_status} → {new_status}"
                )
                stats["updated"] += 1

                # إضافة حدث تغير الحالة
                db.add_event(
                    shipment_id=shipment_id,
                    event_type="status_change",
                    description=f"تغير الحالة من '{old_status}' إلى '{new_status}'",
                    raw_payload={
                        "old_status": old_status,
                        "new_status": new_status,
                        "status_ar": result.status_ar,
                    },
                )

                # جلب بيانات العميل
                customer = None
                customer_id = shipment.get("customer_id")
                if customer_id:
                    try:
                        res = (
                            db.client.table("customers")
                            .select("*")
                            .eq("id", customer_id)
                            .limit(1)
                            .execute()
                        )
                        customer = res.data[0] if res.data else None
                    except Exception as e:
                        logger.debug(f"ℹ️ فشل جلب العميل: {e}")

                customer_name = (customer or {}).get("customer_name", "عميلنا الكريم")
                tg_id = (customer or {}).get("telegram_id")

                # توليد رسالة عبر العقل الذكي
                msg = ai_brain.compose_notification(
                    customer_name=customer_name,
                    tracking_number=tracking,
                    status=new_status,
                    status_ar=result.status_ar,
                    last_location=result.last_location,
                    eta=result.eta.isoformat() if result.eta else None,
                    carrier=result.carrier,
                )

                # إرسال الإشعار
                sent = await notifier.send_customer_notification(
                    customer_telegram_id=tg_id,
                    customer_name=customer_name,
                    tracking_number=tracking,
                    shipment_id=shipment_id,
                    message=msg.body,
                    customer_id=customer_id,
                )
                if sent:
                    stats["notifications_sent"] += 1

                stats["details"].append({
                    "tracking": tracking,
                    "old_status": old_status,
                    "new_status": new_status,
                    "notification_sent": sent,
                    "ai_message": msg.body[:80] + "...",
                })

            else:
                logger.info(f"✅ لا تغيير في حالة {tracking}")
                stats["details"].append({
                    "tracking": tracking,
                    "status": new_status,
                    "updated": False,
                })

        except Exception as e:
            logger.error(f"❌ خطأ في فحص {tracking}: {e}")
            stats["errors"] += 1
            stats["details"].append({
                "tracking": tracking,
                "error": str(e),
            })

    # === تقرير للمدير ===
    report_body = (
        f"📊 تقرير الفحص الدوري\n"
        f"⏰ الوقت: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"📦 شحنات تم فحصها: {stats['polled']}\n"
        f"🔄 تحديثات جديدة: {stats['updated']}\n"
        f"📨 إشعارات مُرسلة: {stats['notifications_sent']}\n"
        f"❌ أخطاء: {stats['errors']}"
    )
    await notifier.send_admin_report(
        title="تقرير الفحص الدوري",
        body=report_body,
        level="success" if stats["errors"] == 0 else "warning",
    )

    logger.info("=" * 60)
    logger.info(f"✅ انتهت دورة الفحص - {stats}")
    logger.info("=" * 60)

    # نجاح الدورة = لا أخطاء في فحص أي شحنة
    stats["success"] = stats["errors"] == 0
    if not stats["success"]:
        stats["error"] = f"{stats['errors']} shipment error(s)"
    return stats


def main():
    """نقطة الدخول للسكريبت."""
    try:
        stats = asyncio.run(poll_once())
        print(f"\n📊 النتائج النهائية:")
        print(f"  - تم الفحص: {stats.get('polled', 0)}")
        print(f"  - تم التحديث: {stats.get('updated', 0)}")
        print(f"  - إشعارات مُرسلة: {stats.get('notifications_sent', 0)}")
        print(f"  - أخطاء: {stats.get('errors', 0)}")
        # إرجاع رمز فشل حقيقي حتى يعمل إنذار GitHub Actions
        if not stats.get("success", True):
            logger.error(f"❌ انتهت الدورة بفشل: {stats.get('error', 'unknown')}")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف الفحص بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل الفحص: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
