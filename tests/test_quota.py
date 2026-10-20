import pytest
from enki_research.core.db import Database
from enki_research.core.quota import QuotaManager


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


def test_quota_hard_cap_and_reservation(db):
    limits = {"tavily": 1000.0, "test_prov": 10.0}
    # 90% safety on 10.0 -> cap is 9.0
    qm = QuotaManager(db, limits=limits, safety=0.90)

    assert qm.cap("test_prov") == 9.0
    status = qm.status("test_prov")
    assert status.remaining == 9.0

    # Reserve 5 units
    assert qm.try_reserve("test_prov", 5.0) is True
    status = qm.status("test_prov")
    assert status.used == 5.0
    assert status.remaining == 4.0

    # Reserve another 4 units -> total 9.0 (exact cap)
    assert qm.try_reserve("test_prov", 4.0) is True
    status = qm.status("test_prov")
    assert status.remaining == 0.0

    # Exceeding cap by even 0.1 must be rejected
    assert qm.try_reserve("test_prov", 0.1) is False


def test_quota_reported_vs_local(db):
    limits = {"tavily": 100.0}  # cap 90.0
    qm = QuotaManager(db, limits=limits, safety=0.90)

    qm.try_reserve("tavily", 10.0)
    assert qm.status("tavily").effective == 10.0

    # External dashboard reports 50 units used
    qm.set_reported("tavily", 50.0)
    status = qm.status("tavily")
    assert status.effective == 50.0
    assert status.remaining == 40.0

    # Try reserve 41 units -> 50 + 41 = 91 > 90 -> blocked
    assert qm.try_reserve("tavily", 41.0) is False
    # Try reserve 30 units -> 50 + 30 = 80 <= 90 -> allowed
    assert qm.try_reserve("tavily", 30.0) is True
