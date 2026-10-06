"""Disk cache for OSS API results, keyed by NIB. JSON file, TTL-based."""
import json
import time
from pathlib import Path

CACHE_FILE = Path(__file__).parent.parent / ".cache" / "nib_cache.json"
TTL_OK = 24 * 3600      # success: NIB registry data changes rarely
TTL_ERR = 5 * 60        # failures expire fast so retries happen


def _load() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _save(store: dict) -> None:
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(store))


def get(nib: str) -> dict | None:
    entry = _load().get(nib)
    if not entry:
        return None
    ttl = TTL_OK if entry.get("data") else TTL_ERR
    if time.time() - entry["ts"] > ttl:
        return None
    return entry.get("data")


def put(nib: str, data: dict | None) -> None:
    store = _load()
    store[nib] = {"ts": time.time(), "data": data}
    _save(store)
