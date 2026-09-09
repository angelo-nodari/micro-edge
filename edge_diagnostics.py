"""Causal, descriptive diagnostics for the MicroEdge baseline strategy."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from reporting import DEFAULT_STRATEGY_PARAMETERS
from simulator import calculate_performance, simulate_strategy


REGIME_ORDER = ["low", "normal", "high"]


def calculate_causal_volatility(
    data: pd.DataFrame,
    *,
    window: int = 30,
    min_periods: int = 5,
) -> pd.DataFrame:
    """Calculate rolling one-minute volatility using no future observations."""

    if window < 2 or min_periods < 2 or min_periods > window:
        raise ValueError("invalid volatility window")

    ordered = data.sort_values("timestamp").reset_index(drop=True).copy()
    returns = ordered.groupby("session", sort=False)["close"].pct_change()
    ordered["volatility_bps"] = returns.groupby(ordered["session"], sort=False).transform(
        lambda values: values.rolling(window, min_periods=min_periods).std() * 10_000
    )
    return ordered[["timestamp", "volatility_bps"]]


def attach_volatility_regimes(
    trades: pd.DataFrame,
    volatility: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Attach descriptive monthly volatility terciles at each signal time."""

    if trades.empty:
        empty = trades.copy()
        empty["volatility_bps"] = pd.Series(dtype=float)
        empty["volatility_regime"] = pd.Series(dtype=str)
        return empty, {"low_upper_bps": 0.0, "normal_upper_bps": 0.0}

    enriched = trades.merge(
        volatility,
        left_on="signal_time",
        right_on="timestamp",
        how="left",
        validate="many_to_one",
    ).drop(columns="timestamp")
    if enriched["volatility_bps"].isna().any():
        raise ValueError("volatility is unavailable for one or more trade signals")

    low_upper = float(enriched["volatility_bps"].quantile(1 / 3))
    normal_upper = float(enriched["volatility_bps"].quantile(2 / 3))
    enriched["volatility_regime"] = np.select(
        [
            enriched["volatility_bps"] <= low_upper,
            enriched["volatility_bps"] <= normal_upper,
        ],
        ["low", "normal"],
        default="high",
    )
    return enriched, {
        "low_upper_bps": low_upper,
        "normal_upper_bps": normal_upper,
    }


