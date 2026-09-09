"""Versioned local storage for MicroEdge market datasets."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd


EXPECTED_FULL_SESSION_BARS = 386
REQUIRED_COLUMNS = ["timestamp", "session", "open", "high", "low", "close", "volume"]


def inspect_data_quality(data: pd.DataFrame) -> dict[str, object]:
    """Return deterministic, serialization-safe quality checks."""

    missing_columns = sorted(set(REQUIRED_COLUMNS).difference(data.columns))
    if missing_columns:
        raise ValueError(f"missing required columns: {', '.join(missing_columns)}")

    prices = data[["open", "high", "low", "close"]]
    invalid_ohlcv = (
        (prices <= 0).any(axis=1)
        | (data["high"] < data[["open", "close"]].max(axis=1))
        | (data["low"] > data[["open", "close"]].min(axis=1))
        | (data["volume"] < 0)
    )
    session_counts = data.groupby("session").size().sort_index()

    return {
        "missing_values": int(data[REQUIRED_COLUMNS].isna().sum().sum()),
        "duplicate_timestamps": int(data["timestamp"].duplicated().sum()),
        "invalid_ohlcv_rows": int(invalid_ohlcv.sum()),
        "session_bar_counts": {
            str(session): int(count) for session, count in session_counts.items()
        },
        "incomplete_full_sessions": [
            str(session)
            for session, count in session_counts.items()
            if count != EXPECTED_FULL_SESSION_BARS
        ],
    }


def save_dataset(
    data: pd.DataFrame,
    *,
    root: str | Path,
    symbol: str,
    feed: str,
    requested_start: str | date,
    requested_end: str | date,
    downloaded_at: datetime | None = None,
) -> tuple[Path, Path]:
    """Save an immutable Parquet dataset and adjacent provenance metadata."""

    if data.empty:
        raise ValueError("cannot save an empty dataset")

    quality = inspect_data_quality(data)
    if quality["missing_values"] or quality["duplicate_timestamps"]:
        raise ValueError("dataset contains missing values or duplicate timestamps")
    if quality["invalid_ohlcv_rows"]:
        raise ValueError("dataset contains invalid OHLCV rows")

    normalized_symbol = symbol.strip().upper()
    normalized_feed = feed.strip().lower()
    start_text = str(requested_start)
    end_text = str(requested_end)
    destination = Path(root) / "alpaca" / normalized_feed / normalized_symbol
    destination.mkdir(parents=True, exist_ok=True)
    base_name = f"{normalized_symbol}_{start_text}_{end_text}_1min"
    parquet_path = destination / f"{base_name}.parquet"
    metadata_path = destination / f"{base_name}.metadata.json"

    if parquet_path.exists() or metadata_path.exists():
        raise FileExistsError(f"dataset version already exists: {base_name}")

    ordered = data.sort_values("timestamp").reset_index(drop=True)
    temporary_path = parquet_path.with_suffix(".parquet.tmp")
    ordered.to_parquet(temporary_path, index=False)
    temporary_path.replace(parquet_path)

    checksum = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    timestamp = downloaded_at or datetime.now(timezone.utc)
    metadata = {
        "schema_version": 1,
        "source": "alpaca",
        "feed": normalized_feed,
        "symbol": normalized_symbol,
        "timeframe": "1Min",
        "adjustment": "all",
        "requested_start": start_text,
        "requested_end": end_text,
        "downloaded_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
        "rows": int(len(ordered)),
        "sessions": int(ordered["session"].nunique()),
        "first_timestamp": ordered.iloc[0]["timestamp"].isoformat(),
        "last_timestamp": ordered.iloc[-1]["timestamp"].isoformat(),
        "parquet_sha256": checksum,
        "quality": quality,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return parquet_path, metadata_path


def load_dataset(parquet_path: str | Path) -> pd.DataFrame:
    """Load a saved dataset after verifying its recorded checksum."""

    parquet_path = Path(parquet_path)
    metadata_path = parquet_path.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    checksum = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    if checksum != metadata.get("parquet_sha256"):
        raise ValueError("dataset checksum does not match its metadata")
    return pd.read_parquet(parquet_path)
