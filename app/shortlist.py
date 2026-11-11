"""My list: the companies someone saved, with a note. Kept when the data is reloaded."""
import csv
import io

from psycopg.rows import dict_row


def add_to_list(conn, cui, note=""):
    """Adding a company that's already saved keeps its note."""
    conn.execute(
        "INSERT INTO shortlist (cui, note) VALUES (%s, %s) ON CONFLICT (cui) DO NOTHING",
        (cui, note),
    )


def update_note(conn, cui, note):
    conn.execute("UPDATE shortlist SET note = %s WHERE cui = %s", (note, cui))


def remove_from_list(conn, cui):
    conn.execute("DELETE FROM shortlist WHERE cui = %s", (cui,))


def get_list(conn):
    """A company missing from the current data stays on the list, marked with in_data."""
    with conn.cursor(row_factory=dict_row) as cursor:
        return cursor.execute(
            """
            SELECT s.cui, s.note, p.name, p.county, p.status_group, p.category,
                   p.employees, p.revenue, p.net_result, p.latest_year,
                   p.cui IS NOT NULL AS in_data
            FROM shortlist s
            LEFT JOIN company_profile p ON p.cui = s.cui
            ORDER BY s.added_at, s.cui
            """
        ).fetchall()


def list_as_csv(rows):
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
