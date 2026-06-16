"""
VATCalculator — single-rate VAT (e.g. 19% in Germany).
"""

from decimal import Decimal

from billing_engine.money import Money
from billing_engine.taxes.base import TaxCalculator, TaxContext, TaxBreakdown


class VATCalculator(TaxCalculator):
    def __init__(self, rate: Decimal) -> None:
        # TODO Day 1
        #   - Validate 0 <= rate <= 1.
        #   - Reject float.
        #   - Store on self.
        if not isinstance(rate, Decimal):
            raise TypeError("Rate must be an instance of Decimal")
        if not (rate >= 0 and rate <= 1):
            raise ValueError("Decimal should be in the range [0, 1]")
        self.rate = rate

    def apply(self, taxable: Money, context: TaxContext) -> TaxBreakdown:
        # TODO Day 1
        #   - vat = taxable * self.rate
        #   - Return TaxBreakdown with one component (f"VAT {percent}%", vat) and total = vat.
        #   - Tip: format the rate as a percentage cleanly.
        vat = taxable * self.rate
        pct = self.rate * 100
        label = f"VAT {pct}%"
        return TaxBreakdown(components=[(label, vat)], total=vat)