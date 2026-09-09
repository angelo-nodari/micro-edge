import json
import tempfile
import unittest
from pathlib import Path

from research_status import REPORT_FILES, load_research_status


class ResearchStatusTests(unittest.TestCase):
    def test_missing_reports_are_marked_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            status = load_research_status(directory)

        self.assertEqual(status["verdict"], "RESEARCH_INCOMPLETE")
        self.assertEqual(status["experiments"], [])

    def test_rejected_and_empty_screens_produce_no_edge_verdict(self) -> None:
        reports = {
            "v1": {
                "decision": "REJECT",
                "metrics": {
                    "trade_count": 60,
                    "expectancy": -0.3,
                    "profit_factor": 0.6,
                },
            },
            "volume": {
                "candidate_screen": {"qualifying_bands": []},
                "bands": [
                    {
                        "range": "≥ 2.00",
                        "trade_count": 78,
                        "expectancy": -0.2,
                        "profit_factor": 0.7,
                    }
                ],
            },
            "qqq": {
                "candidate_screen": {"qualifying_regimes": []},
                "regimes": [
                    {
                        "qqq_regime": "stable",
                        "trade_count": 335,
                        "expectancy": -0.4,
                        "profit_factor": 0.5,
                    }
                ],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, content in reports.items():
                path = root / REPORT_FILES[key]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(content), encoding="utf-8")

            status = load_research_status(root)

        self.assertEqual(status["verdict"], "NO_EDGE_DEMONSTRATED")
        self.assertEqual(len(status["experiments"]), 3)
        self.assertEqual(status["experiments"][1]["segmento"], "Migliore fascia: ≥ 2.00")
