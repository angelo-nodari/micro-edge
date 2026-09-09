"""Reproducible baseline reports for MicroEdge backtests."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from broker_costs import BROKER_LABELS
from simulator import calculate_performance, simulate_strategy


DEFAULT_STRATEGY_PARAMETERS: dict[str, object] = {
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


def daily_performance(data: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    """Aggregate net results by session, including sessions without trades."""

    sessions = pd.Index(sorted(data["session"].drop_duplicates()), name="session")
    if trades.empty:
        grouped = pd.DataFrame(index=sessions)
    else:
        prepared = trades.assign(session=trades["entry_time"].dt.date)
        grouped = _aggregate(prepared, "session").set_index("session")
    return _fill_missing_groups(grouped.reindex(sessions)).reset_index()


def hourly_performance(trades: pd.DataFrame) -> pd.DataFrame:
    """Aggregate net results by entry hour for the configured trading window."""

    hours = pd.Index(range(9, 16), name="entry_hour")
    if trades.empty:
        grouped = pd.DataFrame(index=hours)
    else:
        prepared = trades.assign(entry_hour=trades["entry_time"].dt.hour)
        grouped = _aggregate(prepared, "entry_hour").set_index("entry_hour")
    return _fill_missing_groups(grouped.reindex(hours)).reset_index()


def exit_reason_performance(trades: pd.DataFrame) -> pd.DataFrame:
    """Aggregate results by take-profit, stop-loss, or timed exit."""

    reasons = pd.Index(["take_profit", "stop_loss", "max_holding"], name="exit_reason")
    if trades.empty:
        grouped = pd.DataFrame(index=reasons)
    else:
        grouped = _aggregate(trades, "exit_reason").set_index("exit_reason")
    return _fill_missing_groups(grouped.reindex(reasons)).reset_index()


def slippage_sensitivity(
    data: pd.DataFrame,
    *,
    slippage_values: Iterable[float] = (0.0, 1.0, 2.0, 5.0),
    parameters: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Run the unchanged baseline under multiple per-side slippage assumptions."""

    base = dict(DEFAULT_STRATEGY_PARAMETERS)
    if parameters:
        base.update(parameters)

    rows: list[dict[str, float | int]] = []
    for slippage in slippage_values:
        scenario = dict(base)
        scenario["slippage_bps"] = float(slippage)
        trades = simulate_strategy(data, **scenario)
        metrics, _ = calculate_performance(trades)
        rows.append({"slippage_bps": float(slippage), **metrics})
    return pd.DataFrame(rows)


