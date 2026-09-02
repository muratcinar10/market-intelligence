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



def _has_factual_payload(claim: Claim) -> bool:
    metric = (claim.metric or "").strip()
    value = (claim.value or "").strip()
    event_type = (claim.event_type or "").strip()

    return bool(metric or value or event_type)


def _looks_like_hype_statement(text: str) -> bool:
    lowered = (text or "").lower()

    patterns = [
        "nothing can stop",
        "absolute monster",
        "to the moon",
        "moon",
        "easy money",
        "generational buying opportunity",
        "bears are dead",
        "bears are officially dead",
        "cannot lose",
        "can't lose",
        "unstoppable stock",
        "tren kalkıyor",
        "kaçmaz",
        "uçuyor",
    ]

    return any(p in lowered for p in patterns)


def filter_truth_claims(
    claims: List[Claim],
    signals: TextSignals,
) -> List[Claim]:
    accepted = []

    for claim in claims:
        event_type = (claim.event_type or "").strip().lower()

        if event_type in BLOCKED_EVENT_TYPES:
            continue

        if _looks_like_hype_statement(claim.statement):
            continue

        if not _has_factual_payload(claim):
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
