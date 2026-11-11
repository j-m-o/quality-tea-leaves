"""Render a Quality Tea Leaves reading as SVG cards, an HTML page, Markdown and console text.

No network and no third-party packages. Fonts fall back to local serif and
monospace faces, so the HTML works offline.

Quality Tea Leaves, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import json
from html import escape
from pathlib import Path

INK = "#0E2626"
GROUND = "#091C1C"
PANEL = "#133333"
GOLD = "#D4B062"
TEXT = "#E8E1CF"
MUTED = "#9FB3AC"
LINE = "#2C4A47"
DISPLAY = "Cinzel, 'Trajan Pro', Georgia, serif"
BODY = "Inter, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, monospace"

FOG = ('<g stroke="#9FB3AC" stroke-width="2.2" fill="none" stroke-linecap="round">'
       '<path d="M18 58 C40 48 58 66 82 56 C104 46 120 64 144 54 C160 48 172 54 184 50"/>'
       '<path d="M10 82 C34 72 54 92 80 80 C104 70 126 90 150 78 C164 72 178 78 190 74" opacity="0.8"/>'
       '<path d="M24 104 C46 96 64 112 90 102 C112 94 132 110 156 100 C168 96 178 100 186 98" opacity="0.6"/></g>')


def wrap(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def badge(card):
    return {"upright": "UPRIGHT", "reversed": "REVERSED · IMPROVING", "clouded": "CLOUDED · WITHHELD"}.get(card["state"], "QUIET")


def meter(card):
    if card["state"] == "clouded":
        return "NONE ○○○"
    return {"HIGH": "HIGH ●●●", "MEDIUM": "MEDIUM ●●○", "LOW": "LOW ●○○"}.get(card["confidence"], "")


def card_svg(card, art):
    """One 360 x 620 card. Upright art stands; reversed art is turned; clouded art sits under fog."""
    clouded = card["state"] == "clouded"
    accent = MUTED if clouded else GOLD
    dash = ' stroke-dasharray="4 4"' if clouded else ""
    x = escape
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="620" viewBox="0 0 360 620" role="img" '
           f'aria-label="{x(card["name"])}, {x(badge(card).lower())}">',
           f'<rect width="360" height="620" rx="20" fill="{INK}"/>',
           f'<rect x="12.5" y="12.5" width="335" height="595" rx="12" fill="none" stroke="{"#5E716B" if clouded else "#6E5B2E"}"{dash}/>',
           f'<text x="34" y="50" font-family="{DISPLAY}" font-size="16" letter-spacing="2" fill="{accent}">{x(card["numeral"])}</text>']
    label = badge(card)
    w = 12 + 7.2 * len(label)
    if card["state"] == "upright":
        out.append(f'<rect x="{326 - w:.0f}" y="34" width="{w:.0f}" height="22" rx="11" fill="{GOLD}"/>')
        label_fill = INK
    else:
        out.append(f'<rect x="{326 - w:.0f}" y="34" width="{w:.0f}" height="22" rx="11" fill="none" stroke="{accent}"{dash}/>')
        label_fill = "#C9D4CF" if clouded else GOLD
    out.append(f'<text x="{326 - w / 2:.0f}" y="49" text-anchor="middle" font-family="{BODY}" font-size="10.5" font-weight="600" '
               f'letter-spacing="1.2" fill="{label_fill}">{x(label)}</text>')
    out.append(f'<text x="180" y="96" text-anchor="middle" font-family="{DISPLAY}" font-size="25" font-weight="700" '
               f'letter-spacing="1" fill="{accent}">{x(card["name"])}</text>')
    out.append(f'<line x1="32" y1="114" x2="328" y2="114" stroke="{LINE}"/><line x1="32" y1="264" x2="328" y2="264" stroke="{LINE}"/>')
    turn = ' transform="rotate(180 100 70)"' if card["state"] == "reversed" else ""
    opacity = ' opacity="0.22"' if clouded else ""
    out.append(f'<g transform="translate(80 119)"><g fill="none" stroke="{GOLD}" stroke-width="1.5" stroke-linecap="round" '
               f'stroke-linejoin="round"{opacity}{turn}>{art}</g>{FOG if clouded else ""}</g>')
    y = 292
    for line in wrap(card.get("prophecy") or "The leaves are still. No omen here.", 40)[:4]:
        out.append(f'<text x="180" y="{y}" text-anchor="middle" font-family="{BODY}" font-size="14" font-style="italic" fill="{TEXT}">{x(line)}</text>')
        y += 20
    y += 10
    out.append(f'<text x="34" y="{y}" font-family="{BODY}" font-size="11" letter-spacing="1.5" fill="{MUTED}">CONFIDENCE</text>')
    out.append(f'<text x="326" y="{y}" text-anchor="end" font-family="{MONO}" font-size="12" font-weight="500" '
               f'fill="{"#C9D4CF" if clouded else GOLD}">{x(meter(card))}</text>')
    y += 16
    rows = card["missing"] if clouded else card["evidence"]
    rows = rows[:4]
    box_h = 34 + 18 * len(rows)
    if clouded:
        out.append(f'<rect x="32" y="{y}" width="296" height="{box_h}" rx="8" fill="none" stroke="#5E716B" stroke-dasharray="4 4"/>')
    else:
        out.append(f'<rect x="32" y="{y}" width="296" height="{box_h}" rx="8" fill="{PANEL}"/>')
    out.append(f'<text x="44" y="{y + 22}" font-family="{BODY}" font-size="11" letter-spacing="1.5" fill="{MUTED}">'
               f'{"MISSING EVIDENCE" if clouded else "EVIDENCE"}</text>')
    for i, row in enumerate(rows):
        out.append(f'<text x="44" y="{y + 42 + 18 * i}" font-family="{MONO}" font-size="11" fill="{TEXT}">{x(row[:42])}</text>')
    out.append(f'<text x="34" y="592" font-family="{BODY}" font-size="11" fill="{MUTED}">Signal: {x(card["signal"])}</text>')
    out.append(f'<text x="326" y="592" text-anchor="end" font-family="{MONO}" font-size="10" fill="{MUTED}">{x(card["source"].split(" ")[0])}</text>')
    out.append("</svg>")
    return "\n".join(out)


def html_page(reading, svgs):
    by_id = {c["id"]: c for c in reading["cards"]}
    slots = []
    for s in reading["spread"]:
        body = svgs.get(s["card"]) if s["card"] else '<p class="still">The leaves are still.</p>'
        slots.append(f'<figure><figcaption>{escape(s["label"].upper())}</figcaption>{body}</figure>')
    others = [c for c in reading["cards"] if c["id"] not in {s["card"] for s in reading["spread"]}]
    rows = "".join(
        f'<tr><td>{escape(c["numeral"])}</td><td>{escape(c["name"])}</td><td>{escape(c["signal"])}</td>'
        f'<td>{escape(c["state"])}</td><td>{escape(c["confidence"] or "")}</td>'
        f'<td>{escape("; ".join(c["missing"] or c["evidence"][:2]))}</td></tr>' for c in others)
    c = reading["counts"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quality Tea Leaves: {escape(reading["subject"])}</title>
<style>
body{{margin:0;background:{GROUND};color:{TEXT};font-family:{BODY}}}
main{{max-width:1280px;margin:0 auto;padding:48px 24px}}
.eyebrow{{font-size:13px;letter-spacing:3px;text-transform:uppercase;color:{MUTED}}}
h1{{font-family:{DISPLAY};color:{GOLD};font-size:44px;margin:8px 0 12px;letter-spacing:2px}}
.omen{{font-size:19px;font-style:italic;max-width:900px;line-height:1.5}}
.draft{{display:inline-block;margin:16px 0 0;padding:6px 12px;border:1px dashed {MUTED};border-radius:999px;font-size:12px;letter-spacing:1px;color:#C9D4CF}}
.spread{{display:flex;flex-wrap:wrap;justify-content:center;gap:48px;margin:40px 0}}
figure{{margin:0;display:flex;flex-direction:column;align-items:center;gap:12px}}
figcaption{{font-family:{DISPLAY};color:{GOLD};letter-spacing:3px}}
figure svg{{max-width:100%;height:auto;filter:drop-shadow(0 18px 30px rgba(0,0,0,.45))}}
.still{{width:360px;height:620px;display:flex;align-items:center;justify-content:center;border:1px dashed {LINE};border-radius:20px;color:{MUTED}}}
h2{{font-family:{DISPLAY};color:{GOLD};font-size:22px;letter-spacing:1px}}
.table{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid {LINE};vertical-align:top}}
th{{color:{MUTED};font-weight:500;font-size:12px;letter-spacing:1px;text-transform:uppercase}}
td:last-child{{font-family:{MONO};font-size:12px}}
footer{{margin-top:40px;color:{MUTED};font-size:13px;line-height:1.6}}
</style></head><body><main>
<div class="eyebrow">A reading for {escape(reading["subject"])}{" · PR #" + escape(str(reading["pr"]["number"])) if reading.get("pr") else ""}{" · release " + escape(reading["release"]) if reading.get("release") else ""} · as of {escape(reading["as_of"][:10])}</div>
<h1>Quality Tea Leaves</h1>
<p class="omen">{escape(reading["summary"])}</p>
<span class="draft">DRAFT · PENDING HUMAN REVIEW</span>
<section class="spread" aria-label="Three-card spread">{"".join(slots)}</section>
<h2>The rest of the deck</h2>
<div class="table"><table><thead><tr><th>#</th><th>Card</th><th>Signal</th><th>State</th><th>Confidence</th><th>Evidence</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<footer>{c["upright"]} upright · {c["reversed"]} reversed · {c["quiet"]} quiet · {c["clouded"]} clouded and withheld.<br>
Cards are chosen by signal strength, not chance: the same data always gives the same reading. The shuffle is theater.<br>
Sources read: {escape(", ".join(reading["sources"]))}. Deck v{escape(reading["deck_version"])}.</footer>
</main></body></html>
"""


