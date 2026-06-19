"""
Repositories — the ONLY place SQL lives.

Each repository wraps the Database connection and exposes methods that
take/return domain dataclasses (defined in billing_engine/models/).

⚠️ YOU IMPLEMENT every method body marked TODO.
   The signatures, docstrings, and the LedgerRepository's append-only
   guarantee are already in place — do not change them.

Beginner map (Day 2):
  1) CustomerRepository: add, get, find_by_email, list_all
  2) PlanRepository: add, get, list_all
  3) PlanTierRepository: add, list_for_plan
  4) DiscountRepository: add, get_by_code
  5) SubscriptionRepository: add, get, list_all, get_due_for_billing
  6) UsageRecordRepository: add, sum_for_period
  7) InvoiceRepository: add, get
  8) InvoiceLineItemRepository: add, list_for_invoice

Skip on Day 2 (read-only for now):
  - SubscriptionRepository.update_period / update_status / update_plan
  - InvoiceRepository.count_for_subscription / mark_paid / mark_failed / set_pdf_path
  - LedgerRepository and PaymentAttemptRepository

Conventions:
  - Always use parameterized queries (`?` placeholders) — NEVER f-string SQL.
  - Money values are persisted as TEXT using `money.to_storage()`.
  - Dates are persisted as ISO strings (`date.isoformat()`).

New layering (beginner-friendly):
  - Raw SQL lives in `billing_engine/db/queries.py`.
  - Repository methods call those query helpers.
  - Your Day 2 focus is:
      1) Convert domain -> storage values before helper call
      2) Convert rows -> domain dataclasses after helper call
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from billing_engine.db.database import Database
from billing_engine.db import queries as q
from billing_engine.money import Money
from billing_engine.models import (
    Customer,
    Plan, PricingType, BillingPeriod,
    Subscription, SubscriptionStatus,
    Invoice, InvoiceStatus, InvoiceLineItem, LineItemKind,
    LedgerEntry, LedgerDirection,
)


# ============================================================
# CUSTOMERS
# ============================================================
# Day 2: start here.
class CustomerRepository:
    """Persistence boundary for customers.

    A Customer is the billing account owner: invoices, subscriptions, and
    ledger entries ultimately belong to a customer. This repository hides the
    `customers` table and returns Customer dataclasses so the rest of the app
    does not need to know SQL column names.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, customer: Customer) -> Customer:
        # TODO Day 2
        # Hint: q.insert_customer(...)
        with self.db.transaction() as conn:
            new_id = q.insert_customer(
                conn, 
                customer.name, 
                customer.email, 
                customer.country_code,
                customer.state_code
            )
        return Customer(
            id=new_id,
            name=customer.name,
            email=customer.email,
            country_code=customer.country_code,
            state_code=customer.state_code,
            created_at=customer.created_at
        )
        
    def get(self, customer_id: int) -> Optional[Customer]:
        # TODO Day 2
        # Hint: q.select_customer_by_id(...)
        with self.db.connect() as conn:
            row = q.select_customer_by_id(conn, customer_id)
        if row is None:
            return None
        return Customer(id=row["id"], name=row["name"], email=row["email"], country_code=row["country_code"], state_code=row["state_code"])
            
    def find_by_email(self, email: str) -> Optional[Customer]:
        # TODO Day 2
        # Hint: q.select_customer_by_email(...)
        with self.db.connect() as conn:
            row = q.select_customer_by_email(conn, email)
        if row is None:
            return None
        return Customer(id=row["id"], name=row["name"], email=row["email"], country_code=row["country_code"], state_code=row["state_code"])
            
    def list_all(self) -> list[Customer]:
        # TODO Day 2
        # Hint: q.select_all_customers(...)
        with self.db.connect() as conn:
            rows = q.select_all_customers(conn)
        cstmrs = []
        for i in rows:
            cstmr = Customer(id=i["id"], name=i["name"], email=i["email"], country_code=i["country_code"], state_code=i["state_code"])
            cstmrs.append(cstmr)
        return cstmrs

