"""Causal features for the MicroEdge V2 research cycle."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_qqq_return(
    qqq_data: pd.DataFrame,
    *,
    lookback_minutes: int = 5,
) -> pd.DataFrame:
    """Calculate the causal QQQ close-to-close return within each session."""

    required_columns = {"timestamp", "session", "close"}
    missing = required_columns.difference(qqq_data.columns)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")
    if lookback_minutes < 1:
        raise ValueError("lookback_minutes must be positive")
    if (qqq_data["close"] <= 0).any():
        raise ValueError("close must be positive")

    ordered = qqq_data.sort_values("timestamp").reset_index(drop=True).copy()
    prior_close = ordered.groupby("session", sort=False)["close"].shift(
        lookback_minutes
    )
    return pd.DataFrame(
        {
            "timestamp": ordered["timestamp"],
            "qqq_return_5m": ordered["close"].astype(float).div(prior_close) - 1.0,
        }
    )


def calculate_relative_volume(
    data: pd.DataFrame,
    *,
    window: int = 30,
    min_periods: int = 10,
) -> pd.DataFrame:
    """Calculate current volume divided by prior within-session median volume.

    The denominator excludes the current bar, so the feature contains no
    future information and does not dilute a volume shock with itself.
    """

    required_columns = {"timestamp", "session", "volume"}
    missing = required_columns.difference(data.columns)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")
    if window < 1 or min_periods < 1 or min_periods > window:
        raise ValueError("invalid relative-volume window")
    if (data["volume"] < 0).any():
        raise ValueError("volume cannot be negative")

    ordered = data.sort_values("timestamp").reset_index(drop=True).copy()
    prior_volume = ordered.groupby("session", sort=False)["volume"].shift(1)
    prior_median = prior_volume.groupby(
        ordered["session"], sort=False
    ).transform(
        lambda values: values.rolling(
            window=window,
            min_periods=min_periods,
        ).median()
    )
    relative_volume = ordered["volume"].astype(float).div(prior_median)
    relative_volume = relative_volume.where(prior_median > 0, np.nan)

    return pd.DataFrame(
        {
            "timestamp": ordered["timestamp"],
            "relative_volume_30": relative_volume,
        }
    )
