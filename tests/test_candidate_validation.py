import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from candidate_validation import (
    LOW_UPPER_BPS,
    NORMAL_UPPER_BPS,
    select_eligible_signal_times,
    write_candidate_v1_validation,
)
from data_store import save_dataset
from simulator import MARKET_TIMEZONE, generate_synthetic_data


class CandidateEligibilityTests(unittest.TestCase):
    def _data(self) -> pd.DataFrame:
        timestamps = pd.date_range(
            "2026-01-05 10:58", periods=5, freq="min", tz=MARKET_TIMEZONE
        )
        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "session": [timestamps[0].date()] * len(timestamps),
            }
        )

    def test_fixed_threshold_boundaries_are_exact(self) -> None:
        data = self._data()
        volatility = pd.DataFrame(
            {
                "timestamp": data["timestamp"],
                "volatility_bps": [
                    LOW_UPPER_BPS,
                    LOW_UPPER_BPS + 1e-10,
                    NORMAL_UPPER_BPS,
                    NORMAL_UPPER_BPS + 1e-10,
                    10.0,
                ],
            }
        )

        eligible = select_eligible_signal_times(data, volatility=volatility)

        self.assertNotIn(data.iloc[0]["timestamp"], eligible)
        self.assertIn(data.iloc[1]["timestamp"], eligible)
        self.assertIn(data.iloc[2]["timestamp"], eligible)
        self.assertNotIn(data.iloc[3]["timestamp"], eligible)

    def test_filter_uses_next_bar_entry_hour(self) -> None:
        data = self._data()
        volatility = pd.DataFrame(
            {"timestamp": data["timestamp"], "volatility_bps": [10.0] * 5}
        )

        eligible = select_eligible_signal_times(data, volatility=volatility)

        self.assertIn(data.iloc[1]["timestamp"], eligible)  # 10:59 -> 11:00
        self.assertNotIn(data.iloc[0]["timestamp"], eligible)  # 10:58 -> 10:59


class CandidateWriterTests(unittest.TestCase):
    def test_writer_records_checksums_and_refuses_overwrite(self) -> None:
        data = generate_synthetic_data(days=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, _ = save_dataset(
                data,
                root=root / "data",
                symbol="NVDA",
                feed="sip",
                requested_start="2026-01-05",
                requested_end="2026-01-05",
            )
            hypothesis = root / "candidate_hypothesis_v1.md"
            hypothesis.write_text("frozen candidate", encoding="utf-8")
            hypothesis_sha = hashlib.sha256(hypothesis.read_bytes()).hexdigest()
            hypothesis.with_suffix(".sha256").write_text(
                f"{hypothesis_sha}  {hypothesis.name}\n", encoding="utf-8"
            )

            paths = write_candidate_v1_validation(
                data,
                dataset_path=dataset,
                hypothesis_path=hypothesis,
                output_directory=root / "reports",
                report_name="test_validation",
            )
            summary = json.loads(paths["summary"].read_text(encoding="utf-8"))

            self.assertTrue(all(path.exists() for path in paths.values()))
            self.assertEqual(summary["hypothesis_sha256"], hypothesis_sha)
            self.assertEqual(
                summary["dataset_sha256"],
                hashlib.sha256(dataset.read_bytes()).hexdigest(),
            )
            with self.assertRaises(FileExistsError):
                write_candidate_v1_validation(
                    data,
                    dataset_path=dataset,
                    hypothesis_path=hypothesis,
                    output_directory=root / "reports",
                    report_name="test_validation",
                )


if __name__ == "__main__":
    unittest.main()
