"""Field extraction from NIB document text via local LLM (qwen)."""
import json
import os

import httpx

MODEL = os.environ.get("LLM_MODEL", "qwen3.8-27b-q6")

PROMPT = """Ekstrak data dari dokumen NIB berikut. Balas HANYA JSON valid, tanpa penjelasan.
Skema: {"nib": "13 digit", "nama_pelaku_usaha": "string", "alamat_kantor": "string", "judul_dokumen": "string"}
Jika field tidak ditemukan, isi null.

DOKUMEN:
__TEXT__"""


def extract_fields(doc_text: str, timeout: float = 120.0) -> dict:
    base_url = os.environ.get("LLM_BASE_URL", "")
    if not base_url:
        raise RuntimeError("LLM_BASE_URL env var not set")
    api_key = os.environ.get("LLM_API_KEY", "")
    r = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT.replace("__TEXT__", doc_text[:12000])}],
            "temperature": 0,
        },
        timeout=timeout,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return _parse_json(content)


def _parse_json(content: str) -> dict:
    """qwen may wrap in ```json fences or <think>; grab first {...} block."""
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON in LLM output: {content[:200]}")
    return json.loads(content[start : end + 1])
