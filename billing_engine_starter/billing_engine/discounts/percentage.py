"""
PercentageDiscount — e.g., 20% off the subtotal.

Examples:
    PercentageDiscount(Decimal("0.20")).apply(Money(1000, "INR"), ctx)  ->  Money(200, "INR")
    PercentageDiscount(Decimal("1.00")).apply(Money(500, "INR"), ctx)   ->  Money(500, "INR")  # 100% off
"""

from decimal import Decimal

from billing_engine.money import Money
from billing_engine.discounts.base import Discount, DiscountContext


class PercentageDiscount(Discount):
    def __init__(self, percentage: Decimal) -> None:
        # TODO Day 1
        if not isinstance(percentage, Decimal):
            raise TypeError("Percentage must be an instance of Decimal")
        if not (percentage >= 0 and percentage <= 1):
            raise ValueError("Percentage should be in the range [0, 1]")
        self.percentage = percentage


    def apply(self, subtotal: Money, context: DiscountContext) -> Money:
        # TODO Day 1
        return subtotal * self.percentage