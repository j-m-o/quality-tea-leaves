"""Repository checks for Quality Tea Leaves. Run before every commit and in CI.

Checks: SKILL.md frontmatter, deck integrity, JSON parses, no network imports
in skill scripts, no em dashes in text files.

Quality Tea Leaves, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "quality-tea-leaves"
TEXT = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ".svg", ".html"}
NETWORK = re.compile(r"^\s*(import|from)\s+(socket|urllib|http|requests|httpx|aiohttp|ftplib|smtplib)\b", re.M)
CARD_KEYS = {"id", "number", "numeral", "name", "signal", "slot", "source", "min_sample", "prophecy", "omen", "art"}

errors = []

skill_md = (SKILL / "SKILL.md").read_text()
front = re.match(r"^---\n(.*?)\n---\n", skill_md, re.S)
if not front:
    errors.append("SKILL.md: missing frontmatter")
else:
    fields = dict(line.split(":", 1) for line in front.group(1).splitlines() if ":" in line)
    if fields.get("name", "").strip() != "quality-tea-leaves":
        errors.append("SKILL.md: name must be quality-tea-leaves")
    if len(fields.get("description", "").strip()) < 40:
        errors.append("SKILL.md: description too short")

deck = json.loads((SKILL / "assets" / "deck.json").read_text())
ids = [c["id"] for c in deck["cards"]]
if len(ids) != len(set(ids)):
    errors.append("deck.json: duplicate card ids")
for c in deck["cards"]:
    missing = CARD_KEYS - set(c)
    if missing:
        errors.append(f"deck.json: {c.get('id')} missing {sorted(missing)}")
    if c.get("slot") not in {"lagging", "current", "leading"}:
        errors.append(f"deck.json: {c.get('id')} has unknown slot")
    for state in ("upright", "reversed"):
        if not c.get("prophecy", {}).get(state) or not c.get("omen", {}).get(state):
            errors.append(f"deck.json: {c.get('id')} missing {state} prophecy or omen")

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or "dist" in path.parts or path.suffix not in TEXT:
        continue
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)
    if chr(0x2014) in text:
        errors.append(f"{rel}: contains an em dash")
    if path.suffix == ".json":
        try:
            json.loads(text)
        except ValueError as e:
            errors.append(f"{rel}: invalid JSON ({e})")

for path in (SKILL / "scripts").glob("*.py"):
    if NETWORK.search(path.read_text()):
        errors.append(f"{path.relative_to(ROOT)}: network import")

if errors:
    print("FAILED")
    print("\n".join(f"  - {e}" for e in errors))
    sys.exit(1)
print(f"OK: {len(ids)} cards, skill metadata, JSON, no network imports, no em dashes")
