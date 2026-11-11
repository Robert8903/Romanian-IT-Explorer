-- One row per company: repeated CUIs are resolved only when the answer is clear.
DROP TABLE IF EXISTS companies, company_statuses, ambiguous_cui;

-- Kept between loads: it holds what the user saved, so it is never rebuilt.
CREATE TABLE IF NOT EXISTS shortlist (
    cui bigint PRIMARY KEY,
    note text,
    added_at timestamptz NOT NULL DEFAULT now()
);

ANALYZE staging_firms, staging_statuses, status_codes;

-- The worst status of each registry row. A code not in the code list is unknown too.
CREATE TEMP TABLE row_groups ON COMMIT DROP AS
SELECT DISTINCT ON (s.cod_inmatriculare)
       s.cod_inmatriculare,
       p.status_group
FROM staging_statuses s
LEFT JOIN status_codes c ON c.code = s.cod
JOIN status_priority p ON p.status_group = COALESCE(c.status_group, 'unknown')
ORDER BY s.cod_inmatriculare, p.priority DESC;

CREATE TEMP TABLE firm_rows ON COMMIT DROP AS
SELECT f.cui::bigint AS cui,
       f.denumire AS name,
       -- 'SAME NAME S.R.L.' and 'SAME NAME SRL' are one name.
       upper(regexp_replace(translate(f.denumire, 'ăâîșşțţĂÂÎȘŞȚŢ', 'aaissttAAISSTT'), '[^[:alnum:]]', '', 'g')) AS compared_name,
       f.cod_inmatriculare,
       CASE WHEN f.data_inmatriculare ~ '^\d{2}/\d{2}/\d{4}'
            THEN to_date(left(f.data_inmatriculare, 10), 'DD/MM/YYYY')
       END AS registered_on,
       f.forma_juridica AS legal_form,
       f.adr_judet AS county,
       f.adr_localitate AS locality,
       COALESCE(g.status_group, 'unknown') AS status_group
FROM staging_firms f
LEFT JOIN row_groups g ON g.cod_inmatriculare = f.cod_inmatriculare
WHERE f.cui ~ '^[0-9]+$' AND f.cui::bigint <> 0;

-- Several live rows, or only deregistered rows with different names: we don't guess.
CREATE TABLE ambiguous_cui AS
SELECT cui,
       count(*) AS registry_rows,
       CASE WHEN count(*) FILTER (WHERE status_group <> 'deregistered') > 1
            THEN 'several_live_rows'
            ELSE 'deregistered_with_different_names'
       END AS reason
FROM firm_rows
GROUP BY cui
HAVING count(*) FILTER (WHERE status_group <> 'deregistered') > 1
    OR (count(*) FILTER (WHERE status_group <> 'deregistered') = 0
        AND count(DISTINCT compared_name) > 1);
ALTER TABLE ambiguous_cui ADD PRIMARY KEY (cui);

-- What is left has one live row, which sorts first, or one name, where the latest wins.
CREATE TABLE companies AS
SELECT DISTINCT ON (r.cui)
       r.cui,
       r.name,
       lower(translate(r.name, 'ăâîșşțţĂÂÎȘŞȚŢ', 'aaissttAAISSTT')) AS name_search,
       r.cod_inmatriculare AS registration_code,
       r.registered_on,
       r.legal_form,
       translate(r.county, 'şţŞŢ', 'șțȘȚ') AS county,
       translate(r.locality, 'şţŞŢ', 'șțȘȚ') AS locality,
       r.status_group
FROM firm_rows r
WHERE NOT EXISTS (SELECT 1 FROM ambiguous_cui a WHERE a.cui = r.cui)
ORDER BY r.cui, (r.status_group = 'deregistered'), r.registered_on DESC NULLS LAST;
ALTER TABLE companies ADD PRIMARY KEY (cui);

-- Every status of the kept row, notices included. The names are in status_codes.
CREATE TABLE company_statuses AS
SELECT DISTINCT c.cui, s.cod AS code
FROM companies c
JOIN staging_statuses s ON s.cod_inmatriculare = c.registration_code;
ALTER TABLE company_statuses ADD PRIMARY KEY (cui, code);
