import os

import psycopg
import pytest

TEST_DB = "career_app_test"

# The same columns the loader builds, with a handful of companies.
SCHEMA = """
CREATE TABLE company_profile (
    cui bigint PRIMARY KEY, name text, name_search text, legal_form text, county text,
    locality text, status_group text, category text, latest_year integer, first_year integer,
    years_count bigint, employees numeric, employees_suspect boolean, revenue numeric,
    net_result numeric, revenue_per_employee numeric, first_revenue numeric, first_employees numeric
);
CREATE TABLE financials (
    cui bigint, year integer, filing_format text, caen text, revenue numeric, net_result numeric,
    employees_reported numeric, employees_suspect boolean, total_assets numeric, debts numeric,
    equity numeric, PRIMARY KEY (cui, year)
);
CREATE TABLE status_codes (code text PRIMARY KEY, name text, status_group text);
CREATE TABLE company_statuses (cui bigint, code text, PRIMARY KEY (cui, code));
CREATE TABLE shortlist (
    cui bigint PRIMARY KEY, note text, added_at timestamptz NOT NULL DEFAULT now()
);
"""

SOFT = "Software development"
PROFILES = [
    # cui, name, county, status, category, latest, first, years, employees, suspect, revenue, first_revenue, first_employees
    (1, "ALFA SOFT SRL", "Cluj", "active", SOFT, 2025, 2021, 4, 100, False, 2000, 1000, 50),
    (2, "BETA SOFT SRL", "Iași", "active", SOFT, 2025, 2025, 1, 300, False, 500, 500, 300),
    (3, "NO STAFF SOFT SRL", "Cluj", "active", SOFT, 2025, 2024, 2, 0, False, 10, 0, 0),
    (4, "CLOSED SOFT SRL", "Cluj", "deregistered", SOFT, 2024, 2024, 1, 5, False, 10, 10, 5),
    (5, "FARM SRL", "Cluj", "active", None, 2025, 2025, 1, 900, False, 10, 10, 900),
    (6, "NO ACCOUNTS SRL", "Timiș", "active", None, None, None, None, None, False, None, None, None),
    (7, "SUSPECT SOFT SRL", "Cluj", "active", SOFT, 2025, 2025, 1, None, True, 10, 10, None),
    (8, "SOFT TIMIȘ SRL", "Timiș", "active", SOFT, 2025, 2025, 1, 2, False, 10, 10, 2),
    (9, "SOFT TIMIŞ DOI SRL", "Timiș", "active", SOFT, 2025, 2025, 1, 2, False, 10, 10, 2),
    (10, "100% SOFT SRL", "Cluj", "active", SOFT, 2025, 2025, 1, 3, False, 10, 10, 3),
    (11, "O'NEIL SOFT SRL", "Cluj", "active", SOFT, 2025, 2025, 1, 3, False, 10, 10, 3),
]
FINANCIALS = [
    # cui, year, revenue, net result, employees, suspect
    (1, 2021, 1000, 100, 50, False),
    (1, 2022, 1200, 120, 60, False),
    (1, 2024, 1800, -30, 90, False),
    (1, 2025, 2000, 200, 100, False),
    (2, 2025, 500, 50, 300, False),
    (7, 2025, 10, 1, 777777, True),
]


@pytest.fixture
def conn():
    settings = dict(
        host="db",
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=True,
    )
    with psycopg.connect(dbname=os.environ["POSTGRES_DB"], **settings) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
        admin.execute(f"CREATE DATABASE {TEST_DB}")
    connection = psycopg.connect(dbname=TEST_DB, **settings)
    connection.execute(SCHEMA)
    for c, name, county, status, category, latest, first, years, staff, suspect, revenue, first_rev, first_staff in PROFILES:
        search = name.lower().translate(str.maketrans("ășşțţâî", "asst" + "t" + "ai"))
        connection.execute(
            "INSERT INTO company_profile (cui, name, name_search, county, status_group, category, "
            "latest_year, first_year, years_count, employees, employees_suspect, revenue, net_result, "
            "first_revenue, first_employees) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)",
            (c, name, search, county, status, category, latest, first, years, staff, suspect, revenue, first_rev, first_staff),
        )
    for c, year, revenue, net, staff, suspect in FINANCIALS:
        connection.execute(
            "INSERT INTO financials (cui, year, revenue, net_result, employees_reported, employees_suspect) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (c, year, revenue, net, staff, suspect),
        )
    connection.execute(
        "INSERT INTO status_codes VALUES ('1048', 'funcțiune', 'active'), ('2069', 'sediu expirat', 'notice')"
    )
    connection.execute("INSERT INTO company_statuses VALUES (1, '1048'), (1, '2069')")
    yield connection
    connection.close()
    with psycopg.connect(dbname=os.environ["POSTGRES_DB"], **settings) as admin:
        admin.execute(f"DROP DATABASE {TEST_DB}")
