import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_store import save_dataset
from simulator import generate_synthetic_data
from v2_market_research import (
    QQQ_REGIME_ORDER,
    analyze_qqq_regimes,
    attach_qqq_regimes,
    write_qqq_research_report,
)


class QqqRegimeTests(unittest.TestCase):
    def test_boundaries_are_fixed_and_mutually_exclusive(self) -> None:
        timestamps = pd.date_range("2026-05-01", periods=5, freq="min", tz="UTC")
        feature = pd.DataFrame(
            {
                "timestamp": timestamps,
                "qqq_return_5m": [-0.0011, -0.001, 0.0, 0.000999, 0.001],
            }
        )

        result = attach_qqq_regimes(feature)

        self.assertEqual(
            result["qqq_regime"].tolist(),
            ["falling", "falling", "stable", "stable", "rising"],
        )

    def test_misaligned_datasets_are_rejected(self) -> None:
        nvda = generate_synthetic_data(days=1)
        qqq = nvda.copy()
        qqq.loc[0, "timestamp"] = qqq.loc[0, "timestamp"] + pd.Timedelta(seconds=1)

        with self.assertRaises(ValueError):
            analyze_qqq_regimes(nvda, qqq)


class QqqResearchWriterTests(unittest.TestCase):
    def test_report_records_both_checksums_and_refuses_overwrite(self) -> None:
        nvda = generate_synthetic_data(days=1)
        qqq = nvda.copy()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nvda_path, _ = save_dataset(
                nvda,
                root=root / "data",
                symbol="NVDA",
                feed="sip",
                requested_start="2026-05-01",
                requested_end="2026-05-01",
            )
            qqq_path, _ = save_dataset(
                qqq,
                root=root / "data",
                symbol="QQQ",
                feed="sip",
                requested_start="2026-05-01",
                requested_end="2026-05-01",
            )

            paths = write_qqq_research_report(
                nvda,
                qqq,
                nvda_dataset_path=nvda_path,
                qqq_dataset_path=qqq_path,
                output_directory=root / "reports",
                report_name="test_market",
            )
            summary = json.loads(paths["summary"].read_text(encoding="utf-8"))

            self.assertTrue(all(path.exists() for path in paths.values()))
            self.assertEqual(
                summary["nvda_dataset_sha256"],
                hashlib.sha256(nvda_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                summary["qqq_dataset_sha256"],
                hashlib.sha256(qqq_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                [item["qqq_regime"] for item in summary["regimes"]],
                QQQ_REGIME_ORDER,
            )
            with self.assertRaises(FileExistsError):
                write_qqq_research_report(
                    nvda,
                    qqq,
                    nvda_dataset_path=nvda_path,
                    qqq_dataset_path=qqq_path,
                    output_directory=root / "reports",
                    report_name="test_market",
                )


if __name__ == "__main__":
    unittest.main()
