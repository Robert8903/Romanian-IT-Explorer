import pytest

import main
from download import DownloadError


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture(autouse=True)
def fake_database(monkeypatch):
    monkeypatch.setattr(main, "connect", lambda: FakeConnection())
    monkeypatch.delenv("YEARS", raising=False)
    monkeypatch.delenv("SAMPLE_PCT", raising=False)


def test_main_returns_nonzero_and_names_the_problem_on_failure(monkeypatch, capsys):
    def failing_download(source, dest_dir):
        raise DownloadError(f"Could not download {source.key}")

    monkeypatch.setattr(main, "download", failing_download)

    assert main.main() == 1
    assert "Could not download firms" in capsys.readouterr().err


def test_main_returns_nonzero_when_the_load_fails(monkeypatch, capsys):
    def failing_load(*args, **kwargs):
        raise main.LoadError("accounts_2025_long: found 1 rows, expected 2")

    monkeypatch.setattr(main, "download", lambda source, dest_dir: None)
    monkeypatch.setattr(main, "run_pipeline", failing_load)

    assert main.main() == 1
    assert "accounts_2025_long" in capsys.readouterr().err


@pytest.mark.parametrize(
    "name, value, message",
    [
        ("YEARS", "2019", "2019"),
        ("YEARS", "abc", "YEARS"),
        ("YEARS", "", "YEARS"),
        ("SAMPLE_PCT", "0", "SAMPLE_PCT"),
        ("SAMPLE_PCT", "101", "SAMPLE_PCT"),
        ("SAMPLE_PCT", "half", "SAMPLE_PCT"),
    ],
)
def test_invalid_settings_give_a_clear_message(monkeypatch, capsys, name, value, message):
    monkeypatch.setenv(name, value)

    assert main.main() == 1
    assert message in capsys.readouterr().err


def test_main_passes_settings_and_prints_the_report(monkeypatch, capsys):
    calls = {}

    def fake_load(conn, raw_dir, sources, sample_pct, create_indexes):
        calls.update(sample_pct=sample_pct, create_indexes=create_indexes, keys=[s.key for s in sources])
        return main.LoadReport("skipped", counts={"companies": 7})

    monkeypatch.setenv("YEARS", "2025")
    monkeypatch.setenv("SAMPLE_PCT", "25")
    monkeypatch.setenv("CREATE_INDEXES", "false")
    monkeypatch.setattr(main, "download", lambda source, dest_dir: None)
    monkeypatch.setattr(main, "run_pipeline", fake_load)

    assert main.main() == 0
    assert calls["sample_pct"] == 25
    assert calls["create_indexes"] is False
    assert "accounts_2025_long" in calls["keys"]
    output = capsys.readouterr().out
    assert "skipped" in output and "companies" in output