def markdown(reading):
    by_id = {c["id"]: c for c in reading["cards"]}
    lines = [f"# Quality Tea Leaves: {reading['subject']}", "",
             f"**DRAFT, pending human review.** As of {reading['as_of']}" + (f", release {reading['release']}." if reading.get("release") else "."),
             "", f"> {reading['summary']}", "", "## The spread", ""]
    for s in reading["spread"]:
        c = by_id.get(s["card"])
        if not c:
            lines += [f"### {s['label']}: the leaves are still", ""]
            continue
        lines += [f"### {s['label']}: {c['numeral']} {c['name']} ({c['state']})", "", f"*{c['prophecy']}*", ""]
        if c["state"] == "clouded":
            lines += ["Withheld. Missing evidence:", ""] + [f"- {m}" for m in c["missing"]]
        else:
            lines += [f"Confidence: **{c['confidence']}**", ""] + [f"- {e}" for e in c["evidence"]]
        lines.append("")
    lines += ["## The rest of the deck", "", "| # | Card | Signal | State | Confidence | Evidence |", "| --- | --- | --- | --- | --- | --- |"]
    shown = {s["card"] for s in reading["spread"]}
    for c in reading["cards"]:
        if c["id"] in shown:
            continue
        ev = "; ".join(c["missing"] or c["evidence"][:2])
        lines.append(f"| {c['numeral']} | {c['name']} | {c['signal']} | {c['state']} | {c['confidence'] or ''} | {ev} |")
    lines += ["", "Cards are chosen by signal strength, not chance. Clouded cards are withheld, never guessed. "
              "Cards name systems and modules, never people.", ""]
    return "\n".join(lines)


