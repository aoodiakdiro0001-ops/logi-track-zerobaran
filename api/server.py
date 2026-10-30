"""
============================================================
  Logi-Track ZeroBaran - خادم FastAPI
  المؤلف: Baran Avisat
============================================================
  يوفر REST API لإدارة الشحنات والعملاء والإشعارات.
  التشغيل: uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
============================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings, AUTHOR, PROJECT_META
from core.database import db
from core.tracker import tracker
from core.ai_engine import ai_brain
from core.notifier import notifier


# ============================================================
#  نماذج Pydantic
# ============================================================
class CustomerCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., min_length=5, max_length=30)
    telegram_id: Optional[int] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class ShipmentCreate(BaseModel):
    tracking_number: str = Field(..., min_length=3, max_length=100)
    customer_id: str
    carrier: str = "auto"
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    notes: Optional[str] = None


class ShipmentTrack(BaseModel):
    tracking_number: str
    carrier: str = "auto"


class NotificationRequest(BaseModel):
    shipment_id: str
    customer_id: Optional[str] = None


# ============================================================
#  تهيئة التطبيق
# ============================================================
app = FastAPI(
    title=PROJECT_META["name"],
    description=PROJECT_META["description"],
    version=PROJECT_META["version"],
    contact={
        "name": AUTHOR["name"],
        "email": AUTHOR["email"],
    },
    license_info={"name": PROJECT_META["license"]},
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - السماح لكل المصادر في التطوير
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
#  Middleware - تسجيل الطلبات
# ============================================================
@app.middleware("http")
async def log_requests(request, call_next):
    """تسجيل كل طلب HTTP."""
    response = await call_next(request)
    return response


# ============================================================
#  نقاط النهاية - معلومات عامة
# ============================================================
@app.get("/", tags=["info"])
async def root():
    """معلومات عامة عن النظام."""
    return {
        "name": PROJECT_META["name"],
        "version": PROJECT_META["version"],
        "description": PROJECT_META["description"],
        "author": AUTHOR,
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health", tags=["info"])
async def health():
    """فحص صحة النظام."""
    return {
        "status": "healthy",
        "database": "connected" if db.is_connected else "disconnected",
        "ai_provider": settings.ai_provider,
        "telegram": "active" if settings.has_telegram else "inactive",
    }


# ============================================================
#  نقاط النهاية - العملاء
# ============================================================
@app.get("/api/customers", tags=["customers"])
async def list_customers(limit: int = Query(100, ge=1, le=500)):
    """قائمة العملاء."""
    return db.list_customers(limit=limit)


@app.post("/api/customers", tags=["customers"], status_code=201)
async def create_customer(customer: CustomerCreate):
    """إضافة عميل جديد."""
    result = db.upsert_customer(
        name=customer.customer_name,
        phone=customer.phone,
        telegram_id=customer.telegram_id,
        email=customer.email,
        notes=customer.notes,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create customer")
    return result


@app.get("/api/customers/{phone}", tags=["customers"])
async def get_customer(phone: str):
    """البحث عن عميل برقم الهاتف."""
    customer = db.get_customer_by_phone(phone)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


# ============================================================
#  نقاط النهاية - الشحنات
# ============================================================
@app.get("/api/shipments", tags=["shipments"])
async def list_shipments(
    active_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
):
    """قائمة الشحنات."""
    if active_only:
        return db.list_active_shipments()
    return db.list_all_shipments(limit=limit)


@app.post("/api/shipments", tags=["shipments"], status_code=201)
async def create_shipment(shipment: ShipmentCreate):
    """تسجيل شحنة جديدة."""
    result = db.add_shipment(
        tracking_number=shipment.tracking_number,
        customer_id=shipment.customer_id,
        carrier=shipment.carrier,
        origin_address=shipment.origin_address,
        destination_address=shipment.destination_address,
        notes=shipment.notes,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to register shipment")
    return result


@app.get("/api/shipments/{tracking_number}", tags=["shipments"])
async def get_shipment(tracking_number: str):
    """البحث عن شحنة برقم التتبع."""
    shipment = db.get_shipment(tracking_number)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    events = db.list_events(shipment["id"])
    shipment["events"] = events
    return shipment


@app.post("/api/shipments/track", tags=["shipments"])
async def track_shipment(req: ShipmentTrack):
    """تتبع شحنة فورياً عبر شركة الشحن."""
    result = tracker.track(req.tracking_number, req.carrier)
    return {
        "tracking_number": result.tracking_number,
        "carrier": result.carrier,
        "status": result.status,
        "status_ar": result.status_ar,
        "last_location": result.last_location,
        "eta": result.eta.isoformat() if result.eta else None,
        "success": result.success,
        "error": result.error,
    }


@app.put("/api/shipments/{shipment_id}/status", tags=["shipments"])
async def update_shipment_status(
    shipment_id: str,
    status: str = Query(...),
    status_ar: Optional[str] = None,
    last_location: Optional[str] = None,
    eta: Optional[str] = None,
):
    """تحديث حالة شحنة."""
    success = db.update_shipment_status(
        shipment_id, status, status_ar, last_location, eta
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update shipment")
    return {"status": "updated", "shipment_id": shipment_id}


# ============================================================
#  نقاط النهاية - الأحداث
# ============================================================
@app.get("/api/shipments/{shipment_id}/events", tags=["events"])
async def list_events(shipment_id: str, limit: int = Query(50, ge=1, le=200)):
    """سجل أحداث شحنة."""
    return db.list_events(shipment_id, limit=limit)


# ============================================================
#  نقاط النهاية - الإشعارات
# ============================================================
@app.get("/api/notifications", tags=["notifications"])
async def list_notifications(
    shipment_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    """سجل الإشعارات."""
    return db.list_notifications(shipment_id=shipment_id, limit=limit)


@app.post("/api/notifications/compose", tags=["notifications"])
async def compose_notification(req: NotificationRequest):
    """توليد وإرسال إشعار لشحنة."""
    shipment = db.get_shipment_by_id(req.shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    customer_id = req.customer_id or shipment.get("customer_id")
    customer = None
    if customer_id and db.is_connected:
        try:
            res = (
                db.client.table("customers")
                .select("*")
                .eq("id", customer_id)
                .limit(1)
                .execute()
            )
            customer = res.data[0] if res.data else None
        except Exception:
            customer = None

    customer_name = (customer or {}).get("customer_name", "عميلنا الكريم")
    tg_id = (customer or {}).get("telegram_id")

    # توليد رسالة عبر AI
    msg = ai_brain.compose_notification(
        customer_name=customer_name,
        tracking_number=shipment.get("tracking_number", ""),
        status=shipment.get("status", "pending"),
        status_ar=shipment.get("status_ar", ""),
        last_location=shipment.get("last_location"),
        eta=str(shipment.get("eta", "")),
        carrier=shipment.get("carrier"),
    )

    # إرسال
    sent = notifier.send_sync(
        customer_telegram_id=tg_id,
        customer_name=customer_name,
        tracking_number=shipment.get("tracking_number", ""),
        shipment_id=shipment["id"],
        message=msg.body,
        customer_id=customer_id,
    )

    return {
        "message": msg.body,
        "tone": msg.tone,
        "ai_generated": True,
        "sent": sent,
        "channel": "telegram",
    }


# ============================================================
#  نقاط النهاية - الإحصائيات
# ============================================================
@app.get("/api/stats", tags=["stats"])
async def get_stats():
    """إحصائيات لوحة المعلومات."""
    return db.get_dashboard_stats()


# ============================================================
#  نقاط النهاية - الإعدادات
# ============================================================
@app.get("/api/settings/{key}", tags=["settings"])
async def get_setting(key: str):
    """قراءة إعداد."""
    value = db.get_setting(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": key, "value": value}


@app.put("/api/settings/{key}", tags=["settings"])
async def set_setting(key: str, value: str = Query(...), description: Optional[str] = None):
    """تحديث إعداد."""
    success = db.set_setting(key, value, description)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update setting")
    return {"key": key, "value": value, "updated": True}


# ============================================================
#  نقطة النهاية - تشغيل دورة فحص يدوية
# ============================================================
@app.post("/api/admin/poll-now", tags=["admin"])
async def admin_poll_now():
    """تشغيل دورة فحص فورية لكل الشحنات النشطة."""
    if not db.is_connected:
        raise HTTPException(status_code=503, detail="Database not connected")

    active = db.list_active_shipments()
    results = []
    for s in active:
        tracking = s.get("tracking_number")
        carrier = s.get("carrier", "auto")
        try:
            result = tracker.track(tracking, carrier)
            if result.success and result.status != s.get("status"):
                db.update_shipment_status(
                    s["id"],
                    status=result.status,
                    status_ar=result.status_ar,
                    last_location=result.last_location,
                    eta=result.eta.isoformat() if result.eta else None,
                )
                results.append({
                    "tracking_number": tracking,
                    "old_status": s.get("status"),
                    "new_status": result.status,
                    "updated": True,
                })
            else:
                results.append({
                    "tracking_number": tracking,
                    "status": s.get("status"),
                    "updated": False,
                })
        except Exception as e:
            results.append({
                "tracking_number": tracking,
                "error": str(e),
                "updated": False,
            })

    return {
        "polled_count": len(active),
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
#  معالج الأخطاء العام
# ============================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """معالج أخطاء عام."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ============================================================
#  نقطة الدخول
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