# ============================================================
# PLANS  +  PLAN TIERS
# ============================================================
# Day 2
class PlanRepository:
    """Persistence boundary for subscription plans.

    A Plan describes what the customer bought: pricing type, billing period,
    currency, and strategy configuration. Pricing code consumes Plan objects,
    while this repository handles the `plans` table representation.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan: Plan) -> Plan:
        # TODO Day 2.
        # Hint: q.insert_plan(...)
        # Open transaction
        with self.db.transaction() as conn:
            new_id = q.insert_plan(
                conn, 
                plan.name, 
                plan.pricing_type.value, 
                plan.billing_period.value, 
                plan.currency, 
                plan.config_json
            )
        # INSERT (name, pricing_type, billing_period, currency, config_json)
        # REMEMBER: convert .pricing_type.value and .billing_period.value
        # Get lastrowid
        # Return Plan with id populated
        return Plan(
            id=new_id,
            name=plan.name,
            pricing_type=plan.pricing_type,
            billing_period=plan.billing_period,
            currency=plan.currency,
            config_json=plan.config_json
        )
            
    def get(self, plan_id: int) -> Optional[Plan]:
        # TODO Day 2.
        # Hint: q.select_plan_by_id(...)
        with self.db.connect() as conn:
            sel_plan_id = q.select_plan_by_id(conn, plan_id)
        if sel_plan_id is None:
            return None
        return Plan(id = sel_plan_id["name"], name = sel_plan_id["name"], pricing_type=sel_plan_id["pricing_type"], billing_period=sel_plan_id["billing_period"], currency = sel_plan_id["currency"], config_json = sel_plan_id["config_json"])

    def list_all(self) -> list[Plan]:
        # TODO Day 2.
        # Hint: q.select_all_plans(...)
        with self.db.connect() as conn:
            plan_rows = q.select_all_plans(conn)
            plans=[]
            for plan in plan_rows:
                plan = Plan(id = plan["name"], name = plan["name"], pricing_type=plan["pricing_type"], billing_period=plan["billing_period"], currency = plan["currency"], config_json = plan["config_json"])
                plans.append(plan)
        return plans
    

class PlanTierRepository:
    """Persistence boundary for pricing tiers attached to a plan.

    Tiered and usage-based plans need rows such as "0-100 units at 1.00" and
    "101+ units at 0.75". These rows live separately from plans because one
    plan can have many tiers.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan_id: int, from_units: int, to_units: Optional[int], unit_price: Money) -> int:
        # TODO Day 2.
        # Hint: q.insert_plan_tier(...)
        #Open transaction
        #INSERT (plan_id, from_units, to_units, unit_price)
        #Store unit_price using .to_storage()
        #Get lastrowid
        # Return the new tier id
        with self.db.transaction() as conn:
            new_tier_id = q.insert_plan_tier(conn, plan_id, from_units, to_units, unit_price.to_storage())
        return new_tier_id

    def list_for_plan(self, plan_id: int, currency: str) -> list[tuple[int, Optional[int], Money]]:
        # TODO Day 2.
        # Hint: q.select_plan_tiers(...)
        #SELECT all tiers for plan_id, ordered by from_units
        #For each row:
        #   Reconstruct as (from_units, to_units, Money(amount, currency))
        #   NOTE: currency is passed in as a parameter (from the parent plan)
        #Return list
        with self.db.connect() as conn:
            plan_tier_rows = q.select_plan_tiers(conn, plan_id)
            list_of_tiers =[]
            for row in plan_tier_rows:
                list_of_tiers.append((row["from_units"], row["to_units"], Money(row["unit_price"], currency)))
            return list_of_tiers


