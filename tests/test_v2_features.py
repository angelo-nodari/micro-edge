import unittest

import numpy as np
import pandas as pd

from simulator import MARKET_TIMEZONE
from v2_features import calculate_qqq_return, calculate_relative_volume


def volume_bars(volumes: list[int], start: str = "2026-05-01 09:30") -> pd.DataFrame:
    timestamps = pd.date_range(start, periods=len(volumes), freq="min", tz=MARKET_TIMEZONE)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "session": [timestamps[0].date()] * len(volumes),
            "volume": volumes,
        }
    )


class RelativeVolumeTests(unittest.TestCase):
    def test_uses_prior_median_and_excludes_current_bar(self) -> None:
        data = volume_bars([10] * 10 + [50])

        feature = calculate_relative_volume(data)

        self.assertTrue(feature.iloc[:10]["relative_volume_30"].isna().all())
        self.assertAlmostEqual(feature.iloc[10]["relative_volume_30"], 5.0)

    def test_window_keeps_only_thirty_prior_bars(self) -> None:
        data = volume_bars([10] + [20] * 30 + [40])

        feature = calculate_relative_volume(data)

        self.assertAlmostEqual(feature.iloc[-1]["relative_volume_30"], 2.0)

    def test_feature_resets_at_session_boundary(self) -> None:
        first = volume_bars([10] * 12)
        second = volume_bars([20] * 11, start="2026-05-04 09:30")
        data = pd.concat([first, second], ignore_index=True)

        feature = calculate_relative_volume(data)

        second_start = len(first)
        self.assertTrue(
            feature.iloc[second_start : second_start + 10]["relative_volume_30"]
            .isna()
            .all()
        )
        self.assertAlmostEqual(
            feature.iloc[second_start + 10]["relative_volume_30"], 1.0
        )

    def test_future_change_does_not_change_past_feature(self) -> None:
        data = volume_bars(list(range(10, 25)))
        original = calculate_relative_volume(data)
        changed = data.copy()
        changed.loc[changed.index[-1], "volume"] = 1_000_000

        recalculated = calculate_relative_volume(changed)

        np.testing.assert_allclose(
            original.iloc[:-1]["relative_volume_30"],
            recalculated.iloc[:-1]["relative_volume_30"],
            equal_nan=True,
        )

    def test_zero_prior_median_produces_unavailable_feature(self) -> None:
        data = volume_bars([0] * 10 + [100])

        feature = calculate_relative_volume(data)

        self.assertTrue(np.isnan(feature.iloc[-1]["relative_volume_30"]))

    def test_invalid_configuration_is_rejected(self) -> None:
        data = volume_bars([10] * 12)

        with self.assertRaises(ValueError):
            calculate_relative_volume(data, window=5, min_periods=10)


class QqqReturnTests(unittest.TestCase):
    def test_five_minute_return_is_aligned_to_current_timestamp(self) -> None:
        data = volume_bars([10] * 7).rename(columns={"volume": "close"})
        data["close"] = [100.0, 100.0, 100.0, 100.0, 100.0, 101.0, 102.0]

        feature = calculate_qqq_return(data)

        self.assertTrue(feature.iloc[:5]["qqq_return_5m"].isna().all())
        self.assertEqual(feature.iloc[5]["timestamp"], data.iloc[5]["timestamp"])
        self.assertAlmostEqual(feature.iloc[5]["qqq_return_5m"], 0.01)

    def test_return_resets_at_session_boundary(self) -> None:
        first = volume_bars([100] * 7).rename(columns={"volume": "close"})
        second = volume_bars(
            [200] * 6, start="2026-05-04 09:30"
        ).rename(columns={"volume": "close"})
        data = pd.concat([first, second], ignore_index=True)

        feature = calculate_qqq_return(data)

        second_start = len(first)
        self.assertTrue(
            feature.iloc[second_start : second_start + 5]["qqq_return_5m"]
            .isna()
            .all()
        )
        self.assertAlmostEqual(
            feature.iloc[second_start + 5]["qqq_return_5m"], 0.0
        )

    def test_future_change_does_not_change_past_return(self) -> None:
        data = volume_bars([100] * 10).rename(columns={"volume": "close"})
        original = calculate_qqq_return(data)
        changed = data.copy()
        changed.loc[changed.index[-1], "close"] = 1_000.0

        recalculated = calculate_qqq_return(changed)

        np.testing.assert_allclose(
            original.iloc[:-1]["qqq_return_5m"],
            recalculated.iloc[:-1]["qqq_return_5m"],
            equal_nan=True,
        )

    def test_invalid_lookback_is_rejected(self) -> None:
        data = volume_bars([100] * 7).rename(columns={"volume": "close"})

        with self.assertRaises(ValueError):
            calculate_qqq_return(data, lookback_minutes=0)


if __name__ == "__main__":
    unittest.main()
