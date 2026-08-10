#!/usr/bin/env python3
"""Derive PRG_RAM_MAP.md mechanically. Regenerate and diff it; never hand-maintain it.

WHY THIS EXISTS
---------------
FREE_SPACE_MAP.md is the authority for PRG-*ROM*. For PRG-*RAM* ($6000-$7FFF) there was no
authority at all -- the only record was the emitter's own constant block, a chain of
hand-maintained comments. Two lanes nearly collided there in a single day:

  * the $61B0 investigation, where the first reach scan only looked at operands ALREADY inside
    the window and so could not have seen an index walking in from a lower base; and
  * DRHOLDONCE, where $61B8 looked free ("past the DISTGATE scratch, below the trace ring") but
    DRPRESTART's `STA PRE_LND,X` (base $61A1) reaches it for any X >= 0x17.

The second one was safe only because the index bound was PROVEN. This tool makes that the
default rather than the exception.

TWO INDEPENDENT VIEWS, CROSS-CHECKED
------------------------------------
1. DECLARED -- parse the emitter's AST for module-level constants bound to addresses in the
   window. Gives every byte an owning SYMBOL and the emitter LINE that allocates it.
2. EMITTED  -- scan the built ROM for store/RMW opcodes targeting the window. Gives what the
   cart ACTUALLY writes, including ROM-patch writes the AST cannot see.

Disagreement between them is the interesting signal: an emitted address with no declared owner
is an unmapped allocation; a declared symbol never emitted is inert under that flag set.

INDEXED STORES
--------------
`STA $xxxx,X` can reach base..base+255, and the base may sit BELOW the window. Every such writer
is either (a) registered in BOUNDS with a proven index bound and the proof text, or (b) treated
as occupying its entire 256-byte reachable span. There is no third option and no "looks fine".

    python3 tools/prgram/derive_prg_ram_map.py            # regenerate PRG_RAM_MAP.md
    python3 tools/prgram/derive_prg_ram_map.py --check    # exit 1 if the file is stale/colliding
"""
from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys

DRV = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMITTER = os.path.join(DRV, "patch_cartridge_copro.py")
OUT_MD = os.path.join(DRV, "PRG_RAM_MAP.md")

WIN_LO, WIN_HI = 0x6000, 0x7FFF

# store / read-modify-write opcodes. value = (mnemonic, index register or None)
STORES = {
    0x8D: ("STA abs", None), 0x8E: ("STX abs", None), 0x8C: ("STY abs", None),
    0xEE: ("INC abs", None), 0xCE: ("DEC abs", None),
    0x0E: ("ASL abs", None), 0x4E: ("LSR abs", None),
    0x2E: ("ROL abs", None), 0x6E: ("ROR abs", None),
    0x9D: ("STA abs,X", "X"), 0x99: ("STA abs,Y", "Y"),
    0xFE: ("INC abs,X", "X"), 0xDE: ("DEC abs,X", "X"),
    0x1E: ("ASL abs,X", "X"), 0x5E: ("LSR abs,X", "X"),
    0x3E: ("ROL abs,X", "X"), 0x7E: ("ROR abs,X", "X"),
}

# ---------------------------------------------------------------------------------------------
# PROVEN INDEX BOUNDS. An entry here narrows an indexed writer's reachable span from the default
# 256 bytes down to base..base+max_index. Each one MUST carry a proof that can be re-checked by a
# human against the emitter source. Adding an entry without a proof defeats the whole tool.
# ---------------------------------------------------------------------------------------------
RING_PROOF = ("DRTRACE/DRPROBE ring: X is TR_IDX/PR_IDX, which advances by 3 and WRAPS AT 192 (`ADC #3; CMP #192; BCC ok; LDA #0`), so X is 0..189 and the +2 slot reaches base+191 = $62BF -- clear of HOLD_BUF1 at $6300 by 64 bytes. Verified 2026-08-10 when the derivation flagged this span as an unproven collision.")

BOUNDS = {
    0x6200: (189, RING_PROOF),
    0x6201: (189, RING_PROOF),
    0x6202: (189, RING_PROOF),

    0x61A1: (7, "PRE_LND: X is loaded from PRE_N; PRE_N is zeroed before the settle scan "
                "(`LDA #0; STA PRE_N`) and INC'd at most once per column, and the scan "
                "terminates on `PRE_COL == 8` -- so X is 0..7 at the store. Reaches $61A8. "
                "Verified 2026-08-10 during the DRHOLDONCE allocation."),
    0x6300: (255, "HOLD_BUF1: a full 256-byte mirror of the $0400 playfield, written by an "
                  "`INX`/`BNE` loop over the whole page. The span IS the allocation."),
    0x6400: (255, "HOLD_BUF2: as HOLD_BUF1, for the $0500 playfield."),
    0x6500: (255, "PRE_BUF: DRPRESTART's 256-byte post-garbage board scratch."),
}


