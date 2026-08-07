# stripe -> JSON
from __future__ import annotations
import json
from datetime import timedelta
from generators.identities import build_persons, DATA_DIR, source_rng, AS_OF

PLANS = [
    {"price_id": "basic",       "amount": 2900,     "interval": "month"},
    {"price_id": "pro",         "amount": 9900,     "interval": "month"},
    {"price_id": "enterprise",  "amount": 29900,    "interval": "month"}
]
SUB_STATUS = ["active", "active", "active", "canceled", "past_due"]   # prefer active
STRIPE_MEMBERSHIP_PROB = 0.70

def _convert_unix_second_epoch(dt) -> int:
    return int(dt.timestamp())

def build_stripe() -> tuple[list, list, list]:
    persons = build_persons(AS_OF)
    customers, subscriptions, invoices = [], [], []

    for person in persons:
        r = source_rng(person.person_id, "stripe")
        if r.random() > STRIPE_MEMBERSHIP_PROB:
            continue

        customers.append({
            "id": person.stripe_customer_id,
            "object": "customer",
            "email": person.email,
            "name": f"{person.first_name} {person.last_name}",
            "created": _convert_unix_second_epoch(person.signup_at),
            "metadata": {"country": person.country}
        })

        plan = r.choice(PLANS)
        sub_id = "sub_" + f"{person.person_id:06d}"
        subscriptions.append({
            "id": sub_id,
            "object": "subscription",
            "customer": person.stripe_customer_id,
            "status": r.choice(SUB_STATUS),
            "created": _convert_unix_second_epoch(person.signup_at),
            "items": {
                "object": "list",
                "data": [{
                    "price": {
                        "id": plan["price_id"],
                        "unit_amount": plan["amount"],
                        "currency": "usd",
                        "recurring": {"interval": plan["interval"]}
                    }
                }]
            }
        })

        for month in range(r.randint(1, 12)):
            start = person.signup_at + timedelta(days=30 * month)
            if start > AS_OF:
                break
            invoices.append({
                "id": "in_" + f"{person.person_id:06d}_{month:02d}",
                "object": "invoice",
                "customer": person.stripe_customer_id,
                "subscription": sub_id,
                "amount_paid": plan["amount"],
                "currency": "usd",
                "status": "paid",
                "created": _convert_unix_second_epoch(start),
                "period_start": _convert_unix_second_epoch(start),
                "period_end": _convert_unix_second_epoch(start + timedelta(days=30))
            })

    return customers, subscriptions, invoices

def _dump(obj: list, name: str) -> None:
    out_dir = DATA_DIR / "stripe"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    with path.open("w", encoding="utf-8") as file:
        json.dump(obj, file, indent=2)
    print(f"Write {len(obj):>5} records in {path}")

def main() -> None:
    customers, subscriptions, invoices = build_stripe()
    print("Stripe:")
    _dump(customers, "customers.json")
    _dump(subscriptions, "subscriptions.json")
    _dump(invoices, "invoices.json")


if __name__ == "__main__":
    main()
