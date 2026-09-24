#!/usr/bin/env python3
"""
claude_code_tokrate_history.py

Reconstructs approximate historical tok/s for Claude Code sessions straight
from the local JSONL session transcripts Claude Code already writes to disk
-- no telemetry setup needed. This works retroactively on sessions you've
already run (companion to claude_code_tokrate.py, which only sees sessions
going forward from when you start it).

--------------------------------------------------------------------------
HOW THIS WORKS (and why it's approximate)

Claude Code appends every message to a transcript file at:
    ~/.claude/projects/<project>/<session-id>.jsonl
(or under $CLAUDE_CONFIG_DIR, if you've pointed that somewhere other than
the default ~/.claude)

Each assistant response is one JSON line containing:
    - message.model              which model answered
    - message.usage.output_tokens
    - message.content            may include a "thinking" block if extended
                                  thinking was on for that turn
    - timestamp                  when the response was recorded
    - parentUuid                 the message that triggered this response

There's no recorded duration_ms field the way the OTEL telemetry has one,
so this script approximates elapsed time as:

    (this message's timestamp) - (its parent message's timestamp)

That's a solid proxy for request time in the ordinary case -- you send a
prompt (or a tool result lands), the model answers -- but it breaks down
whenever something inserts a human-timed pause in between, most notably a
permission prompt sitting unanswered. --max-delta drops gaps long enough
that they're almost certainly a pause rather than model latency, not
genuine slowness. The opposite failure also happens: a near-zero delta
(two transcript lines landing at essentially the same instant) divides a
token count by almost nothing and produces a nonsense five- or six-digit
tok/s value. --min-delta filters those out. Treat "median" as the
trustworthy column in the breakdown table; "avg" and "max" are still
shown but remain more exposed to whatever outliers slip past both filters.

IMPORTANT: this transcript format is internal to Claude Code, not a
documented/stable schema, and has changed between versions before. This
script fails soft -- if a future format change breaks the field names it
expects, you'll just get "0 usable records" rather than a crash, so check
the reported counts. Subagent detection (via an `isSidechain` marker) is
similarly best-effort and may not catch every subagent transcript on every
version; treat the "source" column as a rough signal, not a guarantee.

USAGE

    python3 claude_code_tokrate_history.py                  # last 14 days, daily buckets
    python3 claude_code_tokrate_history.py --days 30 --by week
    python3 claude_code_tokrate_history.py --project myrepo  # only paths containing this substring
    python3 claude_code_tokrate_history.py --max-delta 120   # ignore gaps over 2 minutes
    python3 claude_code_tokrate_history.py --min-delta 1     # stricter near-instant filter
    python3 claude_code_tokrate_history.py --model-filter=sonnet
"""

import argparse
import glob
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def has_thinking(content):
    if not isinstance(content, list):
        return False
    return any(
        isinstance(b, dict) and b.get("type") in ("thinking", "redacted_thinking")
        for b in content
    )


def iter_transcript_files(project_filter):
    root = os.path.join(config_dir(), "projects")
    pattern = os.path.join(root, "**", "*.jsonl")
    for path in glob.glob(pattern, recursive=True):
        if project_filter and project_filter not in path:
            continue
        yield path


