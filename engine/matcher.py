"""Fuzzy company-name matching between PDF and OSS API."""
import difflib
import re

NAME_THRESHOLD = 0.75

_STRIP = re.compile(r"\b(pt|cv|ud|pma|pmdn|tbk|persero|terbuka)\b|[.,&\-]", re.IGNORECASE)


def normalize(name: str) -> str:
    s = _STRIP.sub(" ", name.lower())
    return " ".join(s.split())


def match_names(pdf_name: str, api_name: str) -> dict:
    """Compare normalized names. Returns {is_match, score, method}."""
    a, b = normalize(pdf_name), normalize(api_name)
    if not a or not b:
        return {"is_match": False, "score": 0.0, "method": "empty"}
    if a == b:
        return {"is_match": True, "score": 1.0, "method": "exact"}
    if a in b or b in a:
        return {"is_match": True, "score": 0.95, "method": "containment"}
    score = difflib.SequenceMatcher(None, a, b).ratio()
    return {"is_match": score >= NAME_THRESHOLD, "score": round(score, 3), "method": "difflib"}


if __name__ == "__main__":
    assert match_names("PT INDAH KIAT PULP & PAPER Tbk.", "INDAH KIAT PULP & PAPER")["is_match"]
    assert not match_names("PT Sinar Jaya", "INDAH KIAT PULP & PAPER")["is_match"]
    assert match_names("PT Maju Mapan", "Maju Mapan")["is_match"]
    print("matcher self-check OK")
