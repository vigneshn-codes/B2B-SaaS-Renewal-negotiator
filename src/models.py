from __future__ import annotations
from pydantic import BaseModel, computed_field
from typing import Optional
from enum import Enum


class NegotiationOutcome(str, Enum):
    AGREED = "agreed"
    WALKED_AWAY = "walked_away"
    ESCALATED = "escalated"
    IN_PROGRESS = "in_progress"


class Contract(BaseModel):
    vendor: str
    current_arr: float
    seats_licensed: int
    seats_used: int
    contract_end_date: str

    @computed_field
    @property
    def utilization_pct(self) -> float:
        return round(self.seats_used / self.seats_licensed * 100, 1)


class ProcurementContext(BaseModel):
    contract: Contract
    market_low: float       # low end of comp set
    market_high: float      # high end of comp set
    target_price: float     # ideal outcome
    walkaway_price: float   # private: will switch vendors above this
    opening_anchor: float   # first offer price


class VendorContext(BaseModel):
    vendor: str
    current_arr: float
    floor_price: float          # private: minimum acceptable
    max_discount_pct: float     # private: max discount authority
    quota_attainment_pct: float # private: how rep tracks vs quota


class Offer(BaseModel):
    price: float
    seats: int
    term_months: int = 12
    add_ons: list[str] = []
    notes: str = ""
    accepted: bool = False
    walked_away: bool = False


class NegotiationMessage(BaseModel):
    role: str   # "procurement" | "vendor"
    text: str
    offer: Optional[Offer] = None
    round_num: int = 0


class NegotiationResult(BaseModel):
    vendor: str
    outcome: NegotiationOutcome
    final_price: Optional[float] = None
    original_arr: float
    savings: float = 0.0
    rounds: int = 0
    transcript: list[NegotiationMessage] = []
    summary: str = ""


class NegotiationScenario(BaseModel):
    procurement: ProcurementContext
    vendor: VendorContext
    port: int
