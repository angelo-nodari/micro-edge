"""Core, UI-independent components for the MicroEdge simulator."""

from __future__ import annotations

from datetime import date
from math import floor

import numpy as np
import pandas as pd

from broker_costs import get_broker_cost_model


MARKET_TIMEZONE = "America/New_York"
MARKET_DATA_START = "09:30"
SESSION_START = "09:35"
SESSION_END = "15:55"


def generate_synthetic_data(
    *,
    seed: int = 42,
    days: int = 20,
    start_date: str | date = "2026-01-05",
    initial_price: float = 180.0,
) -> pd.DataFrame:
    """Generate deterministic synthetic one-minute OHLCV sessions.

    The series deliberately contains no engineered mean-reversion edge. Each
    session follows a random log-price process with higher volatility and
    volume near the start and end of the trading window.
    """

    if days < 1:
        raise ValueError("days must be at least 1")
    if initial_price <= 0:
        raise ValueError("initial_price must be positive")

    sessions = pd.bdate_range(start=start_date, periods=days)
    rng = np.random.default_rng(seed)
    frames: list[pd.DataFrame] = []

    minutes_per_session = 386
    position = np.linspace(-1.0, 1.0, minutes_per_session)
    activity_curve = 0.55 + 0.85 * np.abs(position) ** 1.6

    for session_number, session in enumerate(sessions):
        timestamps = pd.date_range(
            f"{session.date()} {MARKET_DATA_START}",
            periods=minutes_per_session,
            freq="min",
            tz=MARKET_TIMEZONE,
        )

        overnight_gap = rng.normal(0.0, 0.004)
        session_open = initial_price * np.exp(overnight_gap)

        minute_volatility = 0.00055 * activity_curve
        log_returns = rng.normal(0.0, minute_volatility)

        opens = np.empty(minutes_per_session)
        closes = np.empty(minutes_per_session)
        opens[0] = session_open
        closes[0] = opens[0] * np.exp(log_returns[0])

        for minute in range(1, minutes_per_session):
            opens[minute] = closes[minute - 1]
            closes[minute] = opens[minute] * np.exp(log_returns[minute])

        wick_scale = np.abs(rng.normal(0.0, minute_volatility * 0.65))
        highs = np.maximum(opens, closes) * (1.0 + wick_scale)
        lows = np.minimum(opens, closes) * (1.0 - wick_scale)

        expected_volume = 55_000 * activity_curve
        volumes = rng.poisson(expected_volume).astype(np.int64)

        frames.append(
            pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "session": session.date(),
                    "session_number": session_number,
                    "open": opens,
                    "high": highs,
                    "low": lows,
                    "close": closes,
                    "volume": volumes,
                }
            )
        )

    return pd.concat(frames, ignore_index=True)