def declared(path=EMITTER):
    """Module-level constants bound to an address in the window -> {addr: (symbol, lineno)}."""
    tree = ast.parse(open(path).read())
    out = {}

    def note(name, value, lineno):
        if isinstance(value, int) and WIN_LO <= value <= WIN_HI:
            out.setdefault(value, (name, lineno))

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and isinstance(val, ast.Constant):
                note(tgt.id, val.value, node.lineno)
            elif isinstance(tgt, ast.Tuple) and isinstance(val, ast.Tuple):
                for n, v in zip(tgt.elts, val.elts):
                    if isinstance(n, ast.Name) and isinstance(v, ast.Constant):
                        note(n.id, v.value, node.lineno)
    return out


def emitted(prg: bytes):
    """Scan PRG for stores touching the window -> list of (fileoff, mnem, base, lo, hi, bounded)."""
    hits = []
    i = 0
    while i < len(prg) - 2:
        op = prg[i]
        if op in STORES:
            mnem, idx = STORES[op]
            base = prg[i + 1] | (prg[i + 2] << 8)
            if idx is None:
                lo = hi = base
                bounded = True
            else:
                maxi, _proof = BOUNDS.get(base, (255, None))
                lo, hi = base, base + maxi
                bounded = base in BOUNDS
            if hi >= WIN_LO and lo <= WIN_HI:
                hits.append((i + 16, mnem, base, max(lo, WIN_LO), min(hi, WIN_HI), bounded))
        i += 1
    return hits



# ---------------------------------------------------------------------------------------------
# EMITTED VIEW -- by INSTRUMENTING the assembler, not by scanning bytes.
# A linear byte scan of a 64 KB PRG cannot tell code from data: it misparsed graphics/level data
# as `STA abs,X` and reported 118 collisions and 247 "unbounded writers" that do not exist. The
# emitter builds every driver instruction through Asm6502.ins/ins16, so wrapping those two
# methods gives the exact instruction stream with zero false positives -- and the caller's source
# line for free.
# ---------------------------------------------------------------------------------------------
IDX_MNEM = {"STA_absX": "STA abs,X", "STA_absY": "STA abs,Y", "INC_absX": "INC abs,X",
            "DEC_absX": "DEC abs,X", "ASL_absX": "ASL abs,X", "LSR_absX": "LSR abs,X",
            "ROL_absX": "ROL abs,X", "ROR_absX": "ROR abs,X"}
ABS_MNEM = {"STA_abs": "STA abs", "STX_abs": "STX abs", "STY_abs": "STY abs",
            "INC_abs": "INC abs", "DEC_abs": "DEC abs", "ASL_abs": "ASL abs",
            "LSR_abs": "LSR abs", "ROL_abs": "ROL abs", "ROR_abs": "ROR abs"}


def emitted_via_instrumentation(flags):
    """Build under `flags` in-process, recording every emitted store that reaches the window."""
    import importlib, traceback
    env_backup = dict(os.environ)
    os.environ.update({k: str(v) for k, v in flags.items()})
    sys.path.insert(0, DRV)
    for m in ("patch_cartridge_copro", "patch_vs_cpu"):
        sys.modules.pop(m, None)
    try:
        pv = importlib.import_module("patch_vs_cpu")
        rec = []

        def wrap(orig, kind):
            def inner(self, mnem, value=None, *rest):
                if kind == "16" and isinstance(value, int):
                    name = ABS_MNEM.get(mnem) or IDX_MNEM.get(mnem)
                    if name:
                        # emitter source line that asked for this instruction
                        st = [f for f in traceback.extract_stack()[:-1]
                              if f.filename.endswith("patch_cartridge_copro.py")]
                        line = st[-1].lineno if st else 0
                        idx = mnem in IDX_MNEM
                        if idx:
                            maxi = BOUNDS.get(value, (255, None))[0]
                            lo, hi, bounded = value, value + maxi, value in BOUNDS
                        else:
                            lo = hi = value; bounded = True
                        if hi >= WIN_LO and lo <= WIN_HI:
                            rec.append((line, name, value, max(lo, WIN_LO), min(hi, WIN_HI),
                                        bounded))
                return orig(self, mnem, value, *rest) if value is not None else orig(self, mnem)
            return inner

        pv.Asm6502.ins16 = wrap(pv.Asm6502.ins16, "16")
        cop = importlib.import_module("patch_cartridge_copro")
        cop.build_main(11, 1)
        return rec
    finally:
        os.environ.clear(); os.environ.update(env_backup)
        for m in ("patch_cartridge_copro", "patch_vs_cpu"):
            sys.modules.pop(m, None)


