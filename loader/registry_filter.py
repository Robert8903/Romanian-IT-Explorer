"""Keep only companies from the Trade Registry file, without street addresses."""
from dataclasses import dataclass

SEPARATOR = "^"
INDIVIDUAL_FORMS = {"PF", "PFA", "II", "IF", "AF"}
UNCLEAR_FORMS = {"", "N/A"}
KEPT_COLUMNS = [
    "DENUMIRE",
    "CUI",
    "COD_INMATRICULARE",
    "DATA_INMATRICULARE",
    "FORMA_JURIDICA",
    "ADR_JUDET",
    "ADR_LOCALITATE",
]


@dataclass
class FilterStats:
    total: int = 0
    kept: int = 0
    excluded_individual: int = 0
    excluded_unclear_form: int = 0
    malformed: int = 0


def filter_registry(lines, stats):
    """Yield the header and the rows we keep, one at a time, counting the rest in stats."""
    lines = iter(lines)
    header = next(lines).lstrip("﻿").rstrip("\r\n").split(SEPARATOR)
    form_position = header.index("FORMA_JURIDICA")
    kept_positions = [header.index(column) for column in KEPT_COLUMNS]

    yield SEPARATOR.join(KEPT_COLUMNS)

    for line in lines:
        stats.total += 1
        fields = line.rstrip("\r\n").split(SEPARATOR)

        if len(fields) != len(header):
            stats.malformed += 1
        elif fields[form_position] in INDIVIDUAL_FORMS:
            stats.excluded_individual += 1
        elif fields[form_position] in UNCLEAR_FORMS:
            stats.excluded_unclear_form += 1
        else:
            stats.kept += 1
            yield SEPARATOR.join(fields[i] for i in kept_positions)
