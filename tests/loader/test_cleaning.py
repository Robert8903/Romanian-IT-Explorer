import csv
import json
from pathlib import Path

import pytest

import load
from load import run_pipeline
from sources import Source

FIRMS_HEADER = "DENUMIRE^CUI^COD_INMATRICULARE^DATA_INMATRICULARE^FORMA_JURIDICA^ADR_JUDET^ADR_LOCALITATE"
ACCOUNTS_HEADER = "CUI,CAEN," + ",".join(f"I{i}" for i in range(1, 21))
UNMAPPED_CODE = "1081"

# name, cui, registration code, registered on, status codes
FIRMS = [
    ("OLD NAME SRL", "1000", "J1/1/2000", "01/01/2000", ["1084"]),
    ("LIVE NAME SRL", "1000", "J1/2/2010", "01/01/2010", ["1048"]),
    ("FIRST LIVE SRL", "1001", "J1/3/2000", "01/01/2000", ["1048"]),
    ("SECOND LIVE SRL", "1001", "J1/4/2000", "01/01/2001", ["1048"]),
    ("ONE NAME SRL", "1002", "J1/5/2000", "01/01/2000", ["1084"]),
    ("OTHER NAME SRL", "1002", "J1/6/2000", "01/01/2001", ["1084"]),
    ("SAME NAME S.R.L.", "1003", "J1/7/2000", "01/01/2000", ["1084"]),
    ("SAME NAME SRL", "1003", "J1/8/2005", "01/01/2005", ["1084"]),
    ("NO CUI SRL", "", "J1/9/2000", "01/01/2000", ["1048"]),
    ("ZERO CUI SRL", "0", "J1/10/2000", "01/01/2000", ["1048"]),
    ("DEREGISTERED SRL", "2001", "J2/1/2000", "01/01/2000", ["1070", "1084"]),
    ("BANKRUPT SRL", "2002", "J2/2/2000", "01/01/2000", ["1049", "1070"]),
    ("DISSOLVED SRL", "2003", "J2/3/2000", "01/01/2000", ["1107", "1049"]),
    ("INSOLVENT SRL", "2004", "J2/4/2000", "01/01/2000", ["1074", "1107"]),
    ("SUSPENDED SRL", "2005", "J2/5/2000", "01/01/2000", [UNMAPPED_CODE, "1074"]),
    ("UNMAPPED SRL", "2006", "J2/6/2000", "01/01/2000", ["1048", UNMAPPED_CODE]),
    ("ACTIVE WITH NOTICE SRL", "2007", "J2/7/2000", "01/01/2000", ["1048", "2069"]),
    ("ONLY NOTICE SRL", "2008", "J2/8/2000", "01/01/2000", ["2069"]),
    ("NO STATUS SRL", "2009", "J2/9/2000", "01/01/2000", []),
    ("UNLISTED CODE SRL", "2010", "J2/10/2000", "01/01/2000", ["9999"]),
    ("SUSPECT SRL", "3001", "J3/1/2000", "01/01/2000", ["1048"]),
    ("HUGE SRL", "3002", "J3/2/2000", "01/01/2000", ["1048"]),
    ("ZERO STAFF SRL", "3003", "J3/3/2000", "01/01/2000", ["1048"]),
    ("TWO YEARS SRL", "3004", "J3/4/2000", "01/01/2000", ["1048"]),
    ("LOSS SRL", "3005", "J3/5/2000", "01/01/2000", ["1048"]),
    ("EMPTY RESULT SRL", "3006", "J3/6/2000", "01/01/2000", ["1048"]),
    ("NEWS SRL", "3007", "J3/7/2000", "01/01/2000", ["1048"]),
    ("FARM SRL", "3008", "J3/8/2000", "01/01/2000", ["1048"]),
    ("NO ACCOUNTS SRL", "3009", "J3/9/2000", "01/01/2000", ["1048"]),
    ("SOFT TIMIŞ SRL", "4001", "J4/1/2000", "01/01/2000", ["1048"]),
    ("SOFT TIMIȘ SRL", "4002", "J4/2/2000", "01/01/2000", ["1048"]),
    ("DATE WITH TIME SRL", "4003", "J4/3/2000", "15/03/2012 10:30:00", ["1048"]),
]


