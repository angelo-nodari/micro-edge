"""Descriptive research report for the MicroEdge V2 relative-volume idea."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from reporting import DEFAULT_STRATEGY_PARAMETERS
from simulator import calculate_performance, simulate_strategy
from v2_features import calculate_relative_volume


VOLUME_BAND_ORDER = ["low", "normal", "high", "very_high"]
VOLUME_BAND_LABELS = {
    "low": "< 0.75",
    "normal": "0.75–<1.25",
    "high": "1.25–<2.00",
    "very_high": "≥ 2.00",
}


def attach_relative_volume_bands(
    feature: pd.DataFrame,
) -> pd.DataFrame:
    """Apply the predeclared V2 research bands without fitting thresholds."""

    result = feature.copy()
    values = result["relative_volume_30"]
    result["relative_volume_band"] = np.select(
        [
            values < 0.75,
            values < 1.25,
            values < 2.0,
            values >= 2.0,
        ],
        VOLUME_BAND_ORDER,
        default=None,
    )
    return result


def analyze_volume_bands(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate each fixed volume band independently with baseline costs."""

    feature = attach_relative_volume_bands(calculate_relative_volume(data))
    summary_rows: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []

    for band in VOLUME_BAND_ORDER:
        eligible = set(
            feature.loc[feature["relative_volume_band"] == band, "timestamp"]
        )
        trades = simulate_strategy(
            data,
            **DEFAULT_STRATEGY_PARAMETERS,
            eligible_signal_times=eligible,
        )
        metrics, _ = calculate_performance(trades)
        summary_rows.append(
            {
                "relative_volume_band": band,
                "range": VOLUME_BAND_LABELS[band],
                "eligible_timestamp_count": len(eligible),
                **metrics,
            }
        )
        if not trades.empty:
            enriched = trades.merge(
                feature[["timestamp", "relative_volume_30"]],
                left_on="signal_time",
                right_on="timestamp",
                how="left",
                validate="one_to_one",
            ).drop(columns="timestamp")
            enriched.insert(0, "relative_volume_band", band)
            trade_frames.append(enriched)

    band_summary = pd.DataFrame(summary_rows)
    all_trades = (
        pd.concat(trade_frames, ignore_index=True)
        if trade_frames
        else pd.DataFrame()
    )
    return band_summary, all_trades


def write_v2_research_report(
    data: pd.DataFrame,
    *,
    dataset_path: str | Path,
    output_directory: str | Path,
    report_name: str = "NVDA_2026-05_v2_relative_volume_research",
) -> dict[str, Path]:
    """Write an immutable descriptive report for the May research set."""

    dataset_path = Path(dataset_path)
    output_directory = Path(output_directory)
    paths = {
        "markdown": output_directory / f"{report_name}.md",
        "summary": output_directory / f"{report_name}_summary.json",
        "bands": output_directory / f"{report_name}_bands.csv",
        "trades": output_directory / f"{report_name}_trades.csv",
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"research artifact already exists: {existing[0]}")

    dataset_sha = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    metadata = json.loads(
        dataset_path.with_suffix(".metadata.json").read_text(encoding="utf-8")
    )
    if dataset_sha != metadata.get("parquet_sha256"):
        raise ValueError("dataset checksum does not match its metadata")

    bands, trades = analyze_volume_bands(data)
    positive_candidates = bands.loc[
        (bands["trade_count"] >= 30)
        & (bands["expectancy"] > 0)
        & (bands["profit_factor"] > 1),
        "relative_volume_band",
    ].tolist()
    summary = {
        "research_version": 1,
        "status": "DESCRIPTIVE_RESEARCH_NOT_VALIDATION",
        "symbol": "NVDA",
        "feed": "sip",
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha,
        "rows": int(len(data)),
        "sessions": int(data["session"].nunique()),
        "feature": {
            "name": "relative_volume_30",
            "denominator": "median of prior 30 within-session bars",
            "min_periods": 10,
            "current_bar_excluded_from_denominator": True,
            "bands": VOLUME_BAND_LABELS,
        },
        "parameters": DEFAULT_STRATEGY_PARAMETERS,
        "candidate_screen": {
            "minimum_trades": 30,
            "expectancy_must_exceed": 0,
            "profit_factor_must_exceed": 1,
            "qualifying_bands": positive_candidates,
        },
        "bands": [
            {key: _json_value(value) for key, value in row.items()}
            for row in bands.to_dict(orient="records")
        ],
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    bands.to_csv(paths["bands"], index=False)
    trades.to_csv(paths["trades"], index=False)
    paths["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        _render_markdown(summary, bands), encoding="utf-8"
    )
    return paths


def _json_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _render_markdown(summary: dict[str, Any], bands: pd.DataFrame) -> str:
    lines = [
        "# MicroEdge — Ricerca V2 sul volume relativo",
        "",
        "**Analisi descrittiva sul research set di maggio 2026; non è una validazione.**",
        "",
        "## Metodo",
        "",
        "La feature confronta il volume corrente con la mediana delle 30 barre precedenti della stessa sessione. Le fasce sono state definite prima di osservare i risultati. Ogni fascia è simulata separatamente con i parametri baseline e i costi Alpaca.",
        "",
        f"- Dataset SHA-256: `{summary['dataset_sha256']}`",
        f"- Barre/sessioni: {summary['rows']} / {summary['sessions']}",
        "",
        "## Risultati per fascia",
        "",
        "| Fascia | Intervallo | Trade | Win rate | Expectancy | Profit factor | P&L netto |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in bands.iterrows():
        lines.append(
            f"| {row['relative_volume_band']} | {row['range']} | "
            f"{int(row['trade_count'])} | {row['win_rate']:.1%} | "
            f"${row['expectancy']:.4f} | {_format_ratio(row['profit_factor'])} | "
            f"${row['total_net_pnl']:.2f} |"
        )
    qualifying = summary["candidate_screen"]["qualifying_bands"]
    conclusion = (
        "Fasce che superano lo screening minimo: " + ", ".join(qualifying) + "."
        if qualifying
        else "Nessuna fascia supera lo screening minimo predefinito."
    )
    lines.extend(
        [
            "",
            "## Screening",
            "",
            conclusion,
            "",
            "Lo screening non dimostra un edge. Un’eventuale regola deve essere congelata prima di accedere al nuovo holdout di aprile.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_ratio(value: float) -> str:
    return "∞" if math.isinf(value) else f"{value:.3f}"
