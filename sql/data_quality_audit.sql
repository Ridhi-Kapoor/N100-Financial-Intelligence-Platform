-- Data Quality Audit Queries for Nifty 100 SQLite Database
-- These queries perform the audit checks as requested in the requirements.

-- ============================================================================
-- REQUIREMENT 1: Randomly select 5 companies from the database
-- ============================================================================
SELECT id AS ticker, company_name, website, roce_percentage, roe_percentage
FROM companies
ORDER BY RANDOM()
LIMIT 5;

-- ============================================================================
-- REQUIREMENT 2: Verify year-wise data coverage for Profit & Loss, Balance Sheet, Cash Flow, and Stock Prices
-- ============================================================================

-- 2a. Year-wise data coverage for Profit & Loss
SELECT year, COUNT(*) AS pl_record_count
FROM profitandloss
GROUP BY year
ORDER BY year;

-- 2b. Year-wise data coverage for Balance Sheet
SELECT year, COUNT(*) AS bs_record_count
FROM balancesheet
GROUP BY year
ORDER BY year;

-- 2c. Year-wise data coverage for Cash Flow
SELECT year, COUNT(*) AS cf_record_count
FROM cashflow
GROUP BY year
ORDER BY year;

-- 2d. Year-wise data coverage for Stock Prices (extracting year from date YYYY-MM-DD)
SELECT SUBSTR(date, 1, 4) AS year, COUNT(*) AS stock_price_record_count
FROM stock_prices
GROUP BY year
ORDER BY year;

-- ============================================================================
-- REQUIREMENT 3: Identify companies having fewer than 5 years of financial data
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
-- REQUIREMENT 4: Detect missing values, duplicate records, invalid years, and negative financial values
-- ============================================================================

-- 4a. Detect missing values (NULL or empty strings) in critical columns
SELECT 'companies' AS table_name, 'face_value' AS col_name, COUNT(*) AS null_count 
FROM companies 
WHERE face_value IS NULL OR face_value = ''
UNION ALL
SELECT 'profitandloss', 'sales', COUNT(*) 
FROM profitandloss 
WHERE sales IS NULL
UNION ALL
SELECT 'profitandloss', 'net_profit', COUNT(*) 
FROM profitandloss 
WHERE net_profit IS NULL
UNION ALL
SELECT 'balancesheet', 'total_assets', COUNT(*) 
FROM balancesheet 
WHERE total_assets IS NULL
UNION ALL
SELECT 'balancesheet', 'total_liabilities', COUNT(*) 
FROM balancesheet 
WHERE total_liabilities IS NULL
UNION ALL
SELECT 'cashflow', 'net_cash_flow', COUNT(*) 
FROM cashflow 
WHERE net_cash_flow IS NULL
UNION ALL
SELECT 'stock_prices', 'close_price', COUNT(*) 
FROM stock_prices 
WHERE close_price IS NULL;

-- 4b. Detect duplicate records on primary business keys (company_id, year/date)
-- Checks for duplicate company-year combinations in P&L, BS, Cash Flow, and company-date in Stock Prices
SELECT 'profitandloss' AS table_name, company_id, year AS key_value, COUNT(*) AS occurrence_count
FROM profitandloss
GROUP BY company_id, year
HAVING COUNT(*) > 1
UNION ALL
SELECT 'balancesheet', company_id, year, COUNT(*)
FROM balancesheet
GROUP BY company_id, year
HAVING COUNT(*) > 1
UNION ALL
SELECT 'cashflow', company_id, year, COUNT(*)
FROM cashflow
GROUP BY company_id, year
HAVING COUNT(*) > 1
UNION ALL
SELECT 'stock_prices', company_id, date, COUNT(*)
FROM stock_prices
GROUP BY company_id, date
HAVING COUNT(*) > 1;

-- 4c. Detect invalid years (years that are not standard 4-digit integers and are not 'TTM')
-- E.g., checks for decimal years like '2024.5' or unformatted year strings
SELECT 'profitandloss' AS table_name, company_id, year, COUNT(*) AS occurrence_count
FROM profitandloss
WHERE year NOT GLOB '[12][09][0-9][0-9]' AND year != 'TTM'
GROUP BY company_id, year
UNION ALL
SELECT 'balancesheet', company_id, year, COUNT(*)
FROM balancesheet
WHERE year NOT GLOB '[12][09][0-9][0-9]' AND year != 'TTM'
GROUP BY company_id, year
UNION ALL
SELECT 'cashflow', company_id, year, COUNT(*)
FROM cashflow
WHERE year NOT GLOB '[12][09][0-9][0-9]' AND year != 'TTM'
GROUP BY company_id, year
UNION ALL
SELECT 'financial_ratios', company_id, year, COUNT(*)
FROM financial_ratios
WHERE year NOT GLOB '[12][09][0-9][0-9]' AND year != 'TTM'
GROUP BY company_id, year;

-- 4d. Detect negative values in columns that should strictly be positive
SELECT 'profitandloss' AS table_name, 'sales' AS col_name, company_id, year, sales AS value 
FROM profitandloss 
WHERE sales < 0
UNION ALL
SELECT 'profitandloss', 'expenses', company_id, year, expenses 
FROM profitandloss 
WHERE expenses < 0
UNION ALL
SELECT 'balancesheet', 'total_assets', company_id, year, total_assets 
FROM balancesheet 
WHERE total_assets < 0
UNION ALL
SELECT 'balancesheet', 'total_liabilities', company_id, year, total_liabilities 
FROM balancesheet 
WHERE total_liabilities < 0;