def write_baseline_report(
    data: pd.DataFrame,
    *,
    output_directory: str | Path,
    report_name: str,
    dataset_path: str,
    symbol: str = "NVDA",
    feed: str = "sip",
    parameters: dict[str, object] | None = None,
) -> dict[str, Path]:
    """Run the baseline and write Markdown, JSON, and CSV report artifacts."""

    configured = dict(DEFAULT_STRATEGY_PARAMETERS)
    if parameters:
        configured.update(parameters)

    trades = simulate_strategy(data, **configured)
    metrics, _ = calculate_performance(trades)
    daily = daily_performance(data, trades)
    hourly = hourly_performance(trades)
    exits = exit_reason_performance(trades)
    slippage = slippage_sensitivity(data, parameters=configured)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "markdown": output_directory / f"{report_name}.md",
        "summary": output_directory / f"{report_name}_summary.json",
        "trades": output_directory / f"{report_name}_trades.csv",
        "daily": output_directory / f"{report_name}_daily.csv",
        "hourly": output_directory / f"{report_name}_hourly.csv",
        "exits": output_directory / f"{report_name}_exit_reasons.csv",
        "slippage": output_directory / f"{report_name}_slippage.csv",
    }

    trades.to_csv(paths["trades"], index=False)
    daily.to_csv(paths["daily"], index=False)
    hourly.to_csv(paths["hourly"], index=False)
    exits.to_csv(paths["exits"], index=False)
    slippage.to_csv(paths["slippage"], index=False)

    summary = {
        "report_version": 1,
        "symbol": symbol.upper(),
        "feed": feed.lower(),
        "dataset_path": dataset_path,
        "rows": int(len(data)),
        "sessions": int(data["session"].nunique()),
        "first_timestamp": data.iloc[0]["timestamp"].isoformat(),
        "last_timestamp": data.iloc[-1]["timestamp"].isoformat(),
        "parameters": configured,
        "metrics": {key: _json_value(value) for key, value in metrics.items()},
    }
    paths["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )

    markdown = _render_markdown(summary, daily, hourly, exits, slippage)
    paths["markdown"].write_text(markdown, encoding="utf-8")
    return paths


def _aggregate(data: pd.DataFrame, group_column: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group, group_data in data.groupby(group_column, sort=True):
        pnl = group_data["net_pnl"].astype(float)
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        gross_profit = float(wins.sum())
        gross_loss = float(-losses.sum())
        profit_factor = gross_profit / gross_loss if gross_loss else (
            float("inf") if gross_profit else 0.0
        )
        rows.append(
            {
                group_column: group,
                "trade_count": int(len(pnl)),
                "win_rate": float((pnl > 0).mean()),
                "expectancy": float(pnl.mean()),
                "profit_factor": profit_factor,
                "total_net_pnl": float(pnl.sum()),
            }
        )
    return pd.DataFrame(rows)


def _fill_missing_groups(data: pd.DataFrame) -> pd.DataFrame:
    columns = ["trade_count", "win_rate", "expectancy", "profit_factor", "total_net_pnl"]
    for column in columns:
        if column not in data:
            data[column] = 0.0
    data[columns] = data[columns].fillna(0.0)
    data["trade_count"] = data["trade_count"].astype(int)
    return data[columns]


def _json_value(value: float | int) -> float | int | None:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _render_markdown(
    summary: dict[str, Any],
    daily: pd.DataFrame,
    hourly: pd.DataFrame,
    exits: pd.DataFrame,
    slippage: pd.DataFrame,
) -> str:
    metrics = summary["metrics"]
    parameters = summary["parameters"]
    lines = [
        f"# MicroEdge — Baseline report {summary['symbol']}",
        "",
        "## Dataset",
        "",
        f"- Feed: {summary['feed'].upper()}",
        f"- Barre: {summary['rows']}",
        f"- Sessioni: {summary['sessions']}",
        f"- Inizio: {summary['first_timestamp']}",
        f"- Fine: {summary['last_timestamp']}",
        f"- File sorgente: `{summary['dataset_path']}`",
        "",
        "## Parametri baseline",
        "",
        f"- Calo a 5 minuti: {parameters['drop_threshold']:.2%}",
        f"- Take profit: {parameters['take_profit']:.2%}",
        f"- Stop loss: {parameters['stop_loss']:.2%}",
        f"- Holding massimo: {parameters['max_holding_bars']} minuti",
        f"- Capitale per trade: ${parameters['capital_per_trade']:,.2f}",
        f"- Spread totale: {parameters['spread_bps']:.1f} bp",
        f"- Slippage per lato: {parameters['slippage_bps']:.1f} bp",
        f"- Broker: {BROKER_LABELS.get(parameters['broker_profile'], parameters['broker_profile'])}",
        f"- Commissione fissa configurata: ${parameters['commission_per_order']:.2f}",
        "",
        "## Risultato netto",
        "",
        f"- Trade: {metrics['trade_count']}",
        f"- Win rate: {metrics['win_rate']:.1%}",
        f"- Expectancy: ${metrics['expectancy']:.2f}",
        f"- Profit factor: {_format_ratio(metrics['profit_factor'])}",
        f"- Max drawdown: ${metrics['max_drawdown']:.2f}",
        f"- P&L totale: ${metrics['total_net_pnl']:.2f}",
        "",
        "## Sensibilità allo slippage",
        "",
        _markdown_table(
            slippage,
            ["slippage_bps", "trade_count", "win_rate", "expectancy", "profit_factor", "total_net_pnl"],
        ),
        "",
        "## Risultato per ora di ingresso",
        "",
        _markdown_table(hourly, list(hourly.columns)),
        "",
        "## Risultato per motivo di uscita",
        "",
        _markdown_table(exits, list(exits.columns)),
        "",
        "## File di dettaglio",
        "",
        "I risultati giornalieri e l'elenco completo dei trade sono disponibili nei file CSV adiacenti.",
        "",
        "## Interpretazione",
        "",
        "Questo report descrive una baseline su un solo mese. Non costituisce validazione dell'edge e non è stato usato per ottimizzare i parametri.",
        "",
    ]
    return "\n".join(lines)


def _markdown_table(data: pd.DataFrame, columns: list[str]) -> str:
    headers = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    rows = []
    for _, row in data[columns].iterrows():
        values = [_format_cell(column, row[column]) for column in columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([headers, separator, *rows])


def _format_cell(column: str, value: Any) -> str:
    if column in {"trade_count", "entry_hour"}:
        return str(int(value))
    if column == "win_rate":
        return f"{float(value):.1%}"
    if column in {"expectancy", "total_net_pnl"}:
        return f"${float(value):.2f}"
    if column == "profit_factor":
        return _format_ratio(float(value))
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return "∞" if math.isinf(value) else f"{value:.2f}"
