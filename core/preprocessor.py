from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from core.claim_segmenter import segment_message
from core.text_signals import analyze_text


@dataclass
class SegmentDecision:
    text: str
    kind: str
    should_extract: bool
    speculative_extension: str | None = None
    context_type: str | None = None


def _split_clause_conjunctions(text: str) -> List[str]:
    """
    Conservative splitter for clear multi-fact structures.

    We intentionally avoid splitting every 'and/ve'.
    """
    patterns = [
        r"\s+and\s+(?=[A-Z][A-Za-z0-9&.\- ]+\s+(rose|fell|increased|decreased|reported|reached|was|were|added|cut|signed|launched))",
        r"\s+ve\s+(?=[A-ZÇĞİÖŞÜ0-9][A-Za-zÇĞİÖŞÜçğıöşü0-9&.\- ]+\s+(arttı|azaldı|yükseldi|düştü|açıkladı|ulaştı|imzaladı|ekledi))",
    ]

    parts = [text]

    for pattern in patterns:
        next_parts = []
        for part in parts:
            split = re.split(
                pattern,
                part,
                flags=re.IGNORECASE,
            )

            # re.split with capturing groups may include verbs;
            # if that happens, keep original segment intact.
            if len(split) > 2:
                next_parts.append(part)
            else:
                next_parts.extend(
                    item.strip()
                    for item in split
                    if item and item.strip()
                )

        parts = next_parts

    return parts


def _strip_opinion_prefix(text: str) -> str:
    prefixes = [
        r"^honestly,\s*",
        r"^in my opinion,\s*",
        r"^if you ask me,\s*",
        r"^bence\s+",
        r"^harika,\s*",
        r"^sure,\s*",
        r"^amazing performance:\s*",
        r"^nothing to see here\s*[—-]\s*just\s+",
        r"^evet evet,\s*",
    ]

    cleaned = text.strip()

    for pattern in prefixes:
        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

    return cleaned


def _looks_like_pure_prediction(text: str) -> bool:
    signals = analyze_text(text)

    if not signals.prediction:
        return False

    factual_markers = [
        r"\breported\b",
        r"\bannounced\b",
        r"\bsigned\b",
        r"\blaunched\b",
        r"\brevenue\b",
        r"\bprofit\b",
        r"\bmargin\b",
        r"\bdeliveries\b",
        r"\bsales\b",
        r"\bcontract\b",
        r"\baçıkladı\b",
        r"\bimzaladı\b",
        r"\barttı\b",
        r"\bazaldı\b",
        r"\byükseldi\b",
        r"\bdüştü\b",
    ]

    has_factual_marker = any(
        re.search(p, text, re.IGNORECASE)
        for p in factual_markers
    )

    # A sentence like "Tesla deliveries will destroy expectations"
    # contains a business noun but is still a future prediction.
    if re.search(
        r"\bwill\b|\bwill hit\b|\bwill double\b|\bikiye katlanacak\b|"
        r"\byüzde\s*\d+\s*gider\b|\byıl sonuna kadar\b|\bönümüzdeki hafta\b",
        text,
        re.IGNORECASE,
    ):
        if not re.search(
            r"\b(reported|announced|signed|launched|was|were|rose|fell|"
            r"increased|decreased|açıkladı|imzaladı|arttı|azaldı|yükseldi|düştü)\b",
            text,
            re.IGNORECASE,
        ):
            return True

    return signals.prediction and not has_factual_marker


def _looks_like_pure_opinion(text: str) -> bool:
    signals = analyze_text(text)

    if not (signals.opinion or signals.sarcasm_hint):
        return False

    hard_fact_markers = [
        r"\d+%",
        r"\$\d",
        r"\b\d+(\.\d+)?\s*(billion|million|milyar|milyon|baz puan|vehicles|aircraft)\b",
        r"\breported\b",
        r"\bannounced\b",
        r"\bsigned\b",
        r"\blaunched\b",
        r"\baçıkladı\b",
        r"\bimzaladı\b",
        r"\barttı\b",
        r"\bazaldı\b",
        r"\byükseldi\b",
        r"\bdüştü\b",
    ]

    has_hard_fact = any(
        re.search(p, text, re.IGNORECASE)
        for p in hard_fact_markers
    )

    return (signals.opinion or signals.sarcasm_hint) and not has_hard_fact


def preprocess_message(text: str) -> List[SegmentDecision]:
    base_segments = segment_message(text)

    expanded: List[str] = []

    for segment in base_segments:
        expanded.extend(_split_clause_conjunctions(segment))

    decisions: List[SegmentDecision] = []

    for raw_segment in expanded:
        segment = raw_segment.strip()
        if not segment:
            continue

        signals = analyze_text(segment)

        # Explicit inference tail: do not send as factual claim.
        if signals.inference:
            inference_patterns = [
                r"\bwhich means\b",
                r"\btherefore\b",
                r"\bthis proves\b",
                r"\bdemek ki\b",
                r"\bbu yüzden\b",
            ]

            for pattern in inference_patterns:
                match = re.search(pattern, segment, re.IGNORECASE)
                if match:
                    left = segment[:match.start()].strip(" ,;")
                    right = segment[match.end():].strip(" ,;")

                    if left:
                        decisions.append(
                            SegmentDecision(
                                text=_strip_opinion_prefix(left),
                                kind="factual_candidate",
                                should_extract=True,
                                speculative_extension=right or None,
                                context_type="inference",
                            )
                        )
                    break
            else:
                decisions.append(
                    SegmentDecision(
                        text=segment,
                        kind="factual_candidate",
                        should_extract=True,
                    )
                )

            continue

        if signals.rumor:
            decisions.append(
                SegmentDecision(
                    text=segment,
                    kind="rumor_candidate",
                    should_extract=True,
                )
            )
            continue

        if _looks_like_pure_prediction(segment):
            decisions.append(
                SegmentDecision(
                    text=segment,
                    kind="prediction_only",
                    should_extract=False,
                    context_type="prediction",
                )
            )
            continue

        if _looks_like_pure_opinion(segment):
            decisions.append(
                SegmentDecision(
                    text=segment,
                    kind="opinion_only",
                    should_extract=False,
                    context_type="opinion",
                )
            )
            continue

        cleaned = _strip_opinion_prefix(segment)

        decisions.append(
            SegmentDecision(
                text=cleaned,
                kind="factual_candidate",
                should_extract=True,
            )
        )

    return decisions