def segment_performance(
    trades: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    """Aggregate trade outcomes for descriptive segments."""

    rows: list[dict[str, Any]] = []
    for group, group_data in trades.groupby(group_columns, sort=True):
        group_values = group if isinstance(group, tuple) else (group,)
        pnl = group_data["net_pnl"].astype(float)
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        gross_profit = float(wins.sum())
        gross_loss = float(-losses.sum())
        row = dict(zip(group_columns, group_values))
        row.update(
            {
                "trade_count": int(len(pnl)),
                "win_rate": float((pnl > 0).mean()),
                "expectancy": float(pnl.mean()),
                "profit_factor": (
                    gross_profit / gross_loss
                    if gross_loss
                    else (float("inf") if gross_profit else 0.0)
                ),
                "total_net_pnl": float(pnl.sum()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def write_edge_diagnostics(
    data: pd.DataFrame,
    *,
    output_directory: str | Path,
    report_name: str,
    dataset_path: str,
) -> dict[str, Path]:
    """Write costless-vs-Alpaca diagnostics without changing the strategy."""

    alpaca_parameters = dict(DEFAULT_STRATEGY_PARAMETERS)
    alpaca_trades = simulate_strategy(data, **alpaca_parameters)
    alpaca_metrics, _ = calculate_performance(alpaca_trades)

    costless_parameters = dict(alpaca_parameters)
    costless_parameters.update(
        {
            "spread_bps": 0.0,
            "slippage_bps": 0.0,
            "broker_profile": "custom_flat",
            "commission_per_order": 0.0,
        }
    )
    costless_trades = simulate_strategy(data, **costless_parameters)
    costless_metrics, _ = calculate_performance(costless_trades)

    volatility = calculate_causal_volatility(data)
    alpaca_enriched, alpaca_thresholds = attach_volatility_regimes(
        alpaca_trades, volatility
    )
    costless_enriched, costless_thresholds = attach_volatility_regimes(
        costless_trades, volatility
    )
    alpaca_enriched["entry_hour"] = alpaca_enriched["entry_time"].dt.hour
    costless_enriched["entry_hour"] = costless_enriched["entry_time"].dt.hour

    alpaca_regimes = segment_performance(alpaca_enriched, ["volatility_regime"])
    costless_regimes = segment_performance(costless_enriched, ["volatility_regime"])
    alpaca_hour_regime = segment_performance(
        alpaca_enriched, ["entry_hour", "volatility_regime"]
    )
    costless_hour_regime = segment_performance(
        costless_enriched, ["entry_hour", "volatility_regime"]
    )

    decomposition = {
        "gross_pnl_on_alpaca_trade_path": float(alpaca_trades["gross_pnl"].sum()),
        "spread_cost": float(alpaca_trades["spread_cost"].sum()),
        "slippage_cost": float(alpaca_trades["slippage_cost"].sum()),
        "broker_commission": float(alpaca_trades["broker_commission"].sum()),
        "regulatory_fees": float(alpaca_trades["regulatory_fees"].sum()),
        "net_pnl": float(alpaca_trades["net_pnl"].sum()),
    }

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "markdown": output_directory / f"{report_name}.md",
        "summary": output_directory / f"{report_name}_summary.json",
        "alpaca_regimes": output_directory / f"{report_name}_alpaca_regimes.csv",
        "costless_regimes": output_directory / f"{report_name}_costless_regimes.csv",
        "alpaca_hour_regime": output_directory / f"{report_name}_alpaca_hour_regime.csv",
        "costless_hour_regime": output_directory / f"{report_name}_costless_hour_regime.csv",
    }
    alpaca_regimes.to_csv(paths["alpaca_regimes"], index=False)
    costless_regimes.to_csv(paths["costless_regimes"], index=False)
    alpaca_hour_regime.to_csv(paths["alpaca_hour_regime"], index=False)
    costless_hour_regime.to_csv(paths["costless_hour_regime"], index=False)

    summary = {
        "diagnostic_version": 1,
        "dataset_path": dataset_path,
        "rows": int(len(data)),
        "sessions": int(data["session"].nunique()),
        "volatility_method": {
            "return_frequency": "1Min",
            "rolling_window": 30,
            "min_periods": 5,
            "units": "basis_points",
            "regimes": "descriptive monthly terciles",
        },
        "alpaca_metrics": _json_metrics(alpaca_metrics),
        "costless_metrics": _json_metrics(costless_metrics),
        "alpaca_regime_thresholds": alpaca_thresholds,
        "costless_regime_thresholds": costless_thresholds,
        "alpaca_cost_decomposition": decomposition,
    }
    paths["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        _render_diagnostics(summary, alpaca_regimes, costless_regimes),
        encoding="utf-8",
    )
    return paths


def _json_metrics(metrics: dict[str, float | int]) -> dict[str, float | int | None]:
    return {
        key: (None if isinstance(value, float) and not math.isfinite(value) else value)
        for key, value in metrics.items()
    }


def _render_diagnostics(
    summary: dict[str, Any],
    alpaca_regimes: pd.DataFrame,
    costless_regimes: pd.DataFrame,
) -> str:
    alpaca = summary["alpaca_metrics"]
    costless = summary["costless_metrics"]
    costs = summary["alpaca_cost_decomposition"]
    thresholds = summary["alpaca_regime_thresholds"]
    return "\n".join(
        [
            "# MicroEdge — Diagnostica dell'edge NVDA",
            "",
            "## Metodo",
            "",
            "La strategia e i suoi parametri restano invariati. Il confronto senza costi usa spread, slippage e commissioni pari a zero. La volatilità è calcolata causalmente sui rendimenti a un minuto disponibili fino al segnale.",
            "",
            "I regimi sono tercili descrittivi calcolati su questo stesso mese: non sono regole operative e non devono essere applicati out-of-sample senza una validazione separata.",
            "",
            "## Confronto complessivo",
            "",
            "| Scenario | Trade | Win rate | Expectancy | Profit factor | P&L |",
            "|---|---:|---:|---:|---:|---:|",
            _comparison_row("Senza costi", costless),
            _comparison_row("Alpaca + esecuzione", alpaca),
            "",
            "## Scomposizione dei costi sul percorso Alpaca",
            "",
            f"- P&L lordo: ${costs['gross_pnl_on_alpaca_trade_path']:.2f}",
            f"- Spread: ${costs['spread_cost']:.2f}",
            f"- Slippage: ${costs['slippage_cost']:.2f}",
            f"- Commissioni broker: ${costs['broker_commission']:.2f}",
            f"- Fee regolamentari: ${costs['regulatory_fees']:.2f}",
            f"- P&L netto: ${costs['net_pnl']:.2f}",
            "",
            "## Soglie descrittive di volatilità",
            "",
            f"- Bassa: ≤ {thresholds['low_upper_bps']:.2f} bp",
            f"- Normale: ≤ {thresholds['normal_upper_bps']:.2f} bp",
            f"- Alta: > {thresholds['normal_upper_bps']:.2f} bp",
            "",
            "## Regimi — scenario senza costi",
            "",
            _simple_markdown_table(costless_regimes),
            "",
            "## Regimi — scenario Alpaca",
            "",
            _simple_markdown_table(alpaca_regimes),
            "",
            "Le combinazioni complete ora × regime sono disponibili nei CSV adiacenti. Nessun segmento è stato selezionato o trasformato in una regola.",
            "",
        ]
    )


def _comparison_row(label: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {label} | {metrics['trade_count']} | {metrics['win_rate']:.1%} | "
        f"${metrics['expectancy']:.2f} | {_ratio(metrics['profit_factor'])} | "
        f"${metrics['total_net_pnl']:.2f} |"
    )


def _simple_markdown_table(data: pd.DataFrame) -> str:
    columns = list(data.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    for _, row in data.iterrows():
        formatted = []
        for column in columns:
            value = row[column]
            if column == "trade_count":
                formatted.append(str(int(value)))
            elif column == "win_rate":
                formatted.append(f"{float(value):.1%}")
            elif column in {"expectancy", "total_net_pnl"}:
                formatted.append(f"${float(value):.2f}")
            elif column == "profit_factor":
                formatted.append(_ratio(float(value)))
            else:
                formatted.append(str(value))
        lines.append("| " + " | ".join(formatted) + " |")
    return "\n".join(lines)


def _ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return "∞" if math.isinf(value) else f"{value:.2f}"
