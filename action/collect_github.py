"""Collect pull request facts for Quality Tea Leaves inside GitHub Actions (the Lite mode).

This is the only part of the GitHub Action that touches the network, through the
GitHub CLI with the workflow's read token. It writes pr.json (no author), an
optional coverage.json converted from lcov, and a manifest with provenance, into
one folder alongside any data exports the team provides. The reading engine then
works offline on that folder.

Quality Tea Leaves, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gh_lines(*args):
    out = subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def build_pr(event, filenames, check_rows, required_names):
    """Pure: shape the PR facts. The author is deliberately left out."""
    pr = event["pull_request"]
    required = {n.strip() for n in required_names if n.strip()}
    checks = []
    for name, conclusion in check_rows:
        checks.append({"name": name, "required": name in required,
                       "conclusion": None if conclusion in ("", "null", "pending") else conclusion})
    return {"number": pr["number"], "title": pr.get("title", ""), "url": pr.get("html_url", ""),
            "head_sha": pr["head"]["sha"], "base": pr["base"]["ref"], "files": sorted(set(filenames)), "checks": checks}


def lcov_to_coverage(text, strip_prefix=""):
    """Pure: a file counts as covered when lcov reports at least one line hit."""
    files, current, hits = {}, None, 0
    for line in text.splitlines():
        if line.startswith("SF:"):
            current, hits = line[3:].strip(), 0
            if strip_prefix and current.startswith(strip_prefix):
                current = current[len(strip_prefix):].lstrip("/")
        elif line.startswith("LH:"):
            hits = int(line[3:] or 0)
        elif line.strip() == "end_of_record" and current:
            files[current] = files.get(current, False) or hits > 0
            current = None
    return {"generated_at": now(), "files": dict(sorted(files.items()))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default="")
    ap.add_argument("--lcov", default="")
    ap.add_argument("--required-checks", default="")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    if args.data_dir and Path(args.data_dir).is_dir():
        for path in Path(args.data_dir).glob("*.json"):
            shutil.copy(path, out / path.name)
        if (out / "manifest.json").exists():
            manifest = json.loads((out / "manifest.json").read_text())

    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if "pull_request" not in event:
        raise SystemExit("Quality Tea Leaves runs on pull_request events.")
    repo = os.environ["GITHUB_REPOSITORY"]
    number, sha = event["pull_request"]["number"], event["pull_request"]["head"]["sha"]

    files = gh_lines(f"repos/{repo}/pulls/{number}/files", "--paginate", "--jq", ".[].filename")
    rows = [tuple((r.split("\t") + [""])[:2]) for r in gh_lines(
        f"repos/{repo}/commits/{sha}/check-runs", "--paginate",
        "--jq", '.check_runs[] | [.name, (.conclusion // "pending")] | @tsv')]
    # Leave out this workflow's own check so the reading does not judge itself.
    own = os.environ.get("GITHUB_JOB", "")
    rows = [r for r in rows if r[0] != own]
    pr = build_pr(event, files, rows, args.required_checks.split(","))
    (out / "pr.json").write_text(json.dumps(pr, indent=1) + "\n")

    prov = manifest.setdefault("provenance", {})
    prov["pr"] = {"connector": "GitHub", "query": f"PR #{number} files and check runs at {sha[:7]}",
                  "pulled_at": now(), "records": len(files) + len(rows)}
    if args.lcov and Path(args.lcov).is_file():
        cov = lcov_to_coverage(Path(args.lcov).read_text(), os.environ.get("GITHUB_WORKSPACE", ""))
        (out / "coverage.json").write_text(json.dumps(cov, indent=1) + "\n")
        prov["coverage"] = {"connector": "GitHub (lcov)", "query": args.lcov, "pulled_at": now(), "records": len(cov["files"])}
    manifest.setdefault("subject", repo)
    manifest.setdefault("as_of", now())
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"Collected PR #{number}: {len(files)} files, {len(rows)} checks")


if __name__ == "__main__":
    main()
