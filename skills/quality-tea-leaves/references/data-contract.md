# Data contract

Put these JSON files in one folder and pass it with `--data`. Every file is optional: a card whose source is missing is clouded, not guessed. Timestamps are ISO 8601 in UTC (`2026-11-10T00:00:00Z`). See `assets/demo/` for a complete fictional example.

## manifest.json

```json
{"subject": "checkout-platform", "release": "4.3", "as_of": "2026-11-10T00:00:00Z"}
```

`as_of` fixes the reading time so readings are reproducible. Without it the script reads at the current time (or `--as-of`).

## ci_runs.json

```json
{
  "runs": [
    {"id": "run-0001", "branch": "main", "commit": "a1b2c3", "started_at": "...", "tests_total": 1204,
     "flaky_failures": ["test_cart_total_a"], "real_failures": [],
     "e2e": {"total": 86, "passed": 84, "failed": 0, "skipped": 2}}
  ],
  "e2e_quarantine": [{"test": "e2e_guest_checkout_card", "critical_path": true, "since": "..."}]
}
```

A flaky failure is a test that failed and then passed on rerun of the same commit. Most CI tools can export this; the Flaky Test Investigator skill produces it.

## pull_requests.json

```json
{"pull_requests": [{"number": 4101, "merged_at": "...", "author": "someone", "files": ["src/cart/api.py"],
  "checks_bypassed": false, "bypass_method": null}]}
```

`author` may be present in exports. The reading never prints it.

## coverage.json

```json
{"generated_at": "...", "files": {"src/cart/api.py": true, "src/cart/legacy_tax.py": false}}
```

A file is covered if any test exercises it. Files missing from the map count as uncovered.

## incidents.json

```json
{"incidents": [{"id": "INC-01", "opened_at": "...", "severity": "SEV2", "service": "checkout",
  "detected_by": "alert", "escaped_defect": true,
  "postmortem": {"actions": [{"id": "ACT-01", "due": "...", "done": false, "owner_team": "checkout"}]}}]}
```

`detected_by` is `alert` or `customer`. Action owners are teams, not people.

## requirements.json

```json
{"exported_at": "...", "services_total": 9, "services_reporting": 2,
 "requirements": [{"id": "REQ-101", "service": "checkout", "text": "...", "linked_tests": ["e2e_guest_checkout_card"],
   "last_result": "passed"}]}
```

## service_map.json

```json
{"services": ["web", "checkout"], "edges": [{"from": "web", "to": "checkout", "integration_tests": 6, "contract_tests": 2}]}
```

## slo_alerts.json

```json
{"slos": [{"name": "checkout-availability", "service": "checkout", "window_days": 28,
  "burn_rate": {"current": 0.8, "previous": 3.1}, "budget_remaining_pct": {"current": 64, "previous": 9}}],
 "alerts": [{"name": "checkout-5xx-rate", "muted": false}]}
```

`alerts` is read in v1.1 by The Devil (silenced alerts).
