
# Open Source Reference Inventory

These projects are accelerators and references.

The Intelligence Engine must not depend on a third-party project remaining

online or operated by its original author.

## AI Pulse

Potential ideas:

- Reddit RSS discovery

- Google News RSS discovery

- Hacker News discovery

- velocity scoring

- author/story caps

- inexpensive near-duplicate filtering

## Agent Reach

Potential ideas:

- multi-backend collector abstraction

- fallback routing

- YouTube transcript access

- web-reader patterns

- source health checks

MIT-licensed, but platform terms must still be reviewed separately.

## last30days-skill

Potential ideas:

- cross-source clustering

- FROM vs ABOUT separation

- engagement normalization

- watchlist deltas

- source health / doctor

- pre-research source discovery

- StockTwits support

MIT-licensed.

## SurfSense

Potential ideas:

- standardized connector interfaces

- knowledge-base/indexing architecture

- citation architecture

- MCP service patterns

- scheduled research agents

## Huginn

Potential ideas:

- scheduling

- event workflows

- monitoring

- collector orchestration

Should remain replaceable infrastructure, never a core intelligence dependency.

## Twitter Sentiment Analysis

Potential ideas:

- Sentiment140 as auxiliary social-language data

- text preprocessing

- inexpensive sentiment baseline

Not suitable as the Truth Engine.

## Rule

Prefer:

open-source idea/library

→ isolated adapter or our implementation

→ our stable internal interface

Avoid:

our product

→ third-party project-owned API/service

→ critical functionality

