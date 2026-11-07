import dataclasses

import pytest

from load import LoadError, run_pipeline


def count_rows(conn, table):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def firm_cuis(conn):
    return {row[0] for row in conn.execute("SELECT cui FROM staging_firms")}


def with_expected_rows(sources, key, expected_rows):
    return [
        dataclasses.replace(source, expected_rows=expected_rows) if source.key == key else source
        for source in sources
    ]


def test_staging_row_counts_match_files(db_conn, raw_dir, sources):
    report = run_pipeline(db_conn, raw_dir, sources)

    assert report.status == "finished"
    assert count_rows(db_conn, "staging_firms") == 4
    assert count_rows(db_conn, "staging_status_codes") == 2
    assert count_rows(db_conn, "staging_accounts") == 4
    assert report.counts["staging_firms"] == 4
    assert report.counts["staging_accounts"] == 4


def test_text_arrives_exactly_as_in_the_file(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources)

    names = {row[0] for row in db_conn.execute("SELECT denumire FROM staging_firms")}
    assert 'CLINICA "BETA" SRL' in names
    assert "GAMA\\DELTA SNC" in names
    codes = {row[0] for row in db_conn.execute("SELECT cod FROM staging_status_codes")}
    assert codes == {"1048", "1084"}
    last = db_conn.execute("SELECT i20 FROM staging_accounts WHERE cui = '100'").fetchone()[0]
    assert last == "20"


def test_empty_values_become_null(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources)

    i2 = db_conn.execute("SELECT i2 FROM staging_accounts WHERE cui = '100'").fetchone()[0]
    county = db_conn.execute("SELECT adr_judet FROM staging_firms WHERE cui = '150'").fetchone()[0]
    assert i2 is None
    assert county is None


def test_accounts_know_their_year_and_format(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources)

    row = db_conn.execute(
        "SELECT year, filing_format, caen FROM staging_accounts WHERE cui = '150'"
    ).fetchone()
    assert row == ("2024", "long", "6210")


def test_status_rows_of_companies_not_kept_are_dropped(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources)

    assert count_rows(db_conn, "staging_statuses") == 5
    individuals = db_conn.execute(
        "SELECT count(*) FROM staging_statuses WHERE cod_inmatriculare LIKE 'F%'"
    ).fetchone()[0]
    assert individuals == 0


def test_wrong_row_count_fails_with_file_name(db_conn, raw_dir, sources):
    wrong = with_expected_rows(sources, "accounts_2024_long", 2)

    with pytest.raises(LoadError, match="accounts_2024_long"):
        run_pipeline(db_conn, raw_dir, wrong)


def test_registry_is_checked_against_its_original_size(db_conn, raw_dir, sources):
    wrong = with_expected_rows(sources, "firms", 6)

    with pytest.raises(LoadError, match="firms"):
        run_pipeline(db_conn, raw_dir, wrong)


def test_truncated_registry_fails_even_if_its_stats_look_right(db_conn, raw_dir, sources):
    firms = raw_dir / "firms"
    firms.write_text(firms.read_text(encoding="utf-8").rsplit("OMEGA", 1)[0], encoding="utf-8")

    with pytest.raises(LoadError, match="firms"):
        run_pipeline(db_conn, raw_dir, sources)


def test_row_with_wrong_columns_fails_with_file_and_line(db_conn, raw_dir, sources):
    path = raw_dir / "accounts_2024_long"
    path.write_text(path.read_text() + "1,2,3\r\n", newline="")

    with pytest.raises(LoadError, match=r"accounts_2024_long.*line 3"):
        run_pipeline(db_conn, raw_dir, sources)


def test_unexpected_header_fails_with_file_name(db_conn, raw_dir, sources):
    path = raw_dir / "status_codes"
    path.write_text("A^B\r\n1048^x\r\n1084^y\r\n", encoding="utf-8", newline="")

    with pytest.raises(LoadError, match="status_codes"):
        run_pipeline(db_conn, raw_dir, sources)


def test_second_run_is_skipped(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources)
    first = count_rows(db_conn, "staging_firms")

    report = run_pipeline(db_conn, raw_dir, sources)

    assert report.status == "skipped"
    assert report.counts["staging_firms"] == first
    assert count_rows(db_conn, "staging_firms") == first
    assert count_rows(db_conn, "load_runs") == 1


def test_changed_settings_load_again_even_when_returning_to_old_ones(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources, sample_pct=25)
    run_pipeline(db_conn, raw_dir, sources, sample_pct=100)

    report = run_pipeline(db_conn, raw_dir, sources, sample_pct=25)

    assert report.status == "finished"
    assert firm_cuis(db_conn) == {"100"}


def test_failed_run_can_run_again_cleanly(db_conn, raw_dir, sources):
    with pytest.raises(LoadError):
        run_pipeline(db_conn, raw_dir, with_expected_rows(sources, "accounts_2024_long", 2))

    status = db_conn.execute("SELECT status FROM load_runs").fetchone()[0]
    assert status == "failed"

    report = run_pipeline(db_conn, raw_dir, sources)

    assert report.status == "finished"
    assert count_rows(db_conn, "staging_accounts") == 4


def test_failed_reload_keeps_the_previous_data(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources)

    with pytest.raises(LoadError):
        run_pipeline(db_conn, raw_dir, with_expected_rows(sources, "accounts_2024_long", 2))

    assert count_rows(db_conn, "staging_firms") == 4
    assert count_rows(db_conn, "staging_accounts") == 4


def test_sample_pct_is_nested_and_stable(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources, sample_pct=25)
    at_25 = firm_cuis(db_conn)
    run_pipeline(db_conn, raw_dir, sources, sample_pct=50)
    at_50 = firm_cuis(db_conn)
    run_pipeline(db_conn, raw_dir, sources, sample_pct=25)

    assert at_25 == {"100"}
    assert at_50 == {"100", "125"}
    assert firm_cuis(db_conn) == at_25


def test_sample_applies_to_accounts_and_statuses(db_conn, raw_dir, sources):
    run_pipeline(db_conn, raw_dir, sources, sample_pct=25)

    accounts = {row[0] for row in db_conn.execute("SELECT cui FROM staging_accounts")}
    statuses = {row[0] for row in db_conn.execute("SELECT cod_inmatriculare FROM staging_statuses")}
    assert accounts == {"100"}
    assert statuses == {"J1/1/2000"}
