import unittest

import numpy as np
import pandas as pd

from simulator import (
    MARKET_TIMEZONE,
    calculate_performance,
    generate_synthetic_data,
    simulate_strategy,
)


class SyntheticDataTests(unittest.TestCase):
    def test_same_seed_produces_identical_data(self) -> None:
        first = generate_synthetic_data(seed=7, days=2)
        second = generate_synthetic_data(seed=7, days=2)

        pd.testing.assert_frame_equal(first, second)

    def test_shape_and_columns(self) -> None:
        data = generate_synthetic_data(seed=1, days=3)

        self.assertEqual(len(data), 3 * 386)
        self.assertEqual(
            list(data.columns),
            [
                "timestamp",
                "session",
                "session_number",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ],
        )
        self.assertEqual(data["session"].nunique(), 3)

    def test_ohlcv_values_are_consistent(self) -> None:
        data = generate_synthetic_data(seed=99, days=2)

        self.assertTrue((data["high"] >= data[["open", "close"]].max(axis=1)).all())
        self.assertTrue((data["low"] <= data[["open", "close"]].min(axis=1)).all())
        self.assertTrue((data[["open", "high", "low", "close"]] > 0).all().all())
        self.assertTrue((data["volume"] >= 0).all())

    def test_session_times_and_timezone(self) -> None:
        data = generate_synthetic_data(seed=3, days=1)

        self.assertEqual(str(data["timestamp"].dt.tz), MARKET_TIMEZONE)
        self.assertEqual(data.iloc[0]["timestamp"].strftime("%H:%M"), "09:30")
        self.assertEqual(data.iloc[-1]["timestamp"].strftime("%H:%M"), "15:55")

    def test_invalid_arguments_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generate_synthetic_data(days=0)
        with self.assertRaises(ValueError):
            generate_synthetic_data(initial_price=0)


def controlled_bars(
    closes: list[float],
    *,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
) -> pd.DataFrame:
    count = len(closes)
    opens = [closes[0], *closes[:-1]]
    highs = highs or [max(open_, close) + 0.01 for open_, close in zip(opens, closes)]
    lows = lows or [min(open_, close) - 0.01 for open_, close in zip(opens, closes)]
    timestamps = pd.date_range(
        "2026-01-05 09:35", periods=count, freq="min", tz=MARKET_TIMEZONE
    )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "session": [timestamps[0].date()] * count,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
        }
    )


