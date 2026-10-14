#!/usr/bin/env python3
"""Render an epic's Ledger notes + smoke-test guide as Markdown for a project->main PR body.

Usage:
    render_ledger.py EPIC_ID [--tk-dir DIR]     # reads via the tk CLI (run from the repo that owns the tickets)
    render_ledger.py --show-file FILE [--query-file FILE]   # offline: `tk show` text / `tk query` JSONL

Ledger notes are written with `tk add-note <epic> "Ledger: ..."`. The parser is deliberately
tolerant (see resources/LEDGER.md): fields may be `|`-separated, `key=value`, or free text, in any order.
Unparseable entries are kept verbatim under "Unparsed", never dropped.
"""

import argparse
import json
import re
import subprocess
import sys

SEV_ORDER = {"H": 0, "M": 1, "L": 2, "?": 3}
SEV_NAME = {"H": "High", "M": "Medium", "L": "Low", "?": "Unrated"}
DISPOSITIONS = {
    "fixed": "fixed", "fix": "fixed", "resolved": "fixed",
    "deferred": "deferred", "defer": "deferred", "followup": "deferred", "follow-up": "deferred",
    "needs-james": "needs-james", "needs_james": "needs-james", "needs james": "needs-james",
    "james": "needs-james", "open": "needs-james",
}
DISP_ORDER = {"needs-james": 0, "deferred": 1, "fixed": 2, "?": 3}
SEV_WORDS = {"high": "H", "medium": "M", "med": "M", "low": "L", "h": "H", "m": "M", "l": "L"}

PR_RE = re.compile(r"(?:\bPR\s*#?|#)(\d+)", re.I)
LOC_RE = re.compile(r"([\w./\-\[\]@]+\.\w+(?::\d+(?:-\d+)?)?)")
KV_RE = re.compile(r"^\s*([A-Za-z_\- ]+?)\s*[=:]\s*(.+?)\s*$")
INTERRUPT_RE = re.compile(r"\b(interrupt(?:ed)?|interrupt[=:]\s*(?:yes|true|y))\b", re.I)
NO_INTERRUPT_RE = re.compile(r"interrupt[=:]\s*(?:no|false|n)\b", re.I)