def console(reading):
    by_id = {c["id"]: c for c in reading["cards"]}
    out = [f"QUALITY TEA LEAVES  {reading['subject']}  as of {reading['as_of']}", "", reading["summary"], ""]
    for s in reading["spread"]:
        c = by_id.get(s["card"])
        if not c:
            out.append(f"{s['label']:<13} (the leaves are still)")
            continue
        conf = f" [{c['confidence']}]" if c["confidence"] else ""
        out.append(f"{s['label']:<13} {c['numeral']:>5} {c['name']} ({c['state']}){conf}")
        out.append(f"{'':<20}{c['prophecy']}")
        for row in (c["missing"] if c["state"] == "clouded" else c["evidence"]):
            out.append(f"{'':<20}- {row}")
    k = reading["counts"]
    out += ["", f"Deck: {k['upright']} upright, {k['reversed']} reversed, {k['quiet']} quiet, {k['clouded']} clouded.",
            "Status: pending human review."]
    return "\n".join(out)


MARKER = "<!-- quality-tea-leaves -->"
COMMENT_LIMIT = 60000  # GitHub allows 65,536 characters; leave room for the run link


def _state_label(c):
    return {"upright": "upright", "reversed": "reversed, improving", "clouded": "clouded, withheld", "quiet": "quiet"}[c["state"]]


