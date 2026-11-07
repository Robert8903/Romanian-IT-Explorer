import json
import os

import psycopg
import pytest

from sources import Source

TEST_DB = "career_test"


def _connect(dbname, autocommit=True):
    return psycopg.connect(
        host="db",
        dbname=dbname,
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=autocommit,
    )


@pytest.fixture
def db_conn():
    """A connection to a fresh, empty database, removed after the test."""
    with _connect(os.environ["POSTGRES_DB"]) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
        admin.execute(f"CREATE DATABASE {TEST_DB}")
    conn = _connect(TEST_DB)
    yield conn
    conn.close()
    with _connect(os.environ["POSTGRES_DB"]) as admin:
        admin.execute(f"DROP DATABASE {TEST_DB}")


# Small copies of the real files: statuses and codes start with a BOM, and
# everything except the filtered firms file has Windows line endings.
FIRMS = (
    "DENUMIRE^CUI^COD_INMATRICULARE^DATA_INMATRICULARE^FORMA_JURIDICA^ADR_JUDET^ADR_LOCALITATE\n"
    "ALFA SRL^100^J1/1/2000^01/01/2000^SRL^Cluj^Cluj-Napoca\n"
    'CLINICA "BETA" SRL^125^J1/2/2000^02/01/2000^SRL^Iaşi^Iaşi\n'
    "GAMA\\DELTA SNC^150^J1/3/2000^03/01/2000^SNC^^\n"
    "OMEGA SA^175^J1/4/2000^04/01/2000^SA^Timiş^Timişoara\n"
)
FIRMS_STATS = {"total": 5, "kept": 4, "excluded_individual": 1, "excluded_unclear_form": 0, "malformed": 0}
STATUSES = (
    "﻿COD_INMATRICULARE^COD\r\n"
    "J1/1/2000^1048\r\n"
    "J1/2/2000^1048\r\n"
    "J1/2/2000^2069\r\n"
    "J1/3/2000^1084\r\n"
    "J1/4/2000^1048\r\n"
    "F9/9/2015^1084\r\n"
)
STATUS_CODES = "﻿COD^DENUMIRE\r\n1048^funcțiune\r\n1084^radiată\r\n"
ACCOUNTS_COLUMNS = "CUI,CAEN," + ",".join(f"I{i}" for i in range(1, 21))
ACCOUNTS_ABBREVIATED = (
    f"{ACCOUNTS_COLUMNS}\r\n"
    "100,6201,1,,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20\r\n"
    "125,6201,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20\r\n"
    "175,6202,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20\r\n"
)
ACCOUNTS_LONG = (
    f"{ACCOUNTS_COLUMNS}\r\n"
    "150,6210,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20\r\n"
)


@pytest.fixture
def raw_dir(tmp_path):
    (tmp_path / "firms").write_text(FIRMS, encoding="utf-8", newline="")
    (tmp_path / "firms.stats.json").write_text(json.dumps(FIRMS_STATS))
    (tmp_path / "statuses").write_text(STATUSES, encoding="utf-8", newline="")
    (tmp_path / "status_codes").write_text(STATUS_CODES, encoding="utf-8", newline="")
    (tmp_path / "accounts_2025_abbreviated").write_text(ACCOUNTS_ABBREVIATED, newline="")
    (tmp_path / "accounts_2024_long").write_text(ACCOUNTS_LONG, newline="")
    return tmp_path


@pytest.fixture
def sources():
    url = "http://example.test/file"
    return [
        Source("firms", url, "firms", None, None, 5),
        Source("statuses", url, "statuses", None, None, 6),
        Source("status_codes", url, "status_codes", None, None, 2),
        Source("accounts_2025_abbreviated", url, "accounts", 2025, "abbreviated", 3),
        Source("accounts_2024_long", url, "accounts", 2024, "long", 1),
    ]
