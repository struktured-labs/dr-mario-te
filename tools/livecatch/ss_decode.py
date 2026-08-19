#!/usr/bin/env python3
"""LIVE-CATCH: decode a MiSTer NES save-state into board + driver mailbox, and answer the
one question the user's sighting turns on --

    did the SEARCH commit the placement that the DRIVER actually landed?

WHY THIS EXISTS. Three times now the user has watched the shipped core hold a two-colour
pill over two ready columns and take a vertical single instead of the horizontal instant
double. The offline probe reproduced a miss at mid-bottle height (3/9 at h3) but could not
say WHICH of two very different faults it is:

    (a) VALUATION -- the search genuinely preferred a cascade/other line. Nothing is broken;
        the champion is doing the on-brand thing and it merely looks sequential on screen.
    (b) EXECUTION -- the search committed the double and the DRIVER landed something else.
        That is the pair-latch defect (task #1), whose fix has been deployed but never
        verified end to end on silicon.

Those want opposite responses -- (a) is a priced eval credit, (b) is a driver bug -- and
buying one against a misdiagnosis is how you spend a week on the wrong half. A save-state
carries BOTH sides at once: the game's board and capsule state, and the driver's PRG-RAM
mailbox holding what the copro published. So a single snapshot discriminates.

CONTAINER LAYOUT, RE-DERIVED (not taken on faith)
-------------------------------------------------
MiSTer NES save-states are a fixed 1,327,112 bytes. The CPU work RAM base was pinned by a
CROSS-ADDRESS invariant rather than by eyeballing a hexdump: the virus COUNTER byte must
equal the viruses actually present on that player's board,

    popcount(0xD0-0xD2 in $0400..$047F) == bcd($0324)      [P1]
    popcount(0xD0-0xD2 in $0500..$057F) == bcd($03A4)      [P2]

-- two equalities over four addresses spanning 0x280 bytes, which a wrong base has to
satisfy by coincidence twice. That returns exactly ONE offset, 0x102B08, identical across
all five save-states tested (two from the wiggle campaign, three from driver_nav).

Cartridge WRAM then follows CPU RAM contiguously, so $6000 -> 0x103308. Three independent
checks agree: NAV_MAGIC = $A5 at $6149 in every driver cart; the DRTRACE ring magic $54 at
$62C6 present in a DRPROBE build and absent in a normal one; and the resulting ring base
0x103508 matches the offset the driver comment recorded on 2026-07-22 from an unrelated
manual decode. TGT_C1 also reads $50 in the wiggle carts -- the open-bus byte from the
stripped $5000 window, i.e. the instrument independently reproduces the known P1-idle
root cause.

★ THE OFFSET IS A HINT, NEVER AN ASSUMPTION. locate_ram() re-derives it by SIGNATURE on
every file. A MiSTer core update that moves the layout would otherwise make this print a
perfectly plausible WRONG board -- the exact failure class that has cost this project the
most time (a confident number from a stale or mis-parsed source). Decoding garbage silently
is worse than refusing.

WHY THE VIRUS INVARIANT IS NO LONGER THE LOCATOR (task #130, 2026-08-19)
-----------------------------------------------------------------------
The first version located the base by a cross-address VIRUS-COUNT invariant: popcount of
$D0-$D2 in each playfield must equal the BCD counter, over tiles drawn from a LEGAL_TILE
set of {empty, virus, pill}. That set was incomplete, and the consequence was an instrument
outage, not a decode error:

  * $B0-$BF is the CLEAR-ANIMATION tile (`clearedPillOrVirus = $B0`, colour in the low
    nibble). It is on the board during every clear, i.e. routinely.
  * $8D/$8F/$EF are the stock GAME OVER / stage-clear TEXT BOX tiles, which renderGameOver
    writes into the playfield array itself.

So a perfectly healthy mid-clear frame failed the "legal playfield" test. Worse, the code
then reported that failure as "the game was at a title/menu screen, not in a match" -- and
the 99-file wedge corpus of 2026-08-18 was refused 99/99 with that message while sitting at
mode $04, mid-match, holding exactly the $BF board the #129 wedge produces. A capture the
decoder was built to read was described as a menu frame.

⇒ The base is now derived by a DRIVER-STATE SIGNATURE (NAV_MAGIC $6149 == $A5 plus
MATCH_ACTIVE $6164 == 1 and four flags/TURN constrained to their legal ranges), per
mister-savestate-ram-read. The virus invariant survives as a CORROBORATION that is reported,
never as a gate. And a failed scan says what it searched and how many offsets it tried --
"absence is not pass": a scan that finds nothing must never be reported as a game-state fact.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys

SS_SIZE = 1327112
RAM_HINT = 0x102B08          # CPU work RAM $0000 -- a hint to try first, never an assumption
WRAM_DELTA = 0x800           # cartridge WRAM $6000 follows CPU RAM contiguously

# Playfield tiles. The first three groups are the resting board; the last two are transient
# but entirely normal, and omitting them is what made the old locator refuse live captures.
LEGAL_TILE = (set([0x00, 0xFF])
              | set(range(0x40, 0x90))     # pill halves / orphans, colour in low nibble
              | set(range(0xD0, 0xD3))     # viruses
              | set(range(0xB0, 0xC0))     # clearedPillOrVirus $B0 | colour -- clear anim
              | set([0x8D, 0x8F, 0xEF]))   # GAME OVER / stage-clear text-box tiles
VIRUS_TILE = set(range(0xD0, 0xD3))
COLOURS = {0: 'Y', 1: 'R', 2: 'B'}

# Per-player struct: P1 at $0300, P2 at $0380 (+$80). Playfields are separate arrays.
PLAYERS = {
    1: dict(base=0x0300, field=0x0400),
    2: dict(base=0x0380, field=0x0500),
}
OFF_PILLX, OFF_PILLY, OFF_VIRUS, OFF_ORIENT, OFF_LEVEL = 0x05, 0x06, 0x24, 0x25, 0x16

# Driver's own high/low threshold (DRSLAM_LOWY, default 8). Above it the capsule is in open
# air and the driver may still retarget; below it the placement is effectively locked in.
CROSS_LOWY = 8

# Driver mailbox in PRG-RAM. Names and addresses from patch_cartridge_copro.py.
MAILBOX = [
    ("NAV_MAGIC",  0x6149), ("WHICH",      0x614D),
    ("TGT_C1",     0x6150), ("TGT_O1",     0x6151),
    ("TGT_C2",     0x6152), ("TGT_O2",     0x6153),
    ("LASTY2",     0x6155), ("TURN",       0x6160),
    ("ARMED2",     0x6161), ("WDOG2",      0x6162),
    ("MATCH_ACT",  0x6164), ("EFF_C2",     0x617B),
    ("ROT_DONE2",  0x616E), ("LAST_COL2",  0x616F),
    ("LAST_ORI2",  0x6170), ("STABLE_CT2", 0x6171),
    ("SLAM_ARM",   0x6172), ("BUSY",       0x6176),
    ("TUCK_C2",    0x6179), ("TUCK_R2",    0x617A),
    ("WIG_DIR",    0x617C),
]


class NotASaveState(Exception):
    pass


class NotInAMatch(NotASaveState):
    """Container is fine, the GAME just wasn't playing when the snapshot was taken.

    Worth its own type because a live ring will capture title and level-select frames as a
    matter of course, and "skip, the game was at a menu" is a completely different fact
    from "the save-state layout moved". Collapsing them would make a routine, expected
    event look like an instrument failure.
    """


def bcd(b):
    if (b & 0x0F) > 9 or ((b >> 4) & 0x0F) > 9:
        return None
    return (b >> 4) * 10 + (b & 0x0F)


# ---------------------------------------------------------------------------------------
# THE SIGNATURE. Anchors are driver PRG-RAM addresses whose values are pinned or bounded
# for any running driver cart, per mister-savestate-ram-read: several independent bytes at
# fixed spacings, so a wrong offset has to satisfy all of them by coincidence at once.
#
# MATCH_ACTIVE is deliberately in the STRICT set only. A menu/title frame is a legitimate,
# routine capture whose base is still locatable -- so the scan falls back to the RELAXED
# set (no MATCH_ACTIVE) and, if that pins a base, reports "not in a match" as a positive
# finding rather than as a location failure.
SIG_EXACT = [("NAV_MAGIC", 0x6149, 0xA5)]
SIG_MATCH = [("MATCH_ACTIVE", 0x6164, 1)]
SIG_RANGE = [("TURN", 0x6160, (0, 2)),
             ("f_6143", 0x6143, (0, 1)),
             ("ARMED2", 0x6161, (0, 1)),
             ("f_614E", 0x614E, (0, 1)),
             ("ROT_DONE2", 0x616E, (0, 1))]
SIG_SPAN = 0x200                 # highest anchor offset touched from the WRAM base


def _signature_holds(buf, wram, strict=True):
    """True if the driver-state signature sits at this cartridge-WRAM base."""
    if wram < 0 or wram + SIG_SPAN > len(buf):
        return False
    anchors = SIG_EXACT + (SIG_MATCH if strict else [])
    for _name, addr, want in anchors:
        if buf[wram + addr - 0x6000] != want:
            return False
    for _name, addr, (lo, hi) in SIG_RANGE:
        if not lo <= buf[wram + addr - 0x6000] <= hi:
            return False
    return True


def _scan_signature(buf, strict=True):
    """Every WRAM base in the container satisfying the signature, plus the number tried.

    Seeded off NAV_MAGIC so the sweep is a bytes.find walk rather than a 1.3M-iteration
    Python loop, but the CANDIDATE COUNT reported is the full search space -- the error
    message must describe what was searched, not what survived the first filter.
    """
    lo, hi = 0, len(buf) - SIG_SPAN
    _name, magic_addr, magic_val = SIG_EXACT[0]
    delta = magic_addr - 0x6000
    hits, i = [], 0
    while True:
        i = buf.find(bytes([magic_val]), i)
        if i < 0:
            break
        w = i - delta
        if lo <= w < hi and _signature_holds(buf, w, strict):
            hits.append(w)
        i += 1
    return hits, hi - lo


def _describe_signature(strict=True):
    parts = [f"{n} ${a:04X}==${v:02X}" for n, a, v in SIG_EXACT + (SIG_MATCH if strict else [])]
    parts += [f"{n} ${a:04X} in {lo}..{hi}" for n, a, (lo, hi) in SIG_RANGE]
    return "; ".join(parts)


def virus_invariant(buf, ram):
    """CORROBORATION, never a locator: virus popcount vs the BCD counter, per player.

    Returns (ok, note). This used to gate the base, and doing so took the decoder offline
    for every clear animation and every game-over board -- see the module docstring. It is
    reported now, so a genuine mis-parse is still visible without a normal frame being
    refused.
    """
    p1 = buf[ram + 0x400:ram + 0x480]
    p2 = buf[ram + 0x500:ram + 0x580]
    c1, c2 = bcd(buf[ram + 0x324]), bcd(buf[ram + 0x3A4])
    v1 = sum(1 for b in p1 if b in VIRUS_TILE)
    v2 = sum(1 for b in p2 if b in VIRUS_TILE)
    bad = [b for b in list(p1) + list(p2) if b not in LEGAL_TILE]
    notes = []
    if c1 is None or c2 is None:
        notes.append(f"virus counter not BCD (${buf[ram+0x324]:02X}/${buf[ram+0x3A4]:02X})")
    else:
        if v1 != c1:
            notes.append(f"P1 viruses on board {v1} != counter {c1}")
        if v2 != c2:
            notes.append(f"P2 viruses on board {v2} != counter {c2}")
    if bad:
        notes.append(f"{len(bad)} tile(s) outside the known encoding, e.g. "
                     f"${bad[0]:02X}")
    return (not notes), "; ".join(notes) or "virus counts agree; all tiles known"


def locate_ram(buf, hint=RAM_HINT):
    """Return (cpu_ram_base, how), derived by SIGNATURE with the constant only as a hint.

    ★ THE SCAN ALWAYS RUNS. There is deliberately no "trust the hint and skip" fast path:
    that path is what lets a stale constant stay load-bearing, and it also means a second,
    decoy copy of the signature elsewhere in the container would be resolved silently by
    whichever one the constant happened to name. The scan is seeded off NAV_MAGIC via
    bytes.find, so a full 1.3 MB sweep costs single-digit milliseconds; `hint` is now only
    used to say, in the `how` string, whether the recorded constant still agrees.

    Ladder: strict scan; then a relaxed scan dropping MATCH_ACTIVE, which distinguishes
    "the game was at a menu" from "I could not find the driver at all". Every failure names
    the anchors it searched and how many offsets it tried -- a scan that found nothing must
    never be dressed up as a fact about the game.
    """
    strict, n = _scan_signature(buf, strict=True)
    if len(strict) == 1:
        w = strict[0]
        ram = w - WRAM_DELTA
        agree = "matches RAM_HINT" if hint is not None and ram == hint else (
            f"DISAGREES with RAM_HINT 0x{hint:06X} -- container layout moved (core update?)"
            if hint is not None else "no hint")
        return ram, (f"signature scan located WRAM 0x{w:06X} -> CPU RAM 0x{ram:06X} "
                     f"({agree}; {_describe_signature()})")
    if len(strict) > 1:
        raise NotASaveState(
            f"signature is AMBIGUOUS: {len(strict)} offsets satisfy [{_describe_signature()}] "
            f"over {n} candidate offsets ({', '.join('0x%06X' % w for w in strict[:5])}). "
            "Refusing to decode a board I cannot place."
        )

    relaxed, _ = _scan_signature(buf, strict=False)
    if len(relaxed) == 1:
        w = relaxed[0]
        raise NotInAMatch(
            f"driver located at WRAM 0x{w:06X} (anchors [{_describe_signature(strict=False)}] "
            f"all hold), but MATCH_ACTIVE $6164 = {buf[w + 0x164]} != 1 -- the game was not "
            "in a match when this was captured. Skip."
        )
    if len(relaxed) > 1:
        raise NotASaveState(
            f"signature is AMBIGUOUS: no offset satisfies MATCH_ACTIVE, and {len(relaxed)} "
            f"satisfy the relaxed anchors [{_describe_signature(strict=False)}] over {n} "
            f"candidate offsets ({', '.join('0x%06X' % w for w in relaxed[:5])}). Refusing "
            "to decode a board I cannot place."
        )
    raise NotASaveState(
        f"no driver signature found in {n} candidate offsets. Searched for "
        f"[{_describe_signature()}] (strict: 0 hits) and [{_describe_signature(strict=False)}] "
        f"(relaxed: {len(relaxed)} hits). This is an ABSENCE, not a statement about the game "
        "state: either the cart is not a driver build, the container layout changed, or the "
        "capture is not a MiSTer NES save-state."
    )


class Snapshot:
    def __init__(self, path, buf=None):
        self.path = path
        self.buf = open(path, 'rb').read() if buf is None else buf
        if len(self.buf) != SS_SIZE:
            raise NotASaveState(
                f"{path}: {len(self.buf)} bytes, expected {SS_SIZE}. Truncated capture "
                "(the 0-byte/partial scp race) or a different core's save-state."
            )
        self.ram, self.how = locate_ram(self.buf)
        self.wram = self.ram + WRAM_DELTA
        self.invariant_ok, self.invariant_note = virus_invariant(self.buf, self.ram)

    # -- raw accessors -------------------------------------------------------------
    def cpu(self, addr):
        return self.buf[self.ram + addr]

    def prg(self, addr):
        return self.buf[self.wram + (addr - 0x6000)]

    def field(self, player):
        f = PLAYERS[player]['field']
        return self.buf[self.ram + f:self.ram + f + 128]

    def player(self, n):
        b = PLAYERS[n]['base']
        return dict(
            level=self.cpu(b + OFF_LEVEL),
            viruses=bcd(self.cpu(b + OFF_VIRUS)),
            pill_x=self.cpu(b + OFF_PILLX),
            pill_y=self.cpu(b + OFF_PILLY),
            orient=self.cpu(b + OFF_ORIENT),
        )

    def mailbox(self):
        return {name: self.prg(a) for name, a in MAILBOX}

    # -- rendering -----------------------------------------------------------------
    def render(self, player):
        rows = []
        f = self.field(player)
        for r in range(16):
            line = ''
            for c in range(8):
                t = f[r * 8 + c]
                if t in (0x00, 0xFF):
                    line += '.'
                elif t in VIRUS_TILE:
                    line += COLOURS.get(t & 0x0F, '?')
                elif 0xB0 <= t <= 0xBF:
                    line += '*'          # mid-clear animation, not a resting cell
                elif t in (0x8D, 0x8F, 0xEF):
                    line += '#'          # GAME OVER / stage-clear text box
                else:
                    line += COLOURS.get(t & 0x0F, '?').lower()
            rows.append(line)
        return rows

    # -- the discriminator ---------------------------------------------------------
    def verdict(self):
        """SEARCH-committed vs DRIVER-landed, for P2 (the copro side).

        ★ COLUMN IS THE LOAD-BEARING SIGNAL; ORIENTATION IS REPORTED BUT NOT TRUSTED.
        Column is unambiguous -- 0-7 on both sides. Orientation is NOT settled: the driver
        comments call the published value "MAPPED game-orient" (so directly comparable to
        $03A5), while the 2026-07-27 silicon fingerprint run concluded the opposite, that
        "the mailbox TGT_O2 raw byte is copro-space and my V/H display map for it is WRONG
        -- read the placed cells for true game-space orient". Two sources of record
        disagree, and the copro map {0xFF/0:3, 1:1, 2:0, 3:2} does not obviously line up
        with "0 = the horizontal spawn orient" either.

        So the verdict does not hinge on an orientation equality. Resolving it needs
        geometry: the two cells a pill leaves on the board show horizontal-vs-vertical
        directly, and the ring gives consecutive frames to pair a live orient byte with the
        shape it produced. Until then, an orientation mismatch is FLAGGED, never decisive.
        """
        m = self.mailbox()
        p2 = self.player(2)
        tgt_c, tgt_o = m['TGT_C2'], m['TGT_O2']
        out = dict(committed_col=tgt_c, committed_orient=tgt_o,
                   live_col=p2['pill_x'], live_orient=p2['orient'],
                   pill_y=p2['pill_y'], armed=m['ARMED2'],
                   rot_done=m['ROT_DONE2'], stable=m['STABLE_CT2'])
        if tgt_c >= 8:
            out['state'] = 'NO-COMMIT'
            out['note'] = (f"published column {tgt_c} is not a board column. "
                           f"{'$50 = open bus: this core does not decode the copro window.' if tgt_c == 0x50 else 'Noise or no result yet.'}")
        elif m['ARMED2'] == 0:
            out['state'] = 'IDLE'
            out['note'] = "driver not armed for this pill; nothing committed to compare."
        elif tgt_c == p2['pill_x']:
            out['state'] = 'MATCH'
            out['note'] = ("capsule is on the committed COLUMN. If the outcome still looks "
                           "wrong, the fault is VALUATION, not execution.")
            if tgt_o != p2['orient']:
                out['note'] += (f" (orient bytes differ: live {p2['orient']} vs published "
                                f"{tgt_o} -- NOT decisive, the two spaces are unresolved; "
                                f"LAST_ORI2={m['LAST_ORI2']}.)")
        else:
            diffs = [f"column {p2['pill_x']} != committed {tgt_c}"]
            # ★ HEIGHT DECIDES WHETHER DIVERGENCE MEANS ANYTHING, AND THE AXIS IS INVERTED
            # FROM THE OBVIOUS READING. $0386 counts UP FROM THE FLOOR (driver line 134),
            # so a LARGE Y is a capsule near the TOP -- freshly spawned, with the driver
            # still steering it toward the target. Divergence there is the system working.
            # My first version had this backwards and called Y=15 "low", which would have
            # reported a healthy in-flight snapshot as the pair-latch signature.
            if p2['pill_y'] >= CROSS_LOWY:
                out['state'] = 'STEERING'
                out['note'] = ("; ".join(diffs) + f". Capsule is HIGH (Y={p2['pill_y']} >= "
                               f"CROSS_LOWY {CROSS_LOWY}), so the driver is still steering "
                               "toward the target. NOT evidence of anything -- recapture lower.")
            else:
                out['state'] = 'DIVERGED-LOW'
                out['note'] = ("; ".join(diffs) + f". Capsule is LOW (Y={p2['pill_y']} < "
                               f"CROSS_LOWY {CROSS_LOWY}) -- too late to correct. This is "
                               "the EXECUTION-divergence shape: the pair-latch signature, "
                               "task #1.")
        return out


def report(path, as_json=False):
    s = Snapshot(path)
    p1, p2 = s.player(1), s.player(2)
    v = s.verdict()
    if as_json:
        print(json.dumps(dict(path=path, ram_base=s.ram, how=s.how,
                              invariant_ok=s.invariant_ok, invariant=s.invariant_note,
                              p1=p1, p2=p2, mailbox=s.mailbox(), verdict=v,
                              board_p1=s.render(1), board_p2=s.render(2)), indent=2))
        return s
    print(f"== {path}")
    print(f"   RAM base 0x{s.ram:06X}  WRAM 0x{s.wram:06X}   [{s.how}]")
    print(f"   corroboration: {'OK' if s.invariant_ok else 'NOTE'} -- {s.invariant_note}")
    print(f"   P1 level {p1['level']:2d} viruses {p1['viruses']}   "
          f"P2 level {p2['level']:2d} viruses {p2['viruses']}")
    print()
    r1, r2 = s.render(1), s.render(2)
    print("      P1        P2")
    for a, b in zip(r1, r2):
        print(f"    {a}  {b}")
    print()
    print(f"   P2 capsule : col {p2['pill_x']} row {p2['pill_y']} orient {p2['orient']}")
    m = s.mailbox()
    print("   mailbox    : " + "  ".join(f"{k}={m[k]}" for k in
          ('ARMED2', 'TGT_C2', 'TGT_O2', 'ROT_DONE2', 'LAST_COL2', 'LAST_ORI2',
           'STABLE_CT2', 'BUSY')))
    print()
    print(f"   VERDICT: {v['state']} -- {v['note']}")
    return s


# ---------------------------------------------------------------------------------------
# SELF-TEST
#
# Gate standard (dr-mario-gate-standard-killed-mutants): a check must be shown to FAIL on
# wrong inputs, not merely pass on right ones. Each fixture below is a real 0x1000-byte
# silicon window replanted in a full-size container; each MUTANT is that same window with
# one signature byte broken, and every mutant must be refused with a message that NAMES
# what was searched. The relocation case is the one that would have been caught by the old
# code too; the clear-animation and text-box cases are the ones that took it offline.
# ---------------------------------------------------------------------------------------

FIXDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
WINDOW = 0x1000


def _container(win, base):
    """A full-size save-state holding `win` at `base`, zero elsewhere.

    Zero-fill is a deliberately hostile background for the locator: it can produce neither
    NAV_MAGIC ($A5) nor a decoy playfield, so any base the scan returns came from the
    fixture's own bytes.
    """
    buf = bytearray(SS_SIZE)
    buf[base:base + len(win)] = win
    return bytes(buf)


def _fixtures():
    with open(os.path.join(FIXDIR, 'manifest.json')) as fh:
        man = json.load(fh)
    out = []
    for e in man:
        with gzip.open(os.path.join(FIXDIR, e['name']), 'rb') as fh:
            win = fh.read()
        got = hashlib.sha256(win).hexdigest()
        if got != e['sha256']:
            raise AssertionError(f"{e['name']}: sha256 {got[:12]} != manifest {e['sha256'][:12]}")
        out.append((e, win))
    return out


def selftest(verbose=True):
    cases, failures = [], []

    def check(name, want, fn):
        try:
            got = fn()
        except Exception as e:          # noqa: BLE001 -- the exception IS the observable
            got = f"{type(e).__name__}: {e}"
        ok = want(got)
        cases.append((ok, name, got))
        if not ok:
            failures.append(name)

    for e, win in _fixtures():
        base, tag = e['ram_base'], e['source']
        in_match = win[WRAM_DELTA + 0x164] == 1

        # (1) decodes at the recorded base
        if in_match:
            check(f"{tag}: decodes",
                  lambda g: isinstance(g, Snapshot) and g.ram == base,
                  lambda: Snapshot(tag, _container(win, base)))
        else:
            check(f"{tag}: reported not-in-a-match, naming MATCH_ACTIVE",
                  lambda g: isinstance(g, str) and g.startswith('NotInAMatch')
                  and 'MATCH_ACTIVE' in g,
                  lambda: Snapshot(tag, _container(win, base)))

        # (2) RELOCATED: the constant must not be load-bearing. Same bytes, different
        #     offset -- the signature scan has to find them without the hint.
        moved = base + 0x4000
        check(f"{tag}: relocated to 0x{moved:06X} is found by scan",
              lambda g, m=moved: (isinstance(g, Snapshot) and g.ram == m) or
              (isinstance(g, str) and g.startswith('NotInAMatch') and 'MATCH_ACTIVE' in g),
              lambda m=moved: Snapshot(tag, _container(win, m)))

        # (3) MUTANT A: NAV_MAGIC corrupted -> must refuse, naming the anchors searched.
        mA = bytearray(win)
        mA[WRAM_DELTA + 0x149] ^= 0xFF
        check(f"{tag}: MUTANT nav_magic -> refused, names the search",
              lambda g: isinstance(g, str) and g.startswith('NotASaveState')
              and 'no driver signature found' in g and 'NAV_MAGIC' in g
              and 'candidate offsets' in g,
              lambda: Snapshot(tag, _container(bytes(mA), base)))

        # (4) MUTANT B: a range anchor pushed out of range -> same refusal.
        mB = bytearray(win)
        mB[WRAM_DELTA + 0x160] = 0x77            # TURN, legal range 0..2
        check(f"{tag}: MUTANT turn_out_of_range -> refused",
              lambda g: isinstance(g, str) and g.startswith('NotASaveState')
              and 'no driver signature found' in g,
              lambda: Snapshot(tag, _container(bytes(mB), base)))

        # (5) MUTANT C: MATCH_ACTIVE cleared on an in-match fixture -> the message must
        #     switch to not-in-a-match and STILL report the located base. This is the
        #     mutant that proves the two failure modes are actually distinguished, which
        #     is exactly what the old code got wrong in the other direction.
        if in_match:
            mC = bytearray(win)
            mC[WRAM_DELTA + 0x164] = 0
            check(f"{tag}: MUTANT match_inactive -> not-in-a-match, base still located",
                  lambda g: isinstance(g, str) and g.startswith('NotInAMatch')
                  and 'MATCH_ACTIVE' in g and '0x%06X' % (base + WRAM_DELTA) in g,
                  lambda: Snapshot(tag, _container(bytes(mC), base)))

        # (6) MUTANT D: two copies of the signature -> ambiguity must be refused, not
        #     silently resolved by picking the first.
        dup = _container(win, base)
        dup = bytearray(dup)
        dup[base + 0x20000:base + 0x20000 + WINDOW] = win
        check(f"{tag}: MUTANT duplicate signature -> refused as ambiguous",
              lambda g: isinstance(g, str) and 'AMBIGUOUS' in g,
              lambda: Snapshot(tag, bytes(dup)))

    # (7) NOT-INERT / population check: the widened tile set must actually BIND. A fixture
    #     corpus that never contains a clear-animation or text-box tile would pass every
    #     case above vacuously while the real defect walked free.
    seen = set()
    for _e, win in _fixtures():
        for b in win[0x400:0x480] + win[0x500:0x580]:
            if 0xB0 <= b <= 0xBF:
                seen.add('clear-anim $Bx')
            if b in (0x8D, 0x8F, 0xEF):
                seen.add('text-box')
    check("fixtures exercise the tiles the old LEGAL_TILE set omitted",
          lambda g: 'clear-anim $Bx' in g, lambda: seen)

    if verbose:
        for ok, name, got in cases:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
            if not ok:
                print(f"         got: {got}")
        print(f"\n  {len(cases) - len(failures)}/{len(cases)} passed")
    return 0 if not failures else 1


def main(argv):
    if '--selftest' in argv:
        return selftest()
    as_json = '--json' in argv
    paths = [a for a in argv if not a.startswith('--')]
    if not paths:
        print(__doc__)
        print("usage: ss_decode.py [--json] <snapshot.ss> [...]\n"
              "       ss_decode.py --selftest", file=sys.stderr)
        return 64
    rc = 0
    for p in paths:
        try:
            report(p, as_json)
        except NotInAMatch as e:
            # A live ring captures menu and title frames as a matter of course. Saying
            # "REFUSING TO DECODE" here would make routine, expected coverage look like an
            # instrument outage -- which is how this decoder came to be ignored.
            print(f"SKIP {p}: {e}", file=sys.stderr)
        except NotASaveState as e:
            print(f"REFUSING TO DECODE {p}: {e}", file=sys.stderr)
            rc = 65
        print()
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
