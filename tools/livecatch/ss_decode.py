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

★ THE OFFSET IS A HINT, NEVER AN ASSUMPTION. locate_ram() re-checks the invariant on every
file and rescans if it fails. A MiSTer core update that moves the layout would otherwise
make this print a perfectly plausible WRONG board -- the exact failure class that has cost
this project the most time (a confident number from a stale or mis-parsed source). Decoding
garbage silently is worse than refusing.
"""
from __future__ import annotations

import json
import sys

SS_SIZE = 1327112
RAM_HINT = 0x102B08          # CPU work RAM $0000, pinned by the invariant above
WRAM_DELTA = 0x800           # cartridge WRAM $6000 follows CPU RAM contiguously

LEGAL_TILE = set([0x00, 0xFF]) | set(range(0x40, 0x90)) | set(range(0xD0, 0xD3))
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


def _invariant_holds(buf, o, require_viruses=False):
    """The cross-address check that pins the base. See module docstring."""
    if o < 0 or o + 0x800 > len(buf):
        return False
    p1 = buf[o + 0x400:o + 0x480]
    p2 = buf[o + 0x500:o + 0x580]
    if not all(b in LEGAL_TILE for b in p1) or not all(b in LEGAL_TILE for b in p2):
        return False
    c1, c2 = bcd(buf[o + 0x324]), bcd(buf[o + 0x3A4])
    if c1 is None or c2 is None:
        return False
    v1 = sum(1 for b in p1 if b in VIRUS_TILE)
    v2 = sum(1 for b in p2 if b in VIRUS_TILE)
    if v1 != c1 or v2 != c2:
        return False
    if require_viruses and v1 == 0 and v2 == 0:
        return False        # an empty pair is satisfied vacuously and proves nothing
    return True


def locate_ram(buf, hint=RAM_HINT):
    """Return the CPU-RAM base, verifying rather than assuming.

    The hint is accepted only if the invariant holds AND the driver's power-on magic is
    where the contiguous-WRAM hypothesis puts it. Both can be true of a cleanly running
    cart at any point in a match, including a finished board with zero viruses -- which is
    why the magic is checked too, instead of demanding live viruses.
    """
    magic_ok = (hint + WRAM_DELTA + 0x149 < len(buf)
                and buf[hint + WRAM_DELTA + 0x149] == 0xA5)
    if _invariant_holds(buf, hint) and magic_ok:
        return hint, "hint verified (invariant + NAV_MAGIC)"
    if _invariant_holds(buf, hint, require_viruses=True):
        return hint, "hint verified by invariant; NAV_MAGIC absent (not a driver cart?)"

    # The hint failed. Separate the two reasons before doing anything expensive: if the
    # driver's magic is still sitting where the layout says it should, the CONTAINER is
    # fine and it is the game state that is not a board -- a title or level-select frame,
    # which a live ring will capture routinely. Rescanning for those is pointless and
    # reporting them as "layout moved" would be alarming and wrong.
    if magic_ok:
        raise NotInAMatch(
            "container layout is intact (NAV_MAGIC present) but $0400/$0500 do not hold a "
            "legal playfield -- the game was at a title/menu screen, not in a match. Skip."
        )

    cands = [o for o in range(len(buf) - 0x800)
             if _invariant_holds(buf, o, require_viruses=True)]
    if len(cands) == 1:
        return cands[0], (f"HINT FAILED -- relocated to 0x{cands[0]:06X} by rescan. "
                          "The container layout moved (core update?); update RAM_HINT.")
    raise NotASaveState(
        f"cannot locate CPU RAM: hint 0x{hint:06X} failed the invariant and a full rescan "
        f"found {len(cands)} candidate(s). Refusing to decode a board I cannot place."
    )


class Snapshot:
    def __init__(self, path):
        self.path = path
        self.buf = open(path, 'rb').read()
        if len(self.buf) != SS_SIZE:
            raise NotASaveState(
                f"{path}: {len(self.buf)} bytes, expected {SS_SIZE}. Truncated capture "
                "(the 0-byte/partial scp race) or a different core's save-state."
            )
        self.ram, self.how = locate_ram(self.buf)
        self.wram = self.ram + WRAM_DELTA

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
                              p1=p1, p2=p2, mailbox=s.mailbox(), verdict=v,
                              board_p1=s.render(1), board_p2=s.render(2)), indent=2))
        return s
    print(f"== {path}")
    print(f"   RAM base 0x{s.ram:06X}  WRAM 0x{s.wram:06X}   [{s.how}]")
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


def main(argv):
    as_json = '--json' in argv
    paths = [a for a in argv if not a.startswith('--')]
    if not paths:
        print(__doc__)
        print("usage: ss_decode.py [--json] <snapshot.ss> [...]", file=sys.stderr)
        return 64
    rc = 0
    for p in paths:
        try:
            report(p, as_json)
        except NotASaveState as e:
            print(f"REFUSING TO DECODE {p}: {e}", file=sys.stderr)
            rc = 65
        print()
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
