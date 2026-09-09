"""Read immutable research artifacts into a compact MVP status summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPORT_FILES = {
    "v1": Path("2026-06/NVDA_2026-06_candidate_v1_validation_summary.json"),
    "volume": Path("2026-05/NVDA_2026-05_v2_relative_volume_research_summary.json"),
    "qqq": Path("2026-05/NVDA_QQQ_2026-05_v2_market_context_research_summary.json"),
}


def load_research_status(report_root: str | Path = "reports") -> dict[str, Any]:
    """Return experiment rows and the conservative overall MVP verdict."""

    root = Path(report_root)
    loaded: dict[str, dict[str, Any]] = {}
    for key, relative_path in REPORT_FILES.items():
        path = root / relative_path
        if path.exists():
            loaded[key] = json.loads(path.read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    if "v1" in loaded:
        report = loaded["v1"]
        metrics = report["metrics"]
        rows.append(
            {
                "esperimento": "Candidata V1",
                "periodo": "Giugno 2026 (holdout)",
                "segmento": "Ora 11–12 + volatilità normale",
                "trade": int(metrics["trade_count"]),
                "expectancy": float(metrics["expectancy"]),
                "profit_factor": float(metrics["profit_factor"]),
                "esito": "Respinta" if report["decision"] == "REJECT" else report["decision"],
            }
        )

    if "volume" in loaded:
        report = loaded["volume"]
        best = _best_result(report["bands"])
        qualifying = report["candidate_screen"]["qualifying_bands"]
        rows.append(
            {
                "esperimento": "Volume relativo",
                "periodo": "Maggio 2026 (ricerca)",
                "segmento": f"Migliore fascia: {best['range']}",
                "trade": int(best["trade_count"]),
                "expectancy": float(best["expectancy"]),
                "profit_factor": float(best["profit_factor"]),
                "esito": "Nessun candidato" if not qualifying else "Da congelare",
            }
        )

    if "qqq" in loaded:
        report = loaded["qqq"]
        best = _best_result(report["regimes"])
        qualifying = report["candidate_screen"]["qualifying_regimes"]
        rows.append(
            {
                "esperimento": "Contesto QQQ",
                "periodo": "Maggio 2026 (ricerca)",
                "segmento": f"Migliore regime: {best['qqq_regime']}",
                "trade": int(best["trade_count"]),
                "expectancy": float(best["expectancy"]),
                "profit_factor": float(best["profit_factor"]),
                "esito": "Nessun candidato" if not qualifying else "Da congelare",
            }
        )

    complete = set(loaded) == set(REPORT_FILES)
    no_candidate = complete and all(
        row["esito"] in {"Respinta", "Nessun candidato"} for row in rows
    )
    verdict = (
        "NO_EDGE_DEMONSTRATED"
        if no_candidate
        else ("RESEARCH_INCOMPLETE" if not complete else "CANDIDATE_REQUIRES_REVIEW")
    )
    return {
        "verdict": verdict,
        "experiments": rows,
        "reports_loaded": sorted(loaded),
    }


def _best_result(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        raise ValueError("research report contains no results")
    return max(results, key=lambda item: float(item["expectancy"]))
