"""Free-quota guard for commercial providers.

Rules:
* Units are *reserved* before a call; a failed call is not refunded (conservative).
* The effective usage is max(local count, provider-reported usage).
* A provider is blocked once usage + cost would exceed limit * safety (default 90%).
* There is no code path that buys credits, upgrades a plan or enables overage.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

from enki_research.core.db import Database


def current_period(now: float | None = None) -> str:
    return datetime.fromtimestamp(now or time.time(), tz=UTC).strftime("%Y-%m")


@dataclass
class QuotaStatus:
    provider: str
    period: str
    limit: float
    cap: float
    used: float
    reported: float | None
    calls: int

    @property
    def effective(self) -> float:
        return max(self.used, self.reported or 0.0)

    @property
    def remaining(self) -> float:
        return max(0.0, self.cap - self.effective)


class QuotaManager:
    def __init__(self, db: Database, limits: dict[str, float], safety: float = 0.90):
        if not 0 < safety <= 1:
            raise ValueError("quota safety must be in (0, 1]")
        self.db = db
        self.limits = dict(limits)
        self.safety = safety

    def cap(self, provider: str) -> float:
        return self.limits.get(provider, 0.0) * self.safety

    def status(self, provider: str, period: str | None = None) -> QuotaStatus:
        period = period or current_period()
        rows = self.db.query(
            "SELECT used, reported, calls FROM quota_ledger WHERE provider=? AND period=?", (provider, period)
        )
        used, reported, calls = (rows[0]["used"], rows[0]["reported"], rows[0]["calls"]) if rows else (0.0, None, 0)
        return QuotaStatus(provider, period, self.limits.get(provider, 0.0), self.cap(provider),
                           used, reported, calls)

    def try_reserve(self, provider: str, units: float) -> bool:
        """Atomically reserve units if they fit under the cap. Returns False when blocked."""
        if provider not in self.limits or units <= 0:
            return False
        period = current_period()
        cap = self.cap(provider)
        with self.db.tx() as c:
            row = c.execute(
                "SELECT used, reported FROM quota_ledger WHERE provider=? AND period=?", (provider, period)
            ).fetchone()
            used = row["used"] if row else 0.0
            reported = (row["reported"] if row else None) or 0.0
            if max(used, reported) + units > cap + 1e-9:
                return False
            c.execute(
                "INSERT INTO quota_ledger (provider, period, used, reported, calls, updated_at)"
                " VALUES (?,?,?,NULL,1,?)"
                " ON CONFLICT(provider, period) DO UPDATE SET used=used+?, calls=calls+1, updated_at=?",
                (provider, period, units, time.time(), units, time.time()),
            )
        return True

    def adjust(self, provider: str, reserved: float, actual: float) -> None:
        """Account for a provider-reported cost higher than the reservation (never refunds)."""
        extra = actual - reserved
        if extra <= 0:
            return
        with self.db.tx() as c:
            c.execute(
                "UPDATE quota_ledger SET used=used+?, updated_at=? WHERE provider=? AND period=?",
                (extra, time.time(), provider, current_period()),
            )

    def set_reported(self, provider: str, reported: float) -> None:
        """Store usage reported by the provider's own dashboard/API (kept as the max seen)."""
        period = current_period()
        with self.db.tx() as c:
            c.execute(
                "INSERT INTO quota_ledger (provider, period, used, reported, calls, updated_at)"
                " VALUES (?,?,0,?,0,?)"
                " ON CONFLICT(provider, period) DO UPDATE SET"
                " reported=MAX(COALESCE(reported, 0), excluded.reported), updated_at=excluded.updated_at",
                (provider, period, reported, time.time()),
            )
