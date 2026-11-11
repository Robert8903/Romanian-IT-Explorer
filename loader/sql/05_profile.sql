-- The saved result the app searches: one row per company with its latest and first year.
DROP TABLE IF EXISTS company_profile;

ANALYZE financials;

CREATE TABLE company_profile AS
WITH years AS (
    SELECT cui, min(year) AS first_year, max(year) AS latest_year, count(*) AS years_count
    FROM financials
    GROUP BY cui
)
SELECT c.cui,
       c.name,
       c.name_search,
       c.legal_form,
       c.county,
       c.locality,
       c.status_group,
       a.category,
       y.latest_year,
       y.first_year,
       y.years_count,
       CASE WHEN latest.employees_suspect THEN NULL ELSE latest.employees_reported END AS employees,
       COALESCE(latest.employees_suspect, false) AS employees_suspect,
       latest.revenue,
       latest.net_result,
       CASE WHEN latest.employees_suspect THEN NULL
            ELSE latest.revenue / NULLIF(latest.employees_reported, 0)
       END AS revenue_per_employee,
       first.revenue AS first_revenue,
       CASE WHEN first.employees_suspect THEN NULL ELSE first.employees_reported END AS first_employees
FROM companies c
LEFT JOIN years y ON y.cui = c.cui
LEFT JOIN financials latest ON latest.cui = c.cui AND latest.year = y.latest_year
LEFT JOIN financials first ON first.cui = c.cui AND first.year = y.first_year
LEFT JOIN activity_categories a ON a.caen = latest.caen;
ALTER TABLE company_profile ADD PRIMARY KEY (cui);

ANALYZE company_profile, activity_categories, company_statuses;