def simulate_strategy(
    data: pd.DataFrame,
    *,
    drop_threshold: float = 0.002,
    lookback_minutes: int = 5,
    take_profit: float = 0.002,
    stop_loss: float = 0.0015,
    max_holding_bars: int = 5,
    capital_per_trade: float = 1_000.0,
    spread_bps: float = 2.0,
    slippage_bps: float = 1.0,
    broker_profile: str = "custom_flat",
    commission_per_order: float = 1.0,
    eligible_signal_times: set[pd.Timestamp] | None = None,
) -> pd.DataFrame:
    """Run the baseline long-only strategy and return one row per trade."""

    required_columns = {"timestamp", "session", "open", "high", "low", "close"}
    missing = required_columns.difference(data.columns)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")

    positive_parameters = {
        "drop_threshold": drop_threshold,
        "lookback_minutes": lookback_minutes,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "max_holding_bars": max_holding_bars,
        "capital_per_trade": capital_per_trade,
    }
    for name, value in positive_parameters.items():
        if value <= 0:
            raise ValueError(f"{name} must be positive")

    non_negative_parameters = {
        "spread_bps": spread_bps,
        "slippage_bps": slippage_bps,
        "commission_per_order": commission_per_order,
    }
    for name, value in non_negative_parameters.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative")

    ordered = data.sort_values("timestamp").reset_index(drop=True)
    trades: list[dict[str, object]] = []
    half_spread_rate = spread_bps / 2 / 10_000
    slippage_rate = slippage_bps / 10_000
    broker_cost_model = get_broker_cost_model(
        broker_profile,
        commission_per_order=commission_per_order,
    )

    for _, session_data in ordered.groupby("session", sort=True):
        session_data = session_data.reset_index(drop=True)
        signal_index = lookback_minutes

        while signal_index < len(session_data) - 1:
            signal_time = session_data.at[signal_index, "timestamp"]
            if signal_time.strftime("%H:%M") < SESSION_START:
                signal_index += 1
                continue

            current_close = float(session_data.at[signal_index, "close"])
            prior_close = float(
                session_data.at[signal_index - lookback_minutes, "close"]
            )
            drop_return = current_close / prior_close - 1.0

            if drop_return > -drop_threshold:
                signal_index += 1
                continue

            if (
                eligible_signal_times is not None
                and signal_time not in eligible_signal_times
            ):
                signal_index += 1
                continue

            entry_index = signal_index + 1
            entry_mid = float(session_data.at[entry_index, "open"])
            entry_after_spread = entry_mid * (1.0 + half_spread_rate)
            entry_executed = entry_after_spread * (1.0 + slippage_rate)
            quantity = floor(capital_per_trade / entry_executed)

            if quantity < 1:
                signal_index += 1
                continue

            target_price = entry_executed * (1.0 + take_profit)
            stop_price = entry_executed * (1.0 - stop_loss)
            last_exit_index = min(
                entry_index + max_holding_bars - 1,
                len(session_data) - 1,
            )

            exit_index = last_exit_index
            exit_mid = float(session_data.at[last_exit_index, "close"])
            exit_reason = "max_holding"

            for candidate_index in range(entry_index, last_exit_index + 1):
                bar_open = float(session_data.at[candidate_index, "open"])
                bar_high = float(session_data.at[candidate_index, "high"])
                bar_low = float(session_data.at[candidate_index, "low"])

                stop_hit = bar_low <= stop_price
                target_hit = bar_high >= target_price

                if stop_hit:
                    exit_index = candidate_index
                    exit_mid = min(bar_open, stop_price)
                    exit_reason = "stop_loss"
                    break
                if target_hit:
                    exit_index = candidate_index
                    exit_mid = max(bar_open, target_price)
                    exit_reason = "take_profit"
                    break

            exit_after_spread = exit_mid * (1.0 - half_spread_rate)
            exit_executed = exit_after_spread * (1.0 - slippage_rate)

            spread_cost = quantity * (
                (entry_after_spread - entry_mid) + (exit_mid - exit_after_spread)
            )
            slippage_cost = quantity * (
                (entry_executed - entry_after_spread)
                + (exit_after_spread - exit_executed)
            )
            entry_fees = broker_cost_model.calculate(
                side="buy", quantity=quantity, price=entry_executed
            )
            exit_fees = broker_cost_model.calculate(
                side="sell", quantity=quantity, price=exit_executed
            )
            broker_commission = (
                entry_fees.broker_commission + exit_fees.broker_commission
            )
            sec_fee = entry_fees.sec_fee + exit_fees.sec_fee
            finra_taf = entry_fees.finra_taf + exit_fees.finra_taf
            cat_fee = entry_fees.cat_fee + exit_fees.cat_fee
            regulatory_fees = sec_fee + finra_taf + cat_fee
            total_broker_fees = broker_commission + regulatory_fees
            gross_pnl = quantity * (exit_mid - entry_mid)
            net_pnl = quantity * (exit_executed - entry_executed) - total_broker_fees

            trades.append(
                {
                    "signal_time": session_data.at[signal_index, "timestamp"],
                    "entry_time": session_data.at[entry_index, "timestamp"],
                    "exit_time": session_data.at[exit_index, "timestamp"],
                    "drop_return": drop_return,
                    "entry_mid": entry_mid,
                    "entry_executed": entry_executed,
                    "exit_mid": exit_mid,
                    "exit_executed": exit_executed,
                    "quantity": quantity,
                    "exit_reason": exit_reason,
                    "broker_profile": broker_profile,
                    "gross_pnl": gross_pnl,
                    "spread_cost": spread_cost,
                    "slippage_cost": slippage_cost,
                    "broker_commission": broker_commission,
                    "sec_fee": sec_fee,
                    "finra_taf": finra_taf,
                    "cat_fee": cat_fee,
                    "regulatory_fees": regulatory_fees,
                    "total_broker_fees": total_broker_fees,
                    "commission_cost": broker_commission,
                    "net_pnl": net_pnl,
                }
            )

            # Signals can be evaluated again only from the bar after the exit.
            signal_index = exit_index + 1

    trade_columns = [
        "signal_time",
        "entry_time",
        "exit_time",
        "drop_return",
        "entry_mid",
        "entry_executed",
        "exit_mid",
        "exit_executed",
        "quantity",
        "exit_reason",
        "broker_profile",
        "gross_pnl",
        "spread_cost",
        "slippage_cost",
        "broker_commission",
        "sec_fee",
        "finra_taf",
        "cat_fee",
        "regulatory_fees",
        "total_broker_fees",
        "commission_cost",
        "net_pnl",
    ]
    return pd.DataFrame(trades, columns=trade_columns)