def account(cui, caen, year=2025, **values):
    """One accounts row, with only the named columns (i13="5") filled in."""
    columns = [values.get(f"i{i}", "") for i in range(1, 21)]
    return year, ",".join([cui, caen] + columns)


ACCOUNTS = [
    account("3001", "6201", i20="777777777777777", i13="1000"),
    account("3002", "6201", i20="37800", i13="1000"),
    account("3003", "6201", i20="0", i13="1000", i1="10", i2="5", i7="3", i10="12"),
    account("3004", "6201", year=2024, i20="10", i13="1000", i18="100", i19="0"),
    account("3004", "6210", year=2025, i20="20", i13="4000", i18="300", i19="0"),
    account("3005", "6202", i20="5", i13="1000", i18="0", i19="250"),
    account("3006", "6209", i20="5", i13="1000"),
    account("3007", "6391", i20="5", i13="1000"),
    account("3008", "111", i20="5", i13="1000"),
    account("9000", "6201", i20="5", i13="1000"),
    account("1001", "6201", i20="5", i13="1000"),
]


def write_raw(raw_dir):
    firm_lines = [FIRMS_HEADER]
    status_lines = ["COD_INMATRICULARE^COD"]
    for name, cui, code, date, statuses in FIRMS:
        firm_lines.append(f"{name}^{cui}^{code}^{date}^SRL^Timiş^Timişoara")
        status_lines += [f"{code}^{status}" for status in statuses]
    (raw_dir / "firms").write_text("\n".join(firm_lines) + "\n", encoding="utf-8")
    (raw_dir / "firms.stats.json").write_text(
        json.dumps({"total": len(FIRMS), "kept": len(FIRMS)})
    )
    (raw_dir / "statuses").write_text("\r\n".join(status_lines) + "\r\n", encoding="utf-8", newline="")

    with open(load.STATUS_GROUPS, encoding="utf-8") as mapping:
        known = [f"{row['code']}^{row['name']}" for row in csv.DictReader(mapping)]
    code_lines = ["COD^DENUMIRE"] + known + [f"{UNMAPPED_CODE}^not mapped yet"]
    (raw_dir / "status_codes").write_text("\r\n".join(code_lines) + "\r\n", encoding="utf-8", newline="")

    sources = [
        Source("firms", "u", "firms", None, None, len(FIRMS)),
        Source("statuses", "u", "statuses", None, None, len(status_lines) - 1),
        Source("status_codes", "u", "status_codes", None, None, len(code_lines) - 1),
    ]
    for year in (2024, 2025):
        rows = [row for row_year, row in ACCOUNTS if row_year == year]
        key = f"accounts_{year}_abbreviated"
        (raw_dir / key).write_text("\r\n".join([ACCOUNTS_HEADER] + rows) + "\r\n", newline="")
        sources.append(Source(key, "u", "accounts", year, "abbreviated", len(rows)))
    return sources


@pytest.fixture
def cleaned(db_conn, tmp_path):
    run_pipeline(db_conn, tmp_path, write_raw(tmp_path))
    return db_conn


def one(conn, sql, *params):
    return conn.execute(sql, params).fetchone()


def profile(conn, cui, column):
    return one(conn, f"SELECT {column} FROM company_profile WHERE cui = %s", cui)[0]


def test_live_row_beats_deregistered_for_same_cui(cleaned):
    assert one(cleaned, "SELECT name, status_group FROM companies WHERE cui = 1000") == ("LIVE NAME SRL", "active")


def test_two_live_rows_go_to_ambiguous_and_stay_out(cleaned):
    assert one(cleaned, "SELECT count(*) FROM ambiguous_cui WHERE cui = 1001")[0] == 1
    assert one(cleaned, "SELECT count(*) FROM companies WHERE cui = 1001")[0] == 0
    assert one(cleaned, "SELECT count(*) FROM company_profile WHERE cui = 1001")[0] == 0


def test_deregistered_duplicates_with_different_names_are_ambiguous(cleaned):
    assert one(cleaned, "SELECT count(*) FROM ambiguous_cui WHERE cui = 1002")[0] == 1
    assert one(cleaned, "SELECT count(*) FROM companies WHERE cui = 1002")[0] == 0


