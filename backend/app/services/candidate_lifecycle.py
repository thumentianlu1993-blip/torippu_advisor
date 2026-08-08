"""Source absence lifecycle that ignores incomplete/budget-truncated runs."""

from datetime import datetime, timedelta

from app.models import CandidateSource


def record_observation(
    source: CandidateSource,
    *,
    at: datetime,
    seen: bool,
    complete: bool,
    successful: bool,
    budget_truncated: bool,
) -> bool:
    before = (
        source.consecutive_absences,
        source.absence_window_started_at,
        source.active,
    )
    if seen:
        source.last_seen_at = at
        source.consecutive_absences = 0
        source.absence_window_started_at = None
        source.active = True
        return before != (
            source.consecutive_absences,
            source.absence_window_started_at,
            source.active,
        )
    if not complete or not successful or budget_truncated:
        return False
    if source.consecutive_absences == 0:
        source.absence_window_started_at = at
    source.consecutive_absences += 1
    if (
        source.consecutive_absences >= 3
        and source.absence_window_started_at
        and at - source.absence_window_started_at >= timedelta(days=7)
    ):
        source.active = False
    return before != (
        source.consecutive_absences,
        source.absence_window_started_at,
        source.active,
    )
