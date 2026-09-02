
from __future__ import annotations

from dataclasses import dataclass, field

from datetime import datetime

from enum import Enum

from typing import Any

class TruthStatus(str, Enum):

    VERIFIED = "verified"

    PARTLY_TRUE = "partly_true"

    FALSE = "false"

    STALE = "stale"

    UNVERIFIED = "unverified"

    NOISE = "noise"

class EvidenceRelation(str, Enum):

    SUPPORTS = "supports"

    CONTRADICTS = "contradicts"

    CONTEXT = "context"

@dataclass(slots=True)

class NormalizedMessage:

    id: str

    source: str

    text: str

    published_at: datetime | None = None

    author: str | None = None

    url: str | None = None

    language: str | None = None

    ticker: str | None = None

    engagement: dict[str, float] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)

class Claim:

    id: str

    message_id: str

    statement: str

    entity: str | None = None

    ticker: str | None = None

    metric: str | None = None

    value: str | None = None

    period: str | None = None

    event_type: str | None = None

    speculative_extension: str | None = None

@dataclass(slots=True)

class Evidence:

    id: str

    claim_id: str

    source: str

    text: str

    relation: EvidenceRelation

    url: str | None = None

    published_at: datetime | None = None

    source_weight: float | None = None

@dataclass(slots=True)

class TruthDecision:

    claim_id: str

    status: TruthStatus

    confidence: float

    reason: str

    evidence_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:

        if not 0.0 <= self.confidence <= 1.0:

            raise ValueError("confidence must be between 0.0 and 1.0")