def _via(c):
    return f" · via {', '.join(c['via'])}" if c.get("via") else ""


def comment_md(reading):
    """Compact Markdown for a PR comment. Text only: PR comments cannot show the SVG cards."""
    by_id = {c["id"]: c for c in reading["cards"]}
    pr = reading.get("pr") or {}
    title = f"PR #{pr['number']}" if pr.get("number") else reading["subject"]
    lines = [MARKER, f"## 🍵 Quality Tea Leaves: {title}", "",
             f"> *{reading['summary']}*", ""]
    for s in reading["spread"]:
        c = by_id.get(s["card"])
        if not c:
            lines += [f"**{s['label']}**: the leaves are still.", ""]
            continue
        scope = " · this PR" if c.get("scope") == "pr" else ""
        conf = f" · confidence **{c['confidence']}**" if c["confidence"] else ""
        lines += [f"**{s['label']}: {c['numeral']} {c['name']}** ({_state_label(c)}{conf}{scope})", "",
                  f"*{c['prophecy']}*", ""]
        rows = c["missing"] if c["state"] == "clouded" else c["evidence"]
        if c["state"] == "clouded":
            lines.append("Missing evidence:")
        lines += [f"- {r}" for r in rows]
        lines += ["", f"<sub>Source: {c['source']}{_via(c)}</sub>", ""]
    shown = {s["card"] for s in reading["spread"]}
    rest = [c for c in reading["cards"] if c["id"] not in shown]
    k = reading["counts"]
    lines += ["<details><summary>Show full deck "
              f"({k['upright']} upright, {k['reversed']} reversed, {k['quiet']} quiet, {k['clouded']} clouded)</summary>", "",
              "| # | Card | Scope | State | Confidence | Evidence |", "| --- | --- | --- | --- | --- | --- |"]
    for c in rest:
        ev = "; ".join(c["missing"] or c["evidence"][:2]).replace("|", "/")
        lines.append(f"| {c['numeral']} | {c['name']} | {c.get('scope', 'repo')} | {c['state']} | {c['confidence'] or ''} | {ev} |")
    lines += ["", "</details>", ""]
    prov = reading.get("provenance") or {}
    if prov:
        lines += ["<details><summary>Where the evidence came from</summary>", "", "| Source | Via | Pulled | Records |",
                  "| --- | --- | --- | --- |"]
        for name, p in sorted(prov.items()):
            lines.append(f"| {name}.json | {p.get('connector', '')} | {str(p.get('pulled_at', ''))[:16]} | {p.get('records', '')} |")
        lines += ["", "</details>", ""]
    if reading.get("source_problems"):
        bad = ", ".join(f"{n}.json" for n in sorted(reading["source_problems"]))
        lines += [f"**Set aside** for failing the data contract: {bad}. Cards that need them are clouded.", ""]
    lines += ["---", "<sub>Advisory only: this reading never blocks a merge. Cards are chosen by evidence, not chance; "
              "clouded cards are withheld, never guessed. Draft for human review.</sub>"]
    body = "\n".join(lines) + "\n"
    if len(body) > COMMENT_LIMIT:
        body = body[:COMMENT_LIMIT] + "\n\n(Reading truncated. See the full reading attached to the workflow run.)\n"
    return body


def write_all(reading, deck, out_dir):
    out_dir = Path(out_dir)
    cards_dir = out_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    art = {c["id"]: c["art"] for c in deck["cards"]}
    svgs = {}
    for c in reading["cards"]:
        if c["state"] == "quiet":
            continue
        svg = card_svg(c, art[c["id"]])
        svgs[c["id"]] = svg
        (cards_dir / f"{c['number']:02d}-{c['id']}-{c['state']}.svg").write_text(svg + "\n")
    (out_dir / "reading.json").write_text(json.dumps(reading, indent=2) + "\n")
    (out_dir / "reading.md").write_text(markdown(reading))
    (out_dir / "reading.html").write_text(html_page(reading, svgs))
    written = [out_dir / "reading.json", out_dir / "reading.md", out_dir / "reading.html", cards_dir]
    if reading.get("pr"):
        (out_dir / "comment.md").write_text(comment_md(reading))
        written.append(out_dir / "comment.md")
    return written
