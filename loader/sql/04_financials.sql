-- One row per company and year, with the amounts as numbers.
DROP TABLE IF EXISTS financials, rejected_financials;

ANALYZE staging_accounts, companies;

CREATE TEMP TABLE accounts_checked ON COMMIT DROP AS
SELECT a.*,
       CASE WHEN a.cui ~ '^[0-9]+$' THEN a.cui::bigint END AS cui_number
FROM staging_accounts a;

-- Accounts we can't attach to a company are kept here and counted, not lost.
CREATE TABLE rejected_financials AS
SELECT a.cui, a.year::integer AS year, a.filing_format, a.caen,
       CASE WHEN EXISTS (SELECT 1 FROM ambiguous_cui x WHERE x.cui = a.cui_number)
            THEN 'ambiguous_cui'
            ELSE 'no_company'
       END AS reason
FROM accounts_checked a
WHERE NOT EXISTS (SELECT 1 FROM companies c WHERE c.cui = a.cui_number);

CREATE TABLE financials AS
SELECT a.cui_number AS cui,
       a.year::integer AS year,
       a.filing_format,
       lpad(a.caen, 4, '0') AS caen,
       a.i13::numeric AS revenue,
       CASE WHEN a.i18 IS NOT NULL OR a.i19 IS NOT NULL
            THEN COALESCE(a.i18::numeric, 0) - COALESCE(a.i19::numeric, 0)
       END AS net_result,
       a.i20::numeric AS employees_reported,
       COALESCE(a.i20::numeric >= 30000 OR a.i20 ~ '^(\d)\1{5,}$', false) AS employees_suspect,
       CASE WHEN a.i1 IS NOT NULL OR a.i2 IS NOT NULL
            THEN COALESCE(a.i1::numeric, 0) + COALESCE(a.i2::numeric, 0)
       END AS total_assets,
       a.i7::numeric AS debts,
       a.i10::numeric AS equity
FROM accounts_checked a
JOIN companies c ON c.cui = a.cui_number;
ALTER TABLE financials ADD PRIMARY KEY (cui, year);