# ============================================================
# DISCOUNTS
# ============================================================
# Day 2
class DiscountRepository:
    """Persistence boundary for discount definitions.

    Discounts are stored as flexible rows because different discount types need
    different interpretation: percentage, fixed amount, or first-month-free.
    This repository intentionally returns dictionaries instead of a dataclass.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, code: str, discount_type: str, value: str, currency: Optional[str] = None) -> int:
        # TODO Day 2.
        # Hint: q.insert_discount(...)
        with self.db.transaction() as conn:
            discount_id = q.insert_discount(conn, code, discount_type, value, currency)
        return discount_id

    def get_by_code(self, code: str) -> Optional[dict]:
        # TODO Day 2.
        # Hint: q.select_discount_by_code(...)
        with self.db.connect() as conn:
            row = q.select_discount_by_code(conn, code)
        if row is None: return None
        return dict(row)

# ============================================================
# SUBSCRIPTIONS
# ============================================================
# Day 2 (only add/get/list_all/get_due_for_billing)
class SubscriptionRepository:
    """Persistence boundary for customer subscriptions.

    A Subscription connects a customer to a plan and tracks lifecycle state:
    TRIAL, ACTIVE, PAST_DUE, or CANCELLED. It also stores the current billing
    period, trial end date, optional discount, and dunning state.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, subscription: Subscription) -> Subscription:
        # TODO Day 2.
        # Hint: q.insert_subscription(...)
        with self.db.transaction() as conn:
            new_subs_id = q.insert_subscription(conn,
                        subscription.customer_id,
                        subscription.plan_id,
                        subscription.status.value,
                        subscription.current_period_start.isoformat(),
                        subscription.current_period_end.isoformat(),
                        subscription.trial_end.isoformat() if subscription.trial_end else None,
                        subscription.discount_id,
                        subscription.past_due_since.isoformat() if subscription.past_due_since else None)
            
        return Subscription(
                id = new_subs_id,
                customer_id=subscription.customer_id,
                plan_id=subscription.plan_id,
                status=subscription.status,
                current_period_start=subscription.current_period_start,
                current_period_end=subscription.current_period_end,
                trial_end=subscription.trial_end,
                discount_id=subscription.discount_id,
                past_due_since=subscription.past_due_since)

    def get(self, subscription_id: int) -> Optional[Subscription]:
        # TODO Day 2.
        # Hint: q.select_subscription_by_id(...)
        with self.db.connect() as conn:
            row = q.select_subscription_by_id(conn, subscription_id)
        return Subscription(
                id=row["id"],
                customer_id=row["customer_id"],
                plan_id=row["plan_id"],
                status=SubscriptionStatus(row["status"]),
                current_period_start=date.fromisoformat(row["current_period_start"]),
                current_period_end=date.fromisoformat(row["current_period_end"]),
                trial_end=date.fromisoformat(row["trial_end"]) if row["trial_end"] else None,
                discount_id=row["discount_id"],
                past_due_since=date.fromisoformat(row["past_due_since"]) if row["past_due_since"] else None
            )
        

    def list_all(self) -> list[Subscription]:
        # TODO Day 2.
        # Hint: q.select_all_subscriptions(...)
        with self.db.connect() as conn:
            rows = q.select_all_subscriptions(conn)
            subs = []
            for row in rows:
                subs.append(Subscription(
                    id=row["id"],
                    customer_id=row["customer_id"],
                    plan_id=row["plan_id"],
                    status=SubscriptionStatus(row["status"]),
                    current_period_start=date.fromisoformat(row["current_period_start"]),
                    current_period_end=date.fromisoformat(row["current_period_end"]),
                    trial_end=date.fromisoformat(row["trial_end"]) if row["trial_end"] else None,
                    discount_id=row["discount_id"],
                    past_due_since=date.fromisoformat(row["past_due_since"]) if row["past_due_since"] else None
                ))
            return subs

    def get_due_for_billing(self, as_of: date) -> list[Subscription]:
        # TODO Day 2.
        # Hint: q.select_due_subscriptions(...)
        with self.db.connect() as conn:
            rows = q.select_due_subscriptions(conn, as_of.isoformat())
            subs = []
            for row in rows:
                subs.append(Subscription(
                    id=row["id"],
                    customer_id=row["customer_id"],
                    plan_id=row["plan_id"],
                    status=SubscriptionStatus(row["status"]),
                    current_period_start=date.fromisoformat(row["current_period_start"]),
                    current_period_end=date.fromisoformat(row["current_period_end"]),
                    trial_end=date.fromisoformat(row["trial_end"]) if row["trial_end"] else None,
                    discount_id=row["discount_id"],
                    past_due_since=date.fromisoformat(row["past_due_since"]) if row["past_due_since"] else None
                ))
            return subs

    # ------------------------------------------------------------------
    # Day 2 boundary:
    # Everything below this line in this class is intentionally deferred.
    # Keep the method stubs so Day 3/4 can build on the same API surface.
    # ------------------------------------------------------------------
    def update_period(self, subscription_id: int, new_start: date, new_end: date) -> None:
        # TODO Day 3.
        # Hint: q.update_subscription_period(...)
        with self.db.transaction() as conn:
            q.update_subscription_period(
                conn, 
                subscription_id, 
                new_start.isoformat(), 
                new_end.isoformat()
            )

    def update_status(
        self,
        subscription_id: int,
        new_status: SubscriptionStatus,
        past_due_since: Optional[date] = None,
    ) -> None:
        # TODO Day 3.
        # Hint: q.update_subscription_status(...)
        with self.db.transaction() as conn:
            date_string = past_due_since.isoformat() if past_due_since else None
            q.update_subscription_status(conn, subscription_id, new_status.value, date_string)

    def update_plan(self, subscription_id: int, new_plan_id: int) -> None:
        # TODO Day 4.
        # Hint: q.update_subscription_plan(...)
        raise NotImplementedError("Day 4: implement SubscriptionRepository.update_plan")


