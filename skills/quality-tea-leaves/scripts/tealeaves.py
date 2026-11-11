"""Quality Tea Leaves: deterministic, evidence-backed tarot readings of software quality.

Read-only. No network. Reads JSON sources from a data folder and writes a reading.
Every card is decided by a rule over the data. A card without enough evidence is
clouded and withheld; it is never guessed. The same data always gives the same
reading.

Usage:
  python tealeaves.py demo [--out DIR]
  python tealeaves.py read --data DIR [--out DIR] [--as-of 2026-11-10T00:00:00Z]

Quality Tea Leaves, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DECK_PATH = SKILL_DIR / "assets" / "deck.json"
DEMO_DIR = SKILL_DIR / "assets" / "demo"
SOURCES = ["manifest", "ci_runs", "pull_requests", "coverage", "incidents", "requirements", "service_map", "slo_alerts"]
SLOTS = [("past", "Past", "lagging"), ("present", "Present", "current"), ("next", "Next Release", "leading")]
CONFIDENCE = {3: "HIGH", 2: "MEDIUM", 1: "LOW"}


class Clouded(Exception):
    """Raised by a rule when the evidence is missing, stale or too thin."""

    def __init__(self, *missing):
        super().__init__("; ".join(missing))
        self.missing = list(missing)


def parse_ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_deck():
    return json.loads(DECK_PATH.read_text())


def load_sources(data_dir):
    data_dir = Path(data_dir)
    found = {}
    for name in SOURCES:
        path = data_dir / f"{name}.json"
        if path.exists():
            found[name] = json.loads(path.read_text())
    return found


def need(sources, name):
    if name not in sources:
        raise Clouded(f"{name}.json not provided")
    return sources[name]


def in_window(stamp, as_of, days, back=0):
    """True when stamp falls in (as_of - (back+1)*days, as_of - back*days]."""
    t = parse_ts(stamp)
    end = as_of - timedelta(days=days * back)
    return end - timedelta(days=days) < t <= end


def pct(part, whole):
    return 100.0 * part / whole if whole else 0.0


def confidence(sample, min_sample, margin):
    s = 3 if sample >= 4 * min_sample else 2 if sample >= 2 * min_sample else 1
    m = 3 if margin >= 2 else 2 if margin >= 1.3 else 1
    return CONFIDENCE[min(s, m)]


def judge(card, current, previous, sample, evidence):
    """Shared upright / reversed / quiet decision for threshold cards."""
    threshold = card["threshold"]
    min_sample = card["min_sample"]
    if sample < min_sample:
        raise Clouded(f"Sample: {sample} (need {min_sample})")

    def strength(value):
        return value / threshold if threshold else float(value)

    if current > threshold:
        s = strength(current)
        return {"state": "upright", "strength": round(s, 3), "confidence": confidence(sample, min_sample, s), "evidence": evidence}
    if previous is not None and previous > threshold:
        s = strength(previous)
        return {"state": "reversed", "strength": round(s, 3), "confidence": confidence(sample, min_sample, s), "evidence": evidence}
    return {"state": "quiet", "strength": 0.0, "confidence": None, "evidence": evidence}


def fmt(value, unit):
    if unit == "%":
        return f"{value:.1f}%"
    if unit == "x burn":
        return f"{value:.1f}x"
    return f"{value:g}"


# ---------------------------------------------------------------- card rules

def rule_fool(card, src, as_of):
    prs = need(src, "pull_requests")["pull_requests"]
    covered = need(src, "coverage")["files"]
    w = card["window_days"]

    def untested_share(back):
        merged = [p for p in prs if p.get("merged_at") and in_window(p["merged_at"], as_of, w, back)]
        risky = [p for p in merged if any(not covered.get(f, False) for f in p["files"])]
        return merged, risky

    merged, risky = untested_share(0)
    prev_merged, prev_risky = untested_share(1)
    cur, prev = pct(len(risky), len(merged)), pct(len(prev_risky), len(prev_merged)) if prev_merged else None
    files = sorted({f for p in risky for f in p["files"] if not covered.get(f, False)})
    ev = [f"Untested merges: {len(risky)} of {len(merged)} ({cur:.1f}%)", f"Threshold: {card['threshold']}%",
          f"Window: {w} days"] + ([f"Untested file: {files[0]}"] if files else [])
    return judge(card, cur, prev, len(merged), ev)


def rule_emperor(card, src, as_of):
    prs = need(src, "pull_requests")["pull_requests"]
    w = card["window_days"]
    merged = [p for p in prs if p.get("merged_at") and in_window(p["merged_at"], as_of, w)]
    prev = [p for p in prs if p.get("merged_at") and in_window(p["merged_at"], as_of, w, 1)]
    bypass = [p for p in merged if p.get("checks_bypassed")]
    prev_bypass = [p for p in prev if p.get("checks_bypassed")]
    ev = [f"Checks bypassed: {len(bypass)} of {len(merged)} merges", "Threshold: 0 allowed", f"Window: {w} days"]
    if bypass:
        ev.append(f"Example: PR #{bypass[0]['number']} ({bypass[0].get('bypass_method') or 'unknown'})")
    return judge(card, len(bypass), len(prev_bypass) if prev else None, len(merged), ev)


def rule_hierophant(card, src, as_of):
    req = need(src, "requirements")
    missing = []
    reporting, total = req.get("services_reporting", 0), req.get("services_total", 0)
    need_services = min(card["min_sample"], total) if total else card["min_sample"]
    if reporting < need_services:
        missing.append(f"Services reporting: {reporting} of {total} (need {need_services})")
    age = (as_of - parse_ts(req["exported_at"])).days
    if age > card["max_age_days"]:
        missing.append(f"Traceability export: {age} days old (max {card['max_age_days']})")
    if missing:
        raise Clouded(*missing, "To read: link requirements to tests")
    items = req["requirements"]
    unproven = [r for r in items if not r["linked_tests"] or r.get("last_result") != "passed"]
    cur = pct(len(unproven), len(items))
    prev = req.get("previous_unproven_pct")
    ev = [f"Unproven requirements: {len(unproven)} of {len(items)} ({cur:.1f}%)", f"Threshold: {card['threshold']}%",
          f"Services reporting: {reporting} of {total}"]
    return judge(card, cur, prev, reporting, ev)


def rule_hermit(card, src, as_of):
    edges = need(src, "service_map")["edges"]
    bare = [e for e in edges if not e.get("integration_tests")]
    cur = pct(len(bare), len(edges))
    ev = [f"Untested borders: {len(bare)} of {len(edges)} ({cur:.1f}%)", f"Threshold: {card['threshold']}%"]
    if bare:
        ev.append(f"Example: {bare[0]['from']} to {bare[0]['to']}")
    return judge(card, cur, src["service_map"].get("previous_untested_pct"), len(edges), ev)


def rule_hanged_man(card, src, as_of):
    ci = need(src, "ci_runs")
    w = card["window_days"]
    main = [r for r in ci["runs"] if r["branch"] == "main"]
    cur_runs = [r for r in main if in_window(r["started_at"], as_of, w)]
    prev_runs = [r for r in main if in_window(r["started_at"], as_of, w, 1)]

    def pass_rate(runs):
        total = sum(r["e2e"]["total"] for r in runs)
        return pct(sum(r["e2e"]["passed"] for r in runs), total) if total else None

    stuck = [q for q in ci.get("e2e_quarantine", []) if q.get("critical_path")]
    cur_rate, prev_rate = pass_rate(cur_runs), pass_rate(prev_runs)
    drop = (prev_rate - cur_rate) if (cur_rate is not None and prev_rate is not None) else 0.0
    drop_strength = drop / card["pass_rate_drop_points"] if drop > card["pass_rate_drop_points"] else 0.0
    value = max(len(stuck), drop_strength)
    ev = [f"Critical E2E quarantined: {len(stuck)}", f"E2E pass rate: {cur_rate:.1f}%" if cur_rate is not None else "E2E pass rate: none",
          f"Window: {w} days, {len(cur_runs)} runs"]
    if stuck:
        ev.append(f"Example: {stuck[0]['test']}")
    return judge(card, value, src["ci_runs"].get("previous_critical_quarantined"), len(cur_runs), ev)


def rule_death(card, src, as_of):
    slos = need(src, "slo_alerts")["slos"]
    if not slos:
        raise Clouded("No SLOs defined")
    burning = sorted(slos, key=lambda s: (-s["burn_rate"]["current"], s["name"]))[0]
    target = burning
    if burning["burn_rate"]["current"] <= card["threshold"]:
        target = sorted(slos, key=lambda s: (-s["burn_rate"].get("previous", 0), s["name"]))[0]
    br, bud = target["burn_rate"], target.get("budget_remaining_pct", {})
    ev = [f"SLO: {target['name']}"[:40], f"Burn rate: {br['current']:.1f}x (was {br.get('previous', 0):.1f}x)",
          f"Budget left: {bud.get('current', '?')}% (was {bud.get('previous', '?')}%)",
          f"Window: {target['window_days']} days"]
    return judge(card, br["current"], br.get("previous"), target["window_days"], ev)


def rule_flaky_tower(card, src, as_of):
    runs = [r for r in need(src, "ci_runs")["runs"] if r["branch"] == "main"]
    w = card["window_days"]
    cur = [r for r in runs if in_window(r["started_at"], as_of, w)]
    prev = [r for r in runs if in_window(r["started_at"], as_of, w, 1)]
    flaky = [r for r in cur if r["flaky_failures"]]
    tests = {t for r in cur for t in r["flaky_failures"]}
    total = max((r["tests_total"] for r in cur), default=0)
    rate = pct(len(flaky), len(cur))
    prev_rate = pct(sum(1 for r in prev if r["flaky_failures"]), len(prev)) if prev else None
    ev = [f"Flaky rate on main: {rate:.1f}%", f"Threshold: {card['threshold']}%", f"Tests affected: {len(tests)} of {total:,}",
          f"Window: {w} days, {len(cur)} runs"]
    return judge(card, rate, prev_rate, len(cur), ev)


def rule_star(card, src, as_of):
    incs = need(src, "incidents")["incidents"]
    w = card["window_days"]
    cur = [i for i in incs if in_window(i["opened_at"], as_of, w)]
    prev = [i for i in incs if in_window(i["opened_at"], as_of, w, 1)]
    if len(cur) + len(prev) < card["min_sample"]:
        raise Clouded(f"Incidents: {len(cur) + len(prev)} (need {card['min_sample']})")
    esc, pesc = sum(i["escaped_defect"] for i in cur), sum(i["escaped_defect"] for i in prev)
    ev = [f"Escaped defects: {esc} (was {pesc})", f"Window: {w} days vs prior {w}", f"Incidents: {len(cur)} (was {len(prev)})"]
    sample = len(cur) + len(prev)
    if esc >= card["min_count"] and esc > pesc * card["rise_ratio"]:
        s = esc / max(pesc, 1)
        return {"state": "upright", "strength": round(s, 3), "confidence": confidence(sample, card["min_sample"], s), "evidence": ev}
    if pesc >= card["min_count"] and esc < pesc * card["fall_ratio"]:
        s = pesc / max(esc, 1)
        return {"state": "reversed", "strength": round(s, 3), "confidence": confidence(sample, card["min_sample"], s), "evidence": ev}
    return {"state": "quiet", "strength": 0.0, "confidence": None, "evidence": ev}


def rule_moon(card, src, as_of):
    incs = need(src, "incidents")["incidents"]
    w = card["window_days"]
    cur = [i for i in incs if in_window(i["opened_at"], as_of, w)]
    prev = [i for i in incs if in_window(i["opened_at"], as_of, w, 1)]
    by_customer = sum(i["detected_by"] == "customer" for i in cur)
    prev_customer = sum(i["detected_by"] == "customer" for i in prev)
    cur_pct = pct(by_customer, len(cur))
    prev_pct = pct(prev_customer, len(prev)) if prev else None
    ev = [f"Found by customers first: {by_customer} of {len(cur)}", f"Now {cur_pct:.1f}%, was {prev_pct or 0:.1f}%",
          f"Threshold: {card['threshold']}%", f"Window: {w} days"]
    return judge(card, cur_pct, prev_pct, len(cur), ev)


def rule_judgement(card, src, as_of):
    incs = need(src, "incidents")["incidents"]
    actions = [a for i in incs for a in i.get("postmortem", {}).get("actions", [])]
    overdue = [a for a in actions if not a["done"] and parse_ts(a["due"]) < as_of]
    cur = pct(len(overdue), len(actions))
    ev = [f"Overdue actions: {len(overdue)} of {len(actions)} ({cur:.1f}%)", f"Threshold: {card['threshold']}%"]
    if overdue:
        oldest = min(overdue, key=lambda a: a["due"])
        ev.append(f"Oldest: {oldest['id']}, {(as_of - parse_ts(oldest['due'])).days} days late")
    return judge(card, cur, None, len(actions), ev)


RULES = {
    "fool": rule_fool, "emperor": rule_emperor, "hierophant": rule_hierophant, "hermit": rule_hermit,
    "hanged_man": rule_hanged_man, "death": rule_death, "flaky_tower": rule_flaky_tower, "star": rule_star,
    "moon": rule_moon, "judgement": rule_judgement,
}


# ---------------------------------------------------------------- reading

def read_card(card, deck, sources, as_of):
    base = {k: card[k] for k in ("id", "number", "numeral", "name", "signal", "slot", "source")}
    try:
        result = RULES[card["id"]](card, sources, as_of)
    except Clouded as c:
        return {**base, "state": "clouded", "strength": 0.0, "confidence": None, "evidence": [], "missing": c.missing,
                "prophecy": deck["clouded_prophecy"]}
    prophecy = card["prophecy"].get(result["state"]) if result["state"] in ("upright", "reversed") else None
    return {**base, **result, "missing": [], "prophecy": prophecy}


def choose_spread(cards):
    """Deterministic: strongest drawn card per slot, else a clouded card, else nothing."""
    spread = []
    for key, label, slot in SLOTS:
        pool = [c for c in cards if c["slot"] == slot]
        drawn = sorted((c for c in pool if c["state"] in ("upright", "reversed")), key=lambda c: (-c["strength"], c["number"]))
        clouded = sorted((c for c in pool if c["state"] == "clouded"), key=lambda c: c["number"])
        pick = drawn[0] if drawn else (clouded[0] if clouded else None)
        spread.append({"position": key, "label": label, "card": pick["id"] if pick else None})
    return spread


def summary_line(deck, cards, spread):
    by_id = {c["id"]: c for c in cards}
    omens = {c["id"]: c["omen"] for c in deck["cards"]}
    parts = []
    for slot in spread:
        c = by_id.get(slot["card"])
        if c is None:
            phrase = "the leaves are still"
        elif c["state"] == "clouded":
            phrase = f"the road {deck['clouded_omen']}" if slot["position"] == "next" else f"{c['name']} {deck['clouded_omen']}"
        else:
            phrase = omens[c["id"]][c["state"]]
        parts.append(phrase)
    return f"In the past, {parts[0]}; in the present, {parts[1]}; and for the next release, {parts[2]}."


def read(data_dir, as_of=None):
    deck = load_deck()
    sources = load_sources(data_dir)
    manifest = sources.get("manifest", {})
    if as_of is None:
        as_of = manifest.get("as_of")
    as_of_dt = parse_ts(as_of) if as_of else datetime.now(timezone.utc).replace(microsecond=0)
    cards = [read_card(card, deck, sources, as_of_dt) for card in deck["cards"]]
    spread = choose_spread(cards)
    return {
        "deck": deck["deck"],
        "deck_version": deck["version"],
        "subject": manifest.get("subject", "unnamed system"),
        "release": manifest.get("release"),
        "as_of": as_of_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": sorted(sources),
        "summary": summary_line(deck, cards, spread),
        "spread": spread,
        "cards": cards,
        "counts": {s: sum(c["state"] == s for c in cards) for s in ("upright", "reversed", "quiet", "clouded")},
        "review": {"status": "pending_human_review",
                   "note": "Advisory only. A human reviews this reading before it is shared or acted on."},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evidence-backed tarot readings of software quality.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    demo = sub.add_parser("demo", help="Read the bundled fictional checkout platform")
    demo.add_argument("--out", default="reading")
    rd = sub.add_parser("read", help="Read your own data folder")
    rd.add_argument("--data", required=True)
    rd.add_argument("--out", default="reading")
    rd.add_argument("--as-of", default=None, help="ISO time to read at; defaults to manifest.json as_of, else now")
    args = parser.parse_args(argv)

    data_dir = DEMO_DIR if args.cmd == "demo" else Path(args.data)
    if not data_dir.is_dir():
        print(f"Data folder not found: {data_dir}", file=sys.stderr)
        return 2
    reading = read(data_dir, getattr(args, "as_of", None))

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import render  # local module, no third-party dependencies
    out = render.write_all(reading, load_deck(), Path(args.out))
    print(render.console(reading))
    print(f"\nWrote {', '.join(str(p) for p in out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
