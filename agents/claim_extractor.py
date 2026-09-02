from __future__ import annotations

import json
import subprocess
import uuid
from typing import Any, Dict, List

from core.claim_extraction import ClaimExtractionResult, validate_claims_for_message
from core.domain import Claim, NormalizedMessage


SYSTEM_PROMPT = """
You are a financial claim extraction engine.

Your only task is to extract objectively verifiable claims from a message.

Do NOT:
- decide whether the claim is true
- decide whether the message should be kept
- assign sentiment
- assign bullish/bearish direction
- speculate
- summarize opinions as facts

A claim must be something that could theoretically be verified against evidence.

Examples:

Input:
"AMD Q2 revenue was $11.5B and data center revenue more than doubled."

Output:
{
  "claims": [
    {
      "statement": "AMD Q2 revenue was $11.5B",
      "entity": "AMD",
      "ticker": "AMD",
      "metric": "revenue",
      "value": "$11.5B",
      "period": "Q2",
      "event_type": "earnings",
      "speculative_extension": null
    },
    {
      "statement": "AMD data center revenue more than doubled",
      "entity": "AMD",
      "ticker": "AMD",
      "metric": "data_center_revenue",
      "value": "more than doubled",
      "period": null,
      "event_type": "earnings",
      "speculative_extension": null
    }
  ]
}

Input:
"NVDA to the moon 🚀"

Output:
{
  "claims": []
}

Input:
"Tesla delivered 480,126 vehicles, so the stock will definitely explode."

Output:
{
  "claims": [
    {
      "statement": "Tesla delivered 480,126 vehicles",
      "entity": "Tesla",
      "ticker": "TSLA",
      "metric": "deliveries",
      "value": "480126",
      "period": null,
      "event_type": "deliveries",
      "speculative_extension": "the stock will definitely explode"
    }
  ]
}

Return JSON only.

Schema:
{
  "claims": [
    {
      "statement": string,
      "entity": string|null,
      "ticker": string|null,
      "metric": string|null,
      "value": string|null,
      "period": string|null,
      "event_type": string|null,
      "speculative_extension": string|null
    }
  ]
}
""".strip()


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()

    if not text:
        return {"claims": []}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return {"claims": []}

    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {"claims": []}


def _call_ollama(model: str, prompt: str, timeout: int = 120) -> str:
    full_prompt = f"{SYSTEM_PROMPT}\n\nMESSAGE:\n{prompt}"

    result = subprocess.run(
        ["ollama", "run", model],
        input=full_prompt,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def extract_claims(
    message: NormalizedMessage,
    model: str = "qwen3:1.7b",
) -> ClaimExtractionResult:
    raw = _call_ollama(model=model, prompt=message.text)
    payload = _extract_json(raw)

    claims: List[Claim] = []

    for item in payload.get("claims", []):
        if not isinstance(item, dict):
            continue

        statement = str(item.get("statement") or "").strip()

        if not statement:
            continue

        claims.append(
            Claim(
                id=f"claim-{uuid.uuid4().hex[:12]}",
                message_id=message.id,
                statement=statement,
                entity=item.get("entity"),
                ticker=item.get("ticker"),
                metric=item.get("metric"),
                value=item.get("value"),
                period=item.get("period"),
                event_type=item.get("event_type"),
                speculative_extension=item.get("speculative_extension"),
            )
        )

    result = validate_claims_for_message(message, claims)
    result.raw_model_output = raw
    return result
