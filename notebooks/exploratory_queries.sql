-- Nifty 100 Financial Database - 10 Exploratory SQL Queries
-- Use these queries to gain insights and audit the SQLite database data.

-- ============================================================================
-- 1. Total Companies Summary
-- Calculates the total count of companies in the database, highlighting
-- original companies and generated stubs (missing from companies profile Excel).
-- ============================================================================
SELECT 
    COUNT(*) AS total_companies,
    SUM(CASE WHEN company_name LIKE '%(Stub)%' THEN 1 ELSE 0 END) AS stub_companies_count,
    SUM(CASE WHEN company_name NOT LIKE '%(Stub)%' THEN 1 ELSE 0 END) AS original_companies_count
FROM companies;


-- ============================================================================
-- 2. Company Count by Sector
-- Displays how companies are distributed across broad and sub-sectors.
-- ============================================================================
SELECT 
    broad_sector, 
    sub_sector, 
    COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector, sub_sector
ORDER BY broad_sector ASC, company_count DESC;


-- ============================================================================
-- 3. Companies with Less than 5 Years of Data
-- Identifies companies that have incomplete financial data coverage (less than 5
-- distinct years of data) in Profit & Loss, Balance Sheet, or Cash Flow.
-- ============================================================================
SELECT c.id AS ticker, c.company_name,
       COALESCE(pl.cnt, 0) AS pl_years,
       COALESCE(bs.cnt, 0) AS bs_years,
       COALESCE(cf.cnt, 0) AS cf_years
FROM companies c
LEFT JOIN (
    SELECT company_id, COUNT(DISTINCT year) AS cnt 
    FROM profitandloss 
    WHERE year != 'TTM' 
    GROUP BY company_id
) pl ON c.id = pl.company_id
LEFT JOIN (
    SELECT company_id, COUNT(DISTINCT year) AS cnt 
    FROM balancesheet 
    GROUP BY company_id
) bs ON c.id = bs.company_id
LEFT JOIN (
    SELECT company_id, COUNT(DISTINCT year) AS cnt 
    FROM cashflow 
    GROUP BY company_id
) cf ON c.id = cf.company_id
WHERE pl_years < 5 OR bs_years < 5 OR cf_years < 5
ORDER BY ticker;


-- ============================================================================
-- 4. Top Companies by Revenue (latest year 2024, excluding TTM)
-- Ranks the top 10 highest revenue (sales) companies in 2024.
-- ============================================================================
SELECT 
    c.id AS ticker, 
    c.company_name, 
    pl.year, 
    pl.sales AS revenue_crores
FROM profitandloss pl
JOIN companies c ON pl.company_id = c.id
WHERE pl.year = '2024' AND pl.sales IS NOT NULL
ORDER BY pl.sales DESC
LIMIT 10;


-- ============================================================================
-- 5. Top Companies by Market Cap
-- Ranks the top 10 companies by market capitalization in the latest reporting year.
-- ============================================================================
SELECT 
    c.id AS ticker, 
    c.company_name, 
    m.year, 
    m.market_cap_crore
FROM market_cap m
JOIN companies c ON m.company_id = c.id
WHERE m.year = (SELECT MAX(year) FROM market_cap) AND m.market_cap_crore IS NOT NULL
ORDER BY m.market_cap_crore DESC
LIMIT 10;


-- ============================================================================
-- 6. Average Net Profit by Sector (latest year 2024)
-- Aggregates average net profit across broad sectors for 2024.
-- ============================================================================
SELECT 
    s.broad_sector, 
    ROUND(AVG(pl.net_profit), 2) AS avg_net_profit_crores,
    COUNT(DISTINCT pl.company_id) AS company_count
FROM profitandloss pl
JOIN sectors s ON pl.company_id = s.company_id
WHERE pl.year = '2024' AND pl.net_profit IS NOT NULL
GROUP BY s.broad_sector
ORDER BY avg_net_profit_crores DESC;


-- ============================================================================
-- 7. Cash Flow Summary (latest year 2024)
-- Shows operating, investing, financing activities, and overall net cash flow
-- for the top 10 companies sorted by net cash flow.
-- ============================================================================
SELECT 
    c.id AS ticker, 
    c.company_name, 
    cf.year, 
    cf.operating_activity AS operating_cash_flow, 
    cf.investing_activity AS investing_cash_flow, 
    cf.financing_activity AS financing_cash_flow, 
    cf.net_cash_flow
FROM cashflow cf
JOIN companies c ON cf.company_id = c.id
WHERE cf.year = '2024' AND cf.net_cash_flow IS NOT NULL
ORDER BY cf.net_cash_flow DESC
LIMIT 10;


-- ============================================================================
-- 8. Recent Stock Prices
-- Retrieves the most recent stock closing price and volume for all companies.
-- ============================================================================
WITH LatestPrices AS (
    SELECT 
        company_id, 
        date, 
        close_price, 
        volume,
        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY date DESC) AS rn
    FROM stock_prices
)
SELECT 
    c.id AS ticker, 
    c.company_name, 
    lp.date AS last_price_date, 
    lp.close_price, 
    lp.volume
FROM LatestPrices lp
JOIN companies c ON lp.company_id = c.id
WHERE lp.rn = 1
ORDER BY lp.close_price DESC;


-- ============================================================================
-- 9. Financial Ratio Summary (latest year 2024)
-- Ranks the top 10 companies based on Return on Equity (ROE) and displays their
-- Net Profit Margin and Debt to Equity ratio for 2024.
-- ============================================================================
SELECT 
    c.id AS ticker, 
    c.company_name, 
    fr.year, 
    fr.return_on_equity_pct AS roe_percentage, 
    fr.net_profit_margin_pct AS npm_percentage, 
    fr.debt_to_equity
FROM financial_ratios fr
JOIN companies c ON fr.company_id = c.id
WHERE fr.year = '2024' AND fr.return_on_equity_pct IS NOT NULL
ORDER BY fr.return_on_equity_pct DESC
LIMIT 10;


-- ============================================================================
-- 10. Table Row Counts
-- Useful sanity check query to quickly verify the total number of records
-- in all 10 tables loaded in the database.
-- ============================================================================
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL
SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL
SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL
SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL
SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL
SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL
SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL
SELECT 'peer_groups', COUNT(*) FROM peer_groups
UNION ALL
SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL
SELECT 'stock_prices', COUNT(*) FROM stock_prices;
