import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "measure"))

import benchmark


class ParseMemTest(unittest.TestCase):
    def test_mebibytes(self):
        self.assertEqual(benchmark.parse_mem("420.5MiB / 8GiB"), int(420.5 * 1024**2))

    def test_gibibytes(self):
        self.assertEqual(benchmark.parse_mem("1.2GiB / 8GiB"), int(1.2 * 1024**3))

    def test_kibibytes_and_bytes(self):
        self.assertEqual(benchmark.parse_mem("512KiB / 8GiB"), 512 * 1024)
        self.assertEqual(benchmark.parse_mem("0B / 0B"), 0)


class AverageTest(unittest.TestCase):
    def test_average_over_three_runs(self):
        runs = [
            {"size_pct": 25, "repeat": 1, "load_s": 10.0},
            {"size_pct": 25, "repeat": 2, "load_s": 20.0},
            {"size_pct": 25, "repeat": 3, "load_s": 30.0},
        ]
        self.assertEqual(
            benchmark.average(runs),
            {"size_pct": 25, "repeat": "average", "load_s": 20.0},
        )


class SafetyTest(unittest.TestCase):
    def test_script_uses_its_own_database_volume(self):
        env = benchmark.bench_env({"PATH": "x", "DB_VOLUME": "career_dbdata"})
        self.assertEqual(env["DB_VOLUME"], "career_bench_dbdata")
        self.assertEqual(env["PATH"], "x")

    def test_refuses_to_remove_the_real_database_volume(self):
        for name in ("career_dbdata", "", "romanian-it-explorer_rawdata"):
            with self.assertRaises(ValueError):
                benchmark.check_bench_volume(name)

    def test_accepts_the_bench_volume(self):
        benchmark.check_bench_volume("career_bench_dbdata")


class ReadingOutputTest(unittest.TestCase):
    def test_splits_queries_by_name(self):
        text = "-- name: one\nSELECT 1;\n\n-- name: two\nSELECT\n  2;\n"
        self.assertEqual(
            benchmark.split_queries(text),
            {"one": "SELECT 1;", "two": "SELECT\n  2;"},
        )

    def test_reads_times_from_psql(self):
        output = "Timing is on.\nTime: 12.500 ms\nTime: 1.500 ms\n"
        self.assertEqual(benchmark.parse_times(output), [12.5, 1.5])

    def test_reads_times_above_one_second(self):
        output = "Time: 1234.567 ms (00:01.235)\n"
        self.assertEqual(benchmark.parse_times(output), [1234.567])

    def test_warm_time_leaves_out_the_first_run(self):
        self.assertEqual(benchmark.warm_time([100.0, 2.0, 4.0]), 3.0)


if __name__ == "__main__":
    unittest.main()
