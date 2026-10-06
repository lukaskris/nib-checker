"""Orchestrator: PDF -> fields -> OSS API -> verdict.

Speed strategy: regex extraction first (LLM only as fallback), OSS results
cached per NIB (24h), token pre-minted in background, LLM and mint run in
parallel, minimum spacing between OSS calls with one 429 retry.

CLI: uv run python -m engine.check <pdf>
Programmatic: iterate steps(pdf_path) for (phase, payload) events.
"""
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import cache, fast_extract, llm_extract, matcher, oss_client, tokens

MIN_OSS_GAP = 12  # seconds between real OSS API calls
_oss_lock = threading.Lock()
_last_oss = 0.0


def _call_oss(nib: str, token: str) -> dict:
    """OSS call with spacing guard + one 429 retry on a fresh token."""
    global _last_oss
    with _oss_lock:
        wait = _last_oss + MIN_OSS_GAP - time.time()
        if wait > 0:
            time.sleep(wait)
        try:
            return oss_client.check_nib(nib, token)
        except oss_client.OssError as e:
            if e.status != 429:
                raise
            time.sleep(15)
            return oss_client.check_nib(nib, tokens.get_token())
        finally:
            _last_oss = time.time()


def steps(pdf_path: str):
    """Yield (phase, data) events; final yield is ("result", result_dict)."""
    from .pdf_extract import extract as read_pdf

    pdf = read_pdf(pdf_path)
    yield "read", {"page_count": pdf["page_count"]}

    fields = fast_extract.extract_fast(pdf["full_text"])
    nib = (fields.get("nib") or "").strip()

    # LLM fallback only when regex missed something, run in parallel with mint
    need_llm = not nib or not fields.get("nama_pelaku_usaha")
    cached = cache.get(nib) if nib else None

    with ThreadPoolExecutor(max_workers=2) as pool:
        llm_fut = pool.submit(llm_extract.extract_fields, pdf["full_text"]) if need_llm else None
        token_fut = None if cached else pool.submit(tokens.get_token)

        if llm_fut:
            extra = llm_fut.result()
            for k, v in extra.items():
                if v and not fields.get(k):
                    fields[k] = v
            nib = (fields.get("nib") or "").strip()

    result = {
        "file": None,
        "page_count": pdf["page_count"],
        "judul_dokumen": fields.get("judul_dokumen"),
        "nib": nib,
        "nama_pdf": fields.get("nama_pelaku_usaha"),
        "alamat_pdf": fields.get("alamat_kantor"),
        "nib_valid": False,
        "nama_match": None,
        "oss_data": None,
        "error": None,
        "from_cache": bool(cached),
    }
    yield "extract", {"fields": {k: fields.get(k) for k in ("nib", "judul_dokumen")}}

    if not nib or not nib.isdigit() or len(nib) != 13:
        result["error"] = f"Invalid NIB in document: {nib!r}"
        yield "result", result
        return

    if cached:
        data = cached
        tokens.warm_next()  # pool already had one; keep the chain going
    else:
        yield "mint", {"nib": nib}
        try:
            token = token_fut.result()
        except Exception as e:
            result["error"] = f"Failed to mint verification token: {type(e).__name__}: {str(e)[:160]}"
            yield "result", result
            return
        try:
            api = _call_oss(nib, token)
        except oss_client.OssError as e:
            result["error"] = str(e)
            cache.put(nib, None)  # negative cache, short TTL
            yield "result", result
            return
        if api.get("kode") != 200 or not api.get("data"):
            result["error"] = f"OSS API: {api.get('kode')} {api.get('desc')}"
            cache.put(nib, None)
            yield "result", result
            return
        data = api["data"]
        cache.put(nib, data)
        tokens.warm_next()

    result["oss_data"] = data
    result["nib_valid"] = bool(data.get("nib"))
    result["nama_match"] = matcher.match_names(result["nama_pdf"] or "", data.get("nama") or "")
    yield "verify", {"nama_oss": data.get("nama"), "status_aktif": data.get("status_aktif")}
    yield "result", result


def run(pdf_path: str) -> dict:
    result = None
    for phase, payload in steps(pdf_path):
        if phase == "result":
            result = payload
    return result


if __name__ == "__main__":
    out = run(sys.argv[1])
    print(json.dumps(out, indent=2, ensure_ascii=False))
    sys.exit(0 if out["nib_valid"] and out["nama_match"] and out["nama_match"]["is_match"] else 1)
