import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data_store import inspect_data_quality, load_dataset, save_dataset
from simulator import generate_synthetic_data


class DataStoreTests(unittest.TestCase):
    def test_quality_report_for_complete_session(self):
        data = generate_synthetic_data(seed=5, days=1)

        quality = inspect_data_quality(data)

        self.assertEqual(quality["missing_values"], 0)
        self.assertEqual(quality["duplicate_timestamps"], 0)
        self.assertEqual(quality["invalid_ohlcv_rows"], 0)
        self.assertEqual(quality["incomplete_full_sessions"], [])

    def test_save_and_verified_load_round_trip(self):
        data = generate_synthetic_data(seed=5, days=1).drop(columns="session_number")
        fixed_download_time = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as directory:
            parquet_path, metadata_path = save_dataset(
                data,
                root=directory,
                symbol="nvda",
                feed="sip",
                requested_start="2026-01-05",
                requested_end="2026-01-05",
                downloaded_at=fixed_download_time,
            )
            restored = load_dataset(parquet_path)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            pd.testing.assert_frame_equal(restored, data)
            self.assertEqual(metadata["symbol"], "NVDA")
            self.assertEqual(metadata["feed"], "sip")
            self.assertEqual(metadata["rows"], 386)
            self.assertEqual(metadata["quality"]["incomplete_full_sessions"], [])
            self.assertNotIn("key", json.dumps(metadata).lower())
            self.assertTrue(parquet_path.is_file())

    def test_existing_dataset_is_not_overwritten(self):
        data = generate_synthetic_data(seed=5, days=1).drop(columns="session_number")

        with tempfile.TemporaryDirectory() as directory:
            arguments = {
                "root": directory,
                "symbol": "NVDA",
                "feed": "sip",
                "requested_start": "2026-01-05",
                "requested_end": "2026-01-05",
            }
            save_dataset(data, **arguments)

            with self.assertRaises(FileExistsError):
                save_dataset(data, **arguments)


if __name__ == "__main__":
    unittest.main()
