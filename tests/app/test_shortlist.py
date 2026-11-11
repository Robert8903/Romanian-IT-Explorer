import csv
import io

from shortlist import add_to_list, get_list, list_as_csv, remove_from_list, update_note


def test_adding_twice_keeps_one_row_and_the_note(conn):
    add_to_list(conn, 1, "first note")
    add_to_list(conn, 1)

    rows = get_list(conn)
    assert len(rows) == 1
    assert rows[0]["note"] == "first note"


def test_note_can_change_and_company_can_leave(conn):
    add_to_list(conn, 1)
    update_note(conn, 1, "call them")
    assert get_list(conn)[0]["note"] == "call them"

    remove_from_list(conn, 1)
    assert get_list(conn) == []


def test_list_shows_company_data(conn):
    add_to_list(conn, 1)

    row = get_list(conn)[0]
    assert row["name"] == "ALFA SOFT SRL"
    assert row["county"] == "Cluj"
    assert row["in_data"] is True


def test_saved_company_absent_after_reload_stays_visible_and_marked(conn):
    add_to_list(conn, 1, "keep me")
    conn.execute("DELETE FROM company_profile WHERE cui = 1")

    row = get_list(conn)[0]
    assert row["cui"] == 1
    assert row["note"] == "keep me"
    assert row["in_data"] is False
    assert row["name"] is None


def test_csv_handles_commas_quotes_and_diacritics():
    rows = [{"cui": 1, "name": 'FIRMA "X", SRL', "county": "Iași", "note": "bună, firmă"}]

    parsed = list(csv.DictReader(io.StringIO(list_as_csv(rows))))

    assert parsed == [{"cui": "1", "name": 'FIRMA "X", SRL', "county": "Iași", "note": "bună, firmă"}]


def test_csv_of_empty_list_is_empty():
    assert list_as_csv([]) == ""
