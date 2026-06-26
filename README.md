# B2B SaaS Renewal Negotiator 🤝

**Your procurement agent negotiates SaaS renewals with vendor sales agents — in parallel, over the A2A protocol.**

Most SaaS renewals are negotiable, but nobody has time to run them. This project puts an autonomous **procurement agent** across the table from autonomous **vendor sales agents** (Salesforce, Notion, Datadog) and lets them negotiate price, seats, and term — round by round, all at once. An ops team that could realistically negotiate one renewal can now run thirty.

Each side holds **private information** the other never sees, which is what makes the negotiation real:

| Procurement agent knows | Vendor agent knows |
|---|---|
| Seat utilization (e.g. 138/200 used) | Floor price (absolute minimum) |
| Market comps for comparable tools | Discount authority (max %) |
| Target price + private **walk-away** threshold | Quota attainment (deal pressure) |

---

## How it works

```
                 ┌─────────────────────────┐
                 │   React Dashboard (SSE)  │   live transcript + savings
                 └────────────▲────────────┘
                              │ /api/stream
                 ┌────────────┴────────────┐
                 │   FastAPI SSE server     │   src/api.py
                 │   EventBroadcaster       │
                 └────────────▲────────────┘
                              │ event_callback
                 ┌────────────┴────────────┐
                 │   Orchestrator           │   asyncio.gather → N in parallel
                 └──┬──────────┬──────────┬─┘
                    │          │          │
        ┌───────────▼┐  ┌──────▼─────┐  ┌─▼──────────┐
        │ Procurement│  │ Procurement│  │ Procurement│  (one negotiation each)
        │   Agent    │  │   Agent    │  │   Agent    │
        └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
              │ A2A/HTTP       │ A2A/HTTP      │ A2A/HTTP
        ┌─────▼──────┐  ┌──────▼─────┐  ┌──────▼─────┐
        │ Salesforce │  │   Notion   │  │  Datadog   │  vendor A2A servers
        │ Sales Agent│  │ Sales Agent│  │ Sales Agent│  (FastAPI, :8200-8202)
        └────────────┘  └────────────┘  └────────────┘
```

- Agents talk over the **[A2A protocol](https://google.github.io/A2A/)** — each vendor exposes an Agent Card at `/.well-known/agent.json` and accepts negotiation tasks at `/tasks/send`.
- Offers travel as structured **`DataPart`** payloads (`{price, seats, term_months, notes}`) alongside the natural-language **`TextPart`** message.
- Negotiation runs up to **6 rounds**, then resolves to one of: `Agreed`, `Walked Away`, or `Escalated`.
- Reasoning is powered by **OpenAI GPT-4o-mini**.

---

## Tech stack

| Layer | Tech |
|---|---|
| Agents & protocol | Python · FastAPI · httpx · Pydantic · A2A |
| LLM | OpenAI GPT-4o-mini |
| Streaming | Server-Sent Events (SSE) |
| Frontend | React · Vite · Tailwind CSS · lucide-react |
| Design | OLED dark mode · glassmorphism bento grid · Plus Jakarta Sans |

---

## Setup

### 1. Prerequisites
- Python 3.11+ with [`uv`](https://docs.astral.sh/uv/)
- Node.js 18+

### 2. Configure your API key
```bash
cp .env.example .env
# then edit .env and set your key:
# OPENAI_API_KEY=sk-...
```

### 3. Install dependencies
```bash
# Backend
uv venv && uv pip install -e .

# Frontend
cd frontend && npm install && cd ..
```

---

## Running

You need **two terminals**.

**Terminal 1 — Backend (FastAPI + agents):**
```bash
uv run uvicorn src.api:app --port 8000
```

**Terminal 2 — Frontend (dashboard):**
```bash
cd frontend && npm run dev
```

Open **http://localhost:5173** and click **“Start negotiations.”** Watch all three renewals negotiate in parallel, round by round, with savings tallied live.

### CLI-only mode (no UI)
Prints the full transcript to your terminal:
```bash
uv run demo.py                 # all three vendors
uv run demo.py --vendor sf     # single: sf | notion | dd
```

---

## Project structure

```
.
├── src/
│   ├── config.py            # loads .env
│   ├── models.py            # domain models (Contract, contexts, results)
│   ├── a2a/types.py         # A2A protocol types (AgentCard, Task, Message, Parts)
│   ├── agents/
│   │   ├── vendor.py        # VendorAgentServer — A2A server w/ private state
│   │   └── procurement.py   # ProcurementAgent — negotiates over HTTP
│   ├── orchestrator.py      # boots vendors, fans out negotiations in parallel
│   └── api.py               # FastAPI SSE server (POST /api/start, GET /api/stream)
├── demo.py                  # CLI runner with sample scenarios
├── frontend/                # React + Vite + Tailwind dashboard
└── .env                     # OPENAI_API_KEY (gitignored)
```

---

## Extending it

- **Add a vendor:** drop a new scenario into `SCENARIOS` in `src/api.py` (and `demo.py`) with a fresh port, a `ProcurementContext`, and a `VendorContext`. The orchestrator picks it up automatically.
- **Real data:** replace the hardcoded contexts with live seat-utilization pulls and market-comp lookups.
- **Real vendors:** the vendor agents are A2A-compliant servers — swap them for actual vendor endpoints when they exist.

---

## Why A2A?

Two agents with **asymmetric private state**, negotiating toward a deal, is exactly the shape A2A was designed for. This is a small, honest demonstration of agents that *transact* — not just chat.
