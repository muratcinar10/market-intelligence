
# Intelligence Engine v5 Architecture

## Product definition

This project is not primarily a stock-analysis application.

It is an intelligence engine that turns high-volume information from the

internet into verified, structured and personalized intelligence.

Primary flow:

Collectors

→ Normalize

→ Fast Dedupe

→ Claim Extraction

→ Evidence Retrieval

→ Truth Decision

→ Event Clustering

→ Source Reliability

→ Importance Scoring

→ User Relevance

→ Alert

## Core principle

LLMs may extract, classify and explain information.

LLMs must not be the sole authority for truth, importance or alert decisions.

The engine owns the final decision.

## Layers

### 1. Collectors

Examples:

- SEC

- KAP

- Company IR

- RSS

- News discovery

- Reddit

- YouTube

- Hacker News

- X

- Telegram

- StockTwits

Every collector must eventually emit the same normalized message format.

### 2. Normalize

Raw source-specific content becomes NormalizedMessage.

No intelligence decision happens here.

### 3. Fast Dedupe

Cheap deterministic duplicate and near-duplicate filtering runs before LLMs.

### 4. Claim Extraction

A message may contain zero, one or multiple claims.

The model extracts structured facts such as:

- entity

- ticker

- metric

- value

- period

- event type

- time reference

- factual statement

- speculative extension

### 5. Evidence

Claims are matched against supporting or contradicting evidence.

Evidence hierarchy will distinguish:

- primary official source

- high-quality secondary source

- social/community source

- unknown/unverified source

### 6. Truth

Allowed truth states:

- verified

- partly_true

- false

- stale

- unverified

- noise

Truth is a separate decision from sentiment, direction and importance.

### 7. Event Clustering

Many messages about the same real-world event become one event.

100 posts should not become 100 alerts.

### 8. Source Reliability

Sources accumulate historical reliability over time.

Reliability must use Bayesian/rolling logic so small samples do not create

extreme scores.

### 9. Importance

Importance is not sentiment.

Future inputs may include:

- novelty

- materiality

- source reliability

- cross-confirmation

- engagement velocity

- urgency

- market relevance

Output: 0–10 intelligence score.

### 10. User Relevance

The same event may have different relevance for different users.

Examples:

- watchlist

- portfolio

- selected sources

- alert threshold

### 11. Alert

Only events that satisfy truth, importance and user relevance rules should

become alerts.

## Model responsibilities

### Small model

Preferred responsibilities:

- noise detection

- claim presence

- claim extraction

- basic structural classification

It must not make the final keep/discard decision.

### Large model

Used only when ambiguity remains:

- complicated claim decomposition

- partly-true reasoning

- nuanced language

- conflicting statements

Large-model output is still evidence for the engine, not final authority.

## Benchmark discipline

Datasets are separated into:

- training

- validation

- blind test

Once a blind test is inspected or used for tuning, it becomes validation data.

Gold labels must never be available to the inference pipeline.

## Current baseline

Blind/validation baseline before v5:

- KEEP Precision: 57.0%

- KEEP Recall: 100.0%

- KEEP F1: 72.6%

- Truth Accuracy: 61.5%

- Direction Accuracy: 34.2%

- Category Accuracy: 31.5%

- False Positive: 55

- False Negative: 0

Primary v5 objective:

Reduce false positives and improve truth generalization without sacrificing

verified-claim recall.