# ============================================================
# USAGE
# ============================================================
# Day 2
class UsageRecordRepository:
    """Persistence boundary for metered usage.

    Usage records store quantities such as API calls, seats, messages, or GBs.
    Usage-based pricing strategies ask this repository for the total quantity
    they should charge for a subscription.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, subscription_id: int, metric: str, quantity: int) -> int:
        # TODO Day 2.
        # Hint: q.insert_usage_record(...)
        with self.db.transaction() as conn:
            usage_id = q.insert_usage_record(conn, subscription_id, metric, quantity)
        return usage_id

    def sum_for_period(
        self, subscription_id: int, metric: str, period_start: date, period_end: date
    ) -> int:
        # TODO Day 2: SELECT COALESCE(SUM(quantity), 0) ...
        # Hint: q.sum_usage_for_subscription_metric(...)
        #pseudo code:
            # SELECT COALESCE(SUM(quantity), 0) FROM usage_records
            # WHERE subscription_id = ? AND metric = ?
            # Return the sum (int)
            # NOTE: Do NOT filter by date range
        with self.db.connect() as conn:
            usage_total = q.sum_usage_for_subscription_metric(conn, subscription_id, metric)
        return usage_total



# ============================================================
# INVOICES + LINE ITEMS
# ============================================================
# Day 2 (InvoiceRepository only add/get)
class InvoiceRepository:
    """Persistence boundary for invoice headers.

    An Invoice stores the totals for one subscription period: subtotal,
    discounts, tax, final total, status, issue time, and optional PDF path.
    Line items are stored separately by InvoiceLineItemRepository.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, invoice: Invoice) -> Invoice:
        # TODO Day 2.
        # Hint: q.insert_invoice(...)
        with self.db.transaction() as conn:
            inv_id = q.insert_invoice(conn,
                    invoice.subscription_id,
                    invoice.period_start.isoformat(),
                    invoice.period_end.isoformat(),
                    invoice.subtotal.currency,
                    invoice.subtotal.to_storage(),
                    invoice.discount_total.to_storage(),
                    invoice.tax_total.to_storage(),
                    invoice.total.to_storage(),
                    invoice.status.value,
                    invoice.issued_at.isoformat() if invoice.issued_at else None,
                    invoice.pdf_path)
            
        return Invoice(
            id = inv_id,
            subscription_id=invoice.subscription_id,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
            subtotal=invoice.subtotal,
            discount_total=invoice.discount_total,
            tax_total=invoice.tax_total,
            total=invoice.total,
            status=invoice.status,
            issued_at=invoice.issued_at,
            pdf_path=invoice.pdf_path
        )

    def get(self, invoice_id: int) -> Optional[Invoice]:
        # TODO Day 2.
        # Hint: q.select_invoice_by_id(...)
        with self.db.connect() as conn:
            row = q.select_invoice_by_id(conn, invoice_id)
            if row is None:
                return None
                
            return Invoice(
                id=row["id"],
                subscription_id=row["subscription_id"],
                period_start=date.fromisoformat(row["period_start"]),
                period_end=date.fromisoformat(row["period_end"]),
                subtotal=Money(row["subtotal"], row["currency"]),
                discount_total=Money(row["discount_total"], row["currency"]),
                tax_total=Money(row["tax_total"], row["currency"]),
                total=Money(row["total"], row["currency"]),
                status=InvoiceStatus(row["status"]),
                issued_at=datetime.fromisoformat(row["issued_at"]) if row["issued_at"] else None,
                pdf_path=row["pdf_path"]
            )

    def count_for_subscription(self, subscription_id: int) -> int:
        # TODO Day 3.
        # Hint: q.count_invoices_for_subscription(...)
        with self.db.connect() as conn:
            return q.count_invoices_for_subscription(conn, subscription_id)
        
    def mark_paid(self, invoice_id: int) -> None:
        # TODO Day 4.
        # Hint: q.update_invoice_status(..., "PAID")
        with self.db.transaction() as conn:
            q.update_invoice_status(conn, invoice_id, "PAID")

    def mark_failed(self, invoice_id: int) -> None:
        # TODO Day 4.
        # Hint: q.update_invoice_status(..., "FAILED")
        with self.db.transaction() as conn:
            q.update_invoice_status(conn, invoice_id, "FAILED")

    def set_pdf_path(self, invoice_id: int, path: str) -> None:
        # TODO Day 4.
        # Hint: q.update_invoice_pdf_path(...)
        with self.db.transaction() as conn:
            q.update_invoice_pdf_path(conn, invoice_id, path)


