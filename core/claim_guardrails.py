from __future__ import annotations

from typing import List

from core.domain import Claim
from core.text_signals import TextSignals


BLOCKED_EVENT_TYPES = {
    "prediction",
    "price_prediction",
    "demand_prediction",
    "opinion",
    "recommendation",
}


def filter_truth_claims(
    claims: List[Claim],
    signals: TextSignals,
) -> List[Claim]:
    accepted = []

    for claim in claims:
        event_type = (claim.event_type or "").strip().lower()

        if event_type in BLOCKED_EVENT_TYPES:
            continue

        # Pure future prediction/opinion without a factual event
        # must not enter Truth Engine.
        if (
            signals.prediction
            and not signals.rumor
            and event_type in {"", "forecast"}
        ):
            continue

        accepted.append(claim)

    return accepted
