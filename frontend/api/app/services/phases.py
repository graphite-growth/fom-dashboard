"""Phase config and helpers for date-scoped dashboard views.

A "phase" is a budget window the campaign was managed in. The Mar–Apr phase
spent the first $2.5K lifetime cap; May spends the remaining $2.4K of the
$5K total. The "all" phase spans the union and uses the lifetime cap as its
budget for pacing math.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

ACCOUNT_TZ = ZoneInfo("America/Chicago")

PhaseStatus = Literal["closed", "in-progress"]


@dataclass(frozen=True)
class Phase:
    id: str
    label: str
    start: str
    end: str
    budget: float

    def status(self, today: str | None = None) -> PhaseStatus:
        ref = today or datetime.now(ACCOUNT_TZ).strftime("%Y-%m-%d")
        return "in-progress" if self.start <= ref <= self.end else "closed"

    def to_dict(self, today: str | None = None) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "budget": self.budget,
            "status": self.status(today),
        }


# Hardcoded campaign structure. Update in code when phases are added.
#
# Budgets are the **Video Views** portion only — the Subscribers campaigns
# (FOM - Subscribers - *) are partitioned to their own tab and excluded from
# Views Daily Performance, so their spend doesn't belong in this pacing math.
#
# Video Views lifetime caps (from Google Ads):
#   Company Size + Interests:  $1,771.22
#   Channel Premium Whitelist:   $556.03
#   Custom Intent Search:         $88.66
#   Retargeting:                 $238.11
#   ────────────────────────────────────
#   Total:                     $2,654.02
#
# - "All" uses the Video Views lifetime cap ($2,654.02)
# - "March–April" budget is the Video Views actual spend in that window
#   ($1,839.02 = sum of Mar-Apr actuals across the 4 video campaigns)
# - "May" budget is the remaining Video Views lifetime cap ($815.00)
PHASES: list[Phase] = [
    Phase(id="all", label="All", start="2026-03-24", end="2026-05-31", budget=2654.02),
    Phase(id="phase-1", label="March–April", start="2026-03-24", end="2026-04-30", budget=1839.02),
    Phase(id="phase-2", label="May", start="2026-05-01", end="2026-05-31", budget=815.00),
]


def get_phase(phase_id: str) -> Phase | None:
    """Look up a phase by id."""
    for p in PHASES:
        if p.id == phase_id:
            return p
    return None


def all_phases() -> list[Phase]:
    """Return all configured phases."""
    return list(PHASES)


def default_phase_id(today: str | None = None) -> str:
    """Return the id of the phase to default to in the UI.

    Picks the in-progress phase that isn't "all" (i.e. the active month-window),
    falling back to "all" if none are in progress.
    """
    ref = today or datetime.now(ACCOUNT_TZ).strftime("%Y-%m-%d")
    for p in PHASES:
        if p.id == "all":
            continue
        if p.status(ref) == "in-progress":
            return p.id
    return "all"
