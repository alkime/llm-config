#!/usr/bin/env python3
"""
claude_code_tokrate.py

A tiny local OTLP/HTTP log receiver that turns Claude Code's own telemetry
into live tokens/second stats, broken down by model, thinking/effort level,
fast-mode, and session source (main thread / subagent / background) -- with
no external backend, database, or collector. This script IS the receiver:
everything lives in memory while it runs.

It works by listening for the `claude_code.api_request` event that Claude
Code emits after every API call. That event already carries model, effort
level, fast-mode flag, query_source (main thread vs. a named subagent),
output_tokens, and duration_ms -- so tok/s = output_tokens / (duration_ms/1000).

--------------------------------------------------------------------------
SETUP (one time)

Add this to ~/.claude/settings.json under "env" (user scope, NOT just a
shell export) so it applies to every Claude Code process on this machine --
including subagents spawned inside a session and locally-hosted background/
dispatched sessions (agent view), not just your interactive terminal:

    {
      "env": {
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        "OTEL_LOGS_EXPORTER": "otlp",
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318"
      }
    }

Note: subagents run inside the same process as their parent session, so
they're covered automatically once the parent session has telemetry on.
Locally-dispatched background sessions (agent view) run as separate local
processes that also read settings.json, so they're covered too. Remote
cloud sessions (claude-code-on-the-web / self-hosted runners) run on
infrastructure that can't reach your machine's localhost, so they won't
show up here -- that's a hard limitation of the "no backend" approach.

USAGE

    python3 claude_code_tokrate.py            # just listen, print a summary on Ctrl+C
    python3 claude_code_tokrate.py --live      # also print a refreshed table every 15s
    python3 claude_code_tokrate.py --verbose   # print every single request as it lands
    python3 claude_code_tokrate.py --port 4319 # if 4318 is taken (update the endpoint above too)

Leave it running in a spare terminal while you use Claude Code normally
(including background/dispatched sessions and subagents). Ctrl+C for a
final summary table.

CAVEATS

- duration_ms is total wall-clock request time (queueing/TTFT + generation
  + any retries), not pure decode speed. If you need to separate "slow to
  start" from "actually generates slower," that needs the trace span
  (`claude_code.llm_request`, which has ttft_ms) -- a further step beyond
  this script.
- Assumes OTEL_EXPORTER_OTLP_PROTOCOL=http/json (this receiver speaks
  plain JSON, not protobuf/gRPC).
- No persistence: stats reset when you stop the script. Add --verbose and
  redirect stdout to a file yourself if you want a durable log.
"""

import argparse
import gzip
import json
import statistics
import sys
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def attr_value(v):
    """Decode one OTLP AnyValue JSON object into a Python scalar."""
    if "stringValue" in v:
        return v["stringValue"]
    if "boolValue" in v:
        return v["boolValue"]
    if "intValue" in v:
        try:
            return int(v["intValue"])
        except (TypeError, ValueError):
            return None
    if "doubleValue" in v:
        try:
            return float(v["doubleValue"])
        except (TypeError, ValueError):
            return None
    return None


def flatten_attrs(attr_list):
    out = {}
    for a in attr_list or []:
        key = a.get("key")
        out[key] = attr_value(a.get("value", {}))
    return out


class Aggregator:
    def __init__(self):
        self.lock = threading.Lock()
        # key: (model, effort, speed, query_source, agent) -> list of (output_tokens, duration_ms)
        self.samples = defaultdict(list)
        self.seen = 0

    def add(self, model, effort, speed, query_source, agent, output_tokens, duration_ms):
        self.seen += 1
        if not duration_ms or duration_ms <= 0 or not output_tokens or output_tokens <= 0:
            return
        key = (
            model or "unknown",
            effort or "none",
            speed or "normal",
            query_source or "repl_main_thread",
            agent or "-",
        )
        with self.lock:
            self.samples[key].append((output_tokens, duration_ms))

    def snapshot(self):
        with self.lock:
            return {k: list(v) for k, v in self.samples.items()}


