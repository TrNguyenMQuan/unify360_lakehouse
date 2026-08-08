# backbone of identity

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from faker import Faker
import os
import random

# Config
EPOCH = datetime(2024, 1, 1) # stable point every event created will relative to EPOCH
SEED = 42
N_PERSONS = 500
DATA_DIR = Path("data")  # use for if want to gen mock data in local

POOL_SIZE = 900          # amount person will be created
ARRIVAL_SPAN_DAYS = 1700    # total time

# create history of scd-2
PLANS = ["free", "basic", "pro", "enterprise"]
MAX_PLAN_CHANGES = 5
CHANGE_GAP_DAYS = (30, 200)
CHURN_PROB = 0.15

def _resolve_as_of() -> datetime:
    # window time to read data not create data
    raw = os.getenv("UNIFY_REFERENCE_NOW")
    if raw:
        return datetime.fromisoformat(raw)
    # truncate 00:00: seed many time in day will create same data
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

AS_OF = _resolve_as_of()
REFERENCE_NOW = AS_OF

def _person_rng(person_id: int) -> random.Random:
    # per-entity seed: each person will have independent row and stable
    return random.Random(SEED * 1_000_003 + person_id)

def source_rng(person_id: int, source: str) -> random.Random:
    # independend rng for each (person, source)
    return random.Random(f"{SEED}:{source}:{person_id}")

def _build_plan_timeline(rng: random.Random, signup_at: datetime) -> list[tuple[datetime, str, str]]:
    # entire history plan of 1 person, create once and dont depend on as_of
    timeline = [(signup_at, rng.choice(PLANS), "active")]
    cursor = signup_at

    for _ in range(rng.randint(0, MAX_PLAN_CHANGES)):
        cursor = cursor + timedelta(days=rng.randint(*CHANGE_GAP_DAYS))
        if rng.random() < CHURN_PROB:
            timeline.append((cursor, timeline[-1][1], "canceled"))
            break
        # timeline.append((cursor, rng.choice(PLANS), "active")) -> it can chose a plan like current
        others = [p for p in PLANS if p != timeline[-1][1]]
        timeline.append((cursor, rng.choice(others), "active"))

    return timeline

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
    plan_changes: list[tuple[datetime, str, str]]

    def state_at(self, as_of: datetime) -> tuple[str, str, datetime]:
        # Plan/status/updated_at in time as_of
        plan, status, updated_at = self.plan_changes[0][1], "active", self.signup_at
        for effective_at, p, s in self.plan_changes:
            if effective_at > as_of:
                break   # change in future -> dont happen
            plan, status, updated_at = p, s, effective_at
        return plan, status, updated_at

def build_persons(as_of: datetime | None = None) -> list[Person]:
    # erson already had at as_of
    as_of = as_of or AS_OF
    fake = Faker()
    fake.seed_instance(SEED)
    persons: list[Person] = []

    for i in range(POOL_SIZE):
        first, last = fake.first_name(), fake.last_name()
        domain = fake.free_email_domain()
        company, country = fake.company(), fake.country_code()
        stripe_id = "cus_" + fake.bothify("??######")
        anon_id = fake.uuid4()

        rng = _person_rng(i)
        signup_at = EPOCH + timedelta(
            days=i * ARRIVAL_SPAN_DAYS / POOL_SIZE,   # đến đều theo person_id
            hours=rng.randint(0, 23),                 # jitter trong ngày
        )
        if signup_at > as_of:
            continue                                  # chưa tới lượt người này

        persons.append(Person(
            person_id=i,
            first_name=first, last_name=last,
            email=f"{first}.{last}.{i}@{domain}".lower(),
            company=company, country=country,
            signup_at=signup_at,
            stripe_customer_id=stripe_id,
            app_user_id=10_000 + i,
            event_anonymous_id=anon_id,
            plan_changes=_build_plan_timeline(rng, signup_at),
        ))

    return persons


if __name__ == "__main__":
    print(f"as_of = {AS_OF:%Y-%m-%d}  ->  {len(build_persons())} persons")