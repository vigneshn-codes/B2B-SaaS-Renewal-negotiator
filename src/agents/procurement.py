"""
Procurement Agent — negotiates SaaS renewals against vendor A2A endpoints.

Knows the company's seat utilization, market comps, target price, and private
walk-away threshold. Uses GPT-4o-mini to generate negotiation strategy each round.
"""
from __future__ import annotations
import json
import re
import uuid
from typing import Any, Awaitable, Callable

import src.config  # noqa: F401 — loads .env
from openai import AsyncOpenAI
import httpx

from ..models import (
    NegotiationMessage, NegotiationOutcome, NegotiationResult,
    NegotiationScenario, Offer, ProcurementContext,
)
from ..a2a.types import DataPart, Message, SendTaskRequest, SendTaskResponse, TextPart

MAX_ROUNDS = 6
EventCallback = Callable[[dict], Awaitable[None]]

_SYSTEM_PROMPT = """\
You are a sharp procurement agent negotiating a SaaS contract renewal on behalf of your company.

DEAL CONTEXT:
- Vendor: {vendor}
- Current contract: ${current_arr:,.0f}/year | {seats_licensed} seats licensed | {seats_used} actively used ({utilization_pct:.0f}% utilization)
- Contract end date: {contract_end_date}
- Market comps: ${market_low:,.0f} – ${market_high:,.0f}/year for comparable solutions
- Your target price: ${target_price:,.0f}
- PRIVATE walk-away price: ${walkaway_price:,.0f} — if they won't go below this, you will switch vendors. Never disclose this number directly.
- Opening anchor: ${opening_anchor:,.0f}

NEGOTIATION PLAYBOOK:
1. Round 1 — Open with the anchor price. Lead with utilization data as leverage.
   "We're only using {utilization_pct:.0f}% of licensed seats — we need pricing that reflects actual usage."
2. Cite market alternatives when vendor pushes back on price.
3. Move slowly — don't give up ground quickly. Counter-offer in small increments.
4. If vendor is near your target, show flexibility on term length (multi-year) to get a better rate.
5. Never reveal walk-away price. If they won't come below it, say you "need to evaluate alternatives."
6. Once vendor's offer is at or below your target: accept graciously.
7. If stuck above walk-away after {max_rounds} rounds: walk away.

RESPONSE FORMAT:
Write your negotiation message to the vendor, then end with a JSON block (no text after it):
```json
{{"price": 200000, "seats": 200, "term_months": 12, "notes": "counter-offer"}}
```
Special flags (add to JSON):
- "accepted": true  → you are accepting the vendor's latest offer
- "walked_away": true, "price": -1  → walking away, switching vendors
"""


