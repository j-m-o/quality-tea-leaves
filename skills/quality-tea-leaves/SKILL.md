---
name: quality-tea-leaves
description: Deals an evidence-backed tarot reading of a codebase's quality from CI runs, PRs, coverage, incidents, requirements, service contracts and SLOs. Use when someone asks for a quality reading, a fun release-health summary, "read the tea leaves" on a repo, or a memorable way to present quality risk. Every card must cite evidence; thin evidence is clouded and withheld.
---

# Quality Tea Leaves

A fortune teller that refuses to guess. Ten Major Arcana cards each map to one quality signal. A deterministic rule decides whether each card is **upright** (the problem is present), **reversed** (it is improving), **quiet** (nothing to read) or **clouded** (not enough evidence, so the card is withheld). The prophecy is theater. The evidence is not.

The point it makes: AI that sounds confident without evidence is fortune telling. This skill shows the alternative.

## When to use

- Someone asks for a "reading", "tea leaves" or a fun, memorable summary of release or quality health.
- A talk, demo, retro or leadership update needs quality risk told as a story without losing the numbers.
- Someone wants to see which quality signals they cannot read yet. Clouded cards are a to-do list of missing evidence.

Do not use it for go/no-go decisions. It is advisory and ends at a human.

## How to run

The script is read-only, uses only the Python standard library and makes no network calls.

```bash
# Bundled fictional checkout platform
python scripts/tealeaves.py demo --out reading

# Your own data folder (see references/data-contract.md)
python scripts/tealeaves.py read --data path/to/data --out reading
```

Outputs in the `--out` folder:

| File | What it is |
| --- | --- |
| `reading.json` | Every card's state, strength, confidence, evidence or missing evidence, and the spread |
| `reading.md` | The reading in Markdown, marked DRAFT pending human review |
| `reading.html` | The spread and the rest of the deck as a page that works offline |
| `cards/*.svg` | One card per drawn or clouded card |

## The deck (v1)

| # | Card | Signal | Slot |
| --- | --- | --- | --- |
| 0 | The Fool | Merges touching code no test covers | Next Release |
| IV | The Emperor | Merges that bypassed required checks | Present |
| V | The Hierophant | Requirements with no linked passing test | Next Release |
| IX | The Hermit | Service borders with no integration tests | Next Release |
| XII | The Hanged Man | Critical E2E tests quarantined, or E2E pass rate falling | Present |
| XIII | Death | SLO error budget burn | Past |
| XVI | The Flaky Tower | Share of main-branch runs with a flaky failure | Present |
| XVII | The Star | Escaped defects rising or falling | Past |
| XVIII | The Moon | Incidents found by customers before alerts | Present |
| XX | Judgement | Overdue postmortem actions | Past |

Thresholds, sample minimums and confidence rules are in `references/card-rules.md`.

## The spread

Three positions: **Past** (lagging signals), **Present** (current signals), **Next Release** (leading signals). Each position shows the strongest drawn card in its slot. If none is drawn but one is clouded, the clouded card is shown so the gap is visible. The shuffle is theater: the same data always gives the same reading.

## Presenting a reading

1. Run the script. Never invent a card, a number or a state the script did not produce.
2. Lead with the summary line, then the three spread cards: prophecy in italics, then confidence, then evidence as plain facts.
3. Keep the two voices separate. Prophecy is theatrical; evidence is plain and exact. Never dress up a number.
4. For a clouded card, say it is withheld and list what evidence would lift the veil. Do not speculate about what it would have said.
5. Name systems, services and modules. Never name people, even if the data contains authors.
6. Close with the status: draft, pending human review. Offer the HTML page or SVG cards if they want something to share.

Prophecy writing rules for new cards are in `references/voice.md`.

## Human in the loop

- The reading is advisory. A named human reviews it before it is shared or acted on.
- Clouded cards are withheld, never guessed.
- No individual scoring or blame. Cards describe systems.
- Read-only: the skill never changes CI, tickets, alerts or code.

## Limits

Thresholds are reasonable defaults, not industry standards; tune them in `assets/deck.json`. A quiet card means the rule found nothing above threshold in the data provided, not that the area is healthy. Garbage in, prophecy out: the reading is only as good as the exports behind it.
