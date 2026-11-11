"""Download the files, load them into PostgreSQL and print what happened."""
import os
import sys
from pathlib import Path

import psycopg

from download import DownloadError, download
from load import LoadError, LoadReport, run_pipeline
from sources import ACCOUNTS, load_sources

RAW_DIR = Path("/data/raw")
DEFAULT_YEARS = "2021,2022,2023,2024,2025"


class SettingsError(Exception):
    pass


def read_years():
    text = os.environ.get("YEARS", DEFAULT_YEARS)
    try:
        years = [int(year) for year in text.split(",")]
    except ValueError as error:
        raise SettingsError(f"YEARS must be years separated by commas, got '{text}'") from error
    for year in years:
        if year not in ACCOUNTS:
            raise SettingsError(f"YEARS: no accounts files for {year}, available: {sorted(ACCOUNTS)}")
    return years


def read_sample_pct():
    text = os.environ.get("SAMPLE_PCT", "100")
    if not text.isdigit() or not 1 <= int(text) <= 100:
        raise SettingsError(f"SAMPLE_PCT must be a whole number from 1 to 100, got '{text}'")
    return int(text)


def connect():
    return psycopg.connect(
        host="db",
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=True,
    )


def print_report(report):
    print(f"Load {report.status}")
    if report.status == "finished":
        print(
            f"  raw copy {report.raw_copy_s:.1f} s, cleaning {report.cleaning_s:.1f} s, "
            f"indexes {report.index_s:.1f} s"
        )
    for name, count in report.counts.items():
        print(f"  {name}: {count:,}")


def main():
    try:
        years = read_years()
        sample_pct = read_sample_pct()
        create_indexes = os.environ.get("CREATE_INDEXES", "true") == "true"
        sources = load_sources(years)

        print(f"Years {years}, sample {sample_pct}%", flush=True)
        for source in sources:
            print(f"Checking {source.key}", flush=True)
            download(source, RAW_DIR)

        with connect() as conn:
            report = run_pipeline(conn, RAW_DIR, sources, sample_pct, create_indexes)
    except (SettingsError, DownloadError, LoadError, psycopg.Error) as error:
        print(f"Load failed: {error}", file=sys.stderr)
        return 1

    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
