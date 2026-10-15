-- ==============================================================================
-- SHOPO ROBO INVENTORY STORE - SUPABASE DATABASE SCHEMA
-- Multi-User Gmail Authenticated Architecture with Voice Khata Ledger
-- Run this script in the Supabase SQL Editor (https://app.supabase.com)
-- ==============================================================================

-- 1. Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Shop Configuration & Profiles Table (Isolated by user_email)
CREATE TABLE IF NOT EXISTS shop_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL UNIQUE,
    shop_name TEXT NOT NULL DEFAULT 'My Store',
    shop_type TEXT NOT NULL DEFAULT 'General Store',
    owner_name TEXT NOT NULL DEFAULT 'Shop Owner',
    currency TEXT NOT NULL DEFAULT 'INR',
    currency_symbol TEXT NOT NULL DEFAULT '₹',
    location TEXT NOT NULL DEFAULT 'India',
    is_onboarded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Inventory Table (User-specific)
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'General',
    stock_quantity NUMERIC NOT NULL DEFAULT 0,
    unit TEXT NOT NULL DEFAULT 'kg',
    min_threshold NUMERIC NOT NULL DEFAULT 10,
    buy_price NUMERIC NOT NULL DEFAULT 0,
    sell_price NUMERIC NOT NULL DEFAULT 0,
    market_price NUMERIC NOT NULL DEFAULT 0,
    market_change_pct NUMERIC NOT NULL DEFAULT 0,
    icon_type TEXT DEFAULT 'box',
    is_loss_making BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Shopkeeper Digital Khata (Ledger / Udhar-Jama Records)
CREATE TABLE IF NOT EXISTS khata_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    phone_number TEXT,
    entry_type TEXT NOT NULL, -- 'udhar' (you gave/debit), 'jama' (you got/credit)
    amount NUMERIC NOT NULL,
    note TEXT,
    date DATE DEFAULT CURRENT_DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Sales Records Table
CREATE TABLE IF NOT EXISTS sales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    item_id UUID REFERENCES inventory(id) ON DELETE SET NULL,
    item_name TEXT NOT NULL,
    quantity NUMERIC NOT NULL,
    unit TEXT NOT NULL,
    sale_price NUMERIC NOT NULL,
    cost_price NUMERIC NOT NULL,
    total_amount NUMERIC NOT NULL,
    profit_amount NUMERIC NOT NULL,
    date DATE DEFAULT CURRENT_DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. AI Alerts Table
CREATE TABLE IF NOT EXISTS ai_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    alert_type TEXT NOT NULL, -- 'low_stock', 'price_increase', 'price_decrease', 'loss_item', 'khata_reminder'
    message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info', -- 'info', 'warning', 'danger', 'success'
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 7. Row Level Security (RLS)
ALTER TABLE shop_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE khata_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read/write on shop_settings" ON shop_settings FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read/write on inventory" ON inventory FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read/write on khata_entries" ON khata_entries FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read/write on sales" ON sales FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read/write on ai_alerts" ON ai_alerts FOR ALL USING (true) WITH CHECK (true);
