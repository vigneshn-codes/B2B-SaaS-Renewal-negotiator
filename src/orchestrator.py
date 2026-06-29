"""
Orchestrator — starts all vendor A2A servers and runs procurement negotiations
in parallel. Each negotiation is fully independent; asyncio.gather fans them out.
"""
from __future__ import annotations
import asyncio
from typing import Awaitable, Callable

import uvicorn

from .agents.procurement import EventCallback, ProcurementAgent
from .agents.vendor import VendorAgentServer
from .models import NegotiationResult, NegotiationScenario


async def _serve(server: VendorAgentServer) -> None:
    config = uvicorn.Config(
        server.app,
        host="127.0.0.1",
        port=server.port,
        log_level="error",
        access_log=False,
    )
    s = uvicorn.Server(config)
    await s.serve()


async def run_negotiations(
    scenarios: list[NegotiationScenario],
    *,
    startup_wait: float = 1.5,
    event_callback: EventCallback | None = None,
) -> list[NegotiationResult]:
    vendor_servers = [VendorAgentServer(s.vendor, s.port) for s in scenarios]
    server_tasks = [asyncio.create_task(_serve(vs)) for vs in vendor_servers]

    await asyncio.sleep(startup_wait)

    agent = ProcurementAgent(event_callback=event_callback)

    try:
        results = await asyncio.gather(
            *[agent.negotiate(s) for s in scenarios],
            return_exceptions=False,
        )
    finally:
        for t in server_tasks:
            t.cancel()
        await asyncio.gather(*server_tasks, return_exceptions=True)

    return list(results)
