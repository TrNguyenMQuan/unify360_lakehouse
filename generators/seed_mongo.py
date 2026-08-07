# event log -> mongo (TIME-AWARE: dòng sự kiện theo ngày)
from __future__ import annotations
from datetime import timedelta
from pymongo import MongoClient
from generators.identities import build_persons, source_rng, AS_OF
from ingestion.config import MONGO

EVENT_TYPES = ["page_view", "feature_click", "session"]
PAGES = ["/", "/pricing", "/docs", "/dashboard", "/settings"]
FEATURES = ["export", "invite_user", "create_report", "connect_source"]
DEVICES = ["mobile", "desktop", "tablet"]
EVENT_MEMBERSHIP_PROB = 0.80   # 80% người có phát sinh event
ANON_EVENTS_RANGE = (5, 20)    # số event ẩn danh trước khi signup
ONBOARD_DAYS = 30              # cửa sổ mới dùng
ONBOARD_RATE = 0.8             # event/ngày trong onboarding
STEADY_RATE = 0.03             # event/ngày sau onboarding


def _event(rng, event_id: str, anon_id: str, user_id: int | None, ts) -> dict:
    # 1 event. rng truyền vào (không dùng biến module)
    etype = rng.choice(EVENT_TYPES)
    if etype == "page_view":
        props = {"page": rng.choice(PAGES),
                 "referrer": rng.choice(["google", "direct", "twitter"])}
    elif etype == "feature_click":
        props = {"feature": rng.choice(FEATURES)}
    else:
        props = {"duration_s": rng.randint(5, 1800)}
    return {
        "event_id": event_id,
        "event_type": etype,
        "anonymous_id": anon_id,
        "user_id": user_id,
        "timestamp": ts,
        "properties": props,
        "context": {"device": rng.choice(DEVICES),
                    "app_version": f"1.{rng.randint(0,9)}.{rng.randint(0,9)}"},
    }


def _churn_at(person, as_of):
    # Ngày huỷ nếu đã xảy ra tính tới as_of — sau ngày này khách ngừng dùng
    for effective_at, _plan, status in person.plan_changes:
        if effective_at > as_of:
            break
        if status == "canceled":
            return effective_at
    return None


def build_events(as_of=None) -> list[dict]:
    as_of = as_of or AS_OF
    persons = build_persons(as_of)
    events: list[dict] = []

    for p in persons:
        r = source_rng(p.person_id, "events")
        if r.random() > EVENT_MEMBERSHIP_PROB:
            continue

        # ẩn danh trước signup — nằm cố định trong quá khứ, không đổi theo as_of
        for k in range(r.randint(*ANON_EVENTS_RANGE)):
            ts = p.signup_at - timedelta(days=r.randint(1, 30), hours=r.randint(0, 23))
            events.append(_event(r, f"evt_{p.person_id:05d}_anon_{k:02d}",
                                 p.event_anonymous_id, None, ts))

        # đã login — dòng sự kiện theo NGÀY, dừng khi churn
        stop = min(_churn_at(p, as_of) or as_of, as_of)
        day = p.signup_at.replace(hour=0, minute=0, second=0, microsecond=0)
        d = 0
        # -> max(timestamp) luôn < as_of, không bao giờ có event tương lai
        while day + timedelta(days=1) <= stop:
            # RNG riêng cho từng (người, ngày): nội dung ngày d bất biến qua
            # mọi lần chạy -> event_id ổn định -> bronze append không sinh trùng
            dr = source_rng(p.person_id, f"day{d}")
            rate = ONBOARD_RATE if d < ONBOARD_DAYS else STEADY_RATE
            n = int(rate) + (1 if dr.random() < rate - int(rate) else 0)
            for k in range(n):
                ts = day + timedelta(hours=dr.randint(0, 23), minutes=dr.randint(0, 59))
                events.append(_event(dr, f"evt_{p.person_id:05d}_{day:%Y%m%d}_{k:02d}",
                                     p.event_anonymous_id, p.app_user_id, ts))
            day += timedelta(days=1)
            d += 1

    # log thật đến theo thứ tự thời gian (thay cho rng.shuffle của bản cũ)
    events.sort(key=lambda e: e["timestamp"])
    return events


def main() -> None:
    events = build_events()
    with MongoClient(**MONGO) as client:
        coll = client["events_db"]["events"]
        coll.delete_many({})              # idempotent: state = f(as_of)
        coll.insert_many(events)
        n = coll.count_documents({})
        n_anon = coll.count_documents({"user_id": None})
    print(f"Mongo events @ {AS_OF:%Y-%m-%d}: {n} events "
          f"({n_anon} incognito = {100*n_anon/n:.1f}%, {n - n_anon} login)")


if __name__ == "__main__":
    main()
