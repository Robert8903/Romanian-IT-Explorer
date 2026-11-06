import io
import json
from urllib.error import HTTPError

import pytest

from download import DownloadError, download
from sources import Source

ACCOUNTS = Source("accounts_2025_long", "http://example.test/a.txt", "accounts", 2025, "long", 1)
FIRMS = Source("firms", "http://example.test/f.csv", "firms", None, None, 2)

HEADER = (
    "DENUMIRE^CUI^COD_INMATRICULARE^DATA_INMATRICULARE^EUID^FORMA_JURIDICA^ADR_TARA^"
    "ADR_JUDET^ADR_LOCALITATE^ADR_DEN_STRADA^ADR_NR_STRADA^ADR_BLOC^ADR_SCARA^ADR_ETAJ^"
    "ADR_APARTAMENT^ADR_COD_POSTAL^ADR_SECTOR^ADR_COMPLETARE^WEB^TARA_FIRMA_MAMA"
)


def firm_row(name, form):
    return f"{name}^1^J1^01/01/2020^E^{form}^RO^Cluj^Cluj^Str^1^^^^^^^^^"


class BreaksHalfway(io.BytesIO):
    def read(self, *args):
        if self.tell() > 0:
            raise OSError("connection lost")
        return super().read(3)


def always_breaks(request, timeout=None):
    return BreaksHalfway(b"abcdefgh")


def test_saves_accounts_file_unchanged(tmp_path):
    path = download(ACCOUNTS, tmp_path, opener=lambda r, timeout=None: io.BytesIO(b"CUI,CAEN\n1,6201\n"))

    assert path == tmp_path / "accounts_2025_long"
    assert path.read_bytes() == b"CUI,CAEN\n1,6201\n"


def test_interrupted_download_leaves_no_file_behind(tmp_path):
    with pytest.raises(DownloadError):
        download(ACCOUNTS, tmp_path, opener=always_breaks, wait_seconds=0)

    assert list(tmp_path.iterdir()) == []


def test_retries_then_succeeds(tmp_path):
    attempts = []

    def fails_twice(request, timeout=None):
        attempts.append(1)
        if len(attempts) < 3:
            raise OSError("temporary")
        return io.BytesIO(b"ok")

    path = download(ACCOUNTS, tmp_path, opener=fails_twice, wait_seconds=0)

    assert len(attempts) == 3
    assert path.read_bytes() == b"ok"


def test_gives_up_after_three_attempts_and_names_the_source(tmp_path):
    attempts = []

    def fails(request, timeout=None):
        attempts.append(1)
        raise HTTPError(request.full_url, 404, "Not Found", None, None)

    with pytest.raises(DownloadError) as error:
        download(ACCOUNTS, tmp_path, opener=fails, wait_seconds=0)

    assert len(attempts) == 3
    assert "accounts_2025_long" in str(error.value)
    assert ACCOUNTS.url in str(error.value)


def test_existing_file_is_not_downloaded_again(tmp_path):
    (tmp_path / "accounts_2025_long").write_bytes(b"already here")

    def must_not_run(request, timeout=None):
        raise AssertionError("should not download")

    path = download(ACCOUNTS, tmp_path, opener=must_not_run)

    assert path.read_bytes() == b"already here"


def test_registry_is_filtered_while_downloading(tmp_path):
    content = "﻿" + "\r\n".join([HEADER, firm_row("Firma", "SRL"), firm_row("Persoana", "PFA")]) + "\r\n"

    path = download(FIRMS, tmp_path, opener=lambda r, timeout=None: io.BytesIO(content.encode("utf-8")))

    saved = path.read_text(encoding="utf-8")
    assert "Firma" in saved
    assert "Persoana" not in saved
    assert "Str" not in saved
    stats = json.loads((tmp_path / "firms.stats.json").read_text())
    assert stats == {
        "total": 2,
        "kept": 1,
        "excluded_individual": 1,
        "excluded_unclear_form": 0,
        "malformed": 0,
    }
