"""
GSTCalculator — Indian Goods & Services Tax.

The rule:
    - If customer_state == seller_state (or seller_state is "")  =>  intra-state
        -> charge CGST + SGST (split equally, e.g. 9% + 9% = 18%)
    - Else  =>  inter-state
        -> charge IGST (e.g. 18%)

Customers without a state code default to IGST (safe choice).
"""

from decimal import Decimal

from billing_engine.money import Money
from billing_engine.taxes.base import TaxCalculator, TaxContext, TaxBreakdown


class GSTCalculator(TaxCalculator):
    def __init__(self, cgst: Decimal, sgst: Decimal, igst: Decimal) -> None:
        # TODO Day 1
        #   - Validate each rate is Decimal in [0, 1].
        #   - Validate cgst + sgst == igst (sanity check on Indian GST setup).
        #   - Store on self.
        if not isinstance(cgst, Decimal):
            raise TypeError("CGST must be an instance of Decimal")
        if not (cgst >= 0 and cgst <= 1):
            raise ValueError("Decimal should be in the range [0, 1]")
        
        if not isinstance(sgst, Decimal):
            raise TypeError("CGST must be an instance of Decimal")
        if not (sgst >= 0 and sgst <= 1):
            raise ValueError("Decimal should be in the range [0, 1]")
        
        if not isinstance(igst, Decimal):
            raise TypeError("CGST must be an instance of Decimal")
        if not (igst >= 0 and igst <= 1):
            raise ValueError("Decimal should be in the range [0, 1]")

        if cgst + sgst != igst:
            raise ValueError("sum of cgst and sgst should be igst.")
        self.cgst = cgst
        self.sgst = sgst
        self.igst = igst


    def apply(self, taxable: Money, context: TaxContext) -> TaxBreakdown:
        # TODO Day 1
        #   - Decide intra vs inter-state from context.
        #     intra = bool(context.customer_state) and context.customer_state == context.seller_state
        #   - If intra: components = [("CGST X%", taxable*cgst), ("SGST Y%", taxable*sgst)], total = sum
        #   - Else:     components = [("IGST Z%", taxable*igst)],                            total = igst leg
        intra = bool(context.customer_state) and context.customer_state == context.seller_state
        if intra:
            cgst_amt = taxable * self.cgst
            sgst_amt = taxable * self.sgst
            components = [(f"CGST {self.cgst*100}%", cgst_amt), (f"SGST {self.sgst*100}%", sgst_amt)]
            total = cgst_amt + sgst_amt
        
        else:
            igst_amt = taxable * self.igst
            components = [(f"IGST {self.igst*100}%", igst_amt)]
            total = igst_amt
        
        return TaxBreakdown(components, total)