def parse_entry(text):
    """Parse one ledger entry string (without the 'Ledger:' prefix) into a dict."""
    raw = text.strip()
    e = {"pr": None, "loc": None, "lens": None, "sev": "?", "summary": None,
         "disp": "?", "interrupt": False, "raw": raw}
    loose = []
    parts = [p.strip() for p in re.split(r"\s+\|\s+|\s*\|\s*", raw) if p.strip()] or [raw]
    for part in parts:
        low = part.lower()
        m = KV_RE.match(part)
        key, val = (m.group(1).strip().lower(), m.group(2).strip()) if m else (None, None)
        if key in ("pr", "pr#"):
            mm = re.search(r"\d+", val)
            e["pr"] = e["pr"] or (mm.group(0) if mm else None)
        elif key in ("file", "loc", "location", "where", "file:line"):
            e["loc"] = e["loc"] or val
        elif key == "lens":
            e["lens"] = val
        elif key in ("sev", "severity"):
            e["sev"] = SEV_WORDS.get(val.lower().strip("[]() "), e["sev"])
        elif key in ("disp", "disposition", "status"):
            e["disp"] = DISPOSITIONS.get(val.lower(), e["disp"])
        elif key in ("summary", "finding", "desc", "description"):
            e["summary"] = val
        elif key == "interrupt":
            e["interrupt"] = val.lower() in ("yes", "true", "y", "1")
        elif PR_RE.fullmatch(part) or re.fullmatch(r"PR\s*#?\d+", part, re.I):
            e["pr"] = e["pr"] or PR_RE.search(part).group(1)
        elif low in DISPOSITIONS:
            e["disp"] = DISPOSITIONS[low]
        elif re.fullmatch(r"[\[(]?([hml]|high|medium|med|low)[\])]?", low):
            e["sev"] = SEV_WORDS[low.strip("[]()")]
        elif re.fullmatch(r"interrupt(ed)?(\s*[:=]\s*yes)?", low):
            e["interrupt"] = True
        elif e["loc"] is None and LOC_RE.fullmatch(part) and ("/" in part or ":" in part or "." in part) \
                and not part.lower().startswith("lens"):
            e["loc"] = part
        else:
            loose.append(part)
    # Fallbacks for free-text entries: mine the raw text for fields still unset, and strip what was
    # mined from the summary so it reads cleanly.
    rest = raw if not loose or len(parts) == 1 else " ".join(loose)
    def mine(rx, flags=0):
        nonlocal rest
        m = re.search(rx, rest, flags)
        if m:
            rest = (rest[:m.start()] + " " + rest[m.end():])
        return m
    if e["pr"] is None:
        m = mine(r"(?:\bPR\s*#?|#)(\d+)", re.I)
        e["pr"] = m.group(1) if m else None
    if e["loc"] is None:
        m = mine(r"[\w./\-\[\]@]+\.\w+:\d+(?:-\d+)?")
        e["loc"] = m.group(0) if m else None
    if e["sev"] == "?":
        m = mine(r"\[(H|M|L)\]|\bsev(?:erity)?[=:\s]*(HIGH|MEDIUM|LOW|H|M|L)\b", re.I) \
            or mine(r"(?<![\w])(HIGH|MEDIUM)(?![\w])") \
            or mine(r"(?:^|(?<=[\s,]))(H|M|L)(?=[\s,:;]|$)")
        if m:
            tok = next(g for g in m.groups() if g) if m.groups() else m.group(0)
            e["sev"] = SEV_WORDS[tok.lower()]
    if e["disp"] == "?":
        for word, norm in DISPOSITIONS.items():
            if word in ("open", "james", "fix"):
                continue
            if mine(r"\b" + re.escape(word) + r"\b", re.I):
                e["disp"] = norm
                break
    if INTERRUPT_RE.search(raw) and not NO_INTERRUPT_RE.search(raw):
        e["interrupt"] = True
    if e["summary"] is None:
        e["summary"] = re.sub(r"\s+", " ", rest).strip(" ,;:-") or raw
        e["summary"] = re.sub(r"^[\s,;:-]+|\s+([,;:])", lambda m: m.group(1) or "", e["summary"])
    return e


def extract_ledger(notes_text):
    """Yield entry strings from `tk show` Notes text. Tolerates multi-entry notes and bullets."""
    entries = []
    for block in re.split(r"\n(?=\*\*\d{4}-\d\d-\d\dT[\d:]+Z\*\*)", notes_text):
        body = re.sub(r"^\*\*[^*]+\*\*\s*", "", block.strip())
        if not re.match(r"ledger\b", body, re.I):
            continue
        lines = body.splitlines()
        first = re.sub(r"^ledger\s*[:\-]?\s*", "", lines[0], flags=re.I)
        cur = [first] if first else []
        for ln in lines[1:]:
            if re.match(r"\s*(?:[-*]\s+|ledger\s*:)", ln, re.I):
                if cur:
                    entries.append(" ".join(cur))
                cur = [re.sub(r"^\s*(?:[-*]\s+|ledger\s*:\s*)", "", ln, flags=re.I)]
            elif ln.strip():
                cur.append(ln.strip())
        if cur:
            entries.append(" ".join(cur))
    return [e for e in entries if e.strip()]


def split_show(text):
    """Split `tk show` output into (frontmatter-less body, notes, children lines)."""
    sections = {}
    cur = "body"
    sections[cur] = []
    for ln in text.splitlines():
        m = re.match(r"^## (Notes|Children|Linked|Blocking|Blockers)\s*$", ln)
        if m:
            cur = m.group(1).lower()
            sections[cur] = []
        else:
            sections[cur].append(ln)
    return {k: "\n".join(v) for k, v in sections.items()}


def section(body, heading_re):
    """Return the text under a '## heading' whose title matches heading_re (until next '## ')."""
    m = re.search(r"^##\s+(?:%s)[^\n]*\n(.*?)(?=^##\s|\Z)" % heading_re, body, re.I | re.M | re.S)
    return m.group(1).strip() if m else ""


