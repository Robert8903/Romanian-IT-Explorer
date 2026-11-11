"""Measure load time, memory, disk and query time at several data sizes.

Runs on the laptop and drives Docker. It only uses its own database volume, so
it can't touch the real one, where My list lives. The downloads are reused.

    python3 measure/benchmark.py --sizes 25 50 100 --repeats 3 --out measure/results.csv
"""
import argparse
import csv
import os
import platform
import re
import subprocess
import time
from pathlib import Path

BENCH_VOLUME = "career_bench_dbdata"
LOADER_CONTAINER = "career-bench-loader"
ROOT = Path(__file__).resolve().parent.parent
UNITS = {"B": 1, "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3, "KB": 1000, "MB": 1000**2, "GB": 1000**3}
QUERY_RUNS = 4


def parse_mem(text):
    """'420.5MiB / 8GiB' -> bytes used."""
    match = re.match(r"\s*([\d.]+)\s*([A-Za-z]+)", text)
    return int(float(match.group(1)) * UNITS[match.group(2).upper()])


def average(runs):
    """Average every measured value of the runs of one size."""
    result = {"size_pct": runs[0]["size_pct"], "repeat": "average"}
    for name in runs[0]:
        if name not in result:
            result[name] = sum(run[name] for run in runs) / len(runs)
    return result


def bench_env(environment):
    return {**environment, "DB_VOLUME": BENCH_VOLUME}


def check_bench_volume(name):
    if name != BENCH_VOLUME:
        raise ValueError(f"Refusing to use volume '{name}': only {BENCH_VOLUME} may be removed")


def split_queries(text):
    """Read measure/queries.sql into {name: query}."""
    parts = re.split(r"^-- name: (\w+)\n", text, flags=re.MULTILINE)
    return {name: query.strip() for name, query in zip(parts[1::2], parts[2::2])}


def parse_times(output):
    return [float(value) for value in re.findall(r"^Time: ([\d.]+) ms", output, flags=re.MULTILINE)]


def warm_time(times):
    """The first run reads from disk; the others show the usual speed."""
    warm = times[1:]
    return sum(warm) / len(warm)


def run(command, env, input_text=None, check=True):
    return subprocess.run(
        command, cwd=ROOT, env=env, input=input_text, text=True, capture_output=True, check=check
    ).stdout


def compose(*arguments):
    return ["docker", "compose", *arguments]


def psql(env, script, *options):
    command = compose("exec", "-T", "db", "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" {" ".join(options)}')
    return run(command, env, input_text=script)


def reset_database(env):
    check_bench_volume(env["DB_VOLUME"])
    run(compose("down"), env)
    run(["docker", "volume", "rm", "--force", env["DB_VOLUME"]], env)


def peak_memory_during(process, env, db_container):
    peaks = {"db": 0, "loader": 0}
    names = {db_container: "db", LOADER_CONTAINER: "loader"}
    while process.poll() is None:
        stats = run(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.MemUsage}}"], env, check=False)
        for line in stats.splitlines():
            name, _, usage = line.partition("|")
            if name in names:
                peaks[names[name]] = max(peaks[names[name]], parse_mem(usage))
    return peaks


def load(env, size_pct):
    """Start the loader, watch memory while it works, and report its stored timings."""
    run(compose("up", "-d", "--wait", "db"), env)
    db_container = run(compose("ps", "--format", "{{.Name}}", "db"), env).strip()
    started = time.perf_counter()
    process = subprocess.Popen(
        compose(
            "run", "--rm", "--no-deps", "--name", LOADER_CONTAINER,
            "-e", f"SAMPLE_PCT={size_pct}", "-e", "CREATE_INDEXES=true", "loader",
        ),
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    peaks = peak_memory_during(process, env, db_container)
    errors = process.stderr.read()
    if process.returncode != 0:
        raise RuntimeError(f"The loader failed at {size_pct}%: {errors}")
    wall_s = time.perf_counter() - started

    timings = psql(
        env,
        "SELECT raw_copy_s, cleaning_s, index_s FROM load_runs ORDER BY id DESC LIMIT 1;",
        "-At", "-F,",
    ).strip()
    raw_copy_s, cleaning_s, index_s = (float(value) for value in timings.split(","))
    return {
        "load_s": wall_s,
        "raw_copy_s": raw_copy_s,
        "cleaning_s": cleaning_s,
        "index_s": index_s,
        "peak_db_bytes": peaks["db"],
        "peak_loader_bytes": peaks["loader"],
    }


def disk_sizes(env):
    output = psql(
        env,
        "SELECT 'database', pg_database_size(current_database()) "
        "UNION ALL SELECT relname, pg_total_relation_size(oid) FROM pg_class "
        "WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace;",
        "-At", "-F,",
    )
    sizes = {}
    for line in output.splitlines():
        name, size = line.split(",")
        sizes[f"disk_{name}_bytes"] = int(size)
    return sizes


def time_queries(env, queries, suffix):
    results = {}
    for name, query in queries.items():
        script = "\\timing on\n\\o /dev/null\n" + (query + "\n") * QUERY_RUNS
        results[f"query_{name}_{suffix}_ms"] = warm_time(parse_times(psql(env, script, "-q")))
    return results


def drop_indexes(env):
    text = (ROOT / "loader/sql/06_indexes.sql").read_text()
    names = re.findall(r"CREATE INDEX (\w+)", text)
    psql(env, "".join(f"DROP INDEX {name};\n" for name in names) + "ANALYZE;\n", "-q")


def measure_once(env, queries, size_pct, repeat):
    reset_database(env)
    result = {"size_pct": size_pct, "repeat": repeat}
    result.update(load(env, size_pct))
    result.update(disk_sizes(env))
    result.update(time_queries(env, queries, "with_indexes"))
    drop_indexes(env)
    result["disk_database_no_indexes_bytes"] = disk_sizes(env)["disk_database_bytes"]
    result.update(time_queries(env, queries, "without_indexes"))
    return result


def laptop_specs(env):
    docker = run(["docker", "info", "--format", "{{.NCPU}} CPUs, {{.MemTotal}} bytes of memory"], env).strip()
    processor = platform.processor() or platform.machine()
    return f"{platform.platform()}, {processor}; Docker: {docker}"


def raw_files_bytes(env):
    output = run(compose("run", "--rm", "--no-deps", "loader", "du", "-sb", "/data/raw"), env)
    return int(output.split()[0])


def write_results(path, specs, rows):
    columns = list(dict.fromkeys(column for row in rows for column in row))
    with open(path, "w", newline="") as output:
        output.write(f"# {specs}\n")
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[25, 50, 100])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", default="measure/results.csv")
    arguments = parser.parse_args()

    env = bench_env(dict(os.environ))
    check_bench_volume(env["DB_VOLUME"])
    queries = split_queries((ROOT / "measure/queries.sql").read_text())
    specs = laptop_specs(env)
    path = ROOT / arguments.out

    rows = []
    try:
        reset_database(env)
        run(compose("build", "loader"), env)
        raw_bytes = raw_files_bytes(env)
        for size_pct in arguments.sizes:
            runs = []
            for repeat in range(1, arguments.repeats + 1):
                print(f"{size_pct}%, run {repeat} of {arguments.repeats}", flush=True)
                result = measure_once(env, queries, size_pct, repeat)
                result["raw_files_bytes"] = raw_bytes
                runs.append(result)
                rows.append(result)
                write_results(path, specs, rows)
            rows.append(average(runs))
            write_results(path, specs, rows)
    finally:
        reset_database(env)
    print(f"Done: {path}. Start the app again with: docker compose up")


if __name__ == "__main__":
    main()
