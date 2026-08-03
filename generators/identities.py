# backbone of identity

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from faker import Faker
import os

def _resolve_reference_now() -> datetime:
    # anchor time for entire dataset
    raw = os.getenv("UNIFY_REFERENCE_NOW")
    if raw:
        return datetime.fromisoformat(raw) # stop if right now

    # truncate to 00:00: if seed many time in a day always reproducibility
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# Config
SEED = 42
N_PERSONS = 500
DATA_DIR = Path("data")  # use for if want to gen mock data in local
REFERENCE_NOW = _resolve_reference_now() # use stable timestamp -> same seed -> same data -> reproducible
REFERENCE_START = REFERENCE_NOW - timedelta(days=730)

@dataclass
class Person:
    person_id: int
    first_name: str
    last_name: str
    email: str
    company: str
    country: str
    signup_at: datetime
    stripe_customer_id: str
    app_user_id: int
    event_anonymous_id: str


def build_persons(n: int = N_PERSONS) -> list[Person]:
    fake = Faker()
    fake.seed_instance(SEED)
    persons: list[Person] = []
    for i in range(n):
        first = fake.first_name()
        last = fake.last_name()
        domain = fake.free_email_domain()
        persons.append(
            Person(
                person_id=i,
                first_name=first,
                last_name=last,
                email=f"{first}.{last}.{i}@{domain}".lower(),
                company=fake.company(),
                country=fake.country_code(),
                signup_at=fake.date_time_between(REFERENCE_START, REFERENCE_NOW),
                stripe_customer_id="cus_" + fake.bothify("??######"),
                app_user_id=10_000 + i,
                event_anonymous_id=fake.uuid4(),
            )
        )
    return persons


if __name__ == "__main__":
    people = build_persons()
    print(f"Generate {len(people)} success")
