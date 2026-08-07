# app -> postgres container (TIME-AWARE: state phát lại từ timeline)
from __future__ import annotations
import os
import psycopg
from dotenv import load_dotenv
from generators.identities import build_persons, source_rng, AS_OF

load_dotenv()

CONN = dict(
    host="localhost",
    port=5434,
    dbname=os.environ["APP_PG_DB"],
    user=os.environ["APP_PG_USER"],
    password=os.environ["APP_PG_PASSWORD"],
)

APP_MEMBERSHIP_PROB = 0.90   # 90% person canonical have account

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
    # build_persons(AS_OF) already filter
    persons = build_persons(AS_OF)
    accounts, users, subs = [], [], []

    for p in persons:
        # memebership stable by person_id: who have app account always have
        if source_rng(p.person_id, "app").random() > APP_MEMBERSHIP_PROB:
            continue

        acc_id = 20_000 + p.person_id
        # updated_at = real day change -> always <= as_of
        plan, status, updated_at = p.state_at(AS_OF)

        accounts.append((acc_id, p.company, p.signup_at))
        users.append((p.app_user_id, acc_id, p.email, p.first_name,
                      p.last_name, p.country, p.signup_at))
        subs.append((30_000 + p.person_id, acc_id, plan, status,
                     p.signup_at, updated_at))

    with psycopg.connect(**CONN) as conn, conn.cursor() as cur:
        for stmt in DDL:
            cur.execute(stmt)
        cur.executemany("INSERT INTO app.accounts VALUES (%s,%s,%s)", accounts)
        cur.executemany("INSERT INTO app.users VALUES (%s,%s,%s,%s,%s,%s,%s)", users)
        cur.executemany("INSERT INTO app.subscriptions VALUES (%s,%s,%s,%s,%s,%s)", subs)
        conn.commit()

    print(f"Postgres app @ {AS_OF:%Y-%m-%d}: {len(accounts)} accounts, "
          f"{len(users)} users, {len(subs)} subscriptions")


if __name__ == "__main__":
    main()