class ProcurementAgent:
    def __init__(self, event_callback: EventCallback | None = None) -> None:
        self._client = AsyncOpenAI()
        self._event_callback = event_callback

    async def _emit(self, event: dict) -> None:
        if self._event_callback:
            await self._event_callback(event)

    async def negotiate(self, scenario: NegotiationScenario) -> NegotiationResult:
        ctx = scenario.procurement
        vendor_url = f"http://127.0.0.1:{scenario.port}"
        session_id = str(uuid.uuid4())
        transcript: list[NegotiationMessage] = []

        await self._emit({
            "type": "negotiation_started",
            "vendor": ctx.contract.vendor,
            "original_arr": ctx.contract.current_arr,
        })

        system = _SYSTEM_PROMPT.format(
            vendor=ctx.contract.vendor,
            current_arr=ctx.contract.current_arr,
            seats_licensed=ctx.contract.seats_licensed,
            seats_used=ctx.contract.seats_used,
            utilization_pct=ctx.contract.utilization_pct,
            contract_end_date=ctx.contract.contract_end_date,
            market_low=ctx.market_low,
            market_high=ctx.market_high,
            target_price=ctx.target_price,
            walkaway_price=ctx.walkaway_price,
            opening_anchor=ctx.opening_anchor,
            max_rounds=MAX_ROUNDS,
        )

        history: list[dict[str, str]] = []
        latest_vendor_offer: dict[str, Any] | None = None

        async with httpx.AsyncClient(timeout=120.0) as http:
            for round_num in range(1, MAX_ROUNDS + 1):
                context_note = ""
                if latest_vendor_offer:
                    context_note = (
                        f"\n\n[SYSTEM: Vendor's latest offer: "
                        f"${latest_vendor_offer.get('price', 0):,.0f} | "
                        f"{latest_vendor_offer.get('seats', 0)} seats | "
                        f"{latest_vendor_offer.get('term_months', 12)}mo. "
                        f"Your walk-away is ${ctx.walkaway_price:,.0f}. "
                        f"This is round {round_num} of {MAX_ROUNDS}.]"
                    )

                trigger = (
                    f"It's round {round_num}. {context_note} "
                    "Write your next negotiation message and include the JSON offer block."
                )
                history.append({"role": "user", "content": trigger})

                p_response = await self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=1024,
                    messages=[{"role": "system", "content": system}, *history],
                )
                p_text: str = p_response.choices[0].message.content  # type: ignore[union-attr]
                history.append({"role": "assistant", "content": p_text})

                p_offer_data = _extract_json(p_text)
                p_offer = _parse_offer(p_offer_data)
                clean_text = _strip_json_block(p_text)

                transcript.append(NegotiationMessage(
                    role="procurement", text=p_text, offer=p_offer, round_num=round_num,
                ))
                await self._emit({
                    "type": "round_message",
                    "vendor": ctx.contract.vendor,
                    "round": round_num,
                    "role": "procurement",
                    "text": clean_text,
                    "offer": {
                        "price": p_offer_data.get("price"),
                        "seats": p_offer_data.get("seats"),
                        "term_months": p_offer_data.get("term_months", 12),
                        "notes": p_offer_data.get("notes", ""),
                    } if p_offer_data else None,
                })

                if p_offer and p_offer.walked_away:
                    result = NegotiationResult(
                        vendor=ctx.contract.vendor,
                        outcome=NegotiationOutcome.WALKED_AWAY,
                        original_arr=ctx.contract.current_arr,
                        savings=0.0, rounds=round_num, transcript=transcript,
                        summary=f"Procurement walked away after {round_num} rounds — vendor could not meet threshold.",
                    )
                    await self._emit_complete(result)
                    return result

                if p_offer and p_offer.accepted and latest_vendor_offer:
                    final_price = latest_vendor_offer["price"]
                    savings = ctx.contract.current_arr - final_price
                    result = NegotiationResult(
                        vendor=ctx.contract.vendor,
                        outcome=NegotiationOutcome.AGREED,
                        final_price=final_price,
                        original_arr=ctx.contract.current_arr,
                        savings=savings, rounds=round_num, transcript=transcript,
                        summary=f"Deal closed at ${final_price:,.0f} (saved ${savings:,.0f} vs. prior contract).",
                    )
                    await self._emit_complete(result)
                    return result

                # Send to vendor A2A endpoint
                parts = [TextPart(type="text", text=p_text)]
                if p_offer_data:
                    clean = {k: v for k, v in p_offer_data.items()
                             if k not in ("accepted", "walked_away")}
                    parts.append(DataPart(type="data", data=clean))

                req = SendTaskRequest(
                    sessionId=session_id,
                    message=Message(role="user", parts=parts),
                )
                raw = await http.post(
                    f"{vendor_url}/tasks/send",
                    content=req.model_dump_json(),
                    headers={"Content-Type": "application/json"},
                )
                raw.raise_for_status()
                v_response = SendTaskResponse.model_validate(raw.json())
                v_msg = v_response.result.status.message if v_response.result else None

                if not v_msg:
                    break

                v_text = " ".join(
                    p.text for p in v_msg.parts if p.type == "text"  # type: ignore[union-attr]
                )
                for p in v_msg.parts:
                    if p.type == "data":
                        latest_vendor_offer = p.data  # type: ignore[union-attr]

                v_offer = _parse_offer(latest_vendor_offer)
                transcript.append(NegotiationMessage(
                    role="vendor", text=v_text, offer=v_offer, round_num=round_num,
                ))
                await self._emit({
                    "type": "round_message",
                    "vendor": ctx.contract.vendor,
                    "round": round_num,
                    "role": "vendor",
                    "text": _strip_json_block(v_text),
                    "offer": latest_vendor_offer,
                })

                history.append({"role": "user", "content": f"[VENDOR MESSAGE]:\n{v_text}"})

                if latest_vendor_offer:
                    vendor_price = latest_vendor_offer.get("price", float("inf"))
                    if vendor_price != -1 and vendor_price <= ctx.target_price:
                        savings = ctx.contract.current_arr - vendor_price
                        result = NegotiationResult(
                            vendor=ctx.contract.vendor,
                            outcome=NegotiationOutcome.AGREED,
                            final_price=vendor_price,
                            original_arr=ctx.contract.current_arr,
                            savings=savings, rounds=round_num, transcript=transcript,
                            summary=f"Auto-accepted at ${vendor_price:,.0f} — at or below target (saved ${savings:,.0f}).",
                        )
                        await self._emit_complete(result)
                        return result

        last_vendor_price = (
            latest_vendor_offer.get("price") if latest_vendor_offer else None
        )
        result = NegotiationResult(
            vendor=ctx.contract.vendor,
            outcome=NegotiationOutcome.ESCALATED,
            final_price=last_vendor_price,
            original_arr=ctx.contract.current_arr,
            savings=(ctx.contract.current_arr - last_vendor_price if last_vendor_price else 0.0),
            rounds=MAX_ROUNDS,
            transcript=transcript,
            summary=f"Escalated to human after {MAX_ROUNDS} rounds. Last vendor offer: "
                    + (f"${last_vendor_price:,.0f}" if last_vendor_price else "unknown"),
        )
        await self._emit_complete(result)
        return result

    async def _emit_complete(self, result: NegotiationResult) -> None:
        await self._emit({
            "type": "negotiation_complete",
            "vendor": result.vendor,
            "outcome": result.outcome.value,
            "final_price": result.final_price,
            "original_arr": result.original_arr,
            "savings": result.savings,
            "rounds": result.rounds,
            "summary": result.summary,
        })


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def _strip_json_block(text: str) -> str:
    return re.sub(r"```json.*?```", "", text, flags=re.DOTALL).strip()


def _parse_offer(data: dict[str, Any] | None) -> Offer | None:
    if not data:
        return None
    try:
        return Offer(
            price=data.get("price", 0),
            seats=data.get("seats", 0),
            term_months=data.get("term_months", 12),
            add_ons=data.get("add_ons", []),
            notes=data.get("notes", ""),
            accepted=data.get("accepted", False),
            walked_away=data.get("walked_away", False) or data.get("price", 0) == -1,
        )
    except Exception:
        return None
