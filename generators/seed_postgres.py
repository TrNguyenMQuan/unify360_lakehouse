# app -> postgress container
from __future__ import annotations
import os
import random
from datetime import timedelta
import psycopg
from dotenv import load_dotenv
from generators.identities import build_persons, SEED

load_dotenv()

CONN = dict(
    host="localhost",
    port=5434,
    dbname=os.environ["APP_PG_DB"],
    user=os.environ["APP_PG_USER"],
    password=os.environ["APP_PG_PASSWORD"],
)

PLANS = ["free", "basic", "pro", "enterprise"]
SUB_STATUS = ["active", "active", "active", "canceled"]
rng = random.Random(SEED + 3)

DDL = [
    "DROP SCHEMA IF EXISTS app CASCADE",
    "CREATE SCHEMA app",
    """CREATE TABLE app.accounts (
        account_id int PRIMARY KEY,
        company    text NOT NULL,
        created_at timestamptz NOT NULL
    )""",
    """CREATE TABLE app.users (
        user_id    int PRIMARY KEY,
        account_id int NOT NULL REFERENCES app.accounts(account_id),
        email      text NOT NULL,
        first_name text,
        last_name  text,
        country    text,
        created_at timestamptz NOT NULL
    )""",
    """CREATE TABLE app.subscriptions (
        subscription_id int PRIMARY KEY,
        account_id      int NOT NULL REFERENCES app.accounts(account_id),
        plan            text NOT NULL,
        status          text NOT NULL,
        started_at      timestamptz NOT NULL,
        updated_at      timestamptz NOT NULL
    )""",
]


def main() -> None:
    persons = build_persons()
    accounts, users, subs = [], [], []

    for p in persons:
        if rng.random() > 0.90:
            continue
        acc_id = 20_000 + p.person_id
        accounts.append((acc_id, p.company, p.signup_at))
        users.append((p.app_user_id, acc_id, p.email, p.first_name,
                      p.last_name, p.country, p.signup_at))
        subs.append((30_000 + p.person_id, acc_id,
                     rng.choice(PLANS), rng.choice(SUB_STATUS),
                     p.signup_at, p.signup_at + timedelta(days=rng.randint(0, 300))))

    with psycopg.connect(**CONN) as conn, conn.cursor() as cur:
        for stmt in DDL:
            cur.execute(stmt)
        cur.executemany("INSERT INTO app.accounts VALUES (%s,%s,%s)", accounts)
        cur.executemany("INSERT INTO app.users VALUES (%s,%s,%s,%s,%s,%s,%s)", users)
        cur.executemany("INSERT INTO app.subscriptions VALUES (%s,%s,%s,%s,%s,%s)", subs)
        conn.commit()                             # PHẢI commit mới lưu thật

    print(f"Postgres app: {len(accounts)} accounts, "
          f"{len(users)} users, {len(subs)} subscriptions")


if __name__ == "__main__":
    main()
