"""Mission schedule schema — D-120 / B-101.

Defines schedule structure for cron-based mission execution.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class MissionSchedule:
    """Cron-based mission schedule linked to a template."""
    id: str = field(default_factory=lambda: f"sched_{uuid.uuid4().hex[:12]}")
    name: str = ""
    template_id: str = ""
    cron: str = ""  # Cron expression: "0 9 * * 1-5"
    timezone: str = "Europe/Istanbul"
    parameters: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[str] = None
    last_mission_id: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    max_concurrent: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "template_id": self.template_id,
            "cron": self.cron,
            "timezone": self.timezone,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "last_mission_id": self.last_mission_id,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "max_concurrent": self.max_concurrent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def parse_cron(expr: str) -> dict:
    """Parse a cron expression into its components.

    Supports: minute hour day_of_month month day_of_week
    Values: * (any), number, range (1-5), list (1,3,5), step (*/5)
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Cron expression must have 5 fields, got {len(parts)}: '{expr}'")

    names = ["minute", "hour", "day_of_month", "month", "day_of_week"]
    limits = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
    result = {}

    for i, (part, name, (lo, hi)) in enumerate(zip(parts, names, limits)):
        result[name] = _parse_cron_field(part, lo, hi)

    return result


def _parse_cron_field(field_str: str, lo: int, hi: int) -> set[int]:
    """Parse a single cron field into a set of valid integers."""
    values = set()

    for token in field_str.split(","):
        if token == "*":
            values.update(range(lo, hi + 1))
        elif "/" in token:
            base, step = token.split("/", 1)
            step = int(step)
            start = lo if base == "*" else int(base)
            values.update(range(start, hi + 1, step))
        elif "-" in token:
            a, b = token.split("-", 1)
            values.update(range(int(a), int(b) + 1))
        else:
            values.add(int(token))

    return {v for v in values if lo <= v <= hi}


def cron_matches(expr: str, dt: datetime) -> bool:
    """Check if a datetime matches a cron expression."""
    parsed = parse_cron(expr)
    return (
        dt.minute in parsed["minute"]
        and dt.hour in parsed["hour"]
        and dt.day in parsed["day_of_month"]
        and dt.month in parsed["month"]
        and dt.weekday() in _weekday_convert(parsed["day_of_week"])
    )


def _weekday_convert(cron_days: set[int]) -> set[int]:
    """Convert cron day_of_week (0=Sun) to Python weekday (0=Mon)."""
    # Cron: 0=Sunday, 1=Monday, ..., 6=Saturday
    # Python: 0=Monday, ..., 6=Sunday
    mapping = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    return {mapping[d] for d in cron_days if d in mapping}


def next_cron_time(expr: str, after: datetime) -> datetime:
    """Calculate the next time a cron expression will match after given datetime.

    Brute-force: checks minute-by-minute up to 366 days ahead.
    """
    from datetime import timedelta
    dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    max_iterations = 366 * 24 * 60  # ~1 year of minutes
    for _ in range(max_iterations):
        if cron_matches(expr, dt):
            return dt
        dt += timedelta(minutes=1)
    raise ValueError(f"No matching time found for cron '{expr}' within 366 days")
