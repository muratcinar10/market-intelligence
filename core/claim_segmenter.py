from __future__ import annotations

import re
from typing import List


STRONG_SPLITS = [
    r"\.\s+",
    r";\s*",
]

MULTI_FACT_SPLITS = [
    r"\s+while\s+",
    r"\s+but\s+",
]


def segment_message(text: str) -> List[str]:
    segments = [text.strip()]

    for pattern in STRONG_SPLITS:
        next_segments = []

        for segment in segments:
            parts = re.split(pattern, segment, flags=re.IGNORECASE)
            next_segments.extend(
                part.strip()
                for part in parts
                if part.strip()
            )

        segments = next_segments

    final_segments = []

    for segment in segments:
        parts = [segment]

        for pattern in MULTI_FACT_SPLITS:
            next_parts = []
            for part in parts:
                split = re.split(pattern, part, flags=re.IGNORECASE)
                next_parts.extend(
                    item.strip()
                    for item in split
                    if item.strip()
                )
            parts = next_parts

        final_segments.extend(parts)

    return final_segments
