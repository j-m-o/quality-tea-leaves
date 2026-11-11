# Changelog

## 1.1.0 (2026-11-11)

- **PR mode.** `tealeaves.py pr` and `demo-pr`. The Fool and The Emperor read the pull request (untested source files it changes, required checks not passing); every other card reads the repo.
- **PR comment.** `comment.md`: one advisory comment with the spread, a folded full deck and a provenance table. Edited in place on every push.
- **GitHub Action.** `action.yml` with a collector (PR files, check runs, optional lcov) and a poster (single sticky comment, fork PRs go to the workflow summary, no `pull_request_target`). Example workflow in `examples/`.
- **Gathering guide.** How an agent fills the data contract from GitHub, mabl, Jira, Sentry and Honeycomb: raw records only, read-only, no people, provenance per file. Jira and Slack destinations documented, not built.
- **Data contract checker.** `check_data.py`. Malformed files are set aside and their cards cloud with a reason.
- **Provenance.** `manifest.json` records the connector, query, time and record count for each file; readings carry it through.

## 1.0.0 (2026-11-11)

- Ten-card deck, deterministic rules, three-card spread, SVG cards, HTML and Markdown readings, synthetic demo, agent definition, tests and CI.
