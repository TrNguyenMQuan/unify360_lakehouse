# create crm -> csv (TIME-AWARE: membership ổn định theo person)
from __future__ import annotations
import csv
import random
from datetime import timedelta
from faker import Faker
from generators.identities import build_persons, source_rng, AS_OF, SEED, DATA_DIR

LEAD_SOURCES = ["organic", "paid_ads", "referral", "event", "cold_outreach"]
INDUSTRIES = ["saas", "fintech", "ecommerce", "healthcare", "logistics", "education"]

CRM_MEMBERSHIP_PROB = 0.90
LEAD_ONLY_COUNT = 50

crm_fake = Faker()
crm_fake.seed_instance(SEED + 1)

def _noisy_email(rng, clean: str) -> str:
    # Email bẩn (hoa / thừa space) — rng truyền vào để bẩn theo người
    email = clean
    if rng.random() < 0.30:
        email = email.upper()
    if rng.random() < 0.20:
        email = f"  {email} "
    return email

def build_crm_rows() -> list[dict]:
    persons = build_persons(AS_OF)
    rows: list[dict] = []

    for p in persons:
        r = source_rng(p.person_id, "crm")
        if r.random() >= CRM_MEMBERSHIP_PROB:
            continue                       # người này không có trong CRM, mãi mãi

        rows.append({
            "contact_email": _noisy_email(r, p.email),
            "first_name": p.first_name,
            "last_name": p.last_name,
            "company": p.company,
            "lead_source": r.choice(LEAD_SOURCES),
            # người mới luôn có person_id lớn hơn -> được nối vào ĐUÔI -> campaign của người cũ không dịch.
            "campaign": crm_fake.catch_phrase(),
            "created_date": p.signup_at.date().isoformat(),
            "industry": r.choice(INDUSTRIES),
        })

    # LEAD-ONLY: bắt buộc Faker riêng.
    lead_fake = Faker()
    lead_fake.seed_instance(SEED + 99)
    lead_rng = random.Random(SEED + 99)

    for _ in range(LEAD_ONLY_COUNT):
        first, last = lead_fake.first_name(), lead_fake.last_name()
        rows.append({
            "contact_email": f"{first}.{last}@{lead_fake.free_email_domain()}".lower(),
            "first_name": first,
            "last_name": last,
            "company": lead_fake.company(),
            "lead_source": lead_rng.choice(LEAD_SOURCES),
            "campaign": lead_fake.catch_phrase(),
            # KHÔNG dùng "today": Faker đọc đồng hồ hệ thống -> phá luôn khả năng
            "created_date": lead_fake.date_between(
                AS_OF - timedelta(days=730), AS_OF).isoformat(),
            "industry": lead_rng.choice(INDUSTRIES),
        })

    # sort ổn định thay cho rng.shuffle 
    rows.sort(key=lambda x: (x["created_date"], x["contact_email"].strip().lower()))
    return rows

def main() -> None:
    rows = build_crm_rows()
    out_dir = DATA_DIR / "crm"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "contacts.csv"

    with out_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"CRM @ {AS_OF:%Y-%m-%d}: Write {len(rows)} contacts in {out_path}")

if __name__ == "__main__":
    main()
