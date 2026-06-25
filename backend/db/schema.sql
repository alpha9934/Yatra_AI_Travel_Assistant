-- ============================================================
-- Yatra AI Travel Assistant — Supabase Schema
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- Enable UUID extension (usually already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Bookings Table ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id      TEXT UNIQUE NOT NULL,           -- e.g. YT3A2F1B
    status          TEXT DEFAULT 'confirmed',
    flight_no       TEXT NOT NULL,
    airline         TEXT NOT NULL,
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    route           TEXT,                           -- e.g. BLR → DEL
    departure       TEXT,
    arrival         TEXT,
    duration        TEXT,
    price           NUMERIC(10, 2),
    travel_date     TEXT,
    booked_at       TEXT,
    seat            TEXT,
    class           TEXT DEFAULT 'Economy',
    baggage         TEXT,
    pnr             TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Expenses Table ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS expenses (
    id              TEXT PRIMARY KEY,               -- e.g. EXP-001
    merchant        TEXT,
    date            TEXT,
    total_amount    NUMERIC(10, 2),
    tax_amount      NUMERIC(10, 2),
    net_amount      NUMERIC(10, 2),
    category        TEXT,                           -- meals | transport | accommodation | other
    line_items      JSONB,                          -- [{description, amount}]
    reimbursable    BOOLEAN DEFAULT TRUE,
    policy_flags    JSONB,                          -- ["flag1", "flag2"]
    confidence      NUMERIC(4, 3),
    notes           TEXT,
    source          TEXT DEFAULT 'text',            -- text | image
    logged_at       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── RAG Audit Log ───────────────────────────────────────────
-- Tracks every retrieval query for eval / monitoring
CREATE TABLE IF NOT EXISTS rag_audit (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query           TEXT NOT NULL,
    retrieved_chunks JSONB,                         -- [{id, score, text}]
    answer          TEXT,
    latency_ms      INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Row Level Security (RLS) ────────────────────────────────
-- Enable RLS on all tables (tighten in production with user policies)
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_audit ENABLE ROW LEVEL SECURITY;

-- Service role bypass (used by backend with SERVICE_KEY)
CREATE POLICY "service_role_all_bookings" ON bookings
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "service_role_all_expenses" ON expenses
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "service_role_all_rag_audit" ON rag_audit
    FOR ALL USING (auth.role() = 'service_role');

-- ─── Indexes ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_bookings_booking_id ON bookings(booking_id);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_rag_audit_created ON rag_audit(created_at DESC);
