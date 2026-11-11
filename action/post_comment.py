"""Post or update the single Quality Tea Leaves comment on a pull request.

One comment per PR, found by its hidden marker and edited in place on every push.
Fork PRs get a read-only token from GitHub, so for them the reading goes to the
workflow summary instead. This script never uses pull_request_target and never
runs code from the PR with a write token.

Quality Tea Leaves, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

MARKER = "<!-- quality-tea-leaves -->"


def is_fork(event):
    pr = event.get("pull_request", {})
    head = (pr.get("head", {}).get("repo") or {}).get("full_name")
    return head is not None and head != event.get("repository", {}).get("full_name")


def find_existing(comments):
    """Pure: the bot comment that carries the marker, if any. Human comments quoting it are ignored."""
    for c in comments:
        if c.get("body", "").startswith(MARKER) and (c.get("user") or {}).get("type") == "Bot":
            return c["id"]
    return None


def with_run_link(body):
    server, repo, run = (os.environ.get(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    if server and repo and run:
        body += f"\n<sub>Full visual reading with the SVG cards: [workflow run artifacts]({server}/{repo}/actions/runs/{run})</sub>\n"
    return body


def gh(*args, payload=None):
    return subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True,
                          input=json.dumps(payload) if payload is not None else None).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", required=True)
    args = ap.parse_args()
    body = with_run_link(Path(args.body).read_text())
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())

    if is_fork(event):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(body)
        print("Fork PR: reading written to the workflow summary instead of a comment.")
        return

    repo, number = os.environ["GITHUB_REPOSITORY"], event["pull_request"]["number"]
    comments = []
    for line in gh(f"repos/{repo}/issues/{number}/comments", "--paginate", "--jq", ".[] | @json").splitlines():
        if line.strip():
            comments.append(json.loads(line))
    existing = find_existing(comments)
    if existing:
        gh(f"repos/{repo}/issues/comments/{existing}", "-X", "PATCH", "--input", "-", payload={"body": body})
        print(f"Updated comment {existing}")
    else:
        gh(f"repos/{repo}/issues/{number}/comments", "-X", "POST", "--input", "-", payload={"body": body})
        print("Posted reading comment")


if __name__ == "__main__":
    main()
