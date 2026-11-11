"""The questions the app asks the database. Every value travels as a query parameter."""
from dataclasses import dataclass, field

from psycopg.rows import dict_row

DEFAULT_IT_CATEGORIES = [
    "Software development",
    "IT consulting and operations",
    "Other IT services",
    "Data processing and hosting",
]
# Must stay the same as the name_search column built in 03_companies.sql.
DIACRITICS = str.maketrans("ăâîșşțţĂÂÎȘŞȚŢ", "aaissttAAISSTT")


@dataclass
class Filters:
    name: str = ""
    counties: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=lambda: list(DEFAULT_IT_CATEGORIES))
    statuses: list[str] = field(default_factory=lambda: ["active"])
    min_employees: int | None = 1
    min_revenue: int | None = None


def _name_pattern(text):
    """Turn what was typed into a LIKE pattern where % and _ mean only themselves."""
    plain = text.strip().translate(DIACRITICS).lower()
    escaped = plain.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _rows(conn, sql, params=()):
    with conn.cursor(row_factory=dict_row) as cursor:
        return cursor.execute(sql, params).fetchall()


def _period(row):
    if row["first_year"] is None:
        return None
    if row["first_year"] == row["latest_year"]:
        return str(row["first_year"])
    return f"{row['first_year']}–{row['latest_year']}"


def _revenue_change_pct(row):
    """Empty with a single year or a zero start: there is nothing to compare with."""
    if row["first_year"] == row["latest_year"] or not row["first_revenue"] or row["revenue"] is None:
        return None
    return round((row["revenue"] - row["first_revenue"]) / abs(row["first_revenue"]) * 100, 1)


def search_companies(conn, f, limit=200):
    conditions = []
    params = []
    if f.name.strip():
        conditions.append("name_search LIKE %s ESCAPE '\\'")
        params.append(_name_pattern(f.name))
    if f.counties:
        conditions.append("county = ANY(%s)")
        params.append(f.counties)
    if f.categories:
        conditions.append("category = ANY(%s)")
        params.append(f.categories)
    if f.statuses:
        conditions.append("status_group = ANY(%s)")
        params.append(f.statuses)
    if f.min_employees is not None:
        conditions.append("employees >= %s")
        params.append(f.min_employees)
    if f.min_revenue is not None:
        conditions.append("revenue >= %s")
        params.append(f.min_revenue)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = _rows(
        conn,
        f"""
        SELECT cui, name, county, locality, status_group, category, employees, employees_suspect,
               revenue, net_result, revenue_per_employee, first_year, latest_year, first_revenue
        FROM company_profile
        {where}
        ORDER BY employees DESC NULLS LAST, revenue DESC NULLS LAST, name
        LIMIT %s
        """,
        params + [limit],
    )
    for row in rows:
        row["period"] = _period(row)
        row["revenue_change_pct"] = _revenue_change_pct(row)
    return rows


def filter_options(conn):
    def values(column):
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM company_profile WHERE {column} IS NOT NULL ORDER BY 1"
        ).fetchall()
        return [row[0] for row in rows]

    return {
        "counties": values("county"),
        "categories": values("category"),
        "statuses": values("status_group"),
    }


def it_companies_by_county(conn):
    """The Explore defaults counted per county, so a county's number matches its search."""
    rows = conn.execute(
        """
        SELECT county, count(*)
        FROM company_profile
        WHERE county IS NOT NULL AND status_group = 'active' AND employees >= 1 AND category = ANY(%s)
        GROUP BY county
        """,
        (DEFAULT_IT_CATEGORIES,),
    ).fetchall()
    return dict(rows)


def company_history(conn, cuis):
    """One row per company and year on the same years, with a missing year left empty."""
    return _rows(
        conn,
        """
        WITH years AS (SELECT DISTINCT year FROM financials),
             chosen AS (SELECT unnest(%s::bigint[]) AS cui)
        SELECT chosen.cui,
               p.name,
               years.year,
               f.revenue,
               f.net_result,
               CASE WHEN f.employees_suspect THEN NULL ELSE f.employees_reported END AS employees,
               COALESCE(f.employees_suspect, false) AS employees_suspect
        FROM chosen
        CROSS JOIN years
        LEFT JOIN company_profile p ON p.cui = chosen.cui
        LEFT JOIN financials f ON f.cui = chosen.cui AND f.year = years.year
        ORDER BY chosen.cui, years.year
        """,
        (cuis,),
    )


def company_statuses(conn, cui):
    rows = conn.execute(
        """
        SELECT COALESCE(c.name, s.code)
        FROM company_statuses s
        LEFT JOIN status_codes c ON c.code = s.code
        WHERE s.cui = %s
        """,
        (cui,),
    ).fetchall()
    return [row[0] for row in rows]