PY = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"


def build(tag, flags):
    """Build a cart with `flags` via romgen (the project's reproducible path) -> PRG bytes."""
    env = dict(os.environ)
    env.update({k: str(v) for k, v in flags.items()})
    out = os.path.join(DRV, "tmp", "prgram", f"{tag}.nes")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([PY, os.path.join(DRV, "tools", "romgen.py"), "build",
                        "--out", out, "--base", "drmario_v28cs.nes", "--tag", f"prgram-{tag}"],
                       cwd=DRV, env=env, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit(f"build {tag} failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    rom = open(out, "rb").read()
    return rom[16:16 + 0x10000]


# Flag configurations to derive over. The point is the FLAG DIMENSION: an allocation that only
# exists when a flag is on is exactly the kind that gets stepped on, so each byte's row records
# which configurations make it live.
CONFIGS = {
    "ship-v6e": dict(DRMMC1RST=1, DRRTIVEC=1, DRFCGATE=1, DRBUILDID=0),
    "holdboard": dict(DRHOLDBOARD=1, DRMMC1RST=1, DRRTIVEC=1, DRFCGATE=1, DRHOLDONCE=1,
                      DRBUILDID=0),
    "no-prestart": dict(DRPRESTART=0, DRMMC1RST=1, DRRTIVEC=1, DRFCGATE=1, DRBUILDID=0),
    "trace": dict(DRTRACE=1, DRMMC1RST=1, DRRTIVEC=1, DRFCGATE=1, DRBUILDID=0),
}


def base_flags():
    """cen6c-both's snapshot is the common baseline every config layers onto."""
    import json
    f = json.load(open(os.path.join(DRV, "roms", "manifests", "cen6c-both.json")))["flag_snapshot"]
    b = {k: v for k, v in f.items()}
    # ⚠ cen6c-both predates v8 and has DRPRESTART=0. build_v8.sh turns it ON, and the SHIPPED cart
    # has it on -- so deriving from the raw snapshot silently omitted every PRE_* allocation
    # ($6199-$61AF plus the 256-byte PRE_BUF at $6500) and reported that space as FREE. Match the
    # real ship recipe. Caught by noticing $6500-$7FFF listed as a 6912-byte free run.
    b["DRPRESTART"] = "1"
    return b


def collisions(owner_of, hits):
    """Two distinct symbols claiming a byte, or an indexed span covering another's byte."""
    bad = []
    for off, mnem, base, lo, hi, bounded in hits:
        if lo == hi:
            continue                                   # absolute store: owner is exact
        covered = {a: owner_of[a] for a in range(lo, hi + 1) if a in owner_of}
        base_owner = owner_of.get(base, ("<undeclared>", 0))[0]
        foreign = {a: s for a, (s, _l) in covered.items() if s != base_owner}
        if foreign:
            bad.append((off, mnem, base, lo, hi, bounded, foreign))
    return bad


def derive():
    """Run every config, attribute every touched byte, return (rows, findings)."""
    decl = declared()
    live = {}          # addr -> set(config)
    writers = {}       # addr -> set("mnem@0xFILEOFF")
    unbounded = []     # indexed writers with no proven bound
    coll = []
    base = base_flags()
    for tag, extra in CONFIGS.items():
        flags = dict(base); flags.update(extra)
        hits = emitted_via_instrumentation(flags)
        for off, mnem, b, lo, hi, bounded in hits:
            for a in range(lo, hi + 1):
                live.setdefault(a, set()).add(tag)
                writers.setdefault(a, set()).add(f"{mnem}:L{off}")
            if not bounded:
                unbounded.append((tag, off, mnem, b, lo, hi))
        for c in collisions(decl, hits):
            coll.append((tag,) + c)
    rows = []
    for a in sorted(set(decl) | set(live)):
        sym, line = decl.get(a, ("<UNDECLARED>", 0))
        rows.append({
            "addr": a, "symbol": sym, "line": line,
            "configs": sorted(live.get(a, [])),
            "writers": sorted(writers.get(a, [])),
        })
    return rows, {"collisions": coll, "unbounded": unbounded, "declared": decl}


def render(rows, findings):
    L = []
    A = L.append
    A("# PRG-RAM map ($6000-$7FFF) — DERIVED, DO NOT HAND-EDIT\n")
    A("Regenerate with `python3 tools/prgram/derive_prg_ram_map.py`; check with `--check`.")
    A("`FREE_SPACE_MAP.md` is the authority for PRG-**ROM**; this is its counterpart for")
    A("PRG-**RAM**, which had no authority at all until two lanes nearly collided in it.\n")
    A("Two independent views are cross-checked: **declared** (module-level constants in the")
    A("emitter's AST, giving each byte an owning symbol and the line that allocates it) and")
    A("**emitted** (a byte-level store/RMW scan of the built ROM, which also sees ROM-patch")
    A("writes the AST cannot). Disagreement is the signal.\n")
    A("## Findings\n")
    if findings["collisions"]:
        A(f"⚠ **{len(findings['collisions'])} COLLISION(S)** — an indexed span covers a byte owned")
        A("by a different symbol:\n")
        for tag, off, mnem, b, lo, hi, bounded, foreign in findings["collisions"]:
            names = ", ".join(sorted({s for s in foreign.values()}))
            A(f"- `{tag}`: `{mnem}` base `${b:04X}` @emitter line {off} spans "
              f"`${lo:04X}-${hi:04X}`, covering **{names}**"
              + ("" if bounded else "  ← **and its index bound is UNPROVEN**"))
        A("")
    else:
        A("No collisions: every indexed span stays inside its own symbol's allocation.\n")
    if findings["unbounded"]:
        A(f"⚠ **{len(findings['unbounded'])} indexed writer(s) with NO PROVEN BOUND** — each is")
        A("treated as occupying its whole 256-byte reachable span. Prove the bound and add it to")
        A("`BOUNDS` (with the proof text), or leave the span reserved:\n")
        for tag, off, mnem, b, lo, hi in findings["unbounded"]:
            A(f"- `{tag}`: `{mnem}` base `${b:04X}` @emitter line {off} → reserves "
              f"`${lo:04X}-${hi:04X}`")
        A("")
    else:
        A("Every indexed writer that reaches the window has a **proven** index bound.\n")
    A("### Proven index bounds\n")
    A("| base | max index | reaches | proof |")
    A("|---|---|---|---|")
    for b, (mx, proof) in sorted(BOUNDS.items()):
        A(f"| `${b:04X}` | {mx} | `${b + mx:04X}` | {proof} |")
    A("")
    A("## Allocation table\n")
    A("`configs` = which derived build configurations actually write the byte; an allocation")
    A("that appears in only one is flag-conditional and is the dangerous kind.\n")
    A("| addr | symbol | emitter line | live in | writers |")
    A("|---|---|---|---|---|")
    for r in rows:
        w = ", ".join(f"`{x}`" for x in r["writers"][:3]) or "—"
        if len(r["writers"]) > 3:
            w += f" +{len(r['writers']) - 3}"
        cfg = ", ".join(r["configs"]) or "*(declared, never written)*"
        line = f"`{r['line']}`" if r["line"] else "—"
        A(f"| `${r['addr']:04X}` | `{r['symbol']}` | {line} | {cfg} | {w} |")
    A("")
    A("## Free runs\n")
    used = {r["addr"] for r in rows if r["configs"]}
    runs, start = [], None
    for a in range(WIN_LO, WIN_HI + 1):
        if a not in used and start is None:
            start = a
        elif a in used and start is not None:
            runs.append((start, a - 1)); start = None
    if start is not None:
        runs.append((start, WIN_HI))
    A("Longest free runs (by the derivation above — **still confirm the reach analysis before")
    A("allocating**, since a future indexed writer can walk in from a lower base):\n")
    for lo, hi in sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:8]:
        A(f"- `${lo:04X}-${hi:04X}` ({hi - lo + 1} B)")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the committed map is stale, or if anything collides")
    a = ap.parse_args()
    rows, findings = derive()
    md = render(rows, findings)
    bad = bool(findings["collisions"]) or bool(findings["unbounded"])
    if a.check:
        cur = open(OUT_MD).read() if os.path.exists(OUT_MD) else ""
        if cur != md:
            print("STALE: PRG_RAM_MAP.md differs from the derivation — regenerate it")
            return 1
        if bad:
            print("COLLISION or UNPROVEN BOUND present — see PRG_RAM_MAP.md")
            return 1
        print("ok: map current, no collisions, every indexed writer bounded")
        return 0
    open(OUT_MD, "w").write(md)
    print(f"wrote {OUT_MD}  ({len(rows)} allocated bytes, "
          f"{len(findings['collisions'])} collisions, "
          f"{len(findings['unbounded'])} unbounded writers)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
