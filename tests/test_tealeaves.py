"""Tests for Quality Tea Leaves. Run: python -m unittest discover -s tests -v"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "quality-tea-leaves"
sys.path.insert(0, str(SKILL / "scripts"))
import render  # noqa: E402
import tealeaves  # noqa: E402

DEMO = SKILL / "assets" / "demo"
EXPECTED = {
    "fool": "quiet", "emperor": "upright", "hierophant": "clouded", "hermit": "quiet", "hanged_man": "upright",
    "death": "reversed", "flaky_tower": "upright", "star": "reversed", "moon": "reversed", "judgement": "upright",
}


def demo_copy():
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(DEMO, tmp / "data")
    return tmp / "data"


class DemoReading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reading = tealeaves.read(DEMO)
        cls.by_id = {c["id"]: c for c in cls.reading["cards"]}

    def test_every_card_matches_expected_state(self):
        self.assertEqual(len(self.reading["cards"]), 10)
        for cid, state in EXPECTED.items():
            with self.subTest(card=cid):
                self.assertEqual(self.by_id[cid]["state"], state)

    def test_spread_is_death_tower_hierophant(self):
        picks = [(s["position"], s["card"]) for s in self.reading["spread"]]
        self.assertEqual(picks, [("past", "death"), ("present", "flaky_tower"), ("next", "hierophant")])

    def test_flaky_tower_evidence_is_computed_not_asserted(self):
        tower = self.by_id["flaky_tower"]
        self.assertEqual(tower["confidence"], "HIGH")
        self.assertIn("Flaky rate on main: 7.7%", tower["evidence"])
        self.assertIn("Tests affected: 41 of 1,204", tower["evidence"])
        self.assertIn("Window: 14 days, 312 runs", tower["evidence"])

    def test_feature_branch_noise_is_ignored(self):
        self.assertIn("Window: 14 days, 312 runs", self.by_id["flaky_tower"]["evidence"])

    def test_reversed_means_improving(self):
        death = self.by_id["death"]
        self.assertEqual(death["state"], "reversed")
        self.assertEqual(death["confidence"], "MEDIUM")
        self.assertIn("Burn rate: 0.8x (was 3.1x)", death["evidence"])

    def test_summary_is_theatrical_and_follows_the_spread(self):
        self.assertEqual(self.reading["summary"], "In the past, the reaper retreats; in the present, the tower trembles; "
                                                  "and for the next release, the road lies in mist.")

    def test_reading_is_pending_human_review(self):
        self.assertEqual(self.reading["review"]["status"], "pending_human_review")


class CloudedCards(unittest.TestCase):
    def test_clouded_card_is_withheld_with_missing_evidence(self):
        h = {c["id"]: c for c in tealeaves.read(DEMO)["cards"]}["hierophant"]
        self.assertEqual(h["state"], "clouded")
        self.assertEqual(h["evidence"], [])
        self.assertIsNone(h["confidence"])
        self.assertIn("Services reporting: 2 of 9 (need 5)", h["missing"])
        self.assertIn("Traceability export: 41 days old (max 14)", h["missing"])
        deck = tealeaves.load_deck()
        self.assertEqual(h["prophecy"], deck["clouded_prophecy"])

    def test_missing_source_clouds_dependent_cards_without_crashing(self):
        data = demo_copy()
        (data / "incidents.json").unlink()
        cards = {c["id"]: c for c in tealeaves.read(data)["cards"]}
        for cid in ("star", "moon", "judgement"):
            with self.subTest(card=cid):
                self.assertEqual(cards[cid]["state"], "clouded")
                self.assertIn("incidents.json not provided", cards[cid]["missing"])
        self.assertEqual(cards["flaky_tower"]["state"], "upright")

    def test_thin_sample_clouds_instead_of_guessing(self):
        data = demo_copy()
        ci = json.loads((data / "ci_runs.json").read_text())
        ci["runs"] = [r for r in ci["runs"] if not r["id"].startswith("run-")][:10] + \
                     [r for r in ci["runs"] if r["id"].startswith("run-")][:12]
        (data / "ci_runs.json").write_text(json.dumps(ci))
        tower = {c["id"]: c for c in tealeaves.read(data)["cards"]}["flaky_tower"]
        self.assertEqual(tower["state"], "clouded")
        self.assertIn("Sample: 12 (need 30)", tower["missing"])

    def test_fresh_traceability_lifts_the_veil(self):
        data = demo_copy()
        req = json.loads((data / "requirements.json").read_text())
        req.update(exported_at="2026-11-08T00:00:00Z", services_reporting=6)
        (data / "requirements.json").write_text(json.dumps(req))
        h = {c["id"]: c for c in tealeaves.read(data)["cards"]}["hierophant"]
        self.assertEqual(h["state"], "upright")
        self.assertIn("Unproven requirements: 3 of 4 (75.0%)", h["evidence"])

    def test_empty_slot_reads_still_rather_than_inventing(self):
        data = demo_copy()
        for name in ("pull_requests", "requirements", "service_map"):
            (data / f"{name}.json").unlink()
        reading = tealeaves.read(data)
        # Leading cards are all clouded now, so the slot shows a clouded card, never a drawn one.
        nxt = reading["spread"][2]["card"]
        self.assertEqual({c["id"]: c for c in reading["cards"]}[nxt]["state"], "clouded")


class Determinism(unittest.TestCase):
    def test_same_data_same_reading(self):
        self.assertEqual(json.dumps(tealeaves.read(DEMO), sort_keys=True), json.dumps(tealeaves.read(DEMO), sort_keys=True))

    def test_confidence_takes_the_weaker_of_sample_and_margin(self):
        self.assertEqual(tealeaves.confidence(400, 30, 2.6), "HIGH")
        self.assertEqual(tealeaves.confidence(400, 30, 1.0), "LOW")
        self.assertEqual(tealeaves.confidence(28, 14, 3.1), "MEDIUM")
        self.assertEqual(tealeaves.confidence(31, 30, 5.0), "LOW")


class Rendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(tempfile.mkdtemp())
        cls.reading = tealeaves.read(DEMO)
        render.write_all(cls.reading, tealeaves.load_deck(), cls.out)

    def test_outputs_written(self):
        for name in ("reading.json", "reading.md", "reading.html"):
            self.assertTrue((self.out / name).exists(), name)
        self.assertEqual(len(list((self.out / "cards").glob("*.svg"))), 8)

    def test_quiet_cards_get_no_svg(self):
        names = {p.name for p in (self.out / "cards").glob("*.svg")}
        self.assertFalse(any("fool" in n or "hermit" in n for n in names))

    def test_no_person_is_ever_named(self):
        authors = {p["author"] for p in json.loads((DEMO / "pull_requests.json").read_text())["pull_requests"]}
        text = "".join(p.read_text() for p in self.out.rglob("*") if p.is_file())
        for author in authors:
            self.assertNotIn(author, text)

    def test_evidence_fits_on_the_card(self):
        for c in self.reading["cards"]:
            for row in c["evidence"] + c["missing"]:
                with self.subTest(card=c["id"], row=row):
                    self.assertLessEqual(len(row), 42)

    def test_html_works_offline(self):
        html = (self.out / "reading.html").read_text()
        self.assertIsNone(re.search(r"(src|href)=\"https?://", html))
        self.assertIn("PENDING HUMAN REVIEW", html)


class Safety(unittest.TestCase):
    def test_scripts_make_no_network_calls(self):
        banned = re.compile(r"^\s*(import|from)\s+(socket|urllib|http|requests|httpx|aiohttp|ftplib|smtplib)\b", re.M)
        for path in (SKILL / "scripts").glob("*.py"):
            with self.subTest(script=path.name):
                self.assertIsNone(banned.search(path.read_text()))


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------- v1.1: PR mode

import check_data  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "action"))
import collect_github  # noqa: E402
import post_comment  # noqa: E402

DEMO_PR = DEMO / "demo_pr.json"


class PullRequestMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reading = tealeaves.read(DEMO, pr_path=DEMO_PR)
        cls.by_id = {c["id"]: c for c in cls.reading["cards"]}
        cls.comment = render.comment_md(cls.reading)

    def test_pr_scoped_cards_replace_repo_windows(self):
        self.assertEqual(self.by_id["fool"]["scope"], "pr")
        self.assertEqual(self.by_id["emperor"]["scope"], "pr")
        self.assertEqual(self.by_id["death"]["scope"], "repo")

    def test_fool_finds_untested_source_and_ignores_tests_and_docs(self):
        fool = self.by_id["fool"]
        self.assertEqual(fool["state"], "upright")
        self.assertIn("Untested files in this PR: 1 of 2", fool["evidence"])
        self.assertIn("File: src/cart/legacy_tax.py", fool["evidence"])

    def test_emperor_counts_only_required_checks(self):
        emp = self.by_id["emperor"]
        self.assertEqual(emp["state"], "upright")
        self.assertIn("Required checks not passing: 1 of 4", emp["evidence"])
        self.assertIn("security-scan: skipped", emp["evidence"])
        self.assertNotIn("lint: failure", emp["evidence"])

    def test_pr_changes_the_next_release_card(self):
        self.assertEqual([s["card"] for s in self.reading["spread"]], ["death", "flaky_tower", "fool"])

    def test_comment_has_marker_provenance_and_no_author(self):
        self.assertTrue(self.comment.startswith(post_comment.MARKER))
        self.assertIn("via Honeycomb (synthetic)", self.comment)
        self.assertIn("Where the evidence came from", self.comment)
        self.assertIn("never blocks a merge", self.comment)
        self.assertNotIn("casey.ruiz", self.comment)
        self.assertLess(len(self.comment), 65536)

    def test_comment_is_written_only_in_pr_mode(self):
        out = Path(tempfile.mkdtemp())
        render.write_all(self.reading, tealeaves.load_deck(), out)
        self.assertTrue((out / "comment.md").exists())
        out2 = Path(tempfile.mkdtemp())
        render.write_all(tealeaves.read(DEMO), tealeaves.load_deck(), out2)
        self.assertFalse((out2 / "comment.md").exists())

    def test_no_required_checks_clouds_the_emperor(self):
        data = demo_copy()
        pr = json.loads(DEMO_PR.read_text())
        for c in pr["checks"]:
            c["required"] = False
        (data / "pr.json").write_text(json.dumps(pr))
        emp = {c["id"]: c for c in tealeaves.read(data, pr_path=data / "pr.json")["cards"]}["emperor"]
        self.assertEqual(emp["state"], "clouded")
        self.assertIn("No required checks reported", emp["missing"])


class DataContract(unittest.TestCase):
    def test_demo_data_passes(self):
        for name in check_data.CONTRACT:
            path = DEMO / ("demo_pr.json" if name == "pr" else f"{name}.json")
            with self.subTest(source=name):
                self.assertEqual(check_data.check(name, json.loads(path.read_text())), [])

    def test_malformed_agent_output_is_set_aside_and_clouds(self):
        data = demo_copy()
        bad = json.loads((data / "slo_alerts.json").read_text())
        del bad["slos"][0]["burn_rate"]
        (data / "slo_alerts.json").write_text(json.dumps(bad))
        reading = tealeaves.read(data)
        death = {c["id"]: c for c in reading["cards"]}["death"]
        self.assertEqual(death["state"], "clouded")
        self.assertIn("slo_alerts.json failed contract check", death["missing"])
        self.assertIn("slo_alerts", reading["source_problems"])

    def test_bad_timestamp_is_caught(self):
        problems = check_data.check("incidents", {"incidents": [
            {"id": "X", "opened_at": "last tuesday", "detected_by": "alert", "escaped_defect": False}]})
        self.assertEqual(problems, ["incidents[0].opened_at is not an ISO time"])


class GitHubAction(unittest.TestCase):
    EVENT = {"pull_request": {"number": 7, "title": "t", "html_url": "u", "user": {"login": "someone"},
                              "head": {"sha": "abc1234", "repo": {"full_name": "fork/repo"}}, "base": {"ref": "main"}},
             "repository": {"full_name": "j-m-o/demo"}}

    def test_build_pr_marks_required_and_drops_author(self):
        pr = collect_github.build_pr(self.EVENT, ["b.py", "a.py", "a.py"],
                                     [("unit", "success"), ("scan", "pending")], ["unit", " scan "])
        self.assertEqual(pr["files"], ["a.py", "b.py"])
        self.assertEqual(pr["checks"], [{"name": "unit", "required": True, "conclusion": "success"},
                                        {"name": "scan", "required": True, "conclusion": None}])
        self.assertNotIn("someone", json.dumps(pr))
        self.assertEqual(check_data.check("pr", pr), [])

    def test_lcov_conversion(self):
        lcov = "SF:/ws/src/a.py\nLH:3\nend_of_record\nSF:/ws/src/b.py\nLH:0\nend_of_record\n"
        cov = collect_github.lcov_to_coverage(lcov, "/ws")
        self.assertEqual(cov["files"], {"src/a.py": True, "src/b.py": False})

    def test_fork_detection(self):
        self.assertTrue(post_comment.is_fork(self.EVENT))
        same = json.loads(json.dumps(self.EVENT))
        same["pull_request"]["head"]["repo"]["full_name"] = "j-m-o/demo"
        self.assertFalse(post_comment.is_fork(same))

    def test_updates_the_bot_comment_not_a_human_quote(self):
        comments = [{"id": 1, "body": post_comment.MARKER + " quoted", "user": {"type": "User"}},
                    {"id": 2, "body": post_comment.MARKER + "\n## reading", "user": {"type": "Bot"}}]
        self.assertEqual(post_comment.find_existing(comments), 2)
        self.assertIsNone(post_comment.find_existing(comments[:1]))