def test_deregistered_duplicates_with_same_name_keep_the_latest(cleaned):
    row = one(cleaned, "SELECT name, registered_on::text FROM companies WHERE cui = 1003")
    assert row == ("SAME NAME SRL", "2005-01-01")


def test_empty_and_zero_cui_are_dropped_and_counted(db_conn, tmp_path):
    report = run_pipeline(db_conn, tmp_path, write_raw(tmp_path))

    assert report.counts["dropped_cui"] == 2
    assert one(db_conn, "SELECT count(*) FROM companies WHERE name IN ('NO CUI SRL', 'ZERO CUI SRL')")[0] == 0


@pytest.mark.parametrize(
    "cui, group",
    [
        (2001, "deregistered"),
        (2002, "bankruptcy"),
        (2003, "dissolution_liquidation"),
        (2004, "insolvency"),
        (2005, "suspended"),
    ],
)
def test_each_status_group_wins_over_the_ones_below_it(cleaned, cui, group):
    assert profile(cleaned, cui, "status_group") == group


def test_unmapped_code_is_unknown_never_active(cleaned):
    assert profile(cleaned, 2006, "status_group") == "unknown"
    assert profile(cleaned, 2010, "status_group") == "unknown"


def test_notice_alone_is_unknown_not_active(cleaned):
    assert profile(cleaned, 2008, "status_group") == "unknown"
    assert profile(cleaned, 2009, "status_group") == "unknown"


def test_notice_does_not_change_the_group_but_is_kept(cleaned):
    assert profile(cleaned, 2007, "status_group") == "active"
    codes = {row[0] for row in cleaned.execute("SELECT code FROM company_statuses WHERE cui = 2007")}
    assert codes == {"1048", "2069"}


def test_every_mapped_group_is_a_known_one():
    with open(load.STATUS_GROUPS, encoding="utf-8") as mapping:
        groups = {row["status_group"] for row in csv.DictReader(mapping)}
    assert groups == {
        "active",
        "suspended",
        "insolvency",
        "dissolution_liquidation",
        "bankruptcy",
        "deregistered",
        "notice",
    }


@pytest.mark.parametrize("cui", [3001, 3002])
def test_suspect_employees_kept_flagged_and_out_of_profile(cleaned, cui):
    reported, suspect = one(cleaned, "SELECT employees_reported, employees_suspect FROM financials WHERE cui = %s", cui)
    assert reported > 0 and suspect is True
    assert profile(cleaned, cui, "employees") is None
    assert profile(cleaned, cui, "employees_suspect") is True
    assert profile(cleaned, cui, "revenue_per_employee") is None


def test_believable_employees_are_not_suspect(cleaned):
    assert profile(cleaned, 3004, "employees") == 20
    assert profile(cleaned, 3004, "employees_suspect") is False


def test_net_result_from_profit_and_loss(cleaned):
    assert profile(cleaned, 3004, "net_result") == 300
    assert profile(cleaned, 3005, "net_result") == -250


def test_net_result_empty_when_both_columns_are_empty(cleaned):
    assert profile(cleaned, 3006, "net_result") is None


def test_amounts_come_from_the_right_columns(cleaned):
    row = one(cleaned, "SELECT revenue, total_assets, debts, equity FROM financials WHERE cui = 3003")
    assert row == (1000, 15, 3, 12)


def test_zero_employees_gives_empty_revenue_per_employee(cleaned):
    assert profile(cleaned, 3003, "employees") == 0
    assert profile(cleaned, 3003, "revenue_per_employee") is None


def test_revenue_per_employee_uses_latest_year(cleaned):
    assert profile(cleaned, 3004, "revenue_per_employee") == 200


def test_profile_knows_first_and_latest_year(cleaned):
    row = one(
        cleaned,
        "SELECT first_year, latest_year, years_count, first_revenue, first_employees, revenue "
        "FROM company_profile WHERE cui = 3004",
    )
    assert row == (2024, 2025, 2, 1000, 10, 4000)