def render(epic_id, show_text, query_lines):
    secs = split_show(show_text)
    entries = [parse_entry(t) for t in extract_ledger(secs.get("notes", ""))]
    out = []

    out.append("## Ledger")
    out.append("")
    if not entries:
        out.append("No flagged review items.")
    else:
        actionable = [e for e in entries if e["disp"] in ("needs-james", "?")]
        out.append("%d item(s): %s." % (len(entries), ", ".join(
            "%d %s" % (n, SEV_NAME[s].lower()) for s in "HML?"
            for n in [sum(1 for e in entries if e["sev"] == s)] if n)))
        if actionable:
            out.append("**%d need your decision.**" % len(actionable))
        out.append("")
        for sev in "HML?":
            group = sorted((e for e in entries if e["sev"] == sev),
                           key=lambda e: (DISP_ORDER[e["disp"]], int(e["pr"] or 0)))
            if not group:
                continue
            out.append("### %s severity" % SEV_NAME[sev])
            out.append("")
            out.append("| PR | Where | Lens | Finding | Disposition |")
            out.append("|----|-------|------|---------|-------------|")
            for e in group:
                disp = e["disp"] if e["disp"] != "?" else "unspecified"
                if e["interrupt"]:
                    disp += " (interrupted)"
                cells = [("#" + e["pr"]) if e["pr"] else "-",
                         ("`%s`" % e["loc"]) if e["loc"] else "-",
                         e["lens"] or "-",
                         (e["summary"] or "").replace("|", "\\|"),
                         disp]
                out.append("| " + " | ".join(cells) + " |")
            out.append("")

    out.append("## Smoke-test guide")
    out.append("")
    body = secs.get("body", "")
    seed = section(body, r"Smoke[- ]test guide")
    out.append(seed if seed else "_No smoke-test seed in the epic body; add steps manually._")
    out.append("")

    tags = {}
    for ln in query_lines:
        try:
            j = json.loads(ln)
        except ValueError:
            continue
        tags[j.get("id")] = j.get("tags", [])
    titles = {}
    for m in re.finditer(r"^- (\S+) \[(\w+)\] (.*)$", secs.get("children", ""), re.M):
        titles[m.group(1)] = (m.group(3), m.group(2))
    groups = [("verify-voice", "Voice (live duplex; not exercised by agents)"),
              ("verify-full", "Simulator flows (agent smoke ran in a worktree; confirm on your build)"),
              ("human-blocker", "Human-only tasks (confirm done)")]
    for tag, heading in groups:
        items = [(i, titles[i]) for i in titles if tag in tags.get(i, [])]
        if items:
            out.append("### " + heading)
            out.append("")
            for i, (title, status) in items:
                box = "x" if status == "closed" and tag == "human-blocker" else " "
                out.append("- [%s] %s (%s)" % (box, title, i))
            out.append("")
    smoke_notes = [t for t in re.split(r"\n(?=\*\*\d{4}-)", secs.get("notes", ""))
                   if re.match(r"(\*\*[^*]+\*\*\s*)?smoke\b", t.strip(), re.I)]
    if smoke_notes:
        out.append("### Added during implementation")
        out.append("")
        for t in smoke_notes:
            out.append("- [ ] " + re.sub(r"^(\*\*[^*]+\*\*\s*)?smoke\s*:?\s*", "", t.strip(), flags=re.I))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("epic", nargs="?")
    ap.add_argument("--show-file")
    ap.add_argument("--query-file")
    a = ap.parse_args()
    if a.show_file:
        show = open(a.show_file).read()
        q = open(a.query_file).read().splitlines() if a.query_file else []
    elif a.epic:
        show = subprocess.run(["tk", "show", a.epic], capture_output=True, text=True, check=True).stdout
        q = subprocess.run(["tk", "query"], capture_output=True, text=True, check=True).stdout.splitlines()
    else:
        ap.error("EPIC_ID or --show-file required")
    sys.stdout.write(render(a.epic, show, q))


if __name__ == "__main__":
    main()
