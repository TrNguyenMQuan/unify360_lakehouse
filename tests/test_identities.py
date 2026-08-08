import os
import subprocess
import sys
from datetime import datetime, timedelta

import pytest

from generators.identities import (
    EPOCH,
    MAX_PLAN_CHANGES,
    PLANS,
    Person,
    _build_plan_timeline,
    _person_rng,
    source_rng,
)

# input tuyet doi
TIMELINE = [
    (datetime(2025, 1, 1), "free", "active"),
    (datetime(2025, 3, 1), "pro", "active"),
    (datetime(2025, 6, 1), "pro", "canceled"),   # churn
]


def _person(timeline):
    """Person toi gian - state_at() chi doc signup_at + plan_changes."""
    return Person(
        person_id=1, first_name="A", last_name="B", email="a@b.c",
        company="C", country="VN", signup_at=timeline[0][0],
        stripe_customer_id="cus_x", app_user_id=1, event_anonymous_id="anon",
        plan_changes=timeline,
    )


# state_at: thay doi TUONG LAI chua xay ra
@pytest.mark.parametrize(
    "as_of, expected",
    [
        (datetime(2025, 2, 1), ("free", "active")),      # truoc lan doi dau
        (datetime(2025, 3, 1), ("pro", "active")),       # DUNG ngay doi -> da xay ra
        (datetime(2025, 5, 31), ("pro", "active")),      # giua 2 lan doi
        (datetime(2026, 1, 1), ("pro", "canceled")),     # sau churn
    ],
)
def test_state_at_khong_nhin_thay_tuong_lai(as_of, expected):
    plan, status, _ = _person(TIMELINE).state_at(as_of)
    assert (plan, status) == expected


# HOP DONG updated_at: la NGAY DOI THAT, khong phai as_of/now()
def test_updated_at_la_ngay_doi_that():
    _, _, updated_at = _person(TIMELINE).state_at(datetime(2025, 5, 1))
    assert updated_at == datetime(2025, 3, 1)   # KHONG phai 2025-05-01


# Churn la trang thai HAP THU
def test_churn_la_trang_thai_hap_thu():
    p = _person(TIMELINE)
    for days in (0, 30, 365, 3650):
        _, status, _ = p.state_at(datetime(2025, 6, 1) + timedelta(days=days))
        assert status == "canceled"


# Bat bien CAU TRUC cua timeline (tren nhieu person that)
@pytest.mark.parametrize("person_id", [0, 7, 42, 123, 899])
def test_timeline_bat_bien(person_id):
    signup = EPOCH + timedelta(days=person_id)
    timeline = _build_plan_timeline(_person_rng(person_id), signup)

    dates = [d for d, _, _ in timeline]
    statuses = [s for _, _, s in timeline]

    assert timeline[0][0] == signup                  # ban ghi dau tai signup
    assert dates == sorted(dates)                    # thoi gian tang dan
    assert all(p in PLANS for _, p, _ in timeline)   # plan hop le
    assert len(timeline) <= MAX_PLAN_CHANGES + 1     # co tran
    assert statuses.count("canceled") <= 1           # churn toi da 1 lan
    if "canceled" in statuses:
        assert statuses[-1] == "canceled"            # va phai o CUOI


# source_rng on dinh QUA CAC PROCESS
def test_source_rng_on_dinh_qua_process():
    code = "from generators.identities import source_rng; print(source_rng(42, 'crm').random())"
    outs = []
    for hash_seed in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": os.getcwd()}
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
        outs.append(r.stdout.strip())
    assert outs[0] == outs[1] != ""


# Nguon khac nhau -> chuoi khac nhau
def test_source_rng_doc_lap_giua_cac_nguon():
    # Neu khong, "ai co app account" se tuong quan voi "plan la gi" (bay M9.1).
    assert source_rng(42, "crm").random() != source_rng(42, "stripe").random()


# Doi plan phai doi sang plan KHAC
def test_khong_bao_gio_doi_plan_sang_chinh_no():
    noop = 0
    for pid in range(200):
        tl = _build_plan_timeline(_person_rng(pid), EPOCH)
        # churn giu nguyen plan nhung DOI status -> khong tinh la no-op
        noop += sum(1 for a, b in zip(tl, tl[1:]) if a[1] == b[1] and a[2] == b[2])
    assert noop == 0, f"{noop} lan doi plan sang chinh no"
