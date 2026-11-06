from registry_filter import FilterStats, filter_registry

HEADER = (
    "DENUMIRE^CUI^COD_INMATRICULARE^DATA_INMATRICULARE^EUID^FORMA_JURIDICA^ADR_TARA^"
    "ADR_JUDET^ADR_LOCALITATE^ADR_DEN_STRADA^ADR_NR_STRADA^ADR_BLOC^ADR_SCARA^ADR_ETAJ^"
    "ADR_APARTAMENT^ADR_COD_POSTAL^ADR_SECTOR^ADR_COMPLETARE^WEB^TARA_FIRMA_MAMA"
)


def row(name, form):
    return (
        f"{name}^123^J40/1/2020^01/02/2020^EU1^{form}^România^Cluj^Cluj-Napoca^"
        "Str. Secret^7^B1^A^2^9^400000^^^^"
    )


SAMPLE = [
    HEADER,
    row("Firma Unu", "SRL"),
    row("Persoana A", "PF"),
    row("Persoana B", "PFA"),
    row("Persoana C", "II"),
    row("Persoana D", "IF"),
    row("Persoana E", "AF"),
    row("Firma Doi", "SA"),
    row("Fara forma", ""),
    row("Forma necunoscuta", "N/A"),
]


def test_keeps_only_companies_and_the_columns_we_need():
    stats = FilterStats()
    out = list(filter_registry(SAMPLE, stats))

    assert out[0] == (
        "DENUMIRE^CUI^COD_INMATRICULARE^DATA_INMATRICULARE^"
        "FORMA_JURIDICA^ADR_JUDET^ADR_LOCALITATE"
    )
    assert out[1] == "Firma Unu^123^J40/1/2020^01/02/2020^SRL^Cluj^Cluj-Napoca"
    assert [line.split("^")[4] for line in out[1:]] == ["SRL", "SA"]


def test_no_street_address_reaches_the_output():
    out = "\n".join(filter_registry(SAMPLE, FilterStats()))
    assert "Secret" not in out
    assert "400000" not in out
    assert "Persoana" not in out


def test_counts_every_row():
    stats = FilterStats()
    list(filter_registry(SAMPLE, stats))

    assert stats.total == 9
    assert stats.kept == 2
    assert stats.excluded_individual == 5
    assert stats.excluded_unclear_form == 2
    assert stats.malformed == 0


def test_malformed_row_is_counted_not_written():
    stats = FilterStats()
    out = list(filter_registry([HEADER, "only^three^fields"], stats))

    assert len(out) == 1
    assert stats.total == 1
    assert stats.malformed == 1


def test_handles_bom_and_line_endings():
    lines = ["﻿" + HEADER + "\r\n", row("Firma", "SRL") + "\r\n"]
    out = list(filter_registry(lines, FilterStats()))

    assert out[0].startswith("DENUMIRE^")
    assert out[1].endswith("Cluj-Napoca")
