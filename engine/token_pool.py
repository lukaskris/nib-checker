"""Warm Turnstile token pool: mint the next token in background while the
current one is being spent, so consecutive checks skip the ~10s mint wait."""
import asyncio
import threading
import time

from .token_minter import mint_token

MAX_AGE = 120  # tokens are short-lived; only trust young ones
_lock = threading.Lock()
_warm: dict = {"token": None, "ts": 0.0}


def _do_mint() -> None:
    try:
        tok = _mint_retry()
    except Exception:
        return  # mint failures are non-fatal: caller mints on demand
    with _lock:
        _warm.update(token=tok, ts=time.time())


def _mint_retry(attempts: int = 2, timeout_s: int = 90) -> str:
    last = None
    for i in range(attempts):
        try:
            return asyncio.run(mint_token(timeout_s=timeout_s))
        except Exception as e:  # timeout or widget error: retry once
            last = e
            time.sleep(5)
    raise last


def get_token() -> str:
    """Return a fresh token: warm one if available, else mint now (with retry)."""
    with _lock:
        tok, ts = _warm["token"], _warm["ts"]
        _warm["token"] = None
    if tok and time.time() - ts < MAX_AGE:
        return tok
    return _mint_retry()


def warm_next() -> None:
    """Kick a background mint for the next check. Fire-and-forget."""
    t = threading.Thread(target=_do_mint, daemon=True)
    t.start()
