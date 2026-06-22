"""
B2B SaaS Renewal Negotiator — Demo
Runs 3 parallel A2A negotiations (Salesforce, Notion, Datadog).

Usage:
    uv run demo.py               # full parallel run
    uv run demo.py --vendor sf   # single vendor: sf | notion | dd
"""
from __future__ import annotations
import asyncio
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

from src.models import (
    Contract, NegotiationOutcome, NegotiationScenario,
    ProcurementContext, VendorContext,
)
from src.orchestrator import run_negotiations

console = Console()

# ------------------------------------------------------------------
# Scenario definitions
# ------------------------------------------------------------------

SCENARIOS: dict[str, NegotiationScenario] = {
    "sf": NegotiationScenario(
        port=8200,
        procurement=ProcurementContext(
            contract=Contract(
                vendor="Salesforce",
                current_arr=240_000,
                seats_licensed=200,
                seats_used=138,
                contract_end_date="2025-09-30",
            ),
            market_low=170_000,
            market_high=210_000,
            target_price=195_000,
            walkaway_price=225_000,
            opening_anchor=175_000,
        ),
        vendor=VendorContext(
            vendor="Salesforce",
            current_arr=240_000,
            floor_price=204_000,   # ~15% discount floor
            max_discount_pct=20.0,
            quota_attainment_pct=72.0,  # behind quota → more flexible
        ),
    ),
    "notion": NegotiationScenario(
        port=8201,
        procurement=ProcurementContext(
            contract=Contract(
                vendor="Notion",
                current_arr=24_000,
                seats_licensed=100,
                seats_used=87,
                contract_end_date="2025-10-31",
            ),
            market_low=14_000,
            market_high=20_000,
            target_price=18_000,
            walkaway_price=22_000,
            opening_anchor=15_000,
        ),
        vendor=VendorContext(
            vendor="Notion",
            current_arr=24_000,
            floor_price=19_200,   # 20% floor
            max_discount_pct=25.0,
            quota_attainment_pct=105.0,  # above quota → less flexible
        ),
    ),
    "dd": NegotiationScenario(
        port=8202,
        procurement=ProcurementContext(
            contract=Contract(
                vendor="Datadog",
                current_arr=96_000,
                seats_licensed=20,
                seats_used=14,
                contract_end_date="2025-11-30",
            ),
            market_low=60_000,
            market_high=80_000,
            target_price=72_000,
            walkaway_price=88_000,
            opening_anchor=58_000,
        ),
        vendor=VendorContext(
            vendor="Datadog",
            current_arr=96_000,
            floor_price=76_800,   # 20% floor
            max_discount_pct=22.0,
            quota_attainment_pct=88.0,  # slightly behind
        ),
    ),
}


# ------------------------------------------------------------------
# Display helpers
# ------------------------------------------------------------------

def _outcome_color(outcome: NegotiationOutcome) -> str:
    return {
        NegotiationOutcome.AGREED: "green",
        NegotiationOutcome.WALKED_AWAY: "red",
        NegotiationOutcome.ESCALATED: "yellow",
        NegotiationOutcome.IN_PROGRESS: "blue",
    }.get(outcome, "white")


def print_transcript(scenario_key: str, result) -> None:
    vendor = result.vendor
    console.rule(f"[bold]{vendor} — Negotiation Transcript[/bold]")
    for msg in result.transcript:
        color = "cyan" if msg.role == "procurement" else "magenta"
        role_label = "PROCUREMENT" if msg.role == "procurement" else f"  {vendor.upper()}"
        console.print(f"\n[{color}][Round {msg.round_num}] {role_label}[/{color}]")
        # Strip the JSON block for cleaner transcript display
        import re
        clean_text = re.sub(r"```json.*?```", "", msg.text, flags=re.DOTALL).strip()
        console.print(clean_text)
        if msg.offer and msg.offer.price > 0:
            console.print(
                f"  [dim]→ Offer: ${msg.offer.price:,.0f} | "
                f"{msg.offer.seats} seats | {msg.offer.term_months}mo"
                + (f" | {msg.offer.notes}" if msg.offer.notes else "")
                + "[/dim]"
            )


def print_summary(results: list) -> None:
    table = Table(
        title="[bold]Renewal Negotiation Results[/bold]",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Vendor", style="bold")
    table.add_column("Outcome", justify="center")
    table.add_column("Original ARR", justify="right")
    table.add_column("Final Price", justify="right")
    table.add_column("Savings", justify="right", style="green")
    table.add_column("Rounds", justify="center")

    total_original = 0.0
    total_savings = 0.0

    for r in results:
        color = _outcome_color(r.outcome)
        outcome_label = Text(r.outcome.value.upper(), style=color)
        final = f"${r.final_price:,.0f}" if r.final_price else "—"
        savings = f"${r.savings:,.0f}" if r.savings > 0 else "—"
        table.add_row(
            r.vendor,
            outcome_label,
            f"${r.original_arr:,.0f}",
            final,
            savings,
            str(r.rounds),
        )
        total_original += r.original_arr
        total_savings += r.savings

    console.print()
    console.print(table)
    console.print()

    pct_saved = (total_savings / total_original * 100) if total_original else 0
    console.print(Panel(
        f"[bold green]Total savings: ${total_savings:,.0f}[/bold green]  "
        f"([dim]{pct_saved:.1f}% off combined ARR of ${total_original:,.0f}[/dim])",
        title="Bottom Line",
        border_style="green",
    ))


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

async def _run(keys: list[str]) -> None:
    scenarios = [SCENARIOS[k] for k in keys]
    vendors = ", ".join(s.vendor.vendor for s in scenarios)

    console.print(Panel(
        f"[bold]Negotiating renewals with:[/bold] {vendors}\n"
        f"Running [cyan]{len(scenarios)}[/cyan] negotiation(s) in parallel via A2A protocol.",
        title="B2B SaaS Renewal Negotiator",
        border_style="cyan",
    ))

    results = await run_negotiations(scenarios)

    # Print each transcript
    for key, result in zip(keys, results):
        print_transcript(key, result)

    console.print()
    print_summary(results)


def main() -> None:
    args = sys.argv[1:]
    if "--vendor" in args:
        idx = args.index("--vendor")
        key = args[idx + 1] if idx + 1 < len(args) else None
        if key not in SCENARIOS:
            console.print(f"[red]Unknown vendor key '{key}'. Choose from: {list(SCENARIOS)}[/red]")
            sys.exit(1)
        keys = [key]
    else:
        keys = list(SCENARIOS.keys())

    asyncio.run(_run(keys))


if __name__ == "__main__":
    main()
