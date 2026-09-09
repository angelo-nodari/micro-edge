"""Broker-specific execution fee models, independent from strategy logic."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Protocol


OrderSide = Literal["buy", "sell"]


@dataclass(frozen=True)
class FeeBreakdown:
    broker_commission: float = 0.0
    sec_fee: float = 0.0
    finra_taf: float = 0.0
    cat_fee: float = 0.0

    @property
    def regulatory_fees(self) -> float:
        return self.sec_fee + self.finra_taf + self.cat_fee

    @property
    def total(self) -> float:
        return self.broker_commission + self.regulatory_fees


class BrokerCostModel(Protocol):
    profile_id: str
    label: str

    def calculate(self, *, side: OrderSide, quantity: int, price: float) -> FeeBreakdown:
        """Return fees for one executed order."""


@dataclass(frozen=True)
class AlpacaPersonalApiCostModel:
    """Alpaca retail API pricing effective from the June 2026 fee schedule."""

    profile_id: str = "alpaca_personal_api"
    label: str = "Alpaca Personal API"
    sec_rate_per_dollar: float = 0.00002060
    finra_taf_per_share: float = 0.000195
    finra_taf_cap: float = 9.79

    def calculate(self, *, side: OrderSide, quantity: int, price: float) -> FeeBreakdown:
        _validate_order(side=side, quantity=quantity, price=price)
        if side == "buy":
            return FeeBreakdown()

        sec_fee = round_up_cent(quantity * price * self.sec_rate_per_dollar)
        finra_taf = round_up_cent(
            min(quantity * self.finra_taf_per_share, self.finra_taf_cap)
        )
        return FeeBreakdown(sec_fee=sec_fee, finra_taf=finra_taf)


@dataclass(frozen=True)
class CustomFlatCostModel:
    commission_per_order: float = 1.0
    profile_id: str = "custom_flat"
    label: str = "Personalizzato — commissione fissa"

    def __post_init__(self) -> None:
        if self.commission_per_order < 0:
            raise ValueError("commission_per_order cannot be negative")

    def calculate(self, *, side: OrderSide, quantity: int, price: float) -> FeeBreakdown:
        _validate_order(side=side, quantity=quantity, price=price)
        return FeeBreakdown(broker_commission=self.commission_per_order)


BROKER_LABELS = {
    "alpaca_personal_api": "Alpaca Personal API",
    "custom_flat": "Personalizzato — commissione fissa",
}


def get_broker_cost_model(
    profile_id: str,
    *,
    commission_per_order: float = 1.0,
) -> BrokerCostModel:
    if profile_id == "alpaca_personal_api":
        return AlpacaPersonalApiCostModel()
    if profile_id == "custom_flat":
        return CustomFlatCostModel(commission_per_order=commission_per_order)
    raise ValueError(f"unknown broker profile: {profile_id}")


def round_up_cent(value: float) -> float:
    if value <= 0:
        return 0.0
    return math.ceil((value * 100) - 1e-12) / 100


def _validate_order(*, side: OrderSide, quantity: int, price: float) -> None:
    if side not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    if price <= 0:
        raise ValueError("price must be positive")