class InvoiceLineItemRepository:
    """Persistence boundary for invoice detail rows.

    Line items explain how the invoice total was built: base charge, usage,
    discount, tax, or proration. They are separate from the invoice header so
    one invoice can contain multiple visible charges and credits.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, line_item: InvoiceLineItem) -> InvoiceLineItem:
        # TODO Day 2.
        # Hint: q.insert_invoice_line_item(...)
        with self.db.transaction() as conn:
            q.insert_invoice_line_item(
                conn,
                line_item.invoice_id,
                line_item.description,
                line_item.amount.to_storage(),         
                line_item.kind.value              
            )
        return line_item

    def list_for_invoice(self, invoice_id: int) -> list[InvoiceLineItem]:
        # TODO Day 2.
        # Hint: q.select_line_items_for_invoice(...)
        with self.db.connect() as conn:
            parent_invoice_row = q.select_invoice_by_id(conn, invoice_id)
            invoice_currency = parent_invoice_row["currency"]
            rows = q.select_line_items_for_invoice(conn, invoice_id)
            
            line_items = []
            for row in rows:
                item = InvoiceLineItem(
                    id=row["id"],
                    invoice_id=row["invoice_id"],
                    description=row["description"],
                    amount=Money(row["amount"], invoice_currency), 
                    kind=LineItemKind(row["kind"])
                )
                line_items.append(item)
    
            return line_items  



# ============================================================
# DAY 3/4 ONLY — keep stubs for later
# ============================================================

# ============================================================
# LEDGER — APPEND-ONLY (do not implement update/delete)
# ============================================================
class LedgerRepository:
    """Persistence boundary for the append-only accounting ledger.

    The ledger records financial movements: DEBIT when the customer owes money,
    CREDIT when money is received or reversed. It is append-only so history is
    auditable; mistakes should be corrected with reversing entries, not edits.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, entry: LedgerEntry) -> LedgerEntry:
        # TODO Day 3.
        # Hint: q.insert_ledger_entry(...)
        with self.db.transaction() as conn:
            new_id = q.insert_ledger_entry(
                conn,
                entry.invoice_id,
                entry.customer_id,
                entry.amount.to_storage(),
                entry.amount.currency,
                entry.direction.value,
                entry.reason
            )
        return LedgerEntry(
            id=new_id,
            customer_id=entry.customer_id,
            invoice_id=entry.invoice_id,
            amount=entry.amount,
            direction=entry.direction,
            reason=entry.reason,
            created_at=entry.created_at
        )
    
    def list_for_customer(self, customer_id: int) -> list[LedgerEntry]:
        # TODO Day 3.
        # Hint: q.select_ledger_for_customer(...)
        with self.db.connect() as conn:
            rows = q.select_ledger_for_customer(conn, customer_id)
        entries = []
        for row in rows:
            entries.append(LedgerEntry(
                id=row["id"],
                customer_id=row["customer_id"],
                invoice_id=row["invoice_id"],
                amount=Money(row["amount"], row["currency"]),
                direction=LedgerDirection(row["direction"]),
                reason=row["reason"],
                created_at=date.fromisoformat(row["created_at"].split()[0])
            ))
        return entries
    
    # These two methods are intentionally implemented to REJECT — do not override.
    def update(self, *args, **kwargs):
        raise NotImplementedError("Ledger is append-only. Post a reversing entry instead.")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Ledger is append-only. Post a reversing entry instead.")


# ============================================================
# PAYMENT ATTEMPTS
# ============================================================
class PaymentAttemptRepository:
    """Persistence boundary for payment retry history.

    Each payment attempt records whether charging an invoice succeeded or
    failed, why it failed, and when the next retry should happen. This history
    powers the Day 3/4 dunning flow.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(
        self,
        invoice_id: int,
        attempt_no: int,
        status: str,
        failure_reason: Optional[str],
        next_retry_at: Optional[datetime],
    ) -> int:
        # TODO Day 3.
        # Hint: q.insert_payment_attempt(...)
        with self.db.transaction() as conn:
            return q.insert_payment_attempt(
                conn,
                invoice_id,
                attempt_no,
                status,
                failure_reason,
                next_retry_at.isoformat() if next_retry_at else None
            )
        
    def list_for_invoice(self, invoice_id: int) -> list[dict]:
        # TODO Day 3.
        # Hint: q.select_attempts_for_invoice(...)
        with self.db.connect() as conn:
            rows = q.select_attempts_for_invoice(conn, invoice_id)
        return [dict(row) for row in rows]
    
    def count_for_invoice(self, invoice_id: int) -> int:
        # TODO Day 3.
        # Hint: q.count_attempts_for_invoice(...)
        with self.db.connect() as conn:
            return q.count_attempts_for_invoice(conn, invoice_id)