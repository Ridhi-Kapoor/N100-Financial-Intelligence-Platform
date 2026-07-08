-- SQLite Queries for Nifty 100 Financial Database
-- Run these queries to gain insights and audit the data.

-- 1. Total number of companies (including generated stubs)
-- Shows how many unique companies are in the companies table.
SELECT 
    COUNT(*) AS total_companies,
    SUM(CASE WHEN company_name LIKE '%(Stub)%' THEN 1 ELSE 0 END) AS stub_companies_count,
    SUM(CASE WHEN company_name NOT LIKE '%(Stub)%' THEN 1 ELSE 0 END) AS original_companies_count
FROM companies;


-- 2. Total rows in each table
-- Handy query to check the size of each table.
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


-- 3. Top 10 companies by market cap
-- Fetches the top 10 companies by market cap for the latest available year in the database.
SELECT 
    c.id AS ticker,
    c.company_name, 
    m.year, 
    m.market_cap_crore
FROM market_cap m
JOIN companies c ON m.company_id = c.id
WHERE m.year = (SELECT MAX(year) FROM market_cap)
ORDER BY m.market_cap_crore DESC
LIMIT 10;


-- 4. Highest revenue companies
-- Finds the top 10 highest revenue (sales) records stored in the profit and loss table.
SELECT 
    c.id AS ticker,
    c.company_name, 
    pl.year, 
    pl.sales AS revenue_crores
FROM profitandloss pl
JOIN companies c ON pl.company_id = c.id
WHERE pl.sales IS NOT NULL
ORDER BY pl.sales DESC
LIMIT 10;


-- 5. Average Net Profit by sector
-- Calculates the average Net Profit across broad sectors for the latest reported year.
WITH LatestProfit AS (
    SELECT 
        company_id, 
        net_profit,
        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY id DESC) as rn
    FROM profitandloss
)
SELECT 
    s.broad_sector, 
    ROUND(AVG(lp.net_profit), 2) AS avg_net_profit_crores, 
    COUNT(DISTINCT lp.company_id) AS company_count
FROM LatestProfit lp
JOIN sectors s ON lp.company_id = s.company_id
WHERE lp.rn = 1
GROUP BY s.broad_sector
ORDER BY avg_net_profit_crores DESC;


-- 6. Cash flow summary
-- Shows the Operating, Investing, and Financing cash flows for each company in their latest reported period.
WITH LatestCashFlow AS (
    SELECT 
        company_id, 
        year, 
        operating_activity, 
        investing_activity, 
        financing_activity, 
        net_cash_flow,
        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY id DESC) as rn
    FROM cashflow
)
SELECT 
    c.id AS ticker,
    c.company_name, 
    lcf.year, 
    lcf.operating_activity AS operating_cash_flow, 
    lcf.investing_activity AS investing_cash_flow, 
    lcf.financing_activity AS financing_cash_flow, 
    lcf.net_cash_flow
FROM LatestCashFlow lcf
JOIN companies c ON lcf.company_id = c.id
WHERE lcf.rn = 1
ORDER BY lcf.net_cash_flow DESC
LIMIT 10;


-- 7. Profit Margin ranking
-- Ranks the top 10 companies by Net Profit Margin (NPM) in their latest financial ratio reports.
WITH LatestRatios AS (
    SELECT 
        company_id, 
        year, 
        net_profit_margin_pct, 
        operating_profit_margin_pct,
        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY id DESC) as rn
    FROM financial_ratios
)
SELECT 
    c.id AS ticker,
    c.company_name, 
    lr.year, 
    lr.net_profit_margin_pct, 
    lr.operating_profit_margin_pct
FROM LatestRatios lr
JOIN companies c ON lr.company_id = c.id
WHERE lr.rn = 1 AND lr.net_profit_margin_pct IS NOT NULL
ORDER BY lr.net_profit_margin_pct DESC
LIMIT 10;


-- 8. Top ROE (Return on Equity) companies
-- Fetches the top 10 companies by Return on Equity (ROE) based on their latest reported ratios.
WITH LatestRatios AS (
    SELECT 
        company_id, 
        year, 
        return_on_equity_pct,
        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY id DESC) as rn
    FROM financial_ratios
)
SELECT 
    c.id AS ticker,
    c.company_name, 
    lr.year, 
    lr.return_on_equity_pct AS roe_pct
FROM LatestRatios lr
JOIN companies c ON lr.company_id = c.id
WHERE lr.rn = 1 AND lr.return_on_equity_pct IS NOT NULL
ORDER BY lr.return_on_equity_pct DESC
LIMIT 10;


-- 9. Recent stock prices
-- Retrieves the most recent stock closing price and trading volume recorded for each company.
WITH LatestPrice AS (
    SELECT 
        company_id, 
        date, 
        close_price, 
        volume,
        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY date DESC) as rn
    FROM stock_prices
)
SELECT 
    c.id AS ticker,
    c.company_name, 
    lp.date AS last_updated_date, 
    lp.close_price, 
    lp.volume
FROM LatestPrice lp
JOIN companies c ON lp.company_id = c.id
WHERE lp.rn = 1
ORDER BY c.company_name ASC;


-- 10. Sector-wise company count
-- Displays the distribution of companies across broad sectors and sub-sectors.
SELECT 
    broad_sector, 
    sub_sector, 
    COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector, sub_sector
ORDER BY broad_sector ASC, company_count DESC;
