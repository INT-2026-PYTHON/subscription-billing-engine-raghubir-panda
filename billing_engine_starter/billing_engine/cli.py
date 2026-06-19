"""
CLI entrypoint.

Subcommands to implement (Day 4):
    billing init                              -- create / migrate the DB
    billing customer add <name> <email> <country> [--state CODE]
    billing plan list
    billing subscribe <customer_id> <plan_id> [--trial-days N] [--discount CODE]
    billing bill run [--date YYYY-MM-DD]
    billing invoice show <invoice_id>          -- prints PLAIN TEXT invoice
    billing upgrade <subscription_id> <new_plan_id> [--date YYYY-MM-DD]   (STRETCH)
    billing demo                              -- run the scripted scenario

Use argparse with subparsers. Keep each subcommand handler in its own function.

PDF rendering is OUT OF SCOPE for the core project — `invoice show` should
print a clean PLAIN-TEXT invoice (see helper `format_invoice_text` below).
PDF generation is BONUS: see `billing_engine/pdf/renderer.py`.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from billing_engine.models import Invoice


def format_invoice_text(invoice: Invoice, customer_name: str, plan_name: str) -> str:
    """Render an invoice as a plain-text receipt. Pure function — easy to test."""
    # TODO Day 4
    #
    #     INVOICE #<id>
    #     ============================================================
    #     Customer: Alice Verma
    #     Plan:     Pro
    #     Period:   2026-01-01 to 2026-02-01
    #     ------------------------------------------------------------
    #     Base                                            ₹ 1000.00
    #     Discount (10%)                                  ₹  -100.00
    #     CGST (9%)                                       ₹    81.00
    #     SGST (9%)                                       ₹    81.00
    #     ------------------------------------------------------------
    #     TOTAL                                           ₹  1062.00
    #     Status: ISSUED
    #
    # Use invoice.line_items, invoice.total, invoice.status, invoice.period_start/end.
    
    lines = []
    lines.append(f"INVOICE #{invoice.id}")
    lines.append("============================================================")
    lines.append(f"Customer: {customer_name}")
    lines.append(f"Plan:     {plan_name}")
    lines.append(f"Period:   {invoice.period_start} to {invoice.period_end}")
    lines.append("------------------------------------------------------------")
    for li in invoice.line_items:
        desc = li.description.ljust(45)
        amt_str = f"{li.amount.currency} {str(li.amount.amount):>8}"
        lines.append(f"{desc}{amt_str}")
    lines.append("------------------------------------------------------------")
    lines.append(f"{'Subtotal:'.ljust(45)}{invoice.subtotal.currency} {str(invoice.subtotal.amount):>8}")
    
    if invoice.discount_total and float(invoice.discount_total.amount) != 0:
        lines.append(f"{'Discount:'.ljust(45)}{invoice.discount_total.currency} {str(invoice.discount_total.amount):>8}")
        
    if invoice.tax_total and float(invoice.tax_total.amount) != 0:
        lines.append(f"{'Tax:'.ljust(45)}{invoice.tax_total.currency} {str(invoice.tax_total.amount):>8}")
        
    lines.append(f"{'TOTAL:'.ljust(45)}{invoice.total.currency} {str(invoice.total.amount):>8}")
    lines.append(f"Status:   {invoice.status.value}")
    lines.append("============================================================")
    return "\n".join(lines)
    

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="billing", description="Subscription Billing CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # TODO Day 4
    cust_parser = sub.add_parser("customer")
    cust_sub = cust_parser.add_subparsers(dest="customer_cmd", required=True)
    cust_add = cust_sub.add_parser("add")
    cust_add.add_argument("name")
    cust_add.add_argument("email")
    cust_add.add_argument("country")
    cust_add.add_argument("--state", default=None, dest="state")

    plan_parser = sub.add_parser("plan")
    plan_sub = plan_parser.add_subparsers(dest="plan_cmd", required=True)
    plan_sub.add_parser("list")

    sub_parser = sub.add_parser("subscribe")
    sub_parser.add_argument("customer_id", type=int)
    sub_parser.add_argument("plan_id", type=int)
    sub_parser.add_argument("--trial-days", type=int, default=0)
    sub_parser.add_argument("--discount", type=int, default=None)

    bill_parser = sub.add_parser("bill")
    bill_sub = bill_parser.add_subparsers(dest="bill_cmd", required=True)
    bill_run = bill_sub.add_parser("run")
    bill_run.add_argument("--date", default=date.today().isoformat())

    inv_parser = sub.add_parser("invoice")
    inv_sub = inv_parser.add_subparsers(dest="invoice_cmd", required=True)
    inv_show = inv_sub.add_parser("show")
    inv_show.add_argument("invoice_id", type=int)

    upg_parser = sub.add_parser("upgrade")
    upg_parser.add_argument("subscription_id", type=int)
    upg_parser.add_argument("new_plan_id", type=int)
    upg_parser.add_argument("--date", default=date.today().isoformat())


    sub.add_parser("init", help="initialize the database")
    sub.add_parser("demo", help="run the demo scenario")
    # TODO Day 4

    from billing_engine.db.database import Database
    from billing_engine.db.repository import (
        CustomerRepository, PlanRepository, SubscriptionRepository,
        InvoiceRepository, LineItemRepository, LedgerRepository, UsageRecordRepository
    )
    from billing_engine.models import Customer, Subscription, SubscriptionStatus
    from billing_engine.billing.cycle import BillingCycle
    
    db = Database("billing.db")
    customer_repo = CustomerRepository(db)
    plan_repo = PlanRepository(db)
    subscription_repo = SubscriptionRepository(db)
    invoice_repo = InvoiceRepository(db)
    line_item_repo = LineItemRepository(db)
    ledger_repo = LedgerRepository(db)
    usage_repo = UsageRecordRepository(db)

    args = parser.parse_args(argv)


    if args.cmd == "init":
        db.migrate()
        print("Database initialized successfully.")
        return 0

    elif args.cmd == "customer":
        c = customer_repo.add(Customer(None, args.name, args.email, args.country, args.state))
        print(f"Customer added with ID: {c.id}")
        return 0

    elif args.cmd == "plan":
        for p in plan_repo.list_all():
            print(f"ID: {p.id} | {p.name} | {p.price.currency} {p.price.amount}/{p.billing_period.value}")
        return 0

    elif args.cmd == "subscribe":
        start_date = date.today()
        end_date = date(start_date.year + (start_date.month // 12), ((start_date.month % 12) + 1), start_date.day)
        s = subscription_repo.add(Subscription(
            None, args.customer_id, args.plan_id, SubscriptionStatus.ACTIVE,
            start_date, end_date, None, args.discount
        ))
        print(f"Subscription ID: {s.id}")
        return 0

    elif args.cmd == "bill":
        run_date = date.fromisoformat(args.date)
        cycle = BillingCycle(subscription_repo, plan_repo, customer_repo, invoice_repo, line_item_repo, ledger_repo, usage_repo, lambda p: None, lambda d: None, lambda c: (None, None))
        res = cycle.run(run_date)
        print(f"Invoices created: {res.invoices_created}")
        return 0

    elif args.cmd == "invoice":
        inv = invoice_repo.get(args.invoice_id)
        sub_obj = subscription_repo.get(inv.subscription_id)
        cust = customer_repo.get(sub_obj.customer_id)
        plan_obj = plan_repo.get(sub_obj.plan_id)
        print(format_invoice_text(inv, cust.name, plan_obj.name))
        return 0

    elif args.cmd == "upgrade":
        cycle = BillingCycle(subscription_repo, plan_repo, customer_repo, invoice_repo, line_item_repo, ledger_repo, usage_repo, lambda p: None, lambda d: None, lambda c: (None, None))
        inv = cycle.upgrade_subscription(args.subscription_id, args.new_plan_id)
        print(f"Proration invoice ID: {inv.id}")
        return 0

    elif args.cmd == "demo":
        return run_demo()
    
    
    print(f"TODO: implement command '{args.cmd}'", file=sys.stderr)
    return 2


def run_demo() -> int:
    """Scripted end-to-end scenario for the `demo` subcommand.

    Should mirror `tests/test_demo_scenario.py::TestEndToEndScenario::test_full_lifecycle`
    and print a human-readable summary to stdout.
    """
    # TODO Day 4

    print("--- Starting Subscription Billing Demo ---\n")
    
    from datetime import date
    from billing_engine.db.database import Database
    from billing_engine.db.repository import (
        CustomerRepository, PlanRepository, SubscriptionRepository,
        InvoiceRepository, LineItemRepository, LedgerRepository, UsageRecordRepository
    )
    from billing_engine.models import Customer, Plan, PricingType, BillingPeriod, Subscription, SubscriptionStatus
    from billing_engine.billing.cycle import BillingCycle

    db = Database(":memory:")
    db.migrate()
    customer_repo = CustomerRepository(db)
    plan_repo = PlanRepository(db)
    subscription_repo = SubscriptionRepository(db)
    invoice_repo = InvoiceRepository(db)
    line_item_repo = LineItemRepository(db)
    ledger_repo = LedgerRepository(db)
    usage_repo = UsageRecordRepository(db)

    print("1. Registering new customer...")
    c = customer_repo.add(Customer(None, "Alice Verma", "alice@example.com", "IN"))
    print(f"   [+] Created Customer: {c.name} (ID: {c.id})\n")

    print("2. Creating subscription plan...")
    p = plan_repo.add(Plan(None, "Pro Plan", PricingType.FLAT, BillingPeriod.MONTHLY, "INR"))
    print(f"   [+] Created Plan: {p.name}\n")

    print("3. Creating active subscription...")
    start_date = date(2026, 1, 1)
    end_date = date(2026, 2, 1)
    s = subscription_repo.add(Subscription(
        None, c.id, p.id, SubscriptionStatus.ACTIVE,
        start_date, end_date, None, None
    ))
    print(f"   [+] Subscribed {c.name} to {p.name}. Period: {start_date} -> {end_date}\n")

    print("4. Running billing cycle as of 2026-02-01...")
    cycle = BillingCycle(
        subscription_repo, plan_repo, customer_repo, invoice_repo, 
        line_item_repo, ledger_repo, usage_repo, 
        lambda p: None, lambda d: None, lambda c: (None, None)
    )
    res = cycle.run(as_of=date(2026, 2, 1))
    print(f"   [+] Cycle complete! Invoices created: {res.invoices_created}\n")

    print("5. Generating Plain-Text Invoice Receipt...\n")
    inv = invoice_repo.get(1)  # ID 1 because it's a fresh in-memory DB
    receipt = format_invoice_text(inv, c.name, p.name)
    print(receipt)
    
    print("\n--- Demo Complete! ---")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
