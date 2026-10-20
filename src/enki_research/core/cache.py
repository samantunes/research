"""Result cache keyed by the normalised request."""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata

from enki_research.core.db import Database
from enki_research.models import SearchRequest, SearchResponse


def normalize_query(q: str) -> str:
    q = unicodedata.normalize("NFKC", q).strip().lower()
    return re.sub(r"\s+", " ", q)


def cache_key(req: SearchRequest) -> str:
    payload = {
        "q": normalize_query(req.query),
        "c": req.category,
        "l": req.lang.lower(),
        "d": req.depth,
        "n": req.max_results,
        "p": sorted(req.providers) if req.providers else None,
        "pb": req.paid_budget(),
        "f": req.freshness_days,
        "dom": sorted(d.lower() for d in req.domains) if req.domains else None,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class ResultCache:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str) -> SearchResponse | None:
        rows = self.db.query("SELECT response, expires_at FROM cache WHERE key=?", (key,))
        if not rows or rows[0]["expires_at"] < time.time():
            return None
        return SearchResponse.model_validate_json(rows[0]["response"])

    def put(self, key: str, response: SearchResponse, ttl: int) -> None:
        now = time.time()
        with self.db.tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO cache (key, response, created_at, expires_at) VALUES (?,?,?,?)",
                (key, response.model_dump_json(), now, now + ttl),
            )

    def purge_expired(self) -> int:
        with self.db.tx() as c:
            return c.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),)).rowcount
