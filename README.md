# NIB Checker

Upload an NIB document (PDF), get a verdict: the number is checked against
Indonesia's public OSS RBA service and the company name in the document is
compared against the official record.

## What it does

1. Extracts the NIB, company name, and address from the PDF. Regex first;
   a local LLM (OpenAI-compatible endpoint) fills in whatever the regex misses.
2. Looks the number up on the public OSS RBA API. The endpoint sits behind
   Cloudflare Turnstile, so each check needs a freshly minted token — handled
   by [turnstile-mint](https://github.com/lukaskris/turnstile-mint).
3. Compares names (normalized: legal-entity prefixes like PT/Tbk are ignored,
   then containment check, then difflib ratio).
4. Shows the verdict: Verified, Needs review, Not valid, or Failed.

## Speed

| Case | Time |
|---|---|
| NIB seen before (24 h cache) | under 2 seconds |
| New NIB | about 10-15 seconds (token mint + API call in parallel with extraction) |

Results are cached per NIB for 24 hours on disk, so repeat checks never touch
the OSS API. The OSS gateway rate-limits per IP (HTTP 429, window of a few
minutes); the cache plus a 12-second minimum gap between real API calls keeps
that away.

## Setup

```bash
uv sync
uv run python -m camoufox fetch        # one-time browser download
cp .env.example .env                   # fill in your LLM endpoint
uv run python server.py                # http://127.0.0.1:8000
```

Environment variables (see `.env.example`):

- `LLM_BASE_URL` — OpenAI-compatible endpoint, e.g. a local qwen server
- `LLM_MODEL` — model name
- `LLM_API_KEY` — key if the endpoint requires one

## Deploy

```bash
SSH_HOST=host SSH_USER=user SSHPASS=pass REMOTE_DIR=/srv/nib-checker ./deploy.sh
```

The script rsyncs the code, syncs dependencies, restarts the systemd service
(`nib-checker`), and health-checks the endpoint. On hosts behind an outbound
proxy, set `http_proxy`/`https_proxy`/`no_proxy` in the unit file — camoufox
needs it for the token mint, and internal endpoints (the LLM server) must be
in `no_proxy`.

## Layout

```
engine/          pdf_extract, fast_extract (regex), llm_extract (fallback),
                 oss_client (public API), tokens (turnstile-mint shim),
                 cache (24 h disk cache), matcher, check (orchestrator)
static/          single-page dashboard: dropzone, 3D scan overlay, verdict dialog
server.py        FastAPI: static files + streaming /api/check (ndjson events)
```

## Notes

- The public OSS API returns name and status only — no address, no KBLI codes.
  The address shown in results comes from the document itself.
- Turnstile tokens are single-use, hostname-bound, and short-lived; minting
  happens on oss.go.id through a patched Firefox (see turnstile-mint).
- Use for documents you are entitled to verify. Space out bulk checks.