def render_table(snapshot, total_seen):
    if not snapshot:
        return f"(no usable api_request samples yet -- {total_seen} events seen)"
    rows = []
    for (model, effort, speed, qsrc, agent), samples in snapshot.items():
        rates = [tok / (ms / 1000) for tok, ms in samples]
        rows.append((
            model, effort, speed, qsrc, agent,
            len(rates),
            statistics.mean(rates),
            statistics.median(rates),
            min(rates),
            max(rates),
        ))
    rows.sort(key=lambda r: -r[6])  # sort by avg tok/s, fastest first
    header = (
        f"{'model':<20}{'effort':<8}{'speed':<8}{'source':<18}{'agent':<16}"
        f"{'n':>5}{'avg':>9}{'median':>9}{'min':>8}{'max':>8}"
    )
    lines = [header, "-" * len(header)]
    for model, effort, speed, qsrc, agent, n, avg, med, lo, hi in rows:
        lines.append(
            f"{model:<20}{effort:<8}{speed:<8}{qsrc:<18}{agent:<16}"
            f"{n:>5}{avg:>9.1f}{med:>9.1f}{lo:>8.1f}{hi:>8.1f}"
        )
    lines.append(f"\n({total_seen} total api_request events seen, "
                  f"{sum(len(v) for v in snapshot.values())} with usable timing)")
    return "\n".join(lines)


def make_handler(agg: Aggregator, verbose: bool):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # silence default per-request HTTP logging

        def do_POST(self):
            if not self.path.startswith("/v1/logs"):
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            if "gzip" in (self.headers.get("Content-Encoding") or "").lower():
                try:
                    body = gzip.decompress(body)
                except OSError:
                    pass

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                sys.stderr.write(
                    "Got a non-JSON payload -- make sure "
                    "OTEL_EXPORTER_OTLP_PROTOCOL=http/json is set "
                    "(this receiver doesn't speak protobuf/gRPC)\n"
                )
                return
            self._handle_payload(payload)

        def _handle_payload(self, payload):
            for rl in payload.get("resourceLogs", []):
                for sl in rl.get("scopeLogs", []):
                    for rec in sl.get("logRecords", []):
                        attrs = flatten_attrs(rec.get("attributes"))
                        if attrs.get("event.name") != "api_request":
                            continue
                        model = attrs.get("model")
                        effort = attrs.get("effort")
                        speed = attrs.get("speed")
                        qsrc = attrs.get("query_source")
                        agent = attrs.get("agent.name")
                        out_tok = attrs.get("output_tokens")
                        dur_ms = attrs.get("duration_ms")
                        agg.add(model, effort, speed, qsrc, agent, out_tok, dur_ms)
                        if verbose:
                            rate = (out_tok / (dur_ms / 1000)) if (out_tok and dur_ms) else 0
                            print(
                                f"[{model}] effort={effort or 'none':<6} speed={speed or 'normal':<6} "
                                f"src={qsrc or 'repl_main_thread':<18} "
                                f"{out_tok or 0}tok in {dur_ms or 0}ms -> {rate:.1f} tok/s",
                                flush=True,
                            )

    return Handler


def live_printer(agg: Aggregator, interval: float):
    while True:
        time.sleep(interval)
        snap = agg.snapshot()
        print("\n" + render_table(snap, agg.seen) + "\n", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=4318, help="port to listen on (default: 4318, the OTLP/HTTP default)")
    parser.add_argument("--live", action="store_true", help="print a refreshed summary table periodically")
    parser.add_argument("--interval", type=float, default=15.0, help="seconds between live table refreshes (default: 15)")
    parser.add_argument("--verbose", action="store_true", help="print every api_request event as it arrives")
    args = parser.parse_args()

    agg = Aggregator()
    handler = make_handler(agg, args.verbose)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)

    endpoint = f"http://localhost:{args.port}"
    print(f"Listening for Claude Code OTLP logs on {endpoint}/v1/logs\n")
    print("Make sure ~/.claude/settings.json has (user scope, so it covers background/subagent sessions too):")
    print(json.dumps({
        "env": {
            "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
            "OTEL_LOGS_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json",
            "OTEL_EXPORTER_OTLP_ENDPOINT": endpoint,
        }
    }, indent=2))
    print("\nCtrl+C for a final summary.\n")

    if args.live:
        t = threading.Thread(target=live_printer, args=(agg, args.interval), daemon=True)
        t.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nFinal summary:\n")
        print(render_table(agg.snapshot(), agg.seen))


if __name__ == "__main__":
    main()
