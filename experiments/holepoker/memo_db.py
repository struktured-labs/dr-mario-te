#!/usr/bin/env python3
"""PERSISTENT CHAMPION-MOVE STORE — a durable project asset, not a cache.

`champion_move(board, cur, next)` is a PURE FUNCTION: the champion is
deterministic, so every evaluation we ever compute is valid forever, for every
lane, across restarts. At ~56 ms per reply and irreducible, recomputing is the
dominant cost of every search in this program. Persisting them converts the
depth limit from a COMPUTE budget into a DISK budget, and every hour of running
makes the next hour cheaper.

LAYOUT (LMDB at /mnt/data/drmario_adversary/champion_memo)
  key   = 260 bytes: col[128] ‖ vir[128] ‖ ca ‖ cb ‖ na ‖ nb   (raw int8/uint8)
  value = 1 byte: action (var*8 + col), or 0xFF for "no legal move"
Fixed-width keys, no serialisation, no schema. sqlite was rejected: the write
volume here is millions of tiny puts and its per-transaction overhead dominates.

CONCURRENCY. LMDB is single-writer / many-reader. Search workers therefore keep
a process-local dict and flush it in batches under a short write lock; readers
never block. `writemap=True` + `map_async` because the store lives on a 13 TB
ext4 volume where the OS page cache does the real work.

⚠ MEMORY IS CAPPED AND ENFORCED, not hoped for. This box has been OOM-killed 5
times by unbounded jobs (`oom-machine-kills`), and an OOM that takes the owner's
desktop with it is a worse outcome than a shallower search. The in-process dict
is bounded by entry count and flushed+cleared on the way past it; the LMDB map
size is a virtual reservation, not resident memory.
"""
from __future__ import annotations

import os
import numpy as np

DB_PATH = os.environ.get("HP_MEMO_DB",
                         "/mnt/data/drmario_adversary/champion_memo")
MAP_SIZE = int(os.environ.get("HP_MEMO_MAPSIZE", str(512 * 1024 ** 3)))  # 512 GB virtual
NO_MOVE = 0xFF
KEY_LEN = 260          # 128 col + 128 vir + 4 pill bytes


class ChampionMemo:
    """Two-tier memo: process-local dict in front, LMDB behind."""

    def __init__(self, path=DB_PATH, max_local=400_000, readonly=False,
                 flush_every=50_000):
        import lmdb
        self.path = path
        self.max_local = max_local
        self.flush_every = flush_every
        self.readonly = readonly
        os.makedirs(path, exist_ok=True)
        self.env = lmdb.open(path, map_size=MAP_SIZE, subdir=True,
                             readonly=readonly, lock=not readonly,
                             writemap=True, map_async=True, max_readers=256,
                             meminit=False)
        self.local = {}
        self.pending = {}
        self.stats = {"calls": 0, "hit_local": 0, "hit_db": 0, "miss": 0,
                      "written": 0}

    # ------------------------------------------------------------------ keys
    @staticmethod
    def key(col, vir, ca, cb, na, nb):
        return (col.tobytes() + vir.tobytes()
                + bytes((ca & 0xFF, cb & 0xFF, na & 0xFF, nb & 0xFF)))

    # ----------------------------------------------------------------- access
    def get(self, k):
        self.stats["calls"] += 1
        v = self.local.get(k)
        if v is not None:
            self.stats["hit_local"] += 1
            return None if v == NO_MOVE else v
        with self.env.begin(buffers=False) as txn:
            raw = txn.get(k)
        if raw is not None:
            a = raw[0]
            self.stats["hit_db"] += 1
            if len(self.local) < self.max_local:
                self.local[k] = a
            return None if a == NO_MOVE else a
        self.stats["miss"] += 1
        return _MISS

    def put(self, k, action):
        a = NO_MOVE if action is None else int(action)
        if len(self.local) < self.max_local:
            self.local[k] = a
        self.pending[k] = a
        if len(self.pending) >= self.flush_every:
            self.flush()

    def flush(self):
        if self.readonly or not self.pending:
            return 0
        import lmdb
        n = 0
        try:
            with self.env.begin(write=True) as txn:
                c = txn.cursor()
                c.putmulti(((k, bytes((v,))) for k, v in self.pending.items()),
                           dupdata=False, overwrite=True)
                n = len(self.pending)
        except lmdb.MapFullError:
            print("[memo] MAP FULL -- raise HP_MEMO_MAPSIZE", flush=True)
            self.pending.clear()
            return 0
        self.stats["written"] += n
        self.pending.clear()
        # bound resident memory: drop the local tier once it is safely on disk
        if len(self.local) >= self.max_local:
            self.local.clear()
        return n

    def close(self):
        self.flush()
        self.env.sync(True)
        self.env.close()

    # ------------------------------------------------------------------ info
    def info(self):
        st = self.env.stat()
        i = self.env.info()
        s = self.stats
        hit = s["hit_local"] + s["hit_db"]
        return {"entries": st["entries"],
                "disk_mb": round(i["last_pgno"] * st["psize"] / 1024 ** 2, 1),
                "local": len(self.local), "pending": len(self.pending),
                "calls": s["calls"], "hits": hit,
                "hit_rate": (hit / s["calls"]) if s["calls"] else 0.0,
                "hit_local": s["hit_local"], "hit_db": s["hit_db"],
                "written": s["written"]}


class _Miss:
    __slots__ = ()


_MISS = _Miss()
MISS = _MISS


# --------------------------------------------------------------- convenience
def open_memo(**kw):
    return ChampionMemo(**kw)


def stats_only(path=DB_PATH):
    """Read the store's size without writing to it."""
    import lmdb
    env = lmdb.open(path, map_size=MAP_SIZE, subdir=True, readonly=True,
                    lock=False, max_readers=256)
    st, i = env.stat(), env.info()
    out = {"entries": st["entries"],
           "disk_mb": round(i["last_pgno"] * st["psize"] / 1024 ** 2, 1)}
    env.close()
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        print(stats_only())
    else:
        m = ChampionMemo()
        print("opened", m.path, m.info())
        m.close()
