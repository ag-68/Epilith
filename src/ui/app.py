"""Local page: type a company name, watch the run, read the memo."""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from data.registry import AmbiguousCompany, CompanyNotFound, ForeignFiler
from decision_log.log import UserActionKind
from research.runner import list_entries, load_entry, memo_markdown, record_action, run_memo

STATIC = Path(__file__).resolve().parent / "static"
_job_lock = threading.Lock()


class ActionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: UserActionKind
    reason: str = Field(min_length=1)
    notes: str | None = None


app = FastAPI(title="Epilith", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/memos")
def memos() -> list[dict]:
    rows = []
    for entry in list_entries():
        _, actions = load_entry(entry.entry_id)
        latest = actions[-1].user_action if actions else None
        rows.append(
            {
                "entry_id": entry.entry_id,
                "ticker": entry.ticker,
                "listing": entry.listing,
                "conclusion": entry.conclusion,
                "timestamp": entry.timestamp.isoformat(),
                "price": str(entry.price) if entry.price is not None else None,
                "action": latest,
            }
        )
    return rows


@app.get("/api/memos/{entry_id}")
def memo(entry_id: str) -> dict:
    try:
        entry, actions = load_entry(entry_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"No memo {entry_id}") from exc
    return {
        "entry_id": entry.entry_id,
        "ticker": entry.ticker,
        "listing": entry.listing,
        "conclusion": entry.conclusion,
        "timestamp": entry.timestamp.isoformat(),
        "price": str(entry.price) if entry.price is not None else None,
        "notes": entry.notes,
        "markdown": memo_markdown(entry_id),
        "actions": [
            {
                "recorded_at": item.recorded_at.isoformat(),
                "action": item.user_action,
                "reason": item.user_action_reason,
                "notes": item.override_notes,
            }
            for item in actions
        ],
    }


@app.post("/api/memos/{entry_id}/action")
def action(entry_id: str, body: ActionBody) -> dict:
    try:
        record = record_action(entry_id, body.action, body.reason, body.notes)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "entry_id": record.entry_id,
        "action": record.user_action,
        "recorded_at": record.recorded_at.isoformat(),
    }


@app.get("/api/run")
def run(q: str) -> StreamingResponse:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Type a company name or ticker.")
    if not _job_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A memo is already being written. Wait for it to finish.")

    events: queue.Queue[dict | None] = queue.Queue()

    def log(line: str) -> None:
        events.put({"type": "log", "text": line})

    def work() -> None:
        try:
            result, entry_id = run_memo(query, log=log)
            events.put(
                {
                    "type": "done",
                    "entry_id": entry_id,
                    "ticker": result.ticker,
                    "conclusion": result.thesis.conclusion.label,
                }
            )
        except (CompanyNotFound, AmbiguousCompany, ForeignFiler, RuntimeError) as exc:
            events.put({"type": "error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001 — the page needs the message; the traceback stays in the server log
            events.put({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
        finally:
            events.put(None)
            _job_lock.release()

    threading.Thread(target=work, name="epilith-memo", daemon=True).start()

    def stream():
        while True:
            item = events.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
