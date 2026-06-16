"""
TieredPricing — different price per unit depending on the tier the quantity falls into.

This is the "cumulative" / "stacked" tier model, NOT the "volume" model:
    Tiers: [(0, 1000, ₹2.00), (1000, 5000, ₹1.50), (5000, None, ₹1.00)]
    Quantity = 6000:
        First 1000 units  @ ₹2.00 = ₹2000
        Next  4000 units  @ ₹1.50 = ₹6000
        Last  1000 units  @ ₹1.00 = ₹1000
        ------------------------------------
        Total                     = ₹9000

A tier with `to_units = None` is the open-ended top tier.

Tier boundaries are HALF-OPEN on the right: a tier (from, to, price)
covers units strictly less than `to` (i.e. [from, to)).
"""

from dataclasses import dataclass
from typing import Optional

from billing_engine.money import Money
from billing_engine.pricing.base import PricingStrategy


@dataclass(frozen=True)
class Tier:
    from_units: int
    to_units: Optional[int]   # None means "unlimited" / open-ended
    unit_price: Money


class TieredPricing(PricingStrategy):
    """Charges across multiple price tiers based on cumulative quantity."""

    def __init__(self, tiers: list[Tier]) -> None:
        # TODO Day 1
        if not tiers:
            raise ValueError("Tiers must not be empty.")
        for i in range(len(tiers)-1):
            if tiers[i+1].from_units != tiers[i].to_units:
                raise ValueError("Not contiguous.")
        if tiers[-1].to_units is not None:
            raise ValueError("Last one must be of 'None' type.")
        currency = tiers[0].unit_price.currency
        for c in tiers:
            if c.unit_price.currency != currency:
                raise ValueError("Currency must be same for everyone.")
        self.tiers = tiers


    def calculate(self, quantity: int) -> Money:
        # TODO Day 1
        if quantity < 0:
            raise ValueError("Quantity must not be negative.")
        currency = self.tiers[0].unit_price.currency
        total = Money.zero(currency)
        for ti in self.tiers:
            if quantity < ti.from_units:
                break
            if ti.to_units is None:
                units = quantity - ti.from_units
            elif quantity > ti.from_units:
               units = min(quantity, ti.to_units) - ti.from_units
            else: 
                units = 0
            total = total + ti.unit_price * units
        
        return total