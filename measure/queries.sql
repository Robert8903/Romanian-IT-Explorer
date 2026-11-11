-- name: explore_filters
SELECT cui, name, county, category, employees, revenue, net_result
FROM company_profile
WHERE category = ANY(ARRAY['Software development', 'IT consulting and operations',
                           'Other IT services', 'Data processing and hosting'])
  AND status_group = 'active'
  AND employees >= 1
  AND county = 'Cluj'
ORDER BY employees DESC NULLS LAST, revenue DESC NULLS LAST, name
LIMIT 200;

-- name: company_history
-- A company whose CUI ends in 01, so it is present in every sample size.
SELECT year, revenue, net_result, employees_reported
FROM financials
WHERE cui = 11027001
ORDER BY year;

-- name: county_category_totals
SELECT p.county, a.category, f.year,
       count(*) AS companies,
       sum(f.revenue) AS revenue,
       sum(f.employees_reported) FILTER (WHERE NOT f.employees_suspect) AS employees
FROM financials f
JOIN company_profile p ON p.cui = f.cui
JOIN activity_categories a ON a.caen = f.caen
WHERE a.on_by_default
GROUP BY p.county, a.category, f.year
ORDER BY p.county, a.category, f.year;
