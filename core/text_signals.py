from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class TextSignals:
    prediction: bool = False
    opinion: bool = False
    inference: bool = False
    rumor: bool = False
    sarcasm_hint: bool = False
    matched: List[str] = field(default_factory=list)


PREDICTION_PATTERNS = [
    r"\bwill\b",
    r"\bgoing to\b",
    r"\bnext (week|month|quarter|year)\b",
    r"\bbefore christmas\b",
    r"\bsoon\b",
    r"\bwill hit\b",
    r"\bwill double\b",
    r"\bwill destroy\b",
    r"\bikiye katlanacak\b",
    r"\btavan olur\b",
    r"\byüzde\s*\d+\s*gider\b",
    r"\bönümüzdeki hafta\b",
    r"\byıl sonuna kadar\b",
]

OPINION_PATTERNS = [
    r"\bi think\b",
    r"\bin my opinion\b",
    r"\bif you ask me\b",
    r"\btrash\b",
    r"\bgarbage\b",
    r"\bundervalued\b",
    r"\bovervalued\b",
    r"\beasy money\b",
    r"\bgenerational buying opportunity\b",
    r"\babsolute monster\b",
    r"\bterrible decision\b",
    r"\bdesperate move\b",
    r"\bbence\b",
    r"\bbitmiş bir şirket\b",
    r"\bçok iyi\b",
    r"\btren kalkıyor\b",
]

INFERENCE_PATTERNS = [
    r"\bwhich means\b",
    r"\btherefore\b",
    r"\bthis proves\b",
    r"\bso\b",
    r"\bdemek ki\b",
    r"\bbu yüzden\b",
]

RUMOR_PATTERNS = [
    r"\brumou?r says\b",
    r"\bsources say\b",
    r"\breportedly\b",
    r"\baccording to sources\b",
    r"\bperson familiar with the matter\b",
    r"\bpiyasada konuşulanlara göre\b",
    r"\bkulislere göre\b",
]

SARCASM_PATTERNS = [
    r"\bsure,",
    r"\bgreat job\b",
    r"\bamazing performance\b",
    r"\bnothing to see here\b",
    r"\bharika,\b",
    r"\bevet evet\b",
    r"\bkesin müthiş haber\b",
]


def _matches(patterns, text):
    found = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(pattern)
    return found


def analyze_text(text: str) -> TextSignals:
    prediction = _matches(PREDICTION_PATTERNS, text)
    opinion = _matches(OPINION_PATTERNS, text)
    inference = _matches(INFERENCE_PATTERNS, text)
    rumor = _matches(RUMOR_PATTERNS, text)
    sarcasm = _matches(SARCASM_PATTERNS, text)

    return TextSignals(
        prediction=bool(prediction),
        opinion=bool(opinion),
        inference=bool(inference),
        rumor=bool(rumor),
        sarcasm_hint=bool(sarcasm),
        matched=prediction + opinion + inference + rumor + sarcasm,
    )
