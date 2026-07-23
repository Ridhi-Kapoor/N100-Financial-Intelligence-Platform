-- Enable SQLite Foreign Key constraints
PRAGMA foreign_keys = ON;

-- Drop existing tables to ensure clean initialization (reverse order of dependencies)
DROP TABLE IF EXISTS stock_prices;
DROP TABLE IF EXISTS sectors;
DROP TABLE IF EXISTS peer_percentiles;
DROP TABLE IF EXISTS peer_groups;
DROP TABLE IF EXISTS market_cap;
DROP TABLE IF EXISTS financial_ratios;
DROP TABLE IF EXISTS analysis;
DROP TABLE IF EXISTS cashflow;
DROP TABLE IF EXISTS balancesheet;
DROP TABLE IF EXISTS profitandloss;
DROP TABLE IF EXISTS companies;

-- 1. Companies Table
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    company_logo TEXT,
    company_name TEXT,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);

-- 2. Profit and Loss Table
CREATE TABLE IF NOT EXISTS profitandloss (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax_percentage REAL,
    net_profit REAL,
    eps REAL,
    dividend_payout REAL,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 3. Balance Sheet Table
CREATE TABLE IF NOT EXISTS balancesheet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    cwip REAL,
    investments REAL,
    other_asset REAL,
    total_assets REAL,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 4. Cash Flow Table
CREATE TABLE IF NOT EXISTS cashflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    operating_activity REAL,
    investing_activity REAL,
    financing_activity REAL,
    net_cash_flow REAL,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 5. Analysis Table
CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 6. Financial Ratios Table
CREATE TABLE IF NOT EXISTS financial_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    asset_turnover REAL,
    free_cash_flow_cr REAL,
    capex_cr REAL,
    earnings_per_share REAL,
    book_value_per_share REAL,
    dividend_payout_ratio_pct REAL,
    total_debt_cr REAL,
    cash_from_operations_cr REAL,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 7. Market Capitalization Table
CREATE TABLE IF NOT EXISTS market_cap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    market_cap_crore REAL,
    enterprise_value_crore REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 8. Peer Groups Table
CREATE TABLE IF NOT EXISTS peer_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_group_name TEXT NOT NULL,
    company_id TEXT NOT NULL,
    is_benchmark TEXT,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 8b. Peer Percentiles Table
CREATE TABLE IF NOT EXISTS peer_percentiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    peer_group_name TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    percentile_rank REAL,
    year TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 9. Sectors Table
CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    broad_sector TEXT,
    sub_sector TEXT,
    index_weight_pct REAL,
    market_cap_category TEXT,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 10. Stock Prices Table
CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    adjusted_close REAL,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- Performance Indexes for Fast Querying and Analytics
CREATE INDEX IF NOT EXISTS idx_profitandloss_comp_yr ON profitandloss(company_id, year);
CREATE INDEX IF NOT EXISTS idx_balancesheet_comp_yr ON balancesheet(company_id, year);
CREATE INDEX IF NOT EXISTS idx_cashflow_comp_yr ON cashflow(company_id, year);
CREATE INDEX IF NOT EXISTS idx_financial_ratios_comp_yr ON financial_ratios(company_id, year);
CREATE INDEX IF NOT EXISTS idx_market_cap_comp_yr ON market_cap(company_id, year);
CREATE INDEX IF NOT EXISTS idx_sectors_comp ON sectors(company_id);
CREATE INDEX IF NOT EXISTS idx_sectors_broad ON sectors(broad_sector);
CREATE INDEX IF NOT EXISTS idx_peer_groups_comp ON peer_groups(company_id);
CREATE INDEX IF NOT EXISTS idx_peer_percentiles_comp ON peer_percentiles(company_id);
CREATE INDEX IF NOT EXISTS idx_stock_prices_comp_date ON stock_prices(company_id, date);
