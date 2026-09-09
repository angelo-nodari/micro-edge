"""Read-only access to Alpaca historical stock bars."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd
import requests

from simulator import MARKET_DATA_START, MARKET_TIMEZONE, SESSION_END


ALPACA_BARS_URL = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"


class AlpacaDataError(RuntimeError):
    """Raised when Alpaca data cannot be downloaded or validated."""


def fetch_historical_bars(
    *,
    api_key: str,
    secret_key: str,
    symbol: str,
    start: str | date | datetime,
    end: str | date | datetime,
    feed: str = "iex",
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Download and normalize one-minute historical OHLCV bars.

    Bars between 09:30 and 15:55 New York time are returned. The first five
    minutes provide context; the strategy itself cannot signal before 09:35.
    Pagination is handled automatically. No trading endpoint is used.
    """

    if not api_key.strip() or not secret_key.strip():
        raise ValueError("Alpaca API key and secret key are required")

    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol or not normalized_symbol.replace(".", "").isalnum():
        raise ValueError("symbol must contain only letters, numbers, or a dot")
    if feed not in {"iex", "sip"}:
        raise ValueError("feed must be 'iex' or 'sip'")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    start_timestamp = _as_utc_timestamp(start, end_of_day=False)
    end_timestamp = _as_utc_timestamp(end, end_of_day=True)
    if start_timestamp >= end_timestamp:
        raise ValueError("start must be earlier than end")

    http = session or requests.Session()
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key,
    }
    base_parameters: dict[str, Any] = {
        "timeframe": "1Min",
        "start": start_timestamp.isoformat().replace("+00:00", "Z"),
        "end": end_timestamp.isoformat().replace("+00:00", "Z"),
        "adjustment": "all",
        "feed": feed,
        "sort": "asc",
        "limit": 10_000,
    }

    raw_bars: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        parameters = dict(base_parameters)
        if page_token:
            parameters["page_token"] = page_token

        try:
            response = http.get(
                ALPACA_BARS_URL.format(symbol=normalized_symbol),
                headers=headers,
                params=parameters,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise AlpacaDataError("Unable to reach Alpaca Market Data API") from exc

        if response.status_code != 200:
            message = _safe_error_message(response)
            raise AlpacaDataError(
                f"Alpaca request failed with HTTP {response.status_code}: {message}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AlpacaDataError("Alpaca returned an invalid JSON response") from exc

        bars = payload.get("bars") or []
        if not isinstance(bars, list):
            raise AlpacaDataError("Alpaca returned an unexpected bars payload")
        raw_bars.extend(bars)

        page_token = payload.get("next_page_token")
        if not page_token:
            break

    return normalize_alpaca_bars(raw_bars)


def normalize_alpaca_bars(raw_bars: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert Alpaca bar objects into the simulator's input schema."""

    columns = ["timestamp", "session", "open", "high", "low", "close", "volume"]
    if not raw_bars:
        return pd.DataFrame(columns=columns)

    required_fields = {"t", "o", "h", "l", "c", "v"}
    records: list[dict[str, Any]] = []
    for position, bar in enumerate(raw_bars):
        missing = required_fields.difference(bar)
        if missing:
            raise AlpacaDataError(
                f"Bar {position} is missing fields: {', '.join(sorted(missing))}"
            )
        records.append(
            {
                "timestamp": bar["t"],
                "open": bar["o"],
                "high": bar["h"],
                "low": bar["l"],
                "close": bar["c"],
                "volume": bar["v"],
            }
        )

    data = pd.DataFrame.from_records(records)
    try:
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True).dt.tz_convert(
            MARKET_TIMEZONE
        )
        for column in ["open", "high", "low", "close", "volume"]:
            data[column] = pd.to_numeric(data[column], errors="raise")
    except (TypeError, ValueError) as exc:
        raise AlpacaDataError("Alpaca returned invalid bar values") from exc

    data = data.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    local_time = data["timestamp"].dt.strftime("%H:%M")
    data = data[
        (local_time >= MARKET_DATA_START) & (local_time <= SESSION_END)
    ].copy()

    if data.empty:
        return pd.DataFrame(columns=columns)

    prices = data[["open", "high", "low", "close"]]
    invalid_prices = (
        (prices <= 0).any(axis=1)
        | (data["high"] < data[["open", "close"]].max(axis=1))
        | (data["low"] > data[["open", "close"]].min(axis=1))
        | (data["volume"] < 0)
    )
    if invalid_prices.any():
        raise AlpacaDataError("Alpaca bars failed OHLCV consistency checks")

    data.insert(1, "session", data["timestamp"].dt.date)
    data["volume"] = data["volume"].astype("int64")
    return data[columns].reset_index(drop=True)


def _as_utc_timestamp(
    value: str | date | datetime,
    *,
    end_of_day: bool,
) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if isinstance(value, date) and not isinstance(value, datetime):
        timestamp += pd.Timedelta(days=1) if end_of_day else pd.Timedelta(0)
    elif isinstance(value, str) and len(value.strip()) == 10:
        timestamp += pd.Timedelta(days=1) if end_of_day else pd.Timedelta(0)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(MARKET_TIMEZONE)
    return timestamp.tz_convert("UTC")


def _safe_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "request rejected"
    message = payload.get("message") if isinstance(payload, dict) else None
    return str(message)[:300] if message else "request rejected"
