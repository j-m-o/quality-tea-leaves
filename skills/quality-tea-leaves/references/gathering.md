# Gathering the evidence

**Agents gather. Rules decide. A human approves.**

The agent running this skill (Claude Code, the Quality Engine orchestrator or any MCP-capable agent) collects raw records through its connectors and writes them into the files in `data-contract.md`. It never computes a rate, picks a card or writes a number of its own. The offline engine does that. If the agent summarized a tool's output ("about 8% flaky"), the reading would be fortune telling, which is the thing this skill exists to call out.

## The rules for gathering

1. **Raw records only.** Copy fields as the tool returns them. Do not round, estimate, average or fill gaps.
2. **Read-only scopes.** Every connector needs read access only. The one write in the whole flow is the PR comment, and it happens after a human says yes (interactive) or through the workflow's scoped token (CI).
3. **No people.** Drop author, assignee and reporter fields unless the contract needs them. Action owners are teams.
4. **Record provenance.** For each file, add an entry to `manifest.json`:

```json
{"provenance": {"ci_runs": {"connector": "mabl", "query": "main-branch runs and reruns, last 28 days",
  "pulled_at": "2026-11-11T14:02:00Z", "records": 642}}}
```

The PR comment shows this table, so every number traces back to a system and a time.

5. **Missing beats wrong.** If a tool is not connected or a field does not exist, leave the file out. Its cards will cloud and say what is missing. That is the honest answer.
6. **Validate before reading.** Run `python scripts/check_data.py <folder>`. Files that fail are set aside and their cards cloud with a reason.

## Source map

Worked examples use common tools. Any tool that can produce the same fields works.

| File | Typical source | What to pull | Field mapping |
| --- | --- | --- | --- |
| `pr.json` | GitHub | PR files, check runs on the head commit, which checks are required | `files` = changed paths; `checks[].conclusion` from check runs; `required` from branch protection or a configured list |
| `pull_requests.json` | GitHub | Merged PRs for the last two windows | `merged_at`, `files`, `checks_bypassed` (merged with a required check not passing, or an admin override) |
| `coverage.json` | GitHub (coverage artifact) or the CI coverage tool | Latest main-branch coverage report | `files[path]` = true when any line is hit (lcov `LH > 0`) |
| `ci_runs.json` | mabl, plus GitHub Actions | Main-branch runs with rerun outcomes; E2E plan results; quarantined tests | `flaky_failures` = tests that failed then passed on rerun of the same commit; `e2e_quarantine[].critical_path` from the test's labels or plan |
| `requirements.json` | Jira (with Xray, Zephyr or issue links) | Stories in the release with linked tests and last result | `linked_tests` from test links; `last_result` from the latest execution; `services_reporting` = services whose projects export links |
| `incidents.json` | Sentry for escaped defects; Jira, PagerDuty or incident.io for incidents and postmortems | Incidents in the last two windows; postmortem action items | `escaped_defect` = Sentry issue first seen in a released version; `detected_by` = `customer` when a support ticket or customer report opened it; actions from postmortem tickets |
| `slo_alerts.json` | Honeycomb (or Datadog, Grafana) | SLOs with current and previous burn rate and budget left | `burn_rate.current/previous`, `budget_remaining_pct`, `window_days` |
| `service_map.json` | Honeycomb traces, a service catalog, or contract-test results | Service-to-service edges with test counts | `integration_tests`, `contract_tests` per edge |

**Known gap:** The Moon needs to know whether a customer or an alert found each incident first. Sentry alone usually cannot say. It comes from support tickets in Jira or the incident tool. Without that source, The Moon stays clouded.

## Two ways to run in CI

| Mode | What runs | Needs |
| --- | --- | --- |
| **Lite** | The GitHub Action in this repo: `action/collect_github.py` gathers PR files and checks with the GitHub CLI, then the engine reads offline and posts one comment | Nothing beyond the workflow token. Other files come from an optional `data-dir` of exports |
| **Full** | The Claude Code GitHub Action, configured with the MCP servers above, follows this skill: gather, validate, read, post | An API key and read-only connector tokens stored as repository secrets. Follow the action's own documentation for MCP configuration |

Both modes end in the same offline engine, so the same data gives the same reading either way.

## Where a reading can go

| Destination | Status | Notes |
| --- | --- | --- |
| GitHub PR comment | **Built** | One comment per PR, edited in place. Fork PRs go to the workflow summary |
| Claude artifact | **Built** (interactive) | Publish `reading.html` as an artifact for the full visual reading with SVG cards. Private until you share it |
| Workflow artifact | **Built** (CI) | The full HTML reading is attached to every run and linked from the comment |
| Jira comment | Possible, not built | With a Jira connector, the agent could post the same text as a comment on the issue linked to the PR |
| Slack message | Possible, not built | With a Slack connector, the agent could send the summary line and spread to a channel |

Any new destination follows the same rules: one message per reading, updated rather than repeated; a human approves before it is sent; it carries the reading, not raw data; and it never names people. Do not auto-link a private Claude artifact from a shared place: teammates would hit a dead link, and sharing it could expose data outside the repo's permissions.
