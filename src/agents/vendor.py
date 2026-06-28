"""
Vendor Sales Agent — runs as an A2A-compliant FastAPI server.

Each vendor instance has private state: floor price, max discount authority,
and quota attainment. These inform Claude's negotiation behavior but are
never disclosed to the procurement agent.
"""
from __future__ import annotations
import json
import re
import uuid
from typing import Any

import src.config  # noqa: F401 — loads .env
from openai import AsyncOpenAI
from fastapi import FastAPI

from ..models import VendorContext
from ..a2a.types import (
    AgentCapabilities, AgentCard, AgentSkill,
    DataPart, Message, Part, SendTaskRequest, SendTaskResponse,
    Task, TaskState, TaskStatus, TextPart,
)

_SYSTEM_PROMPT = """\
You are a sales agent for {vendor} negotiating an annual SaaS contract renewal.

PRIVATE CONTEXT — never reveal exact numbers, use judgment:
- Current annual contract value: ${current_arr:,.0f}
- Your floor price (absolute minimum, non-negotiable): ${floor_price:,.0f}
- Your discount authority: up to {max_discount_pct:.0f}% off current price
- Your quota attainment this quarter: {quota_attainment_pct:.0f}%
  (below 80% = you need this deal to close, be pragmatic)

NEGOTIATION STRATEGY:
1. Open by defending value — reference ROI, integrations, support quality.
2. Counter aggressive anchors by citing customer success data, not just price.
3. Move in small steps: offer 3-5% first, larger discounts only under real pressure.
4. You can add value-adds (extra seats, training, premium support) before cutting price.
5. If quota attainment < 80%, you are authorized to be more flexible to close.
6. Never go below floor price. If pushed there, politely hold the line.
7. Be professional and collegial — the goal is a signed renewal, not winning an argument.

RESPONSE FORMAT:
Write your negotiation reply, then end with a JSON block (no text after it):
```json
{{"price": 95000, "seats": 50, "term_months": 12, "notes": "includes premium support upgrade"}}
```
Special values:
- price: -1  → you are walking away / cannot agree
"""


class VendorAgentServer:
    def __init__(self, context: VendorContext, port: int) -> None:
        self.context = context
        self.port = port
        self.app = FastAPI(title=f"Vendor Agent — {context.vendor}", docs_url=None)
        self._sessions: dict[str, list[dict[str, str]]] = {}
        self._client = AsyncOpenAI()
        self._register_routes()

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def _register_routes(self) -> None:
        ctx = self.context
        port = self.port

        @self.app.get("/.well-known/agent.json", response_model=AgentCard)
        async def agent_card() -> AgentCard:
            return AgentCard(
                name=f"{ctx.vendor} Sales Agent",
                description=(
                    f"Negotiates SaaS renewal pricing and terms on behalf of {ctx.vendor}. "
                    "Accepts structured offers and returns counter-offers via A2A protocol."
                ),
                url=f"http://127.0.0.1:{port}",
                capabilities=AgentCapabilities(streaming=False),
                skills=[
                    AgentSkill(
                        id="negotiate_renewal",
                        name="Negotiate Renewal",
                        description="Multi-round negotiation for annual SaaS contract renewal",
                        tags=["sales", "negotiation", "saas", "renewal"],
                    )
                ],
            )

        @self.app.post("/tasks/send", response_model=SendTaskResponse)
        async def send_task(req: SendTaskRequest) -> SendTaskResponse:
            return await self._handle_task(req)

    # ------------------------------------------------------------------
    # Core negotiation logic
    # ------------------------------------------------------------------

    async def _handle_task(self, req: SendTaskRequest) -> SendTaskResponse:
        session_id = req.sessionId or req.id or str(uuid.uuid4())

        # Extract text and structured offer from incoming message
        user_text, incoming_offer = self._parse_message(req.message)

        history = self._sessions.setdefault(session_id, [])
        history.append({"role": "user", "content": user_text})

        system = _SYSTEM_PROMPT.format(
            vendor=self.context.vendor,
            current_arr=self.context.current_arr,
            floor_price=self.context.floor_price,
            max_discount_pct=self.context.max_discount_pct,
            quota_attainment_pct=self.context.quota_attainment_pct,
        )

        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[{"role": "system", "content": system}, *history],
        )

        agent_text: str = response.choices[0].message.content  # type: ignore[union-attr]
        history.append({"role": "assistant", "content": agent_text})

        offer_data = self._extract_json(agent_text)
        walking_away = offer_data is not None and offer_data.get("price", 0) == -1

        parts: list[Part] = [TextPart(type="text", text=agent_text)]
        if offer_data:
            parts.append(DataPart(type="data", data=offer_data))

        state = TaskState.COMPLETED if walking_away else TaskState.INPUT_REQUIRED
        task = Task(
            id=req.id or str(uuid.uuid4()),
            sessionId=session_id,
            status=TaskStatus(
                state=state,
                message=Message(role="agent", parts=parts),
            ),
        )
        return SendTaskResponse(id=task.id, result=task)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_message(msg: Message) -> tuple[str, dict[str, Any] | None]:
        text_parts: list[str] = []
        data: dict[str, Any] | None = None
        for part in msg.parts:
            if part.type == "text":
                text_parts.append(part.text)  # type: ignore[union-attr]
            elif part.type == "data":
                data = part.data  # type: ignore[union-attr]
        return "\n".join(text_parts), data

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any] | None:
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
