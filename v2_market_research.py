"""Descriptive QQQ market-context research for the MicroEdge V2 cycle."""

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
from v2_features import calculate_qqq_return


QQQ_REGIME_ORDER = ["falling", "stable", "rising"]
QQQ_REGIME_LABELS = {
    "falling": "≤ -0.10%",
    "stable": "> -0.10% and < +0.10%",
    "rising": "≥ +0.10%",
}
QQQ_REGIME_THRESHOLD = 0.001


def attach_qqq_regimes(feature: pd.DataFrame) -> pd.DataFrame:
    """Apply the predeclared, mutually exclusive QQQ return regimes."""

    result = feature.copy()
    values = result["qqq_return_5m"]
    result["qqq_regime"] = np.select(
        [
            values <= -QQQ_REGIME_THRESHOLD,
            (values > -QQQ_REGIME_THRESHOLD)
            & (values < QQQ_REGIME_THRESHOLD),
            values >= QQQ_REGIME_THRESHOLD,
        ],
        QQQ_REGIME_ORDER,
        default=None,
    )
    return result


def analyze_qqq_regimes(
    nvda_data: pd.DataFrame,
    qqq_data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate each fixed QQQ regime independently on the NVDA baseline."""

    nvda_timestamps = nvda_data.sort_values("timestamp")["timestamp"].reset_index(
        drop=True
    )
    qqq_timestamps = qqq_data.sort_values("timestamp")["timestamp"].reset_index(
        drop=True
    )
    if not nvda_timestamps.equals(qqq_timestamps):
        raise ValueError("NVDA and QQQ timestamps are not exactly aligned")

    feature = attach_qqq_regimes(calculate_qqq_return(qqq_data))
    summary_rows: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []

    for regime in QQQ_REGIME_ORDER:
        eligible = set(feature.loc[feature["qqq_regime"] == regime, "timestamp"])
        trades = simulate_strategy(
            nvda_data,
            **DEFAULT_STRATEGY_PARAMETERS,
            eligible_signal_times=eligible,
        )
        metrics, _ = calculate_performance(trades)
        summary_rows.append(
            {
                "qqq_regime": regime,
                "range": QQQ_REGIME_LABELS[regime],
                "eligible_timestamp_count": len(eligible),
                **metrics,
            }
        )
        if not trades.empty:
            enriched = trades.merge(
                feature[["timestamp", "qqq_return_5m"]],
                left_on="signal_time",
                right_on="timestamp",
                how="left",
                validate="one_to_one",
            ).drop(columns="timestamp")
            enriched.insert(0, "qqq_regime", regime)
            trade_frames.append(enriched)

    regime_summary = pd.DataFrame(summary_rows)
    all_trades = (
        pd.concat(trade_frames, ignore_index=True)
        if trade_frames
        else pd.DataFrame()
    )
    return regime_summary, all_trades


def write_qqq_research_report(
    nvda_data: pd.DataFrame,
    qqq_data: pd.DataFrame,
    *,
    nvda_dataset_path: str | Path,
    qqq_dataset_path: str | Path,
    output_directory: str | Path,
    report_name: str = "NVDA_QQQ_2026-05_v2_market_context_research",
) -> dict[str, Path]:
    """Write an immutable QQQ-context research report for May."""

    nvda_dataset_path = Path(nvda_dataset_path)
    qqq_dataset_path = Path(qqq_dataset_path)
    output_directory = Path(output_directory)
    paths = {
        "markdown": output_directory / f"{report_name}.md",
        "summary": output_directory / f"{report_name}_summary.json",
        "regimes": output_directory / f"{report_name}_regimes.csv",
        "trades": output_directory / f"{report_name}_trades.csv",
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"research artifact already exists: {existing[0]}")

    nvda_sha = _verified_dataset_sha(nvda_dataset_path)
    qqq_sha = _verified_dataset_sha(qqq_dataset_path)
    regimes, trades = analyze_qqq_regimes(nvda_data, qqq_data)
    qualifying = regimes.loc[
        (regimes["trade_count"] >= 30)
        & (regimes["expectancy"] > 0)
        & (regimes["profit_factor"] > 1),
        "qqq_regime",
    ].tolist()
    summary = {
        "research_version": 1,
        "status": "DESCRIPTIVE_RESEARCH_NOT_VALIDATION",
        "primary_symbol": "NVDA",
        "market_context_symbol": "QQQ",
        "feed": "sip",
        "nvda_dataset_path": str(nvda_dataset_path),
        "nvda_dataset_sha256": nvda_sha,
        "qqq_dataset_path": str(qqq_dataset_path),
        "qqq_dataset_sha256": qqq_sha,
        "rows": int(len(nvda_data)),
        "sessions": int(nvda_data["session"].nunique()),
        "feature": {
            "name": "qqq_return_5m",
            "definition": "close[t] / close[t-5] - 1 within each session",
            "regime_threshold": QQQ_REGIME_THRESHOLD,
            "regimes": QQQ_REGIME_LABELS,
        },
        "parameters": DEFAULT_STRATEGY_PARAMETERS,
        "candidate_screen": {
            "minimum_trades": 30,
            "expectancy_must_exceed": 0,
            "profit_factor_must_exceed": 1,
            "qualifying_regimes": qualifying,
        },
        "regimes": [
            {key: _json_value(value) for key, value in row.items()}
            for row in regimes.to_dict(orient="records")
        ],
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    regimes.to_csv(paths["regimes"], index=False)
    trades.to_csv(paths["trades"], index=False)
    paths["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        _render_markdown(summary, regimes), encoding="utf-8"
    )
    return paths


def _verified_dataset_sha(path: Path) -> str:
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = json.loads(
        path.with_suffix(".metadata.json").read_text(encoding="utf-8")
    )
    if checksum != metadata.get("parquet_sha256"):
        raise ValueError(f"dataset checksum does not match metadata: {path}")
    return checksum


def _json_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _render_markdown(summary: dict[str, Any], regimes: pd.DataFrame) -> str:
    lines = [
        "# MicroEdge — Ricerca V2 sul contesto QQQ",
        "",
        "**Analisi descrittiva sul research set di maggio 2026; non è una validazione.**",
        "",
        "## Metodo",
        "",
        "Il rendimento QQQ a cinque minuti è misurato allo stesso timestamp del segnale NVDA. I tre regimi sono stati fissati prima dei risultati e sono simulati separatamente con parametri e costi baseline invariati.",
        "",
        f"- SHA-256 NVDA: `{summary['nvda_dataset_sha256']}`",
        f"- SHA-256 QQQ: `{summary['qqq_dataset_sha256']}`",
        f"- Barre/sessioni allineate: {summary['rows']} / {summary['sessions']}",
        "",
        "## Risultati per regime QQQ",
        "",
        "| Regime | Intervallo | Trade | Win rate | Expectancy | Profit factor | P&L netto |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in regimes.iterrows():
        lines.append(
            f"| {row['qqq_regime']} | {row['range']} | {int(row['trade_count'])} | "
            f"{row['win_rate']:.1%} | ${row['expectancy']:.4f} | "
            f"{_format_ratio(row['profit_factor'])} | ${row['total_net_pnl']:.2f} |"
        )
    qualifying = summary["candidate_screen"]["qualifying_regimes"]
    conclusion = (
        "Regimi che superano lo screening minimo: " + ", ".join(qualifying) + "."
        if qualifying
        else "Nessun regime supera lo screening minimo predefinito."
    )
    lines.extend(
        [
            "",
            "## Screening",
            "",
            conclusion,
            "",
            "Lo screening non dimostra un edge. Un’eventuale candidata deve essere congelata prima di accedere al holdout di aprile.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_ratio(value: float) -> str:
    return "∞" if math.isinf(value) else f"{value:.3f}"