class StrategyTests(unittest.TestCase):
    def test_eligible_signal_times_filter_is_applied_before_entry(self) -> None:
        closes = [100.0] * 5 + [99.7, 99.6, 99.5, 99.4, 99.3]
        data = controlled_bars(closes)
        allowed_signal = data.iloc[7]["timestamp"]

        trades = simulate_strategy(
            data,
            spread_bps=0,
            slippage_bps=0,
            commission_per_order=0,
            eligible_signal_times={allowed_signal},
        )

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades.iloc[0]["signal_time"], allowed_signal)
        self.assertEqual(trades.iloc[0]["entry_time"], data.iloc[8]["timestamp"])

    def test_alpaca_profile_flows_into_trade_costs(self) -> None:
        closes = [100.0] * 5 + [99.7, 100.0, 100.0]
        highs = [100.01] * 6 + [100.25, 100.01]
        lows = [99.99] * 5 + [99.69, 99.99, 99.99]
        data = controlled_bars(closes, highs=highs, lows=lows)

        trade = simulate_strategy(
            data,
            spread_bps=0,
            slippage_bps=0,
            broker_profile="alpaca_personal_api",
            commission_per_order=0,
        ).iloc[0]

        self.assertEqual(trade["broker_profile"], "alpaca_personal_api")
        self.assertEqual(trade["broker_commission"], 0.0)
        self.assertEqual(trade["sec_fee"], 0.03)
        self.assertEqual(trade["finra_taf"], 0.01)
        self.assertAlmostEqual(trade["net_pnl"], trade["gross_pnl"] - 0.04)

    def test_first_signal_can_use_0930_to_0935_context(self) -> None:
        closes = [100.0] * 5 + [99.7, 99.7, 99.7]
        timestamps = pd.date_range(
            "2026-01-05 09:30", periods=len(closes), freq="min", tz=MARKET_TIMEZONE
        )
        data = controlled_bars(closes)
        data["timestamp"] = timestamps

        trades = simulate_strategy(
            data, spread_bps=0, slippage_bps=0, commission_per_order=0
        )

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades.iloc[0]["signal_time"].strftime("%H:%M"), "09:35")
        self.assertEqual(trades.iloc[0]["entry_time"].strftime("%H:%M"), "09:36")

    def test_enters_on_next_bar_and_takes_profit(self) -> None:
        closes = [100.0] * 5 + [99.7, 100.0, 100.0]
        highs = [100.01] * 6 + [100.25, 100.01]
        lows = [99.99] * 5 + [99.69, 99.99, 99.99]
        data = controlled_bars(closes, highs=highs, lows=lows)

        trades = simulate_strategy(data, spread_bps=0, slippage_bps=0, commission_per_order=0)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades.iloc[0]["signal_time"], data.iloc[5]["timestamp"])
        self.assertEqual(trades.iloc[0]["entry_time"], data.iloc[6]["timestamp"])
        self.assertEqual(trades.iloc[0]["exit_reason"], "take_profit")
        self.assertAlmostEqual(trades.iloc[0]["exit_mid"], 99.7 * 1.002)

    def test_stop_has_priority_when_stop_and_target_share_a_bar(self) -> None:
        closes = [100.0] * 5 + [99.7, 100.0, 100.0]
        highs = [100.01] * 6 + [100.3, 100.01]
        lows = [99.99] * 5 + [99.69, 99.5, 99.99]
        data = controlled_bars(closes, highs=highs, lows=lows)

        trades = simulate_strategy(data, spread_bps=0, slippage_bps=0, commission_per_order=0)

        self.assertEqual(trades.iloc[0]["exit_reason"], "stop_loss")
        self.assertAlmostEqual(trades.iloc[0]["exit_mid"], 99.7 * (1 - 0.0015))

    def test_position_closes_after_five_bars(self) -> None:
        closes = [100.0] * 5 + [99.7] * 7
        data = controlled_bars(closes)

        trades = simulate_strategy(data, spread_bps=0, slippage_bps=0, commission_per_order=0)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades.iloc[0]["exit_reason"], "max_holding")
        self.assertEqual(trades.iloc[0]["exit_time"], data.iloc[10]["timestamp"])

    def test_intrabar_low_does_not_create_a_signal(self) -> None:
        closes = [100.0] * 8
        lows = [99.99] * 5 + [90.0, 99.99, 99.99]
        data = controlled_bars(closes, lows=lows)

        trades = simulate_strategy(data)

        self.assertTrue(trades.empty)

    def test_costs_are_separate_and_reduce_pnl(self) -> None:
        closes = [100.0] * 5 + [99.7, 100.0, 100.0]
        highs = [100.01] * 6 + [100.4, 100.01]
        lows = [99.99] * 5 + [99.69, 99.99, 99.99]
        data = controlled_bars(closes, highs=highs, lows=lows)

        no_costs = simulate_strategy(
            data, spread_bps=0, slippage_bps=0, commission_per_order=0
        ).iloc[0]
        with_costs = simulate_strategy(data).iloc[0]

        self.assertAlmostEqual(no_costs["gross_pnl"], no_costs["net_pnl"])
        self.assertGreater(with_costs["spread_cost"], 0)
        self.assertGreater(with_costs["slippage_cost"], 0)
        self.assertEqual(with_costs["commission_cost"], 2.0)
        self.assertLess(with_costs["net_pnl"], with_costs["gross_pnl"])
        self.assertTrue(
            np.isclose(
                with_costs["net_pnl"],
                with_costs["gross_pnl"]
                - with_costs["spread_cost"]
                - with_costs["slippage_cost"]
                - with_costs["commission_cost"],
            )
        )


class PerformanceTests(unittest.TestCase):
    @staticmethod
    def trades_with_pnl(values: list[float]) -> pd.DataFrame:
        timestamps = pd.date_range(
            "2026-01-05 10:00", periods=len(values), freq="min", tz=MARKET_TIMEZONE
        )
        return pd.DataFrame({"exit_time": timestamps, "net_pnl": values})

    def test_known_trade_sequence(self) -> None:
        trades = self.trades_with_pnl([10.0, -5.0, 20.0, -10.0])

        metrics, curve = calculate_performance(trades, initial_capital=100.0)

        self.assertEqual(metrics["trade_count"], 4)
        self.assertAlmostEqual(metrics["win_rate"], 0.5)
        self.assertAlmostEqual(metrics["average_win"], 15.0)
        self.assertAlmostEqual(metrics["average_loss"], -7.5)
        self.assertAlmostEqual(metrics["expectancy"], 3.75)
        self.assertAlmostEqual(metrics["profit_factor"], 2.0)
        self.assertAlmostEqual(metrics["max_drawdown"], 10.0)
        self.assertAlmostEqual(metrics["max_drawdown_pct"], 10.0 / 125.0)
        self.assertAlmostEqual(metrics["total_net_pnl"], 15.0)
        self.assertEqual(curve["equity"].tolist(), [100.0, 110.0, 105.0, 125.0, 115.0])

    def test_empty_trade_list(self) -> None:
        trades = pd.DataFrame(columns=["exit_time", "net_pnl"])

        metrics, curve = calculate_performance(trades)

        self.assertEqual(metrics["trade_count"], 0)
        self.assertEqual(metrics["total_net_pnl"], 0.0)
        self.assertTrue(curve.empty)

    def test_all_winners_have_infinite_profit_factor(self) -> None:
        trades = self.trades_with_pnl([2.0, 3.0])

        metrics, _ = calculate_performance(trades)

        self.assertTrue(np.isinf(metrics["profit_factor"]))

    def test_invalid_initial_capital_is_rejected(self) -> None:
        trades = self.trades_with_pnl([1.0])

        with self.assertRaises(ValueError):
            calculate_performance(trades, initial_capital=0)


if __name__ == "__main__":
    unittest.main()
