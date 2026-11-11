import pytest

from common import COUNTY_TILES
from queries import (
    DEFAULT_IT_CATEGORIES,
    Filters,
    company_history,
    company_statuses,
    filter_options,
    it_companies_by_county,
    search_companies,
)


def names(rows):
    return [row["name"] for row in rows]


def everything(**settings):
    return Filters(categories=[], statuses=[], min_employees=None, **settings)


def test_default_filters_show_only_active_it_with_employees(conn):
    found = names(search_companies(conn, Filters()))

    assert "ALFA SOFT SRL" in found
    assert "NO STAFF SOFT SRL" not in found
    assert "CLOSED SOFT SRL" not in found
    assert "FARM SRL" not in found
    assert "NO ACCOUNTS SRL" not in found


def test_sorted_by_employees_and_suspect_values_last(conn):
    found = names(search_companies(conn, Filters(min_employees=None)))

    assert found[:2] == ["BETA SOFT SRL", "ALFA SOFT SRL"]
    assert found[-1] == "SUSPECT SOFT SRL"


@pytest.mark.parametrize("text", ["timis", "TIMIS", "Timiş", "Timiș", "  timis "])
def test_name_search_finds_with_and_without_diacritics(conn, text):
    found = names(search_companies(conn, Filters(name=text)))

    assert set(found) == {"SOFT TIMIȘ SRL", "SOFT TIMIŞ DOI SRL"}


@pytest.mark.parametrize(
    "text, expected",
    [
        ("%", ["100% SOFT SRL"]),
        ("_", []),
        ("'", ["O'NEIL SOFT SRL"]),
        ("o'neil", ["O'NEIL SOFT SRL"]),
        ("\\", []),
        ("%%soft", []),
    ],
)
def test_percent_underscore_and_quote_are_literal(conn, text, expected):
    assert names(search_companies(conn, Filters(name=text))) == expected


def test_no_results_returns_empty_list(conn):
    assert search_companies(conn, Filters(name="nothing like this")) == []


def test_blank_name_does_not_filter(conn):
    assert len(search_companies(conn, Filters(name="   "))) == len(search_companies(conn, Filters()))


def test_turning_it_filter_off_shows_companies_without_accounts(conn):
    found = names(search_companies(conn, Filters(categories=[], min_employees=None)))

    assert "NO ACCOUNTS SRL" in found
    assert "FARM SRL" in found


def test_county_and_status_filters(conn):
    assert names(search_companies(conn, Filters(counties=["Iași"]))) == ["BETA SOFT SRL"]
    assert names(search_companies(conn, Filters(statuses=["deregistered"]))) == ["CLOSED SOFT SRL"]


def test_minimum_revenue_filter(conn):
    assert names(search_companies(conn, Filters(min_revenue=1000))) == ["ALFA SOFT SRL"]


def test_limit_is_respected(conn):
    assert len(search_companies(conn, everything(), limit=3)) == 3


def test_change_uses_named_period_for_company_with_fewer_years(conn):
    rows = {row["name"]: row for row in search_companies(conn, everything())}

    assert rows["ALFA SOFT SRL"]["period"] == "2021–2025"
    assert rows["ALFA SOFT SRL"]["revenue_change_pct"] == 100
    assert rows["BETA SOFT SRL"]["period"] == "2025"
    assert rows["BETA SOFT SRL"]["revenue_change_pct"] is None


def test_change_from_zero_is_empty_not_an_error(conn):
    rows = {row["name"]: row for row in search_companies(conn, everything())}

    assert rows["NO STAFF SOFT SRL"]["period"] == "2024–2025"
    assert rows["NO STAFF SOFT SRL"]["revenue_change_pct"] is None


def test_company_without_accounts_has_empty_period(conn):
    rows = {row["name"]: row for row in search_companies(conn, everything())}

    assert rows["NO ACCOUNTS SRL"]["period"] is None


def test_filter_options_lists_real_values(conn):
    options = filter_options(conn)

    assert options["counties"] == ["Cluj", "Iași", "Timiș"]
    assert "active" in options["statuses"] and "deregistered" in options["statuses"]
    assert options["categories"] == ["Software development"]


def test_default_categories_exclude_telecom():
    assert "Telecommunications" not in DEFAULT_IT_CATEGORIES
    assert len(DEFAULT_IT_CATEGORIES) == 4


def test_history_has_empty_for_missing_years_not_zero(conn):
    rows = company_history(conn, [1])
    by_year = {row["year"]: row for row in rows}

    assert sorted(by_year) == [2021, 2022, 2024, 2025]
    assert by_year[2024]["net_result"] == -30


def test_compare_five_companies_returns_all_years_with_gaps(conn):
    rows = company_history(conn, [1, 2, 7, 6, 3])
    beta = {row["year"]: row for row in rows if row["cui"] == 2}

    assert len(rows) == 5 * 4
    assert beta[2021]["revenue"] is None
    assert beta[2025]["revenue"] == 500
    assert beta[2021]["name"] == "BETA SOFT SRL"


def test_history_hides_suspect_employees(conn):
    rows = {row["year"]: row for row in company_history(conn, [7])}

    assert rows[2025]["employees"] is None
    assert rows[2025]["employees_suspect"] is True


def test_history_of_nobody_is_empty(conn):
    assert company_history(conn, []) == []


def test_statuses_show_their_real_names(conn):
    assert sorted(company_statuses(conn, 1)) == ["funcțiune", "sediu expirat"]


def test_county_counts_use_the_explore_defaults(conn):
    counts = it_companies_by_county(conn)

    assert counts == {"Cluj": 3, "Iași": 1, "Timiș": 2}
    assert counts["Cluj"] == len(search_companies(conn, Filters(counties=["Cluj"])))


def test_map_has_every_county_once_on_its_own_tile():
    positions = [(column, row) for _, column, row in COUNTY_TILES.values()]
    plates = [plate for plate, _, _ in COUNTY_TILES.values()]

    assert len(COUNTY_TILES) == 42
    assert len(set(positions)) == 42
    assert len(set(plates)) == 42