def process_file(path, cutoff, max_delta, min_delta, model_filter, records):
    """Stream one transcript file; append (timestamp, model, thinking, source, tok/s) tuples to records."""
    ts_by_uuid = {}
    try:
        f = open(path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            uuid = obj.get("uuid")
            ts = parse_ts(obj.get("timestamp"))
            if uuid and ts:
                ts_by_uuid[uuid] = ts

            if obj.get("type") != "assistant":
                continue
            if ts is None or ts < cutoff:
                continue

            message = obj.get("message") or {}
            usage = message.get("usage") or {}
            out_tok = usage.get("output_tokens")
            model = message.get("model")
            if not out_tok or not model:
                continue
            if model_filter and model_filter not in model.lower():
                continue

            parent_ts = ts_by_uuid.get(obj.get("parentUuid"))
            if not parent_ts:
                continue
            delta = (ts - parent_ts).total_seconds()
            # A near-zero delta isn't 350,000 tok/s of real throughput -- it's two
            # transcript lines landing at effectively the same instant (e.g. a
            # near-instant cache-hit reply, or a timestamp-resolution artifact).
            # min_delta drops those before they distort the average.
            if delta < min_delta or delta > max_delta:
                continue

            thinking = has_thinking(message.get("content"))
            source = "subagent" if obj.get("isSidechain") else "main"
            records.append((ts, model, thinking, source, out_tok / delta))


def bucket_key(ts, by):
    if by == "week":
        start = ts - timedelta(days=ts.weekday())
        return start.date().isoformat() + " (wk)"
    return ts.date().isoformat()


def _row(cols):
    """Join (text, width, align) cells with a guaranteed 2-space gap, so a value
    that overflows its nominal width pushes columns apart instead of merging
    into its neighbor."""
    parts = []
    for text, width, align in cols:
        parts.append(text.ljust(width) if align == "l" else text.rjust(width))
    return "  ".join(parts)


def _num(x):
    """Comma-grouped, 1 decimal -- keeps six-digit outliers legible."""
    return f"{x:,.1f}"


def render_trend(records, by):
    buckets = defaultdict(list)
    for ts, model, thinking, source, rate in records:
        buckets[(bucket_key(ts, by), model)].append(rate)
    if not buckets:
        return "(no data)"
    header = _row([("period", 14, "l"), ("model", 20, "l"), ("n", 5, "r"),
                   ("avg tok/s", 12, "r"), ("median", 10, "r")])
    lines = [header, "-" * len(header)]
    for (period, model), rates in sorted(buckets.items()):
        lines.append(_row([
            (period, 14, "l"), (model, 20, "l"), (str(len(rates)), 5, "r"),
            (_num(statistics.mean(rates)), 12, "r"),
            (_num(statistics.median(rates)), 10, "r"),
        ]))
    return "\n".join(lines)


def render_breakdown(records):
    buckets = defaultdict(list)
    for ts, model, thinking, source, rate in records:
        buckets[(model, "thinking" if thinking else "no-thinking", source)].append(rate)
    if not buckets:
        return "(no data)"
    header = _row([("model", 20, "l"), ("thinking", 14, "l"), ("source", 10, "l"),
                   ("n", 6, "r"), ("avg", 10, "r"), ("median", 10, "r"),
                   ("min", 9, "r"), ("max", 10, "r")])
    lines = [header, "-" * len(header)]
    for (model, thinking, source), rates in sorted(buckets.items(), key=lambda kv: -statistics.median(kv[1])):
        lines.append(_row([
            (model, 20, "l"), (thinking, 14, "l"), (source, 10, "l"),
            (str(len(rates)), 6, "r"),
            (_num(statistics.mean(rates)), 10, "r"),
            (_num(statistics.median(rates)), 10, "r"),
            (_num(min(rates)), 9, "r"),
            (_num(max(rates)), 10, "r"),
        ]))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=14, help="how many days of history to scan (default: 14)")
    parser.add_argument("--by", choices=["day", "week"], default="day", help="trend bucket size (default: day)")
    parser.add_argument("--project", type=str, default=None, help="only include paths containing this substring")
    parser.add_argument(
        "--model-filter", type=str, default=None,
        help="only include models whose id contains this text, case-insensitive "
             "(e.g. --model-filter=sonnet)",
    )
    parser.add_argument(
        "--max-delta", type=float, default=180.0,
        help="ignore gaps longer than this many seconds -- likely a human/permission-prompt "
             "pause, not model latency (default: 180)",
    )
    parser.add_argument(
        "--min-delta", type=float, default=0.5,
        help="ignore gaps shorter than this many seconds -- near-instant gaps produce "
             "nonsense tok/s values rather than real throughput (default: 0.5)",
    )
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    files = list(iter_transcript_files(args.project))
    if not files:
        print(f"No transcripts found under {os.path.join(config_dir(), 'projects')}")
        sys.exit(1)

    records = []
    model_filter = args.model_filter.lower() if args.model_filter else None
    for path in files:
        process_file(path, cutoff, args.max_delta, args.min_delta, model_filter, records)

    print(
        f"Scanned {len(files)} transcript file(s), {len(records)} usable assistant response(s) "
        f"in the last {args.days} day(s).\n"
    )

    if not records:
        print(
            "No usable records -- either no recent sessions, or the transcript format on this "
            "Claude Code version doesn't match what this script expects (it's unofficial/internal, "
            "see the module docstring)."
        )
        return

    print(f"Trend by {args.by}:\n")
    print(render_trend(records, args.by))
    print("\nOverall breakdown:\n")
    print(render_breakdown(records))


if __name__ == "__main__":
    main()
