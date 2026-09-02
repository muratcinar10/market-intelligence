from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from core.domain import Claim, NormalizedMessage


@dataclass
class ClaimExtractionResult:
    message_id: str
    claims: List[Claim] = field(default_factory=list)
    raw_model_output: str | None = None

    @property
    def has_claims(self) -> bool:
        return len(self.claims) > 0


def validate_claims_for_message(
    message: NormalizedMessage,
    claims: List[Claim],
) -> ClaimExtractionResult:
    valid_claims: List[Claim] = []

    for claim in claims:
        if claim.message_id != message.id:
            continue

        statement = (claim.statement or "").strip()

        if not statement:
            continue

        valid_claims.append(claim)

    return ClaimExtractionResult(
        message_id=message.id,
        claims=valid_claims,
    )
