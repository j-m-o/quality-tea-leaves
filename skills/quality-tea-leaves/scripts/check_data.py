"""Data contract checker for Quality Tea Leaves.

Agents and collectors write the JSON files; this checks their shape before the
engine reads them. A file that fails is set aside, and every card that needs it
is clouded with a reason. Nothing is guessed or repaired.

Usage: python check_data.py path/to/data   (exit 1 when any file fails)

Quality Tea Leaves, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# file: (list key or None, required record fields, timestamp fields, required top-level keys)
CONTRACT = {
    "ci_runs": ("runs", ["id", "branch", "started_at", "tests_total", "flaky_failures", "e2e"], ["started_at"], []),
    "pull_requests": ("pull_requests", ["number", "files"], [], []),
    "coverage": (None, [], [], ["files"]),
    "incidents": ("incidents", ["id", "opened_at", "detected_by", "escaped_defect"], ["opened_at"], []),
    "requirements": ("requirements", ["id", "linked_tests"], [], ["exported_at", "services_total", "services_reporting"]),
    "service_map": ("edges", ["from", "to", "integration_tests"], [], []),
    "slo_alerts": ("slos", ["name", "window_days", "burn_rate"], [], []),
    "pr": ("checks", ["name", "conclusion"], [], ["number", "files"]),
}
MAX_PROBLEMS = 3


def _is_time(value):
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def check(name, data):
    """Return a short list of problems for one source; empty means it passes."""
    if name not in CONTRACT:
        return []
    list_key, fields, times, top = CONTRACT[name]
    problems = []
    if not isinstance(data, dict):
        return ["top level must be an object"]
    for key in top:
        if key not in data:
            problems.append(f"missing top-level key '{key}'")
    if name == "requirements" and "exported_at" in data and not _is_time(data["exported_at"]):
        problems.append("exported_at is not an ISO time")
    if list_key:
        records = data.get(list_key)
        if not isinstance(records, list):
            problems.append(f"'{list_key}' must be a list")
        else:
            for i, rec in enumerate(records):
                if not isinstance(rec, dict):
                    problems.append(f"{list_key}[{i}] is not an object")
                    continue
                gone = [f for f in fields if f not in rec]
                if gone:
                    problems.append(f"{list_key}[{i}] missing {', '.join(gone)}")
                for t in times:
                    if t in rec and not _is_time(rec[t]):
                        problems.append(f"{list_key}[{i}].{t} is not an ISO time")
                if len(problems) >= MAX_PROBLEMS:
                    break
    return problems[:MAX_PROBLEMS]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    folder = Path(argv[0])
    failed = 0
    for name in CONTRACT:
        path = folder / f"{name}.json"
        if not path.exists():
            print(f"  -  {name}.json not provided")
            continue
        try:
            problems = check(name, json.loads(path.read_text()))
        except ValueError as e:
            problems = [f"not valid JSON ({e})"]
        if problems:
            failed += 1
            print(f"FAIL {name}.json: " + "; ".join(problems))
        else:
            print(f"OK   {name}.json")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
