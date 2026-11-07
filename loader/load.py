"""Copy the downloaded files into staging tables, in one transaction, safe to repeat."""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql"
STAGING_TABLES = [
    "staging_firms",
    "staging_statuses",
    "staging_status_codes",
    "staging_accounts",
]


class LoadError(Exception):
    pass


@dataclass
class LoadReport:
    status: str
    raw_copy_s: float = 0.0
    cleaning_s: float = 0.0
    index_s: float = 0.0
    counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class FileLayout:
    table: str
    separator: str
    header: list[str]
    cui_position: int | None = None


ACCOUNTS_HEADER = ["CUI", "CAEN"] + [f"I{i}" for i in range(1, 21)]
LAYOUTS = {
    "firms": FileLayout(
        "staging_firms",
        "^",
        [
            "DENUMIRE",
            "CUI",
            "COD_INMATRICULARE",
            "DATA_INMATRICULARE",
            "FORMA_JURIDICA",
            "ADR_JUDET",
            "ADR_LOCALITATE",
        ],
        cui_position=1,
    ),
    "statuses": FileLayout("all_statuses", "^", ["COD_INMATRICULARE", "COD"]),
    "status_codes": FileLayout("staging_status_codes", "^", ["COD", "DENUMIRE"]),
    "accounts": FileLayout("staging_accounts", ",", ACCOUNTS_HEADER, cui_position=0),
}


def _in_sample(cui, sample_pct):
    """The last two digits decide, so a 25% sample always sits inside the 50% one."""
    return sample_pct == 100 or (cui.isdigit() and int(cui) % 100 < sample_pct)


def _copy_file(cursor, source, path, sample_pct):
    """Send one file to its table through COPY and return how many rows the file has."""
    layout = LAYOUTS[source.kind]
    columns = [name.lower() for name in layout.header]
    fixed_values = []
    if source.kind == "accounts":
        columns = ["year", "filing_format"] + columns
        fixed_values = [str(source.year), source.format]

    rows_in_file = 0
    with open(path, encoding="utf-8-sig", newline="\n") as lines:
        header = next(lines, "").rstrip("\r\n").split(layout.separator)
        if header != layout.header:
            raise LoadError(f"{source.key}: unexpected columns {header}")

        with cursor.copy(f"COPY {layout.table} ({', '.join(columns)}) FROM STDIN") as copy:
            for line_number, line in enumerate(lines, start=2):
                fields = line.rstrip("\r\n").split(layout.separator)
                if len(fields) != len(header):
                    raise LoadError(
                        f"{source.key}: line {line_number} has {len(fields)} columns, "
                        f"expected {len(header)}"
                    )
                rows_in_file += 1
                if layout.cui_position is None or _in_sample(fields[layout.cui_position], sample_pct):
                    copy.write_row(fixed_values + [value or None for value in fields])
    return rows_in_file


def _check_row_count(source, raw_dir, rows_in_file):
    """A file with the wrong size means something went wrong: stop and name it."""
    expected = source.expected_rows
    if source.kind == "firms":
        # The saved file is already filtered, so its size comes from the download's
        # stats, and expected_rows describes the original file.
        stats = json.loads((Path(raw_dir) / f"{source.key}.stats.json").read_text())
        if stats["total"] != source.expected_rows:
            raise LoadError(
                f"{source.key}: the original file had {stats['total']} rows, "
                f"expected {source.expected_rows}"
            )
        expected = stats["kept"]
    if rows_in_file != expected:
        raise LoadError(f"{source.key}: found {rows_in_file} rows, expected {expected}")


def _run_sql(conn, file_name):
    conn.execute((SQL_DIR / file_name).read_text())


def _fingerprint(sources, sample_pct, create_indexes):
    return json.dumps(
        {
            "sources": sorted(f"{source.key} {source.url} {source.expected_rows}" for source in sources),
            "sample_pct": sample_pct,
            "create_indexes": create_indexes,
        }
    )


def _already_loaded(conn, fingerprint):
    """Only the latest run counts: an older one's data has since been replaced."""
    latest = conn.execute(
        "SELECT fingerprint, status FROM load_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return latest == (fingerprint, "finished")


def _count_rows(conn):
    return {
        table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in STAGING_TABLES
    }


def _record_run(conn, fingerprint, status, raw_copy_s=None, cleaning_s=None, index_s=None):
    conn.execute(
        "INSERT INTO load_runs (fingerprint, status, raw_copy_s, cleaning_s, index_s) "
        "VALUES (%s, %s, %s, %s, %s)",
        (fingerprint, status, raw_copy_s, cleaning_s, index_s),
    )


def run_pipeline(conn, raw_dir, sources, sample_pct=100, create_indexes=True):
    """Rebuild staging from the files, or do nothing if this exact load already finished."""
    fingerprint = _fingerprint(sources, sample_pct, create_indexes)

    with conn.transaction():
        _run_sql(conn, "00_load_runs.sql")
        if _already_loaded(conn, fingerprint):
            return LoadReport("skipped", counts=_count_rows(conn))

    try:
        # One transaction: a failure anywhere leaves the previous data untouched.
        with conn.transaction():
            started = time.perf_counter()
            _run_sql(conn, "01_schema.sql")
            with conn.cursor() as cursor:
                for source in sources:
                    path = Path(raw_dir) / source.key
                    rows_in_file = _copy_file(cursor, source, path, sample_pct)
                    _check_row_count(source, raw_dir, rows_in_file)
            conn.execute(
                "INSERT INTO staging_statuses "
                "SELECT cod_inmatriculare, cod FROM all_statuses a WHERE EXISTS ("
                "SELECT 1 FROM staging_firms f WHERE f.cod_inmatriculare = a.cod_inmatriculare)"
            )
            raw_copy_s = time.perf_counter() - started
            _record_run(conn, fingerprint, "finished", raw_copy_s, 0.0, 0.0)
            counts = _count_rows(conn)
    except Exception:
        with conn.transaction():
            _record_run(conn, fingerprint, "failed")
        raise

    return LoadReport("finished", raw_copy_s=raw_copy_s, counts=counts)
