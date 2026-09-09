import tempfile
import unittest

import pandas as pd

from edge_diagnostics import (
    attach_volatility_regimes,
    calculate_causal_volatility,
    segment_performance,
    write_edge_diagnostics,
)
from simulator import MARKET_TIMEZONE, generate_synthetic_data


class EdgeDiagnosticTests(unittest.TestCase):
    def test_future_price_change_does_not_change_past_volatility(self):
        data = generate_synthetic_data(seed=8, days=1)
        first = calculate_causal_volatility(data)
        changed = data.copy()
        changed.loc[changed.index[-1], "close"] *= 1.5
        second = calculate_causal_volatility(changed)

        pd.testing.assert_series_equal(
            first.iloc[:-1]["volatility_bps"].reset_index(drop=True),
            second.iloc[:-1]["volatility_bps"].reset_index(drop=True),
        )

    def test_regime_attachment_uses_signal_timestamp(self):
        timestamps = pd.date_range(
            "2026-01-05 10:00", periods=3, freq="min", tz=MARKET_TIMEZONE
        )
        trades = pd.DataFrame(
            {
                "signal_time": timestamps,
                "entry_time": timestamps + pd.Timedelta(minutes=1),
                "net_pnl": [1.0, -1.0, 2.0],
            }
        )
        volatility = pd.DataFrame(
            {"timestamp": timestamps, "volatility_bps": [1.0, 2.0, 3.0]}
        )

        enriched, thresholds = attach_volatility_regimes(trades, volatility)

        self.assertEqual(enriched["volatility_regime"].tolist(), ["low", "normal", "high"])
        self.assertGreater(thresholds["normal_upper_bps"], thresholds["low_upper_bps"])

    def test_segment_metrics_are_net(self):
        trades = pd.DataFrame(
            {
                "volatility_regime": ["low", "low", "high"],
                "net_pnl": [2.0, -1.0, -3.0],
            }
        )

        report = segment_performance(trades, ["volatility_regime"])
        low = report[report["volatility_regime"] == "low"].iloc[0]

        self.assertEqual(low["trade_count"], 2)
        self.assertAlmostEqual(low["expectancy"], 0.5)
        self.assertAlmostEqual(low["profit_factor"], 2.0)

    def test_writer_creates_all_diagnostic_files(self):
        data = generate_synthetic_data(seed=10, days=2)

        with tempfile.TemporaryDirectory() as directory:
            paths = write_edge_diagnostics(
                data,
                output_directory=directory,
                report_name="diagnostic",
                dataset_path="data/example.parquet",
            )

            self.assertTrue(all(path.is_file() for path in paths.values()))
            self.assertIn("Senza costi", paths["markdown"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
