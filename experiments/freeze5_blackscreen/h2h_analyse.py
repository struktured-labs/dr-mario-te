#!/usr/bin/env python3
"""h2h_analyse.py — timestamp-aligned head-to-head: OLD /proc discriminator vs NEW frame watchdog.

Inputs
  --probe-log   a READ-ONLY slice of /media/fat/wedge_probe.log covering the window
  --watch-log   frame_watchdog.py's framewd/1 jsonl for the same window
Both carry absolute timestamps; PC and device clocks were measured aligned to <100 ms, so
UTC instants compare directly with no fitting or offset.

Alignment rule (stated so it cannot be tuned after seeing the answer):
  * the OLD probe's state AT a new-watchdog poll = its most recent poll line at or before
    that instant (it polls every ~30 s, the new one every 20 s);
  * an OLD ALERT_ONLY is attributed to the new-watchdog poll whose [t, t+interval) window
    contains it.
The headline contradiction count is: ALERT_ONLY firings during which the new watchdog's
verdict was ALIVE.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

POLL = re.compile(
    r"^(?P<ts>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\s+uptime=(?P<up>[\d.]+).*?"
    r"fw_pid=(?P<pid>\S+)\s+fw_state=(?P<state>\S+).*?"
    r"busy_frac=(?P<busy>\d+)%\s+consec=(?P<consec>\d+)")
ALERT = re.compile(r"^(?P<ts>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\s+(?P<kind>ALERT_ONLY|AUTO_REBOOT)")


def tsec(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-log", required=True)
    ap.add_argument("--watch-log", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    polls, alerts = [], []
    with open(a.probe_log, "rb") as fh:                    # binary: the log may carry NULs
        for raw in fh:
            line = raw.decode("utf-8", "replace").strip()
            m = POLL.match(line)
            if m:
                polls.append({"t": tsec(m["ts"]), "ts": m["ts"], "busy": int(m["busy"]),
                              "consec": int(m["consec"]), "state": m["state"],
                              "pid": m["pid"]})
                continue
            m = ALERT.match(line)
            if m:
                alerts.append({"t": tsec(m["ts"]), "ts": m["ts"], "kind": m["kind"]})

    watch = []
    with open(a.watch_log) as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                r["t"] = datetime.fromisoformat(r["ts"]).timestamp()
                watch.append(r)
    watch.sort(key=lambda r: r["t"])
    if not watch:
        print("no watchdog records")
        return 1

    t0, t1 = watch[0]["t"], watch[-1]["t"]
    interval = watch[0].get("interval_s", 20.0)
    polls_w = [p for p in polls if t0 - 60 <= p["t"] <= t1 + 60]
    alerts_w = [x for x in alerts if t0 <= x["t"] <= t1 + interval]

    rows = []
    for r in watch:
        prior = [p for p in polls_w if p["t"] <= r["t"]]
        old = prior[-1] if prior else None
        fired = [x for x in alerts_w if r["t"] <= x["t"] < r["t"] + interval]
        rows.append({
            "seq": r["seq"], "ts": r["ts"], "new_verdict": r["verdict"],
            "new_reason": r["reason"], "changed_frac": r.get("changed_frac"),
            "screen_class": r.get("screen_class"), "capture_ms": r.get("capture_ms"),
            "old_ts": old["ts"] if old else None,
            "old_busy": old["busy"] if old else None,
            "old_consec": old["consec"] if old else None,
            "old_state": old["state"] if old else None,
            "old_alert": bool(fired),
            "old_signature": bool(old and old["busy"] >= 100 and old["state"] == "R"),
        })

    contradictions = [r for r in rows if r["old_alert"] and r["new_verdict"] == "ALIVE"]
    agree_wedge = [r for r in rows if r["old_alert"] and r["new_verdict"] == "WEDGED"]
    new_counts = {}
    for r in rows:
        new_counts[r["new_verdict"]] = new_counts.get(r["new_verdict"], 0) + 1

    busy100 = [p for p in polls_w if p["busy"] >= 100]
    stateR = [p for p in polls_w if p["state"] == "R"]

    summary = {
        "window_start_utc": datetime.fromtimestamp(t0, timezone.utc).isoformat(),
        "window_end_utc": datetime.fromtimestamp(t1, timezone.utc).isoformat(),
        "window_minutes": round((t1 - t0) / 60.0, 2),
        "new_polls": len(rows), "new_verdict_counts": new_counts,
        "new_wedged": new_counts.get("WEDGED", 0),
        "old_polls_in_window": len(polls_w),
        "old_polls_busy_ge_100": len(busy100),
        "old_polls_state_R": len(stateR),
        "old_max_consec": max((p["consec"] for p in polls_w), default=None),
        "old_alerts_in_window": len(alerts_w),
        "old_alert_times": [x["ts"] for x in alerts_w],
        "old_alert_kinds": sorted({x["kind"] for x in alerts_w}),
        "contradictions_old_alert_new_alive": len(contradictions),
        "agreements_old_alert_new_wedged": len(agree_wedge),
        "changed_frac_at_old_alerts": [r["changed_frac"] for r in contradictions],
    }
    with open(a.out, "w") as fh:
        json.dump({"summary": summary, "rows": rows}, fh, indent=1, sort_keys=True)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
