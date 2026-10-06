"""Dashboard server: static page + streaming /api/check."""
import json
import os
import tempfile
from pathlib import Path

import anyio
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from engine import check

MAX_PDF_BYTES = 10 * 1024 * 1024

app = FastAPI()
STATIC = Path(__file__).parent / "static"


def _load_dotenv() -> None:
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


@app.post("/api/check")
async def api_check(file: UploadFile) -> StreamingResponse:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Hanya file PDF")
    body = await file.read()
    if len(body) > MAX_PDF_BYTES:
        raise HTTPException(400, "Maksimal 10 MB")
    if not body:
        raise HTTPException(400, "File kosong")

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(body)
    tmp.close()

    async def stream():
        try:
            it = check.steps(tmp.name)
            while True:
                item = await anyio.to_thread.run_sync(next, it, _SENTINEL)
                if item is _SENTINEL:
                    break
                phase, payload = item
                if phase == "result":
                    payload["file"] = file.filename
                yield json.dumps({"phase": phase, "data": payload}, ensure_ascii=False) + "\n"
        except StopIteration:
            pass
        finally:
            os.unlink(tmp.name)

    return StreamingResponse(stream(), media_type="application/x-ndjson")


_SENTINEL = object()

app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
