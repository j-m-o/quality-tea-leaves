"""Generate the fictional demo data for Quality Tea Leaves.

Everything here is synthetic: a made-up checkout platform, made-up people and
made-up numbers. The output is checked in, so you only need to run this if you
change the scenario. Seeded, so the same files come out every time.

Quality Tea Leaves, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "skills" / "quality-tea-leaves" / "assets" / "demo"
AS_OF = datetime(2026, 11, 10, tzinfo=timezone.utc)
rng = random.Random(4316)


def ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def spread_times(n, start_days_ago, end_days_ago):
    """n timestamps evenly spread between two points in the past, oldest first."""
    start = AS_OF - timedelta(days=start_days_ago)
    span = timedelta(days=start_days_ago - end_days_ago).total_seconds()
    return [start + timedelta(seconds=span * (i + 0.5) / n) for i in range(n)]


def ci_runs():
    tests_total = 1204
    runs = []

    def window(n, start, end, flaky_plan, prefix):
        for i, t in enumerate(spread_times(n, start, end)):
            e2e_failed = 1 if i % 37 == 0 else 0
            runs.append({
                "id": f"{prefix}-{i + 1:04d}",
                "branch": "main",
                "commit": f"{rng.getrandbits(40):010x}",
                "started_at": ts(t),
                "tests_total": tests_total,
                "flaky_failures": flaky_plan.get(i, []),
                "real_failures": [],
                "e2e": {"total": 86, "passed": 84 - e2e_failed, "failed": e2e_failed, "skipped": 2},
            })

    # Current 14 days: 312 runs, 24 with a flaky failure, 41 distinct flaky tests.
    pool = [f"test_{name}_{v}" for name in (
        "cart_total", "promo_apply", "address_lookup", "tax_calc", "payment_retry", "session_refresh",
         "inventory_hold", "shipping_quote", "gift_card", "receipt_email", "order_status", "refund_flow",
         "currency_format", "wishlist_sync", "coupon_expiry", "search_suggest", "login_mfa", "basket_merge",
         "price_rounding", "stock_alert", "checkout_timeout") for v in ("a", "b")][:41]
    picks = sorted(rng.sample(range(312), 24))
    plan, cursor = {}, 0
    for j, run_index in enumerate(picks):
        size = 2 if j < 17 else 1
        plan[run_index] = pool[cursor:cursor + size]
        cursor += size
    window(312, 14, 0, plan, "run")

    # Previous 14 days: 290 runs, 6 with a flaky failure.
    prev_picks = sorted(rng.sample(range(290), 6))
    window(290, 28, 14, {i: [pool[k]] for k, i in enumerate(prev_picks)}, "prev")

    # Feature-branch noise the reading must ignore.
    for i, t in enumerate(spread_times(40, 14, 0)):
        runs.append({"id": f"feat-{i + 1:03d}", "branch": f"feature/demo-{i % 5}", "commit": f"{rng.getrandbits(40):010x}",
                     "started_at": ts(t), "tests_total": tests_total, "flaky_failures": ["test_cart_total_a"] if i % 2 else [],
                     "real_failures": [], "e2e": {"total": 86, "passed": 80, "failed": 6, "skipped": 0}})

    quarantine = [
        {"test": "e2e_guest_checkout_card", "critical_path": True, "since": ts(AS_OF - timedelta(days=9))},
        {"test": "e2e_apple_pay_confirm", "critical_path": True, "since": ts(AS_OF - timedelta(days=4))},
        {"test": "e2e_wishlist_share", "critical_path": False, "since": ts(AS_OF - timedelta(days=20))},
    ]
    return {"runs": runs, "e2e_quarantine": quarantine}


AUTHORS = ["avery.lane", "bo.okafor", "casey.ruiz", "dana.whitfield", "eli.marsh", "fran.ito"]
UNCOVERED = ["src/checkout/promo_rules.py", "src/payments/retry_policy.py", "src/cart/legacy_tax.py"]
COVERED = [f"src/{area}/{name}.py" for area in ("checkout", "cart", "payments", "shipping", "accounts")
           for name in ("api", "service", "models", "validators")]


def pull_requests():
    prs, number = [], 4100

    def window(n, start, end, uncovered_at, bypass_at):
        nonlocal number
        for i, t in enumerate(spread_times(n, start, end)):
            number += 1
            files = rng.sample(COVERED, 3)
            if i in uncovered_at:
                files.append(UNCOVERED[uncovered_at.index(i) % len(UNCOVERED)])
            prs.append({"number": number, "merged_at": ts(t), "author": AUTHORS[i % len(AUTHORS)],
                        "files": sorted(files), "checks_bypassed": i in bypass_at,
                        "bypass_method": "admin_override" if i in bypass_at else None})

    window(45, 28, 14, [7, 30], [])
    window(50, 14, 0, [5, 22, 41], [33])
    return {"pull_requests": prs}


def coverage():
    files = {f: True for f in COVERED}
    files.update({f: False for f in UNCOVERED})
    return {"generated_at": ts(AS_OF - timedelta(days=1)), "files": dict(sorted(files.items()))}


def incidents():
    items = []

    def add(n, start, end, escaped_at, customer_at, prefix):
        for i, t in enumerate(spread_times(n, start, end)):
            items.append({"id": f"{prefix}-{i + 1:02d}", "opened_at": ts(t), "severity": "SEV2" if i % 3 else "SEV3",
                          "service": ["checkout", "payments", "cart", "shipping"][i % 4],
                          "detected_by": "customer" if i in customer_at else "alert",
                          "escaped_defect": i in escaped_at, "postmortem": {"actions": []}})

    add(8, 56, 28, [1, 4, 6], [0, 3, 5], "INC-P")
    add(9, 28, 0, [2, 7], [4, 8], "INC")

    # 20 postmortem actions; 6 overdue (open and past due).
    plan = ["done"] * 10 + ["overdue"] * 6 + ["open_future"] * 4
    for k, state in enumerate(plan):
        inc = items[k % len(items)]
        opened = datetime.fromisoformat(inc["opened_at"].replace("Z", "+00:00"))
        if state == "done":
            due, done = opened + timedelta(days=14), True
        elif state == "overdue":
            due, done = AS_OF - timedelta(days=3 + k), False
        else:
            due, done = AS_OF + timedelta(days=7 + k), False
        inc["postmortem"]["actions"].append({"id": f"ACT-{k + 1:02d}", "due": ts(due), "done": done,
                                             "owner_team": inc["service"]})
    return {"incidents": items}


def requirements():
    reqs = [
        {"id": "REQ-101", "service": "checkout", "text": "Guest checkout completes with a saved card", "linked_tests": ["e2e_guest_checkout_card"], "last_result": "quarantined"},
        {"id": "REQ-102", "service": "checkout", "text": "Promo codes apply before tax", "linked_tests": [], "last_result": None},
        {"id": "REQ-201", "service": "payments", "text": "Declined cards retry once with backoff", "linked_tests": ["test_payment_retry_a"], "last_result": "passed"},
        {"id": "REQ-202", "service": "payments", "text": "Apple Pay confirmation under 3 seconds", "linked_tests": ["e2e_apple_pay_confirm"], "last_result": "quarantined"},
    ]
    return {"exported_at": ts(AS_OF - timedelta(days=41)), "services_total": 9, "services_reporting": 2, "requirements": reqs}


def service_map():
    services = ["web", "checkout", "cart", "payments", "pricing", "inventory", "shipping", "accounts", "notifications"]
    edges = [("web", "checkout"), ("web", "cart"), ("web", "accounts"), ("checkout", "cart"), ("checkout", "payments"),
             ("checkout", "pricing"), ("checkout", "shipping"), ("cart", "pricing"), ("cart", "inventory"),
             ("payments", "notifications"), ("shipping", "inventory"), ("accounts", "notifications")]
    out = []
    for a, b in edges:
        untested = (a, b) == ("payments", "notifications")
        out.append({"from": a, "to": b, "integration_tests": 0 if untested else rng.randint(3, 14),
                    "contract_tests": 0 if untested else rng.randint(1, 6)})
    return {"services": services, "edges": out}


def slo_alerts():
    return {
        "slos": [
            {"name": "checkout-availability", "service": "checkout", "window_days": 28,
             "burn_rate": {"current": 0.8, "previous": 3.1}, "budget_remaining_pct": {"current": 64, "previous": 9}},
            {"name": "payments-latency-p95", "service": "payments", "window_days": 28,
             "burn_rate": {"current": 0.4, "previous": 0.5}, "budget_remaining_pct": {"current": 81, "previous": 77}},
        ],
        "alerts": [
            {"name": "checkout-5xx-rate", "muted": False},
            {"name": "payments-timeout", "muted": False},
            {"name": "inventory-lag", "muted": True},
        ],
    }


def manifest():
    return {"subject": "checkout-platform (fictional)", "release": "4.3", "as_of": ts(AS_OF),
            "note": "Synthetic demo data. No real company, system or person."}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("manifest", manifest), ("ci_runs", ci_runs), ("pull_requests", pull_requests), ("coverage", coverage),
                     ("incidents", incidents), ("requirements", requirements), ("service_map", service_map),
                     ("slo_alerts", slo_alerts)]:
        (OUT / f"{name}.json").write_text(json.dumps(fn(), indent=1) + "\n")
    print(f"Wrote demo data to {OUT}")


if __name__ == "__main__":
    main()
