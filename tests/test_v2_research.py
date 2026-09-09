import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_store import save_dataset
from simulator import generate_synthetic_data
from v2_research import (
    VOLUME_BAND_ORDER,
    attach_relative_volume_bands,
    write_v2_research_report,
)


class VolumeBandTests(unittest.TestCase):
    def test_boundaries_are_predeclared_and_exhaustive(self) -> None:
        timestamps = pd.date_range("2026-05-01", periods=6, freq="min", tz="UTC")
        feature = pd.DataFrame(
            {
                "timestamp": timestamps,
                "relative_volume_30": [0.74, 0.75, 1.2499, 1.25, 1.9999, 2.0],
            }
        )

        result = attach_relative_volume_bands(feature)

        self.assertEqual(
            result["relative_volume_band"].tolist(),
            ["low", "normal", "normal", "high", "high", "very_high"],
        )


class V2ResearchWriterTests(unittest.TestCase):
    def test_report_is_complete_checksummed_and_immutable(self) -> None:
        data = generate_synthetic_data(days=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, _ = save_dataset(
                data,
                root=root / "data",
                symbol="NVDA",
                feed="sip",
                requested_start="2026-05-01",
                requested_end="2026-05-01",
            )

            paths = write_v2_research_report(
                data,
                dataset_path=dataset,
                output_directory=root / "reports",
                report_name="test_v2",
            )
            summary = json.loads(paths["summary"].read_text(encoding="utf-8"))

            self.assertTrue(all(path.exists() for path in paths.values()))
            self.assertEqual(
                summary["dataset_sha256"],
                hashlib.sha256(dataset.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                [item["relative_volume_band"] for item in summary["bands"]],
                VOLUME_BAND_ORDER,
            )
            with self.assertRaises(FileExistsError):
                write_v2_research_report(
                    data,
                    dataset_path=dataset,
                    output_directory=root / "reports",
                    report_name="test_v2",
                )


if __name__ == "__main__":
    unittest.main()
