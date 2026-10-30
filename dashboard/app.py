"""
============================================================
  Logi-Track ZeroBaran - لوحة تحكم Streamlit
  المؤلف: Baran Avisat
============================================================
  واجهة ويب احترافية لإدارة الشحنات والعملاء والإشعارات.
  التشغيل: streamlit run dashboard/app.py
============================================================
"""

import sys
from pathlib import Path
from datetime import datetime

# إضافة جذر المشروع إلى sys.path حتى نستطيع استيراد config و core
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.settings import settings, AUTHOR, PROJECT_META
from core.database import db
from core.tracker import tracker
from core.ai_engine import ai_brain
from core.notifier import notifier


# ============================================================
#  إعداد الصفحة
# ============================================================
st.set_page_config(
    page_title=f"{PROJECT_META['name']} - لوحة التحكم",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS مخصص لتحسين المظهر
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
    }
    .main-header h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 700;
    }
    .main-header p {
        margin: 5px 0 0 0;
        opacity: 0.9;
        font-size: 14px;
    }
    .metric-card {
        background: white;
        padding: 18px;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        text-align: center;
        border-right: 4px solid #2a5298;
    }
    .metric-card h3 {
        margin: 0;
        font-size: 32px;
        font-weight: 700;
        color: #1e3c72;
    }
    .metric-card p {
        margin: 5px 0 0 0;
        color: #666;
        font-size: 13px;
    }
    .footer-info {
        background: #f8f9fa;
        padding: 12px 18px;
        border-radius: 8px;
        border-right: 3px solid #1e3c72;
        margin-top: 20px;
        font-size: 13px;
        color: #444;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
#  رأس الصفحة
# ============================================================
st.markdown(f"""
<div class="main-header">
    <h1>🚚 {PROJECT_META['name']}</h1>
    <p>المنظومة الذاتية الذكية لتتبع الشحنات، إدارة مسارات التوصيل، وإشعارات العملاء</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
#  الشريط الجانبي
# ============================================================
st.sidebar.markdown("## 📑 القائمة الرئيسية")
menu = st.sidebar.radio(
    "اختر القسم:",
    [
        "🏠 لوحة المعلومات",
        "📦 الشحنات",
        "➕ تسجيل شحنة",
        "👥 العملاء",
        "📨 سجل الإشعارات",
        "🔍 تتبع فوري",
        "⚙️ الإعدادات",
        "ℹ️ حول النظام",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"""
<div class="footer-info">
<b>👨‍💻 المؤلف:</b> {AUTHOR['name']}<br>
<b>📧 البريد:</b> {AUTHOR['email']}<br>
<b>📱 واتساب:</b> {AUTHOR['whatsapp']}<br>
<b>🔖 الإصدار:</b> {PROJECT_META['version']}
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
#  الصفحة 1: لوحة المعلومات
# ============================================================
def show_dashboard():
    st.markdown("### 🏠 لوحة المعلومات")

    stats = db.get_dashboard_stats()

    # بطاقات الإحصائيات
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{stats.get('total_shipments', 0)}</h3>
            <p>📦 إجمالي الشحنات</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-right-color: #28a745;">
            <h3 style="color: #28a745;">{stats.get('delivered', 0)}</h3>
            <p>✅ تم التسليم</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-right-color: #ffc107;">
            <h3 style="color: #ffc107;">{stats.get('in_transit', 0)}</h3>
            <p>🚚 في الطريق</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card" style="border-right-color: #17a2b8;">
            <h3 style="color: #17a2b8;">{stats.get('notifications_sent', 0)}</h3>
            <p>📨 إشعارات مُرسلة</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # صف ثاني
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🛵 خرجت للتوصيل", stats.get('out_for_delivery', 0))
    with col2:
        st.metric("⏰ متأخرة", stats.get('delayed', 0))
    with col3:
        st.metric("⚠️ حالات استثنائية", stats.get('exceptions', 0))
    with col4:
        st.metric("👥 العملاء", stats.get('total_customers', 0))

    st.markdown("---")

    # رسم بياني: توزيع حالات الشحنات
    st.markdown("### 📊 توزيع حالات الشحنات")
    status_data = pd.DataFrame([
        {"الحالة": "في الطريق", "العدد": stats.get('in_transit', 0)},
        {"الحالة": "خرجت للتوصيل", "العدد": stats.get('out_for_delivery', 0)},
        {"الحالة": "تم التسليم", "العدد": stats.get('delivered', 0)},
        {"الحالة": "متأخرة", "العدد": stats.get('delayed', 0)},
        {"الحالة": "استثنائية", "العدد": stats.get('exceptions', 0)},
    ])
    if status_data["العدد"].sum() > 0:
        fig = px.bar(
            status_data, x="الحالة", y="العدد",
            color="الحالة",
            color_discrete_sequence=["#1e3c72", "#17a2b8", "#28a745", "#ffc107", "#dc3545"],
            text="العدد",
        )
        fig.update_layout(showlegend=False, height=380, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ لا توجد بيانات شحنات لعرضها بعد.")

    # آخر الشحنات
    st.markdown("### 📦 آخر الشحنات المسجلة")
    shipments = db.list_all_shipments(limit=10)
    if shipments:
        df = pd.DataFrame(shipments)
        if not df.empty:
            display_cols = ["tracking_number", "status_ar", "carrier", "last_location", "created_at"]
            available = [c for c in display_cols if c in df.columns]
            st.dataframe(
                df[available].rename(columns={
                    "tracking_number": "رقم التتبع",
                    "status_ar": "الحالة",
                    "carrier": "الشركة",
                    "last_location": "آخر موقع",
                    "created_at": "تاريخ الإنشاء",
                }),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.warning("⚠️ لا توجد شحنات مسجلة. استخدم قسم 'تسجيل شحنة' لإضافة أول شحنة.")


# ============================================================
#  الصفحة 2: قائمة الشحنات
# ============================================================
def show_shipments():
    st.markdown("### 📦 الشحنات")

    # فلاتر
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "تصفية حسب الحالة:",
            ["الكل", "بانتظار التتبع", "في الطريق", "خرجت للتوصيل", "تم التسليم", "متأخرة", "حالة استثنائية"],
        )
    with col2:
        search = st.text_input("🔍 بحث برقم التتبع:")

    shipments = db.list_all_shipments(limit=200)

    if search:
        shipments = [s for s in shipments if search.lower() in str(s.get("tracking_number", "")).lower()]

    status_map = {
        "بانتظار التتبع": "pending",
        "في الطريق": "in_transit",
        "خرجت للتوصيل": "out_for_delivery",
        "تم التسليم": "delivered",
        "متأخرة": "delayed",
        "حالة استثنائية": "exception",
    }
    if status_filter != "الكل" and status_filter in status_map:
        target_status = status_map[status_filter]
        shipments = [s for s in shipments if s.get("status") == target_status]

    if not shipments:
        st.info("ℹ️ لا توجد شحنات مطابقة.")
        return

    for s in shipments:
        status_emoji = {
            "pending": "⏳", "in_transit": "🚚", "out_for_delivery": "🛵",
            "delivered": "✅", "delayed": "⏰", "exception": "⚠️", "returned": "↩️",
        }.get(s.get("status"), "📦")

        customer = s.get("customers") or {}
        customer_name = customer.get("customer_name", "غير محدد") if customer else "غير محدد"
        customer_phone = customer.get("phone", "") if customer else ""

        with st.expander(
            f"{status_emoji} {s.get('tracking_number', '')} - {customer_name} - {s.get('status_ar', '')}"
        ):
            cols = st.columns([2, 2, 2])
            with cols[0]:
                st.write(f"**رقم التتبع:** `{s.get('tracking_number', '')}`")
                st.write(f"**الشركة:** {s.get('carrier', 'غير محدد')}")
                st.write(f"**الحالة:** {s.get('status_ar', 'غير معروفة')}")
            with cols[1]:
                st.write(f"**العميل:** {customer_name}")
                st.write(f"**الهاتف:** {customer_phone}")
                st.write(f"**آخر موقع:** {s.get('last_location', 'غير محدد')}")
            with cols[2]:
                st.write(f"**التسليم المتوقع:** {s.get('eta', 'غير محدد')}")
                st.write(f"**تاريخ الإنشاء:** {str(s.get('created_at', ''))[:16]}")
                st.write(f"**آخر فحص:** {str(s.get('last_polled_at', ''))[:16]}")

            # أزرار إجراءات
            btn_cols = st.columns(3)
            with btn_cols[0]:
                if st.button(f"🔍 فحص فوري", key=f"track_{s['id']}"):
                    result = tracker.track(s.get("tracking_number"), s.get("carrier", "auto"))
                    if result.success:
                        db.update_shipment_status(
                            s["id"],
                            status=result.status,
                            status_ar=result.status_ar,
                            last_location=result.last_location,
                            eta=result.eta.isoformat() if result.eta else None,
                        )
                        st.success(f"✅ تم التحديث: {result.status_ar}")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.error or 'فشل الفحص'}")
            with btn_cols[1]:
                if st.button(f"📨 إرسال إشعار", key=f"notify_{s['id']}"):
                    msg = ai_brain.compose_notification(
                        customer_name=customer_name,
                        tracking_number=s.get("tracking_number", ""),
                        status=s.get("status", "pending"),
                        status_ar=s.get("status_ar", ""),
                        last_location=s.get("last_location"),
                        eta=str(s.get("eta", "")),
                        carrier=s.get("carrier"),
                    )
                    st.info(msg.body)
                    tg_id = customer.get("telegram_id") if customer else None
                    notifier.send_sync(
                        customer_telegram_id=tg_id,
                        customer_name=customer_name,
                        tracking_number=s.get("tracking_number", ""),
                        shipment_id=s["id"],
                        message=msg.body,
                        customer_id=customer.get("id") if customer else None,
                    )
                    st.success("✅ تم إرسال الإشعار")
            with btn_cols[2]:
                if s.get("status") != "delivered" and st.button(f"🚫 إيقاف المتابعة", key=f"deactivate_{s['id']}"):
                    db.deactivate_shipment(s["id"])
                    st.success("تم إيقاف المتابعة")
                    st.rerun()


# ============================================================
#  الصفحة 3: تسجيل شحنة
# ============================================================
def show_register():
    st.markdown("### ➕ تسجيل شحنة جديدة")

    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            tracking = st.text_input("📦 رقم التتبع *", placeholder="مثال: AR123456789")
            customer_name = st.text_input("👤 اسم العميل *", placeholder="الاسم الكامل")
            phone = st.text_input("📱 رقم الهاتف *", placeholder="00905313263722")
        with col2:
            carriers = ["auto", "aramex", "dhl", "fedex", "ups", "ptt", "yurtici", "mng"]
            carrier = st.selectbox("🚚 شركة الشحن", carriers, format_func=lambda x: {
                "auto": "كشف تلقائي", "aramex": "Aramex", "dhl": "DHL",
                "fedex": "FedEx", "ups": "UPS", "ptt": "PTT Kargo",
                "yurtici": "Yurtiçi", "mng": "MNG Kargo",
            }[x])
            telegram_id = st.text_input("Telegram ID (اختياري)", placeholder="123456789")
            email = st.text_input("📧 البريد الإلكتروني (اختياري)", placeholder="customer@example.com")

        origin = st.text_input("📍 عنوان الإرسال (اختياري)")
        destination = st.text_input("📍 عنوان الاستلام (اختياري)")
        notes = st.text_area("📝 ملاحظات (اختياري)", height=80)

        submitted = st.form_submit_button("🚀 تسجيل الشحنة", use_container_width=True)

    if submitted:
        if not tracking or not customer_name or not phone:
            st.error("❌ يرجى ملء الحقول المطلوبة (*).")
            return

        tg_id = int(telegram_id) if telegram_id.isdigit() else None
        customer = db.upsert_customer(
            name=customer_name,
            phone=phone,
            telegram_id=tg_id,
            email=email or None,
            notes=notes or None,
        )
        if not customer:
            st.error("❌ فشل تسجيل العميل.")
            return

        shipment = db.add_shipment(
            tracking_number=tracking,
            customer_id=customer["id"],
            carrier=carrier,
            origin_address=origin or None,
            destination_address=destination or None,
            notes=notes,
        )

        if shipment:
            st.success(f"✅ تم تسجيل الشحنة بنجاح! رقم التتبع: {tracking}")
            st.balloons()

            # محاولة تتبع فوري
            with st.spinner("🔍 جاري التتبع الفوري..."):
                result = tracker.track(tracking, carrier)
                if result.success and result.status != "pending":
                    db.update_shipment_status(
                        shipment["id"],
                        status=result.status,
                        status_ar=result.status_ar,
                        last_location=result.last_location,
                        eta=result.eta.isoformat() if result.eta else None,
                    )
                    st.info(f"📍 الحالة الحالية: {result.status_ar}")
        else:
            st.error("❌ فشل تسجيل الشحنة. قد تكون موجودة مسبقاً.")


# ============================================================
#  الصفحة 4: العملاء
# ============================================================
def show_customers():
    st.markdown("### 👥 العملاء")
    customers = db.list_customers(limit=200)

    if not customers:
        st.info("ℹ️ لا يوجد عملاء مسجلون بعد.")
        return

    df = pd.DataFrame(customers)
    display_cols = ["customer_name", "phone", "telegram_id", "email", "created_at"]
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(
        df[available].rename(columns={
            "customer_name": "الاسم",
            "phone": "الهاتف",
            "telegram_id": "Telegram ID",
            "email": "البريد",
            "created_at": "تاريخ التسجيل",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
#  الصفحة 5: سجل الإشعارات
# ============================================================
def show_notifications():
    st.markdown("### 📨 سجل الإشعارات")
    notifications = db.list_notifications(limit=100)

    if not notifications:
        st.info("ℹ️ لا توجد إشعارات مُرسلة بعد.")
        return

    for n in notifications:
        ship = n.get("shipments") or {}
        cust = n.get("customers") or {}
        emoji = "✅" if n.get("delivery_status") == "sent" else "❌"

        with st.expander(
            f"{emoji} {n.get('channel', '').upper()} - {ship.get('tracking_number', 'غير معروف')} - {cust.get('customer_name', '')}"
        ):
            st.write(f"**القناة:** {n.get('channel', '')}")
            st.write(f"**الحالة:** {n.get('delivery_status', '')}")
            st.write(f"**الوقت:** {n.get('sent_at', n.get('created_at', ''))}")
            st.write(f"**الرسالة:**")
            st.info(n.get("message_text", ""))
            if n.get("ai_generated"):
                st.write("🤖 مُولَّدة بواسطة الذكاء الاصطناعي")
            if n.get("error_message"):
                st.error(f"الخطأ: {n.get('error_message')}")


# ============================================================
#  الصفحة 6: تتبع فوري
# ============================================================
def show_quick_track():
    st.markdown("### 🔍 تتبع فوري")
    st.write("أدخل رقم التتبع للبحث عن شحنة (مع أو بدون تسجيل في النظام).")

    tracking = st.text_input("📦 رقم التتبع:", placeholder="AR123456789")
    carrier = st.selectbox("🚚 شركة الشحن (اختياري)", ["auto", "aramex", "dhl", "fedex", "ups", "ptt", "yurtici", "mng"])

    if st.button("🔍 ابدأ التتبع", use_container_width=True) and tracking:
        with st.spinner("🔍 جاري التتبع..."):
            result = tracker.track(tracking, carrier)

        if result.success:
            st.success(f"✅ تم العثور على بيانات الشحنة")
            cols = st.columns(2)
            with cols[0]:
                st.write(f"**رقم التتبع:** `{result.tracking_number}`")
                st.write(f"**الشركة:** {result.carrier}")
                st.write(f"**الحالة:** {result.status_ar}")
            with cols[1]:
                st.write(f"**الموقع:** {result.last_location or 'غير محدد'}")
                st.write(f"**التسليم المتوقع:** {result.eta or 'غير محدد'}")
                st.write(f"**عدد الأحداث:** {len(result.events)}")

            # معاينة رسالة AI
            st.markdown("---")
            st.markdown("#### 🤖 معاينة رسالة AI")
            msg = ai_brain.compose_notification(
                customer_name="عميلنا الكريم",
                tracking_number=result.tracking_number,
                status=result.status,
                status_ar=result.status_ar,
                last_location=result.last_location,
                eta=str(result.eta) if result.eta else None,
                carrier=result.carrier,
            )
            st.info(msg.body)
        else:
            st.error(f"❌ {result.error or 'تعذّر العثور على بيانات الشحنة'}")


# ============================================================
#  الصفحة 7: الإعدادات
# ============================================================
def show_settings():
    st.markdown("### ⚙️ الإعدادات")

    st.markdown("#### 📊 حالة الاتصالات")
    cols = st.columns(3)
    cols[0].metric("Supabase", "✅ متصل" if settings.has_supabase else "❌ غير متصل")
    cols[1].metric("AI Provider", settings.ai_provider.upper() if settings.ai_provider != "none" else "❌")
    cols[2].metric("Telegram", "✅ مُفعّل" if settings.has_telegram else "❌ غير مُفعّل")

    st.markdown("#### ⏱️ إعدادات النظام")
    st.write(f"**فترة الفحص:** كل {settings.poll_interval_hours} ساعة")
    st.write(f"**المنطقة الزمنية:** {settings.timezone}")
    st.write(f"**اللغة الافتراضية:** {settings.default_language}")

    st.markdown("#### 🔧 إعدادات قابلة للتعديل")
    new_interval = st.number_input(
        "فترة الفحص (ساعات)", min_value=1, max_value=24, value=settings.poll_interval_hours
    )
    if st.button("💾 حفظ الإعدادات"):
        db.set_setting("poll_interval_hours", str(new_interval), "فترة الفحص بالساعات")
        st.success("✅ تم حفظ الإعدادات")


# ============================================================
#  الصفحة 8: حول النظام
# ============================================================
def show_about():
    st.markdown(f"### ℹ️ حول {PROJECT_META['name']}")

    st.markdown(f"""
<div class="main-header" style="text-align: center;">
    <h1>🚚 {PROJECT_META['name']}</h1>
    <p>{PROJECT_META['description']}</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("#### 📋 ما هو هذا النظام؟")
    st.markdown(PROJECT_META['description'])

    st.markdown("#### 🛠️ البنية التقنية")
    tech_df = pd.DataFrame([
        {"المكون": "محرك التشغيل", "التقنية": "GitHub Actions", "الدور": "فحص دوري للشحنات"},
        {"المكون": "محرك المعالجة", "التقنية": "Python + FastAPI", "الدور": "سحب ومعالجة البيانات"},
        {"المكون": "العقل الذكي", "التقنية": "Gemini / Groq", "الدور": "صياغة الإشعارات الذكية"},
        {"المكون": "قاعدة البيانات", "التقنية": "Supabase Postgres", "الدور": "تخزين كل البيانات"},
        {"المكون": "واجهة الاستقبال", "التقنية": "Telegram Bot + Streamlit", "الدور": "إدخال وإشعارات"},
    ])
    st.dataframe(tech_df, use_container_width=True, hide_index=True)

    st.markdown("#### ⚙️ كيف يعمل؟")
    st.markdown("""
1. **التسجيل:** تُدخل رقم التتبع وبيانات العميل عبر بوت تليجرام أو لوحة التحكم.
2. **المتابعة:** يستيقظ GitHub Actions دورياً ليفحص أحدث مستجدات الشحنة.
3. **التحديث:** عند تغير الحالة، يصيغ الذكاء الاصطناعي رسالة احترافية للعميل.
4. **النتيجة:** يتلقى العميل تحديثاً فورياً، ويصلك تقرير لوجستي على هاتفك.
""")

    st.markdown("#### 💎 لماذا هذا النظام؟")
    st.markdown("""
- 💰 **توفير مال فلكي:** بديل مجاني لأدوات التتبع المدفوعة.
- 📉 **تقليل استفسارات الدعم:** بشكل ملحوظ.
- 🔒 **السيادة والخصوصية:** بياناتك لا تُشارك مع أي طرف خارجي.
""")

    st.markdown("#### 👨‍💻 معلومات المطور والحقوق")
    st.markdown(f"""
<div class="footer-info">
<b>المؤلف:</b> {AUTHOR['name']}<br>
<b>البريد:</b> <a href="mailto:{AUTHOR['email']}">{AUTHOR['email']}</a><br>
<b>واتساب:</b> {AUTHOR['whatsapp']}<br>
<b>الإصدار:</b> {PROJECT_META['version']}<br>
<b>الترخيص:</b> {PROJECT_META['license']}
</div>
""", unsafe_allow_html=True)


# ============================================================
#  توجيه الصفحة
# ============================================================
if menu == "🏠 لوحة المعلومات":
    show_dashboard()
elif menu == "📦 الشحنات":
    show_shipments()
elif menu == "➕ تسجيل شحنة":
    show_register()
elif menu == "👥 العملاء":
    show_customers()
elif menu == "📨 سجل الإشعارات":
    show_notifications()
elif menu == "🔍 تتبع فوري":
    show_quick_track()
elif menu == "⚙️ الإعدادات":
    show_settings()
elif menu == "ℹ️ حول النظام":
    show_about()


# ============================================================
#  الفوتر
# ============================================================
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #888; font-size: 12px;">
🚚 <b>{PROJECT_META['name']}</b> v{PROJECT_META['version']} —
تم التطوير بواسطة <b>{AUTHOR['name']}</b> —
© 2026 جميع الحقوق محفوظة
</div>
""", unsafe_allow_html=True)
