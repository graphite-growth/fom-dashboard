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
# - "All" uses the $5K lifetime cap
# - "March–April" budget is the actual spend (campaign was a lump $2.5K plan, came in at $2,553.90)
# - "May" budget is the remaining lifetime cap
PHASES: list[Phase] = [
    Phase(id="all", label="All", start="2026-03-24", end="2026-05-31", budget=5000.00),
    Phase(id="phase-1", label="March–April", start="2026-03-24", end="2026-04-30", budget=2553.90),
    Phase(id="phase-2", label="May", start="2026-05-01", end="2026-05-31", budget=2446.10),
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
