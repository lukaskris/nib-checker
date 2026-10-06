"""Deterministic field extraction from NIB document text. Regex first, LLM fallback."""
import re

NIB_RE = re.compile(r"NOMOR\s+INDUK\s+BERUSAHA\s*:?\s*(\d{13})", re.IGNORECASE | re.DOTALL)
NAMA_RE = re.compile(
    r"Nama\s+Pelaku\s+Usaha\s*:?\s*\n?\s*(.+?)\s*\n\s*\d", re.IGNORECASE
)
JUDUL_RE = re.compile(r"(PERIZINAN\s+BERUSAHA\s+BERBASIS\s+RISIKO)", re.IGNORECASE)


def extract_fast(text: str) -> dict:
    """Best-effort regex extraction. Missing fields are None; caller falls back to LLM."""
    nib = NIB_RE.search(text)
    nama = NAMA_RE.search(text)
    judul = JUDUL_RE.search(text)
    return {
        "nib": nib.group(1) if nib else None,
        "nama_pelaku_usaha": nama.group(1).strip() if nama else None,
        "judul_dokumen": judul.group(1) if judul else None,
    }


if __name__ == "__main__":
    t = open("sample.txt").read() if False else """NOMOR INDUK BERUSAHA: 8120100772073
1.
Nama Pelaku Usaha
:
PT INDAH KIAT PULP & PAPER Tbk.
2.
Alamat Kantor"""
    r = extract_fast(t)
    assert r["nib"] == "8120100772073", r
    assert r["nama_pelaku_usaha"] == "PT INDAH KIAT PULP & PAPER Tbk.", r
    print("fast_extract self-check OK")
