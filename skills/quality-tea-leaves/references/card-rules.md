# Card rules (deck v1)

Every card is decided by a rule over the data. All thresholds, minimum samples and windows live in `assets/deck.json` so they can be tuned without touching code.

## States

| State | Meaning | Rule |
| --- | --- | --- |
| Upright | The problem is present now | Current value is above threshold |
| Reversed | The problem is improving | Current value is at or below threshold, previous window was above it |
| Quiet | Nothing to read | Neither of the above |
| Clouded | Not enough evidence; withheld | Source missing, sample below minimum, or data stale |

**Strength** ranks cards within a spread slot: value divided by threshold (or the raw count when the threshold is zero). For reversed cards it is the previous value, so a dramatic recovery ranks high.

**Confidence** is the weaker of two tiers:

| Tier | Sample (vs minimum) | Margin (strength) |
| --- | --- | --- |
| HIGH | 4x or more | 2.0 or more |
| MEDIUM | 2x or more | 1.3 or more |
| LOW | below 2x | below 1.3 |

## Rules

| Card | Value | Threshold | Minimum sample | Window |
| --- | --- | --- | --- | --- |
| 0 The Fool | % of merged PRs touching a file marked uncovered (or absent) in coverage | 10% | 10 PRs | 14 days vs prior 14 |
| IV The Emperor | Merged PRs with `checks_bypassed` | 0 | 10 PRs | 14 days vs prior 14 |
| V The Hierophant | % of requirements with no linked test or a last result other than `passed` | 10% | 5 services reporting; export no older than 14 days | Snapshot |
| IX The Hermit | % of service-map edges with zero integration tests | 20% | 5 edges | Snapshot |
| XII The Hanged Man | Critical-path E2E tests in quarantine, or E2E pass-rate drop over 5 points (drop / 5) | 0 | 20 main runs | 14 days vs prior 14 |
| XIII Death | Burn rate of the worst SLO (or, if none is burning, the one that burned hardest before) | 1.0x | 14 days of SLO window | SLO window |
| XVI The Flaky Tower | % of main-branch runs with at least one flaky failure (failed, then passed on rerun) | 3% | 30 runs | 14 days vs prior 14 |
| XVII The Star | Escaped-defect incidents. Upright: at least 3 and over 1.25x the prior window. Reversed: prior at least 3 and now under 0.75x | n/a | 4 incidents across both windows | 28 days vs prior 28 |
| XVIII The Moon | % of incidents first detected by a customer | 25% | 4 incidents | 28 days vs prior 28 |
| XX Judgement | % of postmortem actions that are open and past due | 20% | 5 actions | All open actions |

Feature-branch runs are ignored. Only `main` is read.

## The spread

| Position | Slot | Cards |
| --- | --- | --- |
| Past | lagging | Death, The Star, Judgement |
| Present | current | The Emperor, The Hanged Man, The Flaky Tower, The Moon |
| Next Release | leading | The Fool, The Hierophant, The Hermit |

Each position takes the strongest drawn card (ties go to the lower card number). If none is drawn, the lowest-numbered clouded card is shown, so the gap is visible. If nothing is drawn or clouded, the position reads "the leaves are still".

## Roadmap

- v1.1: the other 12 Major Arcana: The Magician, The High Priestess, The Empress, The Lovers (broken contracts), The Chariot, Strength, The Friday Deploy, Justice, Temperance, The Devil (silenced alerts), The Sun and The World.
- v1.2: richer illustrated card art beyond generated line art.
- v2: Minor Arcana. Four suits as quality domains (Swords testing, Wands delivery, Cups customer and requirements, Pentacles operations), adding latency p95/p99 regressions, accessibility and security testing.
