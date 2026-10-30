-- ============================================================
--  Logi-Track ZeroBaran - مخطط قاعدة البيانات
--  المؤلف: Baran Avisat (Baranavisat@gmail.com)
--  يُنفَّذ على Supabase PostgreSQL عبر SQL Editor
-- ============================================================

-- === تمديدات ضرورية ===
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
--  جدول العملاء
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_name   TEXT NOT NULL,
    phone           TEXT NOT NULL,
    telegram_id     BIGINT,
    email           TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(phone)
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_telegram ON customers(telegram_id);

-- ============================================================
--  جدول الشحنات
-- ============================================================
CREATE TABLE IF NOT EXISTS shipments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tracking_number     TEXT NOT NULL UNIQUE,
    customer_id         UUID REFERENCES customers(id) ON DELETE CASCADE,
    carrier             TEXT NOT NULL DEFAULT 'unknown',
    origin_address      TEXT,
    destination_address TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    -- الحالات: pending, in_transit, out_for_delivery, delivered, delayed, exception, returned
    status_ar           TEXT DEFAULT 'بانتظار التتبع',
    last_location       TEXT,
    eta                 TIMESTAMPTZ,
    weight              TEXT,
    notes               TEXT,
    is_active           BOOLEAN DEFAULT TRUE,
    last_polled_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shipments_tracking ON shipments(tracking_number);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_customer ON shipments(customer_id);
CREATE INDEX IF NOT EXISTS idx_shipments_active ON shipments(is_active) WHERE is_active = TRUE;

-- ============================================================
--  جدول سجل تحركات الشحنة (Timeline)
-- ============================================================
CREATE TABLE IF NOT EXISTS shipment_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id     UUID REFERENCES shipments(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    -- الأنواع: status_change, location_update, eta_update, notification_sent, ai_message
    event_description TEXT,
    raw_payload     JSONB,
    location        TEXT,
    occurred_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_shipment ON shipment_events(shipment_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON shipment_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_time ON shipment_events(occurred_at DESC);

-- ============================================================
--  جدول الإشعارات المُرسلة
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id     UUID REFERENCES shipments(id) ON DELETE CASCADE,
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    channel         TEXT NOT NULL DEFAULT 'telegram',
    -- القنوات: telegram, whatsapp, email, sms
    message_text    TEXT NOT NULL,
    ai_generated    BOOLEAN DEFAULT FALSE,
    delivery_status TEXT DEFAULT 'pending',
    -- حالات: pending, sent, failed, delivered
    sent_at         TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_shipment ON notifications_log(shipment_id);
CREATE INDEX IF NOT EXISTS idx_notif_status ON notifications_log(delivery_status);

-- ============================================================
--  جدول إعدادات النظام
-- ============================================================
CREATE TABLE IF NOT EXISTS system_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    description TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO system_settings (key, value, description) VALUES
    ('project_name', 'Logi-Track ZeroBaran', 'اسم المشروع'),
    ('project_version', '1.0.0', 'إصدار المشروع'),
    ('author', 'Baran Avisat', 'اسم المؤلف'),
    ('author_email', 'Baranavisat@gmail.com', 'بريد المؤلف'),
    ('author_whatsapp', '00905313263722', 'واتساب المؤلف'),
    ('poll_interval_hours', '1', 'فترة الفحص الدوري بالساعات'),
    ('timezone', 'Asia/Istanbul', 'المنطقة الزمنية')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
--  جدول سجل العمليات (Audit Log)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action      TEXT NOT NULL,
    actor       TEXT DEFAULT 'system',
    entity_type TEXT,
    entity_id   UUID,
    details     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at DESC);

-- ============================================================
--  Trigger لتحديث حقل updated_at تلقائياً
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_customers_updated ON customers;
CREATE TRIGGER trg_customers_updated BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_shipments_updated ON shipments;
CREATE TRIGGER trg_shipments_updated BEFORE UPDATE ON shipments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_settings_updated ON system_settings;
CREATE TRIGGER trg_settings_updated BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
--  عرض إحصائي سريع
-- ============================================================
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT
    (SELECT COUNT(*) FROM shipments) AS total_shipments,
    (SELECT COUNT(*) FROM shipments WHERE status = 'in_transit') AS in_transit,
    (SELECT COUNT(*) FROM shipments WHERE status = 'out_for_delivery') AS out_for_delivery,
    (SELECT COUNT(*) FROM shipments WHERE status = 'delivered') AS delivered,
    (SELECT COUNT(*) FROM shipments WHERE status = 'delayed') AS delayed,
    (SELECT COUNT(*) FROM shipments WHERE status = 'exception') AS exceptions,
    (SELECT COUNT(*) FROM customers) AS total_customers,
    (SELECT COUNT(*) FROM notifications_log WHERE delivery_status = 'sent') AS notifications_sent,
    (SELECT COUNT(*) FROM notifications_log WHERE created_at > NOW() - INTERVAL '24 hours') AS notifications_24h;

-- ============================================================
--  Row Level Security (RLS)
-- ============================================================
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- سياسة السماح للخدمة (service_role) بالوصول الكامل
CREATE POLICY "service_role_all_customers" ON customers
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_role_all_shipments" ON shipments
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_role_all_events" ON shipment_events
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_role_all_notifications" ON notifications_log
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_role_all_settings" ON system_settings
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_role_all_audit" ON audit_log
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================================
--  نهاية المخطط - Logi-Track ZeroBaran v1.0.0
-- ============================================================
