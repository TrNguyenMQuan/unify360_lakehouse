# create crm -> csv
from __future__ import annotations
import csv
import random
from faker import Faker
from generators.identities import build_persons, DATA_DIR, SEED

LEAD_SOURCES = ["organic", "paid_ads", "referral", "event", "cold_outreach"]

rng = random.Random(SEED + 1)
crm_fake = Faker()
crm_fake.seed_instance(SEED + 1)

def _noisy_email(clean: str) -> str:
    email = clean
    if rng.random() < 0.30:
        email = email.upper()
    if rng.random() < 0.20:
        email = f"  {email} "

    return email

def build_crm_rows() -> list[dict]:
    persons = build_persons()
    rows: list[dict] = []

    for person in persons:
        if rng.random() < 0.90:
            rows.append({
                "contact_email": _noisy_email(person.email),
                "first_name": person.first_name,
                "last_name": person.last_name,
                "company": person.company,
                "lead_source": rng.choice(LEAD_SOURCES),
                "campaign": crm_fake.catch_phrase(),
                "created_date": person.signup_at.date().isoformat(),
            })

    for _ in range(50):
        first, last = crm_fake.first_name(), crm_fake.last_name()
        rows.append({
            "contact_email": f"{first}.{last}@{crm_fake.free_email_domain()}".lower(),
            "first_name": first,
            "last_name": last,
            "company": crm_fake.company(),
            "lead_source": rng.choice(LEAD_SOURCES),
            "campaign": crm_fake.catch_phrase(),
            "created_date": crm_fake.date_between("-2y", "today").isoformat(),
        })

    rng.shuffle(rows)
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

    print(f"CRM: Write {len(rows)} contacts in {out_path}")

if __name__ == "__main__":
    main()