def test_account_without_company_goes_to_rejected(db_conn, tmp_path):
    report = run_pipeline(db_conn, tmp_path, write_raw(tmp_path))

    rows = dict(db_conn.execute("SELECT cui, reason FROM rejected_financials").fetchall())
    assert rows == {"9000": "no_company", "1001": "ambiguous_cui"}
    assert report.counts["rejected_financials"] == 2


def test_old_and_new_codes_give_same_category(cleaned):
    categories = dict(
        cleaned.execute(
            "SELECT f.year, a.category FROM financials f JOIN activity_categories a USING (caen) "
            "WHERE f.cui = 3004"
        ).fetchall()
    )
    assert categories == {2024: "Software development", 2025: "Software development"}
    assert profile(cleaned, 3004, "category") == "Software development"


def test_6391_is_not_it(cleaned):
    assert profile(cleaned, 3007, "category") is None


def test_activity_code_is_padded_to_four_digits(cleaned):
    assert one(cleaned, "SELECT caen FROM financials WHERE cui = 3008")[0] == "0111"


def test_company_without_accounts_stays_with_no_category(cleaned):
    row = one(cleaned, "SELECT category, latest_year, revenue FROM company_profile WHERE cui = 3009")
    assert row == (None, None, None)


def test_search_name_ignores_diacritics_both_spellings(cleaned):
    found = {row[0] for row in cleaned.execute("SELECT cui FROM company_profile WHERE name_search LIKE '%timis%'")}
    assert found == {4001, 4002}


def test_county_and_locality_use_one_spelling(cleaned):
    assert profile(cleaned, 4001, "county") == "Timiș"
    assert profile(cleaned, 4001, "locality") == "Timișoara"


def test_both_date_formats_parse(cleaned):
    assert one(cleaned, "SELECT registered_on::text FROM companies WHERE cui = 4003")[0] == "2012-03-15"
    assert one(cleaned, "SELECT registered_on::text FROM companies WHERE cui = 4001")[0] == "2000-01-01"


def test_no_individuals_or_addresses_anywhere(cleaned):
    forms = {row[0] for row in cleaned.execute("SELECT DISTINCT legal_form FROM companies")}
    assert not forms & {"PF", "PFA", "II", "IF", "AF"}
    columns = {row[0] for row in cleaned.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public'")}
    assert not {"adr_den_strada", "adr_nr_strada", "adr_bloc", "adr_scara", "adr_etaj", "adr_apartament", "adr_cod_postal"} & columns


def test_report_counts_the_cleaning(db_conn, tmp_path):
    report = run_pipeline(db_conn, tmp_path, write_raw(tmp_path))

    assert report.counts["ambiguous_cui"] == 2
    assert report.counts["unknown_status"] == 4
    assert report.counts["suspect_employees"] == 2
    assert report.cleaning_s > 0
    assert report.index_s > 0


def test_shortlist_survives_a_reload(db_conn, tmp_path):
    sources = write_raw(tmp_path)
    run_pipeline(db_conn, tmp_path, sources)
    db_conn.execute("INSERT INTO shortlist (cui, note) VALUES (3004, 'look at this one')")

    run_pipeline(db_conn, tmp_path, sources, sample_pct=50)

    assert one(db_conn, "SELECT note FROM shortlist WHERE cui = 3004")[0] == "look at this one"


def test_without_indexes_the_load_still_works(db_conn, tmp_path):
    report = run_pipeline(db_conn, tmp_path, write_raw(tmp_path), create_indexes=False)

    assert report.index_s == 0
    names = {row[0] for row in db_conn.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'company_profile'")}
    assert names == {"company_profile_pkey"}


def test_changed_rules_load_again(db_conn, tmp_path, monkeypatch):
    sources = write_raw(tmp_path)
    run_pipeline(db_conn, tmp_path, sources)
    changed = tmp_path / "status_groups.csv"
    changed.write_text(Path(load.STATUS_GROUPS).read_text(encoding="utf-8") + '1081,suspended,"x"\n', encoding="utf-8")
    monkeypatch.setattr(load, "STATUS_GROUPS", changed)

    report = run_pipeline(db_conn, tmp_path, sources)

    assert report.status == "finished"
    assert profile(db_conn, 2006, "status_group") == "suspended"
