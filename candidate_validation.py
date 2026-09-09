"""One-shot, auditable validation of the frozen MicroEdge candidate V1."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from edge_diagnostics import calculate_causal_volatility
from reporting import daily_performance, exit_reason_performance
from simulator import calculate_performance, simulate_strategy


LOW_UPPER_BPS = 8.68276241023262
NORMAL_UPPER_BPS = 13.727347968793827
ENTRY_HOURS = frozenset({11, 12})
FROZEN_PARAMETERS: dict[str, object] = {
    "drop_threshold": 0.002,
    "lookback_minutes": 5,
    "take_profit": 0.002,
    "stop_loss": 0.0015,
    "max_holding_bars": 5,
    "capital_per_trade": 1_000.0,
    "spread_bps": 2.0,
    "slippage_bps": 1.0,
    "broker_profile": "alpaca_personal_api",
    "commission_per_order": 0.0,
}


def select_eligible_signal_times(
    data: pd.DataFrame,
    *,
    volatility: pd.DataFrame | None = None,
) -> set[pd.Timestamp]:
    """Return V1-eligible signal timestamps using only frozen conditions."""

    ordered = data.sort_values("timestamp").reset_index(drop=True)
    feature = volatility if volatility is not None else calculate_causal_volatility(ordered)
    prepared = ordered[["timestamp", "session"]].merge(
        feature,
        on="timestamp",
        how="left",
        validate="one_to_one",
    )
    prepared["entry_time"] = prepared.groupby("session", sort=False)[
        "timestamp"
    ].shift(-1)
    normal = (prepared["volatility_bps"] > LOW_UPPER_BPS) & (
        prepared["volatility_bps"] <= NORMAL_UPPER_BPS
    )
    allowed_hour = prepared["entry_time"].dt.hour.isin(ENTRY_HOURS)
    return set(prepared.loc[normal & allowed_hour, "timestamp"])


def classify_without_confidence_interval(metrics: dict[str, float | int]) -> str:
    """Apply the frozen decision rules that do not require the Step 4 CI."""

    if metrics["expectancy"] <= 0 or metrics["profit_factor"] <= 1:
        return "REJECT"
    if metrics["trade_count"] < 30:
        return "INCONCLUSIVE"
    return "INCONCLUSIVE_PENDING_CONFIDENCE_INTERVAL"


def write_candidate_v1_validation(
    data: pd.DataFrame,
    *,
    dataset_path: str | Path,
    hypothesis_path: str | Path,
    output_directory: str | Path,
    report_name: str = "NVDA_2026-06_candidate_v1_validation",
) -> dict[str, Path]:
    """Run and persist the frozen V1 exactly once; existing artifacts abort it."""

    dataset_path = Path(dataset_path)
    hypothesis_path = Path(hypothesis_path)
    output_directory = Path(output_directory)
    paths = {
        "markdown": output_directory / f"{report_name}.md",
        "summary": output_directory / f"{report_name}_summary.json",
        "trades": output_directory / f"{report_name}_trades.csv",
        "daily": output_directory / f"{report_name}_daily.csv",
        "exits": output_directory / f"{report_name}_exit_reasons.csv",
        "slippage": output_directory / f"{report_name}_slippage.csv",
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"validation artifact already exists: {existing[0]}")

    dataset_sha = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    metadata_path = dataset_path.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if dataset_sha != metadata.get("parquet_sha256"):
        raise ValueError("dataset checksum does not match its metadata")

    hypothesis_sha = hashlib.sha256(hypothesis_path.read_bytes()).hexdigest()
    checksum_path = hypothesis_path.with_suffix(".sha256")
    recorded_hypothesis_sha = checksum_path.read_text(encoding="utf-8").split()[0]
    if hypothesis_sha != recorded_hypothesis_sha:
        raise ValueError("hypothesis checksum does not match its checksum file")

    eligible = select_eligible_signal_times(data)
    trades = simulate_strategy(
        data,
        **FROZEN_PARAMETERS,
        eligible_signal_times=eligible,
    )
    metrics, _ = calculate_performance(trades)
    daily = daily_performance(data, trades)
    exits = exit_reason_performance(trades)
    slippage = _slippage_sensitivity(data, eligible)
    decision = classify_without_confidence_interval(metrics)

    summary: dict[str, Any] = {
        "validation_version": 1,
        "candidate": "V1",
        "status": "FROZEN_HOLDOUT_EVALUATED_ONCE",
        "symbol": "NVDA",
        "feed": "sip",
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha,
        "hypothesis_path": str(hypothesis_path),
        "hypothesis_sha256": hypothesis_sha,
        "rows": int(len(data)),
        "sessions": int(data["session"].nunique()),
        "first_timestamp": data.iloc[0]["timestamp"].isoformat(),
        "last_timestamp": data.iloc[-1]["timestamp"].isoformat(),
        "eligibility": {
            "volatility_low_upper_bps_exclusive": LOW_UPPER_BPS,
            "volatility_normal_upper_bps_inclusive": NORMAL_UPPER_BPS,
            "entry_hours": sorted(ENTRY_HOURS),
            "eligible_signal_timestamp_count": len(eligible),
            "volatility_window": 30,
            "volatility_min_periods": 5,
        },
        "parameters": FROZEN_PARAMETERS,
        "metrics": {key: _json_value(value) for key, value in metrics.items()},
        "decision": decision,
        "confidence_interval_status": "NOT_YET_CALCULATED_STEP_4",
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    trades.to_csv(paths["trades"], index=False)
    daily.to_csv(paths["daily"], index=False)
    exits.to_csv(paths["exits"], index=False)
    slippage.to_csv(paths["slippage"], index=False)
    paths["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        _render_markdown(summary, slippage), encoding="utf-8"
    )
    return paths


def _slippage_sensitivity(
    data: pd.DataFrame, eligible: set[pd.Timestamp]
) -> pd.DataFrame:
    rows: list[dict[str, float | int | None]] = []
    for value in (0.0, 1.0, 2.0, 5.0):
        parameters = dict(FROZEN_PARAMETERS)
        parameters["slippage_bps"] = value
        trades = simulate_strategy(
            data, **parameters, eligible_signal_times=eligible
        )
        metrics, _ = calculate_performance(trades)
        rows.append(
            {
                "slippage_bps": value,
                **{key: _json_value(item) for key, item in metrics.items()},
            }
        )
    return pd.DataFrame(rows)


def _json_value(value: float | int) -> float | int | None:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _render_markdown(summary: dict[str, Any], slippage: pd.DataFrame) -> str:
    metrics = summary["metrics"]
    eligibility = summary["eligibility"]
    lines = [
        "# MicroEdge — Validazione holdout candidata V1",
        "",
        f"**Decisione: {summary['decision']}**",
        "",
        "## Integrità",
        "",
        f"- SHA-256 ipotesi: `{summary['hypothesis_sha256']}`",
        f"- SHA-256 dataset: `{summary['dataset_sha256']}`",
        f"- Periodo: {summary['first_timestamp']} — {summary['last_timestamp']}",
        f"- Barre/sessioni: {summary['rows']} / {summary['sessions']}",
        "",
        "## Regola congelata",
        "",
        f"- Volatilità normale: > {eligibility['volatility_low_upper_bps_exclusive']:.10f} bp e ≤ {eligibility['volatility_normal_upper_bps_inclusive']:.10f} bp",
        "- Ora di ingresso: 11 o 12 (New York)",
        "- Calo a 5 minuti: ≤ -0,20%",
        "- TP +0,20%; SL -0,15%; holding massimo 5 barre",
        "- Alpaca Personal API; spread 2 bp; slippage 1 bp per lato",
        "",
        "## Risultato primario",
        "",
        f"- Trade: {metrics['trade_count']}",
        f"- Win rate: {metrics['win_rate']:.1%}",
        f"- Expectancy netta: ${metrics['expectancy']:.4f}",
        f"- Profit factor: {_format_ratio(metrics['profit_factor'])}",
        f"- P&L netto: ${metrics['total_net_pnl']:.2f}",
        f"- Max drawdown: ${metrics['max_drawdown']:.2f} ({metrics['max_drawdown_pct']:.2%})",
        "",
        "## Sensibilità allo slippage",
        "",
        "| Slippage/lato (bp) | Trade | Expectancy | Profit factor | P&L netto |",
        "|---:|---:|---:|---:|---:|",
    ]
    for _, row in slippage.iterrows():
        lines.append(
            f"| {row['slippage_bps']:.0f} | {int(row['trade_count'])} | "
            f"${row['expectancy']:.4f} | {_format_ratio(row['profit_factor'])} | "
            f"${row['total_net_pnl']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Nota decisionale",
            "",
            "Il risultato usa il holdout una sola volta e senza ricalibrare soglie o parametri. L’intervallo di confidenza per giornata appartiene allo Step 4 e non è stato ancora calcolato.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return "∞" if math.isinf(value) else f"{value:.3f}"
