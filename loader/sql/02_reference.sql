-- Small lookup tables: what each status code means and which activity codes count as IT.
DROP TABLE IF EXISTS status_codes, status_priority, activity_categories;

-- Worst first wins. Notices have no priority: they never decide a company's group.
CREATE TABLE status_priority (
    status_group text PRIMARY KEY,
    priority integer NOT NULL
);
INSERT INTO status_priority VALUES
    ('deregistered', 6),
    ('bankruptcy', 5),
    ('dissolution_liquidation', 4),
    ('insolvency', 3),
    ('suspended', 2),
    ('unknown', 1),
    ('active', 0);

-- A code missing from status_groups.csv is unknown, never active.
CREATE TABLE status_codes AS
SELECT c.cod AS code,
       c.denumire AS name,
       COALESCE(g.status_group, 'unknown') AS status_group
FROM staging_status_codes c
LEFT JOIN staging_status_groups g ON g.code = c.cod;
ALTER TABLE status_codes ADD PRIMARY KEY (code);

-- Both versions of the activity codes, since the 2025 accounts mix them.
CREATE TABLE activity_categories (
    caen text PRIMARY KEY,
    category text NOT NULL,
    on_by_default boolean NOT NULL
);
INSERT INTO activity_categories VALUES
    ('6201', 'Software development', true),
    ('6210', 'Software development', true),
    ('5821', 'Software development', true),
    ('5829', 'Software development', true),
    ('6202', 'IT consulting and operations', true),
    ('6203', 'IT consulting and operations', true),
    ('6220', 'IT consulting and operations', true),
    ('6209', 'Other IT services', true),
    ('6290', 'Other IT services', true),
    ('6311', 'Data processing and hosting', true),
    ('6310', 'Data processing and hosting', true),
    ('6110', 'Telecommunications', false),
    ('6120', 'Telecommunications', false),
    ('6130', 'Telecommunications', false),
    ('6190', 'Telecommunications', false);
