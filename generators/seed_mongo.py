# event log -> mongo
from __future__ import annotations
import os
import random
from datetime import timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
from generators.identities import build_persons, SEED

load_dotenv()

MONGO_KW = dict(
    host="localhost",
    port=27017,
    username=os.environ["MONGO_USER"],
    password=os.environ["MONGO_PASSWORD"],
    authSource="admin",
)

EVENT_TYPES = ["page_view", "feature_click", "session"]
PAGES = ["/", "/pricing", "/docs", "/dashboard", "/settings"]
FEATURES = ["export", "invite_user", "create_report", "connect_source"]
DEVICES = ["mobile", "desktop", "tablet"]
rng = random.Random(SEED + 4)


def _event(anon_id, user_id, ts, i) -> dict:
    etype = rng.choice(EVENT_TYPES)
    # properties diffrence by event
    if etype == "page_view":
        props = {"page": rng.choice(PAGES), "referrer": rng.choice(["google", "direct", "twitter"])}
    elif etype == "feature_click":
        props = {"feature": rng.choice(FEATURES)}
    else:
        props = {"duration_s": rng.randint(5, 1800)}
    return {
        "event_id": f"evt_{i:08d}",
        "event_type": etype,
        "anonymous_id": anon_id,
        "user_id": user_id,
        "timestamp": ts,
        "properties": props,
        "context": {"device": rng.choice(DEVICES),
                    "app_version": f"1.{rng.randint(0,9)}.{rng.randint(0,9)}"},
    }


def build_events() -> list[dict]:
    persons = build_persons()
    events, i = [], 0
    for p in persons:
        if rng.random() > 0.80:
            continue

        # incognito before sigup
        for _ in range(rng.randint(2, 8)):
            ts = p.signup_at - timedelta(days=rng.randint(1, 30), hours=rng.randint(0, 23))
            events.append(_event(p.event_anonymous_id, None, ts, i)); i += 1

        # after login
        for _ in range(rng.randint(5, 30)):
            ts = p.signup_at + timedelta(days=rng.randint(0, 120), hours=rng.randint(0, 23))
            events.append(_event(p.event_anonymous_id, p.app_user_id, ts, i)); i += 1
    rng.shuffle(events)
    return events


def main() -> None:
    events = build_events()
    with MongoClient(**MONGO_KW) as client:
        coll = client["events_db"]["events"]
        coll.delete_many({})              # idempotent
        coll.insert_many(events)
        n = coll.count_documents({})
        n_anon = coll.count_documents({"user_id": None})
    print(f"Mongo events: {n} events ({n_anon} incognito, {n - n_anon} login)")


if __name__ == "__main__":
    main()
