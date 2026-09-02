from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List

from core.claim_extraction import ClaimExtractionResult, validate_claims_for_message
from core.domain import Claim, NormalizedMessage


SYSTEM_PROMPT = """
You are a financial claim extraction engine.

Your only task is to extract objectively verifiable claims from a message.

Rules:

1. Do not decide truth.
2. Do not decide keep/discard.
3. Do not assign sentiment.
4. Do not assign bullish/bearish direction.
5. Do not convert opinions into facts.
6. Rumors are still claims if they describe a specific verifiable allegation.
7. If a factual statement is followed by an opinion, prediction, inference,
   certainty claim, causal leap, or unsupported conclusion, place that second
   part in speculative_extension.
8. speculative_extension must NOT be null when the message contains phrases
   like:
   - "so the stock will..."
   - "which means..."
   - "therefore..."
   - "this proves..."
   - "guaranteed..."
   - "definitely..."
   - "unstoppable..."
   - "easy money..."
9. Preserve uncertainty in the claim statement when present:
   "rumor says", "may", "reportedly", "could", "according to sources".
10. Return JSON only. No reasoning. No markdown.

Examples:

Input:
AMD Q2 revenue was $11.5B and data center revenue more than doubled.

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
NVDA to the moon 🚀

Output:
{
  "claims": []
}

Input:
Tesla delivered 480126 vehicles, so the stock will definitely explode.

Output:
{
  "claims": [
    {
      "statement": "Tesla delivered 480126 vehicles",
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

Input:
Rumor says Amazon may acquire a robotics startup for $4B.

Output:
{
  "claims": [
    {
      "statement": "Rumor says Amazon may acquire a robotics startup for $4B",
      "entity": "Amazon",
      "ticker": "AMZN",
      "metric": "acquisition_price",
      "value": "$4B",
      "period": null,
      "event_type": "acquisition_rumor",
      "speculative_extension": null
    }
  ]
}

Input:
TSMC reported August revenue up 33% YoY, which means NVIDIA demand is unstoppable.

Output:
{
  "claims": [
    {
      "statement": "TSMC reported August revenue up 33% YoY",
      "entity": "TSMC",
      "ticker": "TSM",
      "metric": "revenue_growth",
      "value": "33% YoY",
      "period": "August",
      "event_type": "monthly_revenue",
      "speculative_extension": "NVIDIA demand is unstoppable"
    }
  ]
}

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
    text = (text or "").strip()

    if not text:
        return {"claims": []}

    # Strip known thinking wrappers if a model still emits them.
    if "...done thinking." in text:
        text = text.split("...done thinking.", 1)[-1].strip()

    # Direct JSON parse first.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Scan for all balanced top-level JSON objects and prefer the last
    # successfully parsed object containing "claims".
    depth = 0
    start = None
    candidates = []

    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    candidates.append(text[start:i + 1])
                    start = None

    for candidate in reversed(candidates):
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(obj, dict) and "claims" in obj:
            return obj

    return {"claims": []}


def _call_ollama(model: str, prompt: str, timeout: int = 120) -> str:
    full_prompt = f"{SYSTEM_PROMPT}\\n\\nMESSAGE:\\n{prompt}"

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "format": "json",
        "think": False,
        "options": {
            "temperature": 0
        },
    }

    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return ""

    return str(body.get("response") or "").strip()



def _split_explicit_inference(text: str):
    connectors = (
        ", which means ",
        "; which means ",
        " which means ",
        ", therefore ",
        "; therefore ",
        ", so ",
        "; so ",
    )

    lowered = text.lower()

    for connector in connectors:
        index = lowered.find(connector)
        if index == -1:
            continue

        factual = text[:index].strip(" ,;")
        inference = text[index + len(connector):].strip()

        if factual and inference:
            return factual, inference

    return text, None

def _normalize_optional(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def extract_claims(
    message: NormalizedMessage,
    model: str = "qwen3:1.7b",
) -> ClaimExtractionResult:
    factual_text, explicit_inference = _split_explicit_inference(message.text)

    raw = _call_ollama(model=model, prompt=factual_text)
    payload = _extract_json(raw)

    claims: List[Claim] = []

    raw_claims = payload.get("claims", [])
    if not isinstance(raw_claims, list):
        raw_claims = []

    for item in raw_claims:
        if not isinstance(item, dict):
            continue

        statement = _normalize_optional(item.get("statement"))
        if not statement:
            continue

        event_type = _normalize_optional(item.get("event_type"))

        # Pure predictions/opinions are useful elsewhere in the product,
        # but they are not present-tense factual claims for Truth Engine.
        if event_type in {
            "prediction",
            "price_prediction",
            "demand_prediction",
            "opinion",
        }:
            continue

        claims.append(
            Claim(
                id=f"claim-{uuid.uuid4().hex[:12]}",
                message_id=message.id,
                statement=statement,
                entity=_normalize_optional(item.get("entity")),
                ticker=_normalize_optional(item.get("ticker")),
                metric=_normalize_optional(item.get("metric")),
                value=_normalize_optional(item.get("value")),
                period=_normalize_optional(item.get("period")),
                event_type=event_type,
                speculative_extension=_normalize_optional(
                    item.get("speculative_extension")
                ),
            )
        )

    if explicit_inference and claims:
        # Attach an explicit causal/predictive extension to the factual
        # claim instead of allowing it to become a separate truth claim.
        claims[-1].speculative_extension = explicit_inference

    result = validate_claims_for_message(message, claims)
    result.raw_model_output = raw
    return result
