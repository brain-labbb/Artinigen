"""Cross-call streak state for `articraft template compile-sweep`.

Persists a short rolling history of sweeps per slug under
`<state_dir>/<slug>.json` and tracks how many consecutive sweeps each
FailureCluster signature has appeared in. This lets the CLI emit an
`escalation` block when the same structural failure pattern persists across
multiple iterations of the authoring loop, which signals the agent should
stop trying to patch the failing seed(s) directly and instead narrow
`config_from_seed` or split the template into multiple slugs.

This module deliberately operates on data only (no compile / no SDK imports)
so unit tests can drive it with synthetic state.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_STREAK_THRESHOLD = 3
DEFAULT_HISTORY_LIMIT = 10


@dataclass(slots=True)
class SweepStateSnapshot:
    """One sweep's summary, retained in `sweep_history` for trend detection."""

    timestamp: str
    pass_rate: float
    verdict: str
    cluster_signatures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "pass_rate": self.pass_rate,
            "verdict": self.verdict,
            "cluster_signatures": list(self.cluster_signatures),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SweepStateSnapshot":
        return cls(
            timestamp=str(payload.get("timestamp", "")),
            pass_rate=float(payload.get("pass_rate", 0.0)),
            verdict=str(payload.get("verdict", "fail")),
            cluster_signatures=[str(s) for s in payload.get("cluster_signatures", [])],
        )


@dataclass(slots=True)
class SweepStateRecord:
    """Per-slug persistent state."""

    slug: str
    last_updated_at: str
    sweep_history: list[SweepStateSnapshot] = field(default_factory=list)
    cluster_streaks: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "last_updated_at": self.last_updated_at,
            "sweep_history": [snap.to_dict() for snap in self.sweep_history],
            "cluster_streaks": dict(self.cluster_streaks),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SweepStateRecord":
        history = [
            SweepStateSnapshot.from_dict(item)
            for item in payload.get("sweep_history", [])
            if isinstance(item, dict)
        ]
        return cls(
            slug=str(payload.get("slug", "")),
            last_updated_at=str(payload.get("last_updated_at", "")),
            sweep_history=history,
            cluster_streaks={
                str(k): int(v) for k, v in (payload.get("cluster_streaks") or {}).items()
            },
        )


def _state_path(state_dir: Path, slug: str) -> Path:
    return state_dir / f"{slug}.json"


def load_state(state_dir: Path, slug: str) -> SweepStateRecord | None:
    path = _state_path(state_dir, slug)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return SweepStateRecord.from_dict(payload)


def save_state(state_dir: Path, record: SweepStateRecord) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(state_dir, record.slug)
    path.write_text(
        json.dumps(record.to_dict(), indent=2, sort_keys=False),
        encoding="utf-8",
    )


def _utc_now_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def update_streaks(
    *,
    slug: str,
    previous: SweepStateRecord | None,
    current_cluster_signatures: list[str],
    current_pass_rate: float,
    current_verdict: str,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    now_iso: str | None = None,
) -> SweepStateRecord:
    """Return the next SweepStateRecord with updated streaks and trimmed history.

    Streak rule: a cluster signature's streak count is the number of consecutive
    sweeps it has appeared in. Signatures absent from the current sweep are
    dropped (streak resets to 0 once the cluster goes away).
    """
    timestamp = now_iso or _utc_now_iso()
    prev_streaks = dict(previous.cluster_streaks) if previous else {}
    next_streaks: dict[str, int] = {}
    for sig in current_cluster_signatures:
        prior = prev_streaks.get(sig, 0)
        next_streaks[sig] = prior + 1

    prev_history = list(previous.sweep_history) if previous else []
    snapshot = SweepStateSnapshot(
        timestamp=timestamp,
        pass_rate=round(current_pass_rate, 6),
        verdict=current_verdict,
        cluster_signatures=list(current_cluster_signatures),
    )
    prev_history.append(snapshot)
    trimmed = prev_history[-history_limit:]

    return SweepStateRecord(
        slug=slug,
        last_updated_at=timestamp,
        sweep_history=trimmed,
        cluster_streaks=next_streaks,
    )


@dataclass(slots=True)
class EscalationDecision:
    """Top-level escalation decision attached to the sweep report."""

    required: bool
    reasons: list[str]
    cluster_streaks: dict[str, int]
    pass_rate_trend: list[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "reasons": list(self.reasons),
            "cluster_streaks": dict(self.cluster_streaks),
            "pass_rate_trend": list(self.pass_rate_trend),
        }


def compute_escalation(
    record: SweepStateRecord,
    *,
    streak_threshold: int = DEFAULT_STREAK_THRESHOLD,
    require_history_for_pass_trend: int = 3,
) -> EscalationDecision:
    """Decide whether the agent should escalate (stop patching, narrow scope).

    Triggers:
    - Any cluster_signature has streak >= streak_threshold (a persistent bug).
    - Last `require_history_for_pass_trend` snapshots show non-improving pass_rate
      AND all of them are below 1.0.
    """
    reasons: list[str] = []
    for sig, streak in record.cluster_streaks.items():
        if streak >= streak_threshold:
            reasons.append(
                f"cluster signature {sig} unchanged for {streak} consecutive sweeps "
                f"(>= {streak_threshold}); narrow config_from_seed, fix the shared "
                f"failure axis, or split the template into multiple slugs."
            )

    trend = [snap.pass_rate for snap in record.sweep_history]
    if len(record.sweep_history) >= require_history_for_pass_trend and all(
        snap.pass_rate < 1.0 for snap in record.sweep_history[-require_history_for_pass_trend:]
    ):
        recent = trend[-require_history_for_pass_trend:]
        if all(b <= a for a, b in zip(recent, recent[1:])):
            reasons.append(
                f"pass_rate has not improved over the last "
                f"{require_history_for_pass_trend} sweeps "
                f"(trend={[round(x, 3) for x in recent]}); the current fix strategy is not converging."
            )

    return EscalationDecision(
        required=bool(reasons),
        reasons=reasons,
        cluster_streaks=dict(record.cluster_streaks),
        pass_rate_trend=[round(x, 6) for x in trend],
    )