def calculate_performance(
    trades: pd.DataFrame,
    *,
    initial_capital: float = 10_000.0,
) -> tuple[dict[str, float | int], pd.DataFrame]:
    """Calculate net trade statistics and the corresponding equity curve."""

    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    required_columns = {"exit_time", "net_pnl"}
    missing = required_columns.difference(trades.columns)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")

    if trades.empty:
        metrics: dict[str, float | int] = {
            "trade_count": 0,
            "win_rate": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "expectancy": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "total_net_pnl": 0.0,
        }
        empty_curve = pd.DataFrame(
            columns=["trade_number", "timestamp", "equity", "drawdown", "drawdown_pct"]
        )
        return metrics, empty_curve

    ordered = trades.sort_values("exit_time").reset_index(drop=True)
    net_pnl = ordered["net_pnl"].astype(float)
    wins = net_pnl[net_pnl > 0]
    losses = net_pnl[net_pnl < 0]

    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    trade_equity = initial_capital + net_pnl.cumsum()
    all_equity = np.concatenate(([initial_capital], trade_equity.to_numpy()))
    running_peak = np.maximum.accumulate(all_equity)
    drawdown = all_equity - running_peak
    drawdown_pct = np.divide(
        drawdown,
        running_peak,
        out=np.zeros_like(drawdown),
        where=running_peak != 0,
    )

    first_timestamp = ordered.iloc[0]["exit_time"]
    equity_curve = pd.DataFrame(
        {
            "trade_number": np.arange(0, len(ordered) + 1),
            "timestamp": [first_timestamp, *ordered["exit_time"].tolist()],
            "equity": all_equity,
            "drawdown": drawdown,
            "drawdown_pct": drawdown_pct,
        }
    )

    metrics = {
        "trade_count": int(len(ordered)),
        "win_rate": float((net_pnl > 0).mean()),
        "average_win": float(wins.mean()) if not wins.empty else 0.0,
        "average_loss": float(losses.mean()) if not losses.empty else 0.0,
        "expectancy": float(net_pnl.mean()),
        "profit_factor": float(profit_factor),
        "max_drawdown": float(-drawdown.min()),
        "max_drawdown_pct": float(-drawdown_pct.min()),
        "total_net_pnl": float(net_pnl.sum()),
    }
    return metrics, equity_curve
