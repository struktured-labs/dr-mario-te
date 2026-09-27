"""Reload-event boundaries, read from freeze_watch.log — a REAL event boundary (R95),
not a heuristic on the virus series.

WHY THIS EXISTS: the round boundary rule is "any INCREASE in virus count". A core
reload produces exactly that (a fresh board), so a freeze+reload is INDISTINGUISHABLE
from a round end by that rule. Left alone it fabricates a round boundary, inflating the
denominator of whichever arm froze and biasing that arm's per-round death rate DOWNWARD.
"""
import datetime, os, re, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "reload_events.txt")


def reload_epochs(refresh=False):
    if refresh or not os.path.exists(CACHE):
        out = subprocess.run(["ssh", "bluemage",
                              'command grep -a "RELOADED at" /media/fat/freeze_watch.log'],
                             capture_output=True, text=True, timeout=60).stdout
        open(CACHE, "w").write(out)
    eps = []
    for line in open(CACHE):
        m = re.search(r"RELOADED at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", line)
        if m:
            t = datetime.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ")
            eps.append(t.replace(tzinfo=datetime.timezone.utc).timestamp())
    return sorted(eps)


def drop_reload_rounds(records, epochs):
    """Exclude any round whose [start,end] spans a reload, AND the round after it.
    Returns (kept, dropped)."""
    kept, dropped, drop_next = [], [], False
    for r in records:
        spans = any(r["start"] <= e <= r["end"] for e in epochs)
        if spans:
            r = dict(r, excluded="spans a reload event")
            dropped.append(r); drop_next = True
        elif drop_next:
            r = dict(r, excluded="first round after a reload (partial/corrupt duration)")
            dropped.append(r); drop_next = False
        else:
            kept.append(r)
    return kept, dropped
