import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from reporting import daily_performance, hourly_performance, write_baseline_report
from simulator import MARKET_TIMEZONE, generate_synthetic_data


class ReportingTests(unittest.TestCase):
    @staticmethod
    def sample_trades() -> pd.DataFrame:
        timestamps = pd.to_datetime(
            [
                "2026-01-05 10:00",
                "2026-01-05 10:30",
                "2026-01-07 14:00",
            ]
        ).tz_localize(MARKET_TIMEZONE)
        return pd.DataFrame(
            {
                "entry_time": timestamps,
                "net_pnl": [4.0, -2.0, -3.0],
                "exit_reason": ["take_profit", "stop_loss", "max_holding"],
            }
        )

    def test_daily_report_includes_session_without_trades(self):
        data = generate_synthetic_data(seed=2, days=3)

        report = daily_performance(data, self.sample_trades())

        self.assertEqual(len(report), 3)
        self.assertEqual(report.iloc[0]["trade_count"], 2)
        self.assertEqual(report.iloc[1]["trade_count"], 0)
        self.assertAlmostEqual(report.iloc[0]["total_net_pnl"], 2.0)

    def test_hourly_report_uses_entry_hour(self):
        report = hourly_performance(self.sample_trades())

        ten = report[report["entry_hour"] == 10].iloc[0]
        fourteen = report[report["entry_hour"] == 14].iloc[0]
        self.assertEqual(ten["trade_count"], 2)
        self.assertAlmostEqual(ten["win_rate"], 0.5)
        self.assertEqual(fourteen["trade_count"], 1)

    def test_report_writer_creates_reproducible_artifacts(self):
        data = generate_synthetic_data(seed=4, days=2)

        with tempfile.TemporaryDirectory() as directory:
            paths = write_baseline_report(
                data,
                output_directory=directory,
                report_name="baseline",
                dataset_path="data/example.parquet",
            )
            summary = json.loads(paths["summary"].read_text(encoding="utf-8"))

            self.assertTrue(all(path.is_file() for path in paths.values()))
            self.assertEqual(summary["rows"], 2 * 386)
            self.assertEqual(summary["parameters"]["slippage_bps"], 1.0)
            self.assertIn("Sensibilità allo slippage", paths["markdown"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
