import pytest

from sources import load_sources


def test_only_the_requested_years():
    sources = load_sources([2024, 2025])

    assert len(sources) == 9
    assert {s.year for s in sources if s.kind == "accounts"} == {2024, 2025}
    assert [s.kind for s in sources if s.year is None] == ["firms", "statuses", "status_codes"]


def test_each_source_has_a_unique_file_name():
    sources = load_sources([2021, 2022, 2023, 2024, 2025])

    assert len(sources) == 18
    assert len({s.key for s in sources}) == 18


def test_unknown_year_names_the_year():
    with pytest.raises(ValueError, match="2019"):
        load_sources([2019])
