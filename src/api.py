"""
FastAPI SSE server — streams negotiation events to the React dashboard.

Endpoints:
  POST /api/start   → kicks off all parallel negotiations
  GET  /api/stream  → SSE stream of negotiation events
  GET  /api/health  → liveness check
"""
from __future__ import annotations
import asyncio
import json

import src.config  # noqa: F401 — loads .env
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .models import NegotiationScenario, ProcurementContext, VendorContext, Contract
from .orchestrator import run_negotiations

app = FastAPI(title="B2B Renewal Negotiator API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Scenarios — same set as demo.py
# ------------------------------------------------------------------

SCENARIOS: list[NegotiationScenario] = [
    NegotiationScenario(
        port=8200,
        procurement=ProcurementContext(
            contract=Contract(
                vendor="Salesforce", current_arr=240_000,
                seats_licensed=200, seats_used=138,
                contract_end_date="2025-09-30",
            ),
            market_low=170_000, market_high=210_000,
            target_price=195_000, walkaway_price=225_000, opening_anchor=175_000,
        ),
        vendor=VendorContext(
            vendor="Salesforce", current_arr=240_000,
            floor_price=204_000, max_discount_pct=20.0, quota_attainment_pct=72.0,
        ),
    ),
    NegotiationScenario(
        port=8201,
        procurement=ProcurementContext(
            contract=Contract(
                vendor="Notion", current_arr=24_000,
                seats_licensed=100, seats_used=87,
                contract_end_date="2025-10-31",
            ),
            market_low=14_000, market_high=20_000,
            target_price=18_000, walkaway_price=22_000, opening_anchor=15_000,
        ),
        vendor=VendorContext(
            vendor="Notion", current_arr=24_000,
            floor_price=19_200, max_discount_pct=25.0, quota_attainment_pct=105.0,
        ),
    ),
    NegotiationScenario(
        port=8202,
        procurement=ProcurementContext(
            contract=Contract(
                vendor="Datadog", current_arr=96_000,
                seats_licensed=20, seats_used=14,
                contract_end_date="2025-11-30",
            ),
            market_low=60_000, market_high=80_000,
            target_price=72_000, walkaway_price=88_000, opening_anchor=58_000,
        ),
        vendor=VendorContext(
            vendor="Datadog", current_arr=96_000,
            floor_price=76_800, max_discount_pct=22.0, quota_attainment_pct=88.0,
        ),
    ),
]


# ------------------------------------------------------------------
# Event broadcaster — fan-out to all SSE clients
# ------------------------------------------------------------------

class EventBroadcaster:
    def __init__(self) -> None:
        self._clients: list[asyncio.Queue[str]] = []
        self._is_running = False

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        self._clients.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        try:
            self._clients.remove(q)
        except ValueError:
            pass

    async def emit(self, event: dict) -> None:
        data = json.dumps(event)
        for q in list(self._clients):
            await q.put(data)

    @property
    def is_running(self) -> bool:
        return self._is_running


broadcaster = EventBroadcaster()
_negotiation_task: asyncio.Task | None = None


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "running": broadcaster.is_running}


@app.post("/api/start")
async def start() -> dict:
    global _negotiation_task
    if broadcaster.is_running:
        return {"status": "already_running"}

    broadcaster._is_running = True
    _negotiation_task = asyncio.create_task(_run_all())
    return {"status": "started"}


async def _run_all() -> None:
    try:
        results = await run_negotiations(
            SCENARIOS,
            event_callback=broadcaster.emit,
        )
        total_savings = sum(r.savings for r in results)
        await broadcaster.emit({
            "type": "all_complete",
            "total_savings": total_savings,
            "results": [
                {
                    "vendor": r.vendor,
                    "outcome": r.outcome.value,
                    "final_price": r.final_price,
                    "original_arr": r.original_arr,
                    "savings": r.savings,
                    "rounds": r.rounds,
                    "summary": r.summary,
                }
                for r in results
            ],
        })
    except Exception as exc:
        await broadcaster.emit({"type": "error", "message": str(exc)})
    finally:
        broadcaster._is_running = False


@app.get("/api/stream")
async def stream() -> StreamingResponse:
    q = broadcaster.subscribe()

    async def generate():
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"
        try:
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=20.0)
                    yield f"data: {data}\n\n"
                    if json.loads(data).get("type") == "all_complete":
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            broadcaster.unsubscribe(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
