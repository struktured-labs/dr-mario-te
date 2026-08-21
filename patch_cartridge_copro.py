#!/usr/bin/env python3
"""Build drmario_copro.nes — the COPROCESSOR cartridge for the custom MiSTer NES core
(mapper 100 = MMC1 + Dr.Mario coprocessor at $5000-$51FF), with AUTO-NAV: the cart boots
itself into a VS-CPU L11 match and re-arms after every match. No controller needed (built
for a MiSTer whose physical controls are broken; also makes it a self-running demo).

How: the v28cs blob head at $FB00 (reached from the 0x37CF controller hook EVERY frame,
all modes) is repointed to the $FF54 trampoline, which bank-switches to unit-1 and runs
`main` each frame:
  menu modes  -> autonav state machine injecting P1 presses into $F5 (SELECT,SELECT,START,
                 LEFT x15, RIGHT x11, START) so the hack's own menu toggle sets VS-CPU
                 state properly; mirrors $F5->$F6 when $04=1 (P2 level cursor).
  intro (8)   -> hands off (no stray START).
  play (4)    -> the copro driver: on new pill upload board+colors to the FPGA window,
                 GO, hold pill while DONE=0, then publish best move to $DD/$DA and act.
The heavy depth-2 search runs on the SECOND 6502 inside the FPGA (~0.2-0.3s/pill vs 78s).
NOT Mesen-compatible (mapper 100) — MiSTer custom core only.
"""
import hashlib
import json
import sys
sys.path.insert(0, "tests")
from patch_vs_cpu import Asm6502
import patch_vs_cpu as _pv
_pv.OPS.setdefault("ORA_abs", 0x0D)
for _mn, _op in (("LDX_abs", 0xAE), ("STA_absX", 0x9D), ("CLC", 0x18), ("ADC_imm", 0x69)):
    _pv.OPS.setdefault(_mn, _op)   # for the DRTRACE ring writer (STA $5000,X etc.)
from expand_prg import expand

V28CS = "drmario_v28cs.nes"
OUT = "drmario_copro.nes"
UNIT1_CPU = 0x8000
WRAP_CPU = 0xFF54
WRAP_FILE = 0x4010 + (WRAP_CPU - 0xC000)
BLOB_FILE = 0x7B10                       # CPU $FB00
PRG_REG = 0xFFF0
ARMED = 0x6143             # PRG-RAM: !=0 searching (hold), ==0 act
NAV_T, NAV_MAGIC = 0x6147, 0x6149   # autonav frame counter + PRG-RAM power-on magic
GRAV_P1, GRAV_P2 = 0x0312, 0x0392   # per-player gravity counters
# CPU-vs-CPU: FPGA coprocessor is time-shared between P1 and P2 (~0.3s per pill each);
# ARMED tracks in-flight search, WHICH is 1=serving P1, 2=serving P2, PEND_* records
# player i's pill has locked and needs a search, TGT_C/O_* are that player's target move.
WHICH  = 0x614D
PEND1  = 0x614E
PEND2  = 0x614F
TGT_C1 = 0x6150
TGT_O1 = 0x6151
TGT_C2 = 0x6152
TGT_O2 = 0x6153
LASTY1 = 0x6154
LASTY2 = 0x6155
STKX1, STKY1, STK1 = 0x6156, 0x6157, 0x6158   # P1 stagnation: last x/y + stuck-frame count
STKX2, STKY2, STK2 = 0x6159, 0x615A, 0x615B   # P2 stagnation
WDOG, WRETRY = 0x615C, 0x615D   # search watchdog: ticks-while-ARMED + one-retry latch
DELAY1, DELAY2 = 0x615E, 0x615F  # post-edge settle: preview/board can update a beat after spawn
TURN = 0x6160    # (unused in dual-copro) fair round-robin serving
# DUAL COPRO: each player has its OWN coprocessor + search state -> no time-sharing.
# copro1 window $5000-$51FF serves P1; copro2 window $5200-$53FF serves P2.
ARMED2, WDOG2, WRETRY2 = 0x6161, 0x6162, 0x6163   # P2's independent search state (ARMED/WDOG/WRETRY = P1's)
MATCH_ACTIVE = 0x6164   # set once play is dispatched; gates the full-clear STAGE-CLEAR auto-advance
WDOGH1, WDOGH2 = 0x6165, 0x6166   # watchdog HIGH bytes: depth-3 searches run seconds, not frames
WDOG_HI_LIM = 56                  # timeout = 56*256 = 14336 ticks ~= 4min (FULL-ply1 d3 first pill
                                  # ~95s measured-scaled on the dense 48-virus board; 2.5x margin)
# per-copro tie-break seeds (same eval, different near-tie resolution -> desyncs mirror play).
# Derived once per match from NAV_T; ride the color uploads' HIGH nibbles (firmware masks &$0F
# and extracts SEED=(CB&$F0)|(CA>>4); seed 0 = jitter off).
SEED1, SEED2, TMPSEED = 0x6167, 0x6168, 0x6169
VSEEN1, VSEEN2 = 0x616A, 0x616B   # count-was-nonzero-this-match latches (gate the auto-advance:
                                  # in 1P/demo contexts the unused P2 count reads 0 -> START-spam)
# ROT_DONE2 (DRROTFIX): P2 orient-commit latch, reset per pill. 0 = pre-phase (orient still
# tracks the search while the capsule is frozen HIGH); 1 = committed (orient LOCKED, only the
# column refines as it descends). Stops the mid-flight orient retarget that rotates a low/flush
# capsule and locks it BACKWARDS (field-seen on the Pocket combo brain 2026-07-19). $616C/$616D
# are the anytime torn-read scratch; $616E is the next free PRG-RAM byte.
ROT_DONE2 = 0x616E
# DRSLAM confidence-gated slam: P2 argmax-stability tracking (all free PRG-RAM past ROT_DONE2).
# LAST_COL2/LAST_ORI2 = last published (column, MAPPED game-orient); STABLE_CT2 = hooks the
# published argmax has held unchanged (saturating), reset on any change or a new pill. The slam
# gate reads STABLE_CT2 to decide when the running best is confident enough to fast-drop.
LAST_COL2, LAST_ORI2, STABLE_CT2 = 0x616F, 0x6170, 0x6171
# SLAM_ARM (DRSLAM_MATURE): "the search pipeline is keeping pace, so its pre-DONE argmax is trustworthy."
# The confidence slam + crossover escape only fire while SLAM_ARM=1. It is armed/disarmed per search by
# the LAST P2 search's latency (LAST_LAT = WDOGH2 at DONE = latency/256 hooks): a FAST DONE arms, a slow
# DONE / a watchdog timeout / a pill that locks while its search is still ARMED disarms. First pill of a
# match starts disarmed. So a cold round-1 entry (no validated result yet) and any slow-search episode
# fall back to the proven anytime placement, re-arming on the next fast DONE -- breaking the cold/dense
# vicious cycle (bad placement -> denser board -> slower search -> worse commit) at its root.
SLAM_ARM, LAST_LAT = 0x6172, 0x6173
# NAV_STABLE (DRNAVFIX): consecutive hooks the title menu has read VS-CPU-armed ($04!=0 AND $0727==2).
# The canonical nav fires START the instant $04!=0; at a cold boot $04 can read garbage-nonzero during
# the title fade-in (before the menu inits the 1P default $0727=1/$04=0) while NAV_T is still small so
# the START window is open -> a premature START lands a 1P game (~1-in-3 cold loads, no reset from cart).
# DRNAVFIX withholds START until the armed state has been STABLE for NAV_M hooks, filtering the transient.
# NAV_1P is a diagnostic latch: set if the cart ever runs play-mode with $0727==1 (a 1P game or the
# attract demo) = the nav did NOT land VS-CPU. Readable on hardware to score a cold-load gauntlet.
NAV_STABLE, NAV_1P = 0x6174, 0x6175
# ★ WHERE THE HOOK ACTUALLY RUNS (measured 2026-08-01 from the ROM itself; an earlier version of this
# comment said "from BOTH the NMI and the main loop", which is WRONG and sent a design down an
# impossible path -- there is no main-loop invocation to move work to):
#   NMI vector $FFFA -> $8005; the NMI's LAST call before restoring registers is JSR $9134 =
#   getInputs_checkMode, which has EXACTLY ONE call site in the whole 32K PRG (that one). In
#   non-demo play it does `jsr getInputs; rts`, and getInputs calls addExpansionCTRL TWICE (the
#   two-pass AND read). The 0x37CF hook is the tail of addExpansionCTRL.
#   => THE DRIVER RUNS EXACTLY 2x PER FRAME, BOTH INSIDE THE NMI. Never from the main loop.
#   Corroboration: autonav's `NAV_T & $1F < 4` press window is 4 hooks = 2 whole frames at 2/frame,
#   which is what the two-pass AND needs; at the "~5/frame" this file assumes elsewhere it would be
#   0.8 frames and the nav could not work at all. Several comments below still say ~5 calls/frame --
#   they are calibration prose, not measured, and should be revisited before anyone RE-TUNES the
#   hook-counted constants (MIN_THINK, the K_* stability gates, WDOG limits). The constants
#   themselves were tuned empirically on silicon, so they are fine as shipped.
#   Placement matters for budgeting: the hook runs AFTER every PPU write in the NMI (render_*,
#   PPUSCROLL), so an over-long driver invocation does NOT corrupt the display -- it eats the main
#   loop's share of the 29780-cycle frame. Only overrunning a WHOLE frame is dangerous, which is
#   exactly the re-entrancy below.
# RE-ENTRANCY GUARD latch (build_wrapper): because there is only the NMI, re-entry happens when a driver
# invocation overruns a full frame -- the NEXT NMI fires and RE-ENTERS the driver, clobbering the
# shared abs-addr state (armed/pend/wdog) -> the driver re-issues GO every hook -> the ~83M-clk search never
# DONEs -> the game spins on $5084 = the R47 Pocket HARD-FREEZE (combo-port co-sim proven: cadence not
# silicon, so div2 froze identically; SEI can't help -- NMI is non-maskable). A BUSY latch in free PRG-RAM
# ($6176-$6185) makes the trampoline bail on re-entry BEFORE the bank switch (a re-entrant _sel would corrupt
# the interrupted invocation's bank). Byte-exact for the build_main goldens -- the guard is in the trampoline.
#   ⚠ THE BUSY GUARD DOES NOT COVER THE OVERRUN NMI. It is reached only through the $FF54
#   trampoline; the 6502 takes an NMI by loading PC straight from $FFFA, executing NOT ONE BYTE
#   of $FF54. See DRRTIVEC below -- this comment used to claim the overrun case "is exactly the
#   re-entrancy below", which is FALSE and is hazard 1.
BUSY = 0x6176
DWELL_CNT, DWELL_LAST = 0x6177, 0x6178
# ---- TUCK EXECUTOR (DRTUCK=1, default OFF -> every existing cart stays byte-identical) ----
# A tuck is a placement that slides UNDER an overhang: fall beside the lip, then move
# laterally at the last moment. Measured value (tmp/champion/tuck_ab.py, n=240, on the REAL
# NES capsule stream): median pills 97.5 -> 90.0 at L11 with clear rate 97.5% -> 98.3%, and
# faster at all four levels tested. 18.1% of real positions hold a tuck that kills a virus
# NO straight drop can reach; 88.4% of those are geometrically tuck-only.
#
# ★ THE KEY SIMPLIFICATION: a tuck is the SAME steer-then-drop logic with a ROW-DEPENDENT
# target column. While the capsule is high, steer to the APPROACH column; once it is at or
# below the trigger row, steer to the FINAL column and the existing DAS slide carries it
# under the lip. No new movement primitive, no gravity manipulation, no extra frames.
TUCK_C2 = 0x6179   # approach column for the in-flight P2 capsule; 0xFF = no tuck this pill
TUCK_R2 = 0x617A   # steer to the FINAL column once pill Y <= this ($0386 counts UP from the floor)
EFF_C2  = 0x617B   # effective target column this hook (approach or final)
# W_TCOL/W_TROW -- the copro publishes the tuck descriptor at offsets $87/$88 of P2'S OWN
# window, so the cart address depends on where P2's window sits: DRPOCKET=1 single-window
# carts read $5087/$5088 (byte-identical to the historical hardcode every prior DRTUCK
# validation ran under), but MiSTer dual-window carts talk to P2 at $5200 -- and the winner
# single-copro core STRIPS the $5000-$51FF decode entirely, so a hardcoded $5087 read there
# is OPEN BUS = $50, the same undecoded-address failure the published-column sanity guard
# below documents. Derived from W2_BASE after it is set (it depends on DRPOCKET); the
# executor is only emitted behind DRTUCK=1, so DRTUCK=0 carts are byte-identical either way.
# TITLE DWELL: frames dwelt at the title + last frameCounter($43) seen
# DRP1WIGGLE (see below): per-pill alternating direction latch for the P1 spectator wiggle.
# 0 = hold LEFT this pill, 1 = hold RIGHT. Toggled on the P1 new-pill edge. $617C is the next
# free PRG-RAM byte (BUSY..$6185 is the free window; $6186+ is the DRPROBE ring header).
WIG_DIR = 0x617C
# DRP1NATIVE (see below): the P1 native-AI wrapper's own state. P1AI_Y is the per-pill search
# cache key (last pill Y seen); P1AI_C/P1AI_O hold the search result. The results are copied
# out of the AI's zero-page outputs IMMEDIATELY, because Z_TARGET is $00 = CTRL_exp1, which
# get_CTRL_inputs rewrites on EVERY pad read -- reading it a hook later returns controller
# bits, not a column.
P1AI_Y, P1AI_C, P1AI_O = 0x617D, 0x617E, 0x617F
P1AI_CPU, P1SWAP_CPU = 0x9000, 0x9200   # P1-mirrored d1 AI + its swap_eval, in unit1 (bank 2)
import os as _os

# ---- default-proof manifest replay (provenance, generalized): every DR* env lookup below this
# point is recorded with its RESOLVED value (whatever it actually evaluated to -- the caller's
# override, or the code's own hardcoded default), not just what the caller explicitly passed.
# tools/romgen.py's `build` reads this back (the "##DRFLAGSNAPSHOT##" line at the end of main())
# and stores it in the manifest as `flag_snapshot`, so `rebuild` can set EXACTLY that env on a
# future replay -- immune to any later change to any knob's default, forever, because the
# manifest no longer depends on "what the code currently defaults to" at all. Monkeypatching
# os.environ.get (not e.g. wrapping every call site) is deliberate: it's the one choke point
# every DR* lookup in this file already goes through, verified to need no call-site changes
# (confirmed: `os` and `_os` are the same module object, so a bare `os.environ.get(...)` inside
# main() -- see DRLEVEL/DRSPEED -- is caught by this too).
DR_ENV_SNAPSHOT = {}
_real_environ_get = _os.environ.get


def _tracked_environ_get(key, default=None):
    resolved = _real_environ_get(key, default)
    if isinstance(key, str) and key.startswith("DR"):
        DR_ENV_SNAPSHOT[key] = resolved
    return resolved


_os.environ.get = _tracked_environ_get
# DRNAVESC: stuck-screen escape watchdog (task #38). Three silicon freezes 2026-08-01/02
# (evidence: qa-wt experiments/freeze_20260801/) shared one shape: the game parked on a
# screen awaiting a START the nav never sends -- mode 3 falls through autonav's dispatch
# (only 0/1/7 are handled) and mode-4 round-waits never reach autonav at all. The escape
# watches the tuple ($0046 mode, $F8 screen, $0386 P2 pill row); if UNCHANGED for ESC_N
# consecutive hooks it injects START for a 4-hook press window (2 frames -- survives the
# game's two-pass AND), then re-arms. $0386 moves every frame during real play, so the
# watchdog structurally CANNOT fire mid-game; mode 8 (intro) is excluded per the standing
# hands-off rule; on firing it OWNS THE FRAME (inject + RTS, the fc_clear pattern) so a
# downstream act_p1 writer (wiggle/native) cannot clobber the press. NEVER emitted on
# HUMAN_P1 carts -- a human's pause would read as "stuck" and the escape would unpause them.
NAVESC = _os.environ.get("DRNAVESC", "0") == "1"
ESC_N = int(_os.environ.get("DRNAVESC_N", "1200"))   # hooks unchanged before escape (~10 s at 2 hooks/frame)
ESC_S0, ESC_S1, ESC_S2 = 0x6180, 0x6181, 0x6182      # snapshot: $0046 / $F8 / $0386
ESC_CTL, ESC_CTH = 0x6183, 0x6184                    # 16-bit stuck-hook counter
# DRSTALLWD: play-mode P2 stall watchdog (task #40 follow-up; see experiments/freeze_20260801/
# FREEZE4_ROOTCAUSE.md). NAVESC (above) detects a stuck SCREEN and presses START -- proven
# ineffective against a mid-PLAY search-state wedge (freeze #4, 2026-08-02): pressing START during
# mode 4 only toggles pause, which does not change $0046, so the driver's own dispatch (including
# handle()'s watchdog) keeps running underneath the pause exactly as before -- NAVESC's remediation
# is orthogonal to this bug class. DRSTALLWD instead watches P2's OWN pose ($0385/$0386/$03A5 --
# column, row, orientation), all WRAM the GAME itself owns, for STALLWD_N hooks of zero movement
# while mode==4 and P2 still has viruses (VCOUNT_P2 != 0; BCD-safe -- $00 reads identically in both
# encodings). It deliberately does NOT key off the driver's own PEND2/ARMED2/DELAY2/WDOG2 scratch --
# those are exactly the bytes in question during a wedge like the P0.2 lock-while-armed pin (freeze
# #4's confirmed mechanism), and a single save-state snapshot of them proved impossible to reason
# about after the fact (two non-atomic memory regions -- see the freeze #4 writeup). Remediation is
# a SCOPED reset: force the search-state quintet back to "ready to launch a fresh search against the
# live board" (ARMED2/WDOG2/WDOGH2=0, PEND2=1, DELAY2=0 -- skip the 15-tick settle, the board hasn't
# changed) WITHOUT touching ROT_DONE2/STABLE_CT2/TGT_C2/TGT_O2, so a still-good orientation commit or
# running argmax isn't discarded the way a full fake pill-lock edge would discard it. On the very
# next hook handle(2)'s own `_start` gate (pend!=0 && delay==0) fires immediately and re-GOes the
# copro. Never touches $F5/$F7/$F6/$F8 or pause state, so (unlike NAVESC) it is silent to a human on
# any cart class and cannot itself cause a toggle-and-do-nothing loop. Default OFF (byte-exact
# goldens); the counter re-arms after firing so a search that is merely legitimately slow (not
# wedged) gets a full fresh STALLWD_N-hook grace window before the watchdog reconsiders -- it does
# not spin-reset every hook (which would starve the fresh search of the time to ever complete).
STALLWD = _os.environ.get("DRSTALLWD", "0") == "1"
STALLWD_N = int(_os.environ.get("DRSTALLWD_N", "2400"))   # hooks of static P2 pose (~20s @ 2 hooks/frame)
SWD_S0, SWD_S1, SWD_S2 = 0x618D, 0x618E, 0x618F      # snapshot: $0385 / $0386 / $03A5 (past the
                                                      # DRPROBE/DRTRACE ring header at $6186-$618C)
SWD_CTL, SWD_CTH = 0x6190, 0x6191                    # 16-bit stuck-hook counter
TUCK = _os.environ.get("DRTUCK", "0") == "1"   # tuck executor (see TUCK_C2 above)
# DRTUCKGUARD (task #102, default OFF -> byte-inert; requires DRTUCK). Cart-side fall-budget veto
# on the tuck descriptor: refuse an approach column whose remaining fall cannot pay for the
# lateral trip to the final column. See the adoption site for the mechanism and the numbers.
# ⚠ $61B9/$61BA are the first two bytes of the $61B9-$61FF free run in PRG_RAM_MAP.md. Reach
# checked: the guard's only indexed access is `LDA $0500,X`, a READ of the playfield -- it adds
# no indexed WRITER, so it cannot widen anyone else's reachable span.
TUCKGUARD = TUCK and _os.environ.get("DRTUCKGUARD", "0") == "1"
TG_NEED = 0x61B9   # |approach - final| + 2, the fall this tuck must be able to pay for
TG_OFF  = 0x61BA   # walking board offset while counting free rows below the trigger
REENTRY_GUARD = _os.environ.get("DRREENTRY", "1") != "0"
# DRBUSYESC (default OFF -- ship classes opt in): stale-BUSY escape for the re-entrancy guard.
# SILICON BRICK 2026-08-02: BUSY lives in sticky PRG-RAM (FPGA BRAM survives load_core). The
# freeze-4 recovery reloaded the core while an invocation was IN FLIGHT (BUSY=1) -> every boot
# since inherited NAV_MAGIC=$A5 (warm) AND BUSY=1, so the trampoline bailed before the bank
# switch on every hook and the driver body that clears BUSY could never run: a soft-brick that
# survives reboots, ROM swaps and savestate hygiene (4 boots, 2 builds, NAV_T frozen at $28;
# the attract demo's forced $0727=1 masqueraded as a "1P nav mis-land"). The cold-boot
# bootstrap cannot help -- it keys on NAV_MAGIC, which is exactly as sticky as BUSY. Escape:
# count CONSECUTIVE bails in BUSYSKP; at 255 (~2 s at the measured 2 hooks/frame) force-free
# the latch and enter. Genuine re-entrancy bails 1-2 hooks. A live GO-storm spin is ALSO freed
# after ~2 s, re-entering the driver -- acceptable: the storm family is closed (DRREENTRY +
# DRWRETRY + DRPENDBOUND + DRSTALLWD) and the alternative is this brick. Any successful entry
# resets the count. Unbrick without this flag: cycle menu.rbf then load_core (BRAM re-init).
BUSYESC = _os.environ.get("DRBUSYESC", "0") == "1"
BUSYSKP = 0x6192                                   # consecutive-bail counter (after DRSTALLWD's $6191)
# ==================== NMI-OVERRUN SILICON HAZARDS (both trace-proven 2026-08-09) ====================
# Two INDEPENDENT ways a long NMI hook kills the cart. Mapper 100 routes PRG banking to upstream
# MMC1.sv, so both are identical on MiSTer and Pocket silicon. Ship them TOGETHER (see the
# CO-DEPENDENCE note under DRMMC1RST) -- either one alone leaves a live crash path.
#
# HAZARD 1 -- UNGUARDED VECTOR RE-ENTRY (DRRTIVEC).  An invocation that overruns the whole frame is
# still running when the next vblank NMI fires. The 6502 loads PC straight from $FFFA; with the
# DRIVER bank mapped, $C000-$FFFF is PRG index 3, whose vector bytes are expand_prg.py's verbatim
# copy of the base game's ($8005/$8035). $8005 in the DRIVER bank is not the game's NMI handler --
# it is main's DRDISTGATE dist_table, seven 2-byte non-branching zero-page ALU ops that fall through
# into main at $8013 with NO control flow to escape. So the NMI re-enters driver main with the BUSY
# guard bypassed (the guard is three instructions inside the $FF54 trampoline, and the vector does
# not execute one byte of it), and act_done's terminal RTS pops the NMI frame as an address:
# PC = ((pushed PCL) << 8 | pushed P) + 1, an effectively uniform 64K jump. Trace witness:
# prestart_gate/pilot/probe7.log froze at f=231 with the PC ring ending ... 8B26 (act_done RTS) 0BA6
# (RAM). Measured rate during live play: 2 events in ~299 frames = 0.67%, ~1 per 2.5 s.
#
# HAZARD 2 -- MMC1 SHIFT-REGISTER INTERLEAVE (DRMMC1RST).  MMC1 has ONE 5-bit shift register shared
# by all four registers; the register a sequence lands in is chosen by A14/A13 of its FIFTH write.
# The base game clocks a 5-write $DFFF (CHR1) sequence from the MAIN loop every frame
# ($89C9 -> $B8F4, the virus blink); the trampoline clocks two 5-write $FFF0 (PRG) sequences per
# hook, 2 hooks/frame, all inside the NMI. An NMI landing mid-$DFFF leaves k bits already shifted
# in, so _sel(2) completes with mixed bits: k=1,2,3,4 -> prg_bank 5,9,17,1, and every one of those
# resolves (32KB mode prgsel = {prg_bank[3:1], A14}, masked &3 for a 4-bank ROM) to PRG index 0 =
# THE BASE GAME at $8000. The trampoline's very next instruction is JSR $8000, base $8000 is
# `LDX #$00; JMP $8036`, and $8036 runs the RAM-clear loop = full wipe of $0000-$06FF. BUSY lives at
# $6176 in PRG-RAM, which that loop does not touch, so BUSY stays latched and every later hook bails
# forever: title screen + dead driver + surviving nametable fragments. Trace witness:
# prestart_gate/dbg7/interleave.log f=517 `C01 C00 C00 C00 | NMI | P02 P01 P00 P00 P00`, and the
# 2026-08-09 Pocket field event at t=85.60s (COMMENTARY_TRANSCRIPT.md) is exactly this end-state.
#
# DRRTIVEC (default OFF -> every existing cart rebuilds byte-identical): give the DRIVER UNIT its
# own NMI/IRQ vectors so an overrun NMI is absorbed instead of re-entering main. Cost: one skipped
# GAME NMI per overrun (stale OAM for a frame, one missed $43 tick, one dropped sound tick) -- at
# the measured 0.67% that is well inside the tempo noise the driver already tolerates, and a skipped
# frame beats a KIL. RTI also pops exactly the 3 bytes the NMI pushed, so shielded overruns are
# stack-NEUTRAL; today's path leaks one byte per event and walks S downward.
#
# ⚠ WHY THIS IS NOT THE OBVIOUS "point $FFFA at an RTI in the driver bank".  That design is a BRICK
# the moment DRMMC1RST also ships, and the two fixes are meant to ship together:
#   MMC1.sv:110 `control <= control | 5'b0_11_00` -- a bit-7 (reset) write FORCES PRG mode 3, which
#   HARD-FIXES $C000-$FFFF to the LAST bank = index 3, permanently, for the base game too. Today
#   that is inert only because expand_prg.py makes index 3 a byte-exact duplicate of index 1. The
#   instant index 3's vectors differ, every ordinary game NMI vectors into the driver's stub while
#   the BASE bank is mapped low -- and driver-bank $A02E is $00 in base bank 0, i.e. BRK, whose IRQ
#   vector is the same stub: an unbreakable BRK loop on the first NMI after the first hook.
# So the shield is BANK-DISCRIMINATING and lives in the SHARED high half (bank 1, therefore present
# in index 1 AND index 3 identically):
#     $CEEC  48         PHA           ; v6e: A MUST be preserved -- see below
#     $CEED  AD 2E A0   LDA $A02E     ; probe the currently-mapped LOW bank
#     $CEF0  C9 40      CMP #$40      ; $40 only in the DRIVER bank (base bank 0 is $00 -- asserted)
#     $CEF2  D0 03      BNE $CEF7
#     $CEF4  68         PLA           ; driver bank mapped => absorb the overrun NMI, A intact
#     $CEF5  40         RTI
#     $CEF6  40         RTI           ; <- IRQ vector target; IRQ pushes no A, so a bare RTI is right
#     $CEF7  68         PLA
#     $CEF8  4C 05 80   JMP $8005     ; base bank mapped => the game's own NMI, A intact
# ⚠ THE PHA/PLA IS NOT COSMETIC (v6e, found after c-v8ship 087ff959 had already been gated): the
# original shield probed with LDA and then JMP'd into the game's NMI handler, which opens PHA and
# closes PLA -- so it dutifully saved and restored the value the shield had just destroyed, and the
# interrupted main-loop code resumed with a wrong accumulator on EVERY NMI the shield handled. The
# multi-match gate passed that cart with numbers identical to the unhardened build, because match
# counts and abort counts cannot see a corrupted register. Guard registers you touch, and gate the
# guard with a check that reads the register.
# Only index 3's four vector bytes are repointed; index 1's are untouched, so with DRMMC1RST OFF the
# game's NMI path is bit-for-bit today's (index 3 is only mapped while prg_bank=2, i.e. only inside
# a driver invocation). With DRMMC1RST ON, mode 3 puts index 3 at $C000 permanently and the probe is
# what keeps the game alive -- it costs the game NMI 11 cycles and a JMP.
# $CEEC-$CEFC is FREE_SPACE_MAP.md's 17-byte SHARED-FREE run; re-derived here with a fresh
# RB6C2_PRINT walker (tmp/hazfix/print_walk.py): all 21 tables terminate at or before $CEBA, the
# walker's positive controls ($BC26, $C0A9, $C0EF) come back TOUCHED, and $CEEC-$CEFC has zero
# absolute/indexed operand references anywhere in the 32KB.
RTIVEC = _os.environ.get("DRRTIVEC", "0") == "1"
RTIVEC_PROBE = 0xA02E        # FREE_SPACE_MAP SHARED-FREE run $A02E-$A03D; $00 in base bank 0
RTIVEC_MAGIC = 0x40          # value written there in the DRIVER bank -- doubles as a bare RTI
NMI_SHIELD_CPU = 0xCEEC      # bank 1 (shared high half) -- in unit 0 AND unit 1
# DRMMC1RST (default OFF -> every existing cart rebuilds byte-identical): write the MMC1 reset bit
# ($80, bit 7) before EVERY emitter-side 5-write serial sequence, making each sequence SELF-ALIGNING
# regardless of a half-finished main-thread sequence. +5 B / +6 cy per sequence, 4 sequences per
# frame = +24 cy = 0.081% of a 29,780-cycle frame.
# RESIDUAL, stated honestly: when a hook does land mid-$DFFF the main loop's remaining writes now
# complete against a re-zeroed counter, so THAT frame's CHR1 select is lost -- one frame of frozen
# virus blink. It self-heals on the next hook. Graphics-only and bounded to a frame, versus a RAM
# wipe. Do NOT "optimise" this into `INC $FFF0`: the reset only fires if the written byte has bit 7
# SET, and an RMW writes back what it read -- the ROM byte at $FFF0 is $1C, so `INC $FFF0` would
# shift a ZERO into the register and make the corruption worse, silently.
# ⚠ CO-DEPENDENCE (do not land these independently): the reset permanently forces PRG mode 3, so
# $C000-$FFFF becomes index 3 for the base game too. That is safe ONLY because DRRTIVEC's shield is
# bank-discriminating; a plain-RTI index-3 vector plus this flag is an instant brick. Conversely
# DRRTIVEC alone leaves hazard 2 live -- dbg7 logged TITLEFALL f=518 WITH the emulator NMI shield
# armed. A green ram_exec=false does not mean the field bug is fixed.
MMC1RST = _os.environ.get("DRMMC1RST", "0") == "1"
# ====================================================================================================
# DRDISTGATE (REVIEW #6.2 / task #49 follow-on -- see CART_FIX_REPORT.md; REVIEW-driven change,
# authorized explicitly, not a flag toggle): $6193 is the next free PRG-RAM byte (past BUSYSKP).
# DG_BUDGET = scratch (max DAS-reachable columns this hook); EFF_DIST2 = the distance-clamped
# steering target, substituted for TGT_C2/EFF_C2 in mv_p2 once the gate fires.
DG_BUDGET, EFF_DIST2 = 0x6193, 0x6194
# DRWRETRY (default OFF -- touches build_main, so off keeps the goldens == published c300acb canonical;
# the shipping cart opts in): fix the "re-queue once per pill" watchdog latch. Two bugs: (A) handle()'s
# _start epilogue clears `wretry` every search START (so a re-queued timeout re-GOs indefinitely); (B) the
# P2 pill-lock reset writes WRETRY ($615D=P1) not WRETRY2 ($6163=P2) -- copy-paste bug, so P2's latch never
# resets per-pill. FIX = drop the _start clear AND write WRETRY2 in the P2 path -> correct once-per-pill for
# both. Secondary to the re-entrancy guard (only bites on genuine ~48s timeouts, rare once the storm is gone).
WRETRY_FIX = _os.environ.get("DRWRETRY", "0") != "0"
USE_SEEDS = _os.environ.get("DRSEED", "1") != "0"   # DRSEED=0 -> seeds stay 0 = deterministic mirror
# WEAVE steering: when sliding to the target column is blocked at the pill's row (stuck
# >= WEAVE_LIM hook-cycles), release the gravity freeze for one drop so the pill descends
# a row and can slide past the obstruction (down-and-over), instead of hovering frozen and
# then force-dropping straight down. Measured: 8-17% of legal cols are slide-unreachable at
# half-to-3/4 fill -> misplacement -> burial (hardware walls at ~20 viruses). DRWEAVE=0 off.
USE_WEAVE = _os.environ.get("DRWEAVE", "1") != "0"
# DRHUMAN=1 -> HUMAN-CHALLENGE build: P1 = human passthrough (no copro search, no $F5/$F7
# injection, no P1 gravity pinning in act), P2 = the validated copro AI unchanged.
HUMAN_P1 = _os.environ.get("DRHUMAN", "0") == "1"
# DRNOFREEZE=1 -> ANYTIME steering: never pin P2 gravity while searching. The firmware
# live-publishes its running best into the result mailbox (orient=0xFF = "no result yet"
# sentinel); the driver refreshes TGT every hook and weave-steers while the search refines.
# Pill fall time becomes the AI's honest time budget (kills the visible mid-air pause).
NO_FREEZE = _os.environ.get("DRNOFREEZE", "0") == "1"
WEAVE_LIM = int(_os.environ.get("DRWEAVELIM", "40"))   # hook-cycles of no-move before a weave drop
                                                        # (> DAS repeat ~30 so normal slides don't trip it)
# DRROTFIX=1 (default): the P2 anytime driver gets driver-fidelity steering -- rotation
# PRE-PHASE (rotate to the target orient while frozen high, in open air), FEASIBILITY-GATED
# retarget (orient locks at commit so a late retarget can't rotate a low capsule backwards),
# and a MINIMUM-THINK gate (no lateral/orient commit until DONE or MIN_THINK hooks of search).
# DRROTFIX=0 reproduces the pre-fidelity byte-exact emission (A/B + regression parity).
ROTFIX = _os.environ.get("DRROTFIX", "1") != "0"
# DRROTDIR (default OFF, task #114): shortest-direction rotation. The rotation pre-phase has only
# ever pressed A (= DEC $A5 = CCW at $8E2B), so reaching game orient 1 from spawn costs THREE
# rotations where B (= INC $A5 = CW, same handler) reaches it in one. Requires ROTFIX because the
# pre-phase it edits only exists there; DRROTDIR=0 rebuilds byte-exact (every add is guarded).
# ⚠ default MUST stay off until gated -- a default-on flag decouples artifact from recipe
# ([[pocket-rbf-md5-gate-unsound]]).
ROTDIR = (_os.environ.get("DRROTDIR", "0") != "0") and ROTFIX
# DRROTDIR_MUT: test-only deliberate defects for PREREG_ROTDIR's killed-mutant table.
# "none" (default) is the real fix. Any other value builds a cart that MUST fail the prereg.
#   m1  press B on delta 3 instead of delta 1   (direction inverted)
#   m2b press B UNCONDITIONALLY                 (passes the win, must FAIL the delta-3 control)
#   m3b mark B already-held ($F8=$40)           (kills the press edge on the FIRST press)
#   m4  CMP #$05, so the B branch is unreachable (POPULATION mutant: pressB must stay 0)
# ⚠ m2 and m3 are RETIRED and kept only so this note is auditable. BOTH WERE DEAD ON ARRIVAL,
# and the data said so before any verdict was read (measured 2026-08-19):
#   m2 ("delta computed as ($03A5 - TGT_O2) & 3, CMP #1") is ALGEBRAICALLY EQUIVALENT TO m1 --
#     (cur-tgt)&3 == 1 is exactly (tgt-cur)&3 == 3. Different bytes, different md5, IDENTICAL
#     behaviour: all 6 cells matched m1 to the last digit.
#   m3 ("omit the STA $F8 on the B path") is UNKILLABLE BY CONSTRUCTION on the only arm that
#     exercises B: delta 1 needs exactly ONE press, and the frame before it the driver was not
#     pressing, so $F8 is already 0 and the omitted clear is never reached. m3's 6 cells matched
#     the REAL FIX to the last digit. This is the "wrong observable" case, not a wrong mutant --
#     m3b tests the same property (is the edge armed?) with an observable that can fail.
ROTDIR_MUT = _os.environ.get("DRROTDIR_MUT", "none")
if ROTDIR_MUT not in ("none", "m1", "m2", "m2b", "m3", "m3b", "m4"):
    raise SystemExit(f"DRROTDIR_MUT must be none|m1|m2|m2b|m3|m3b|m4 (got {ROTDIR_MUT!r})")
if ROTDIR_MUT != "none" and not ROTDIR:
    raise SystemExit("DRROTDIR_MUT set but DRROTDIR is off -- the mutant would be a silent no-op")

# ---- HARDENED-CART TRIO (tasks #129/#133/#134, each default OFF -> byte-identical) ----
# DRVERFIX (#129): 3-byte STOCK-ROM fix. checkVerMatch's vertical colour-chain scan steps the
# field index by +8 and tests for the bottom with AND #$F8 / BEQ -- zero only for indices 0..7,
# i.e. it terminates by WRAPPING PAST 255, reading the 128 bytes AFTER the field on the way. If
# that trailing region shares the chain's colour nibble the wrapped index is written back into
# fieldPos and the scan restarts forever (the #129 soak wedge -- stock Nintendo code, byte-
# identical in vanilla drmario.nes; the horizontal twin is correctly bounded). The GAME OVER /
# STAGE CLEAR text boxes write $8D/$8F/$EF straight into the field, so colour-$F chains are
# ROUTINELY armed at every match end. Fix: replace the wrap test with a real bound of identical
# length -- AND #$F8 / BEQ -> CMP #$80 / BCS (branch target byte untouched). Verified offline
# (tempo-wt tmp/wedge129): kills all known hangs; 4000/4000 random legal-colour boards leave a
# byte-identical field; also stops the vertical CLEAR loop ever writing past the field (removes
# the wedge's persistence mechanism, not just the hang). Applied by anchor match, never by
# pinned offset (#120 gate rot).
VERFIX = _os.environ.get("DRVERFIX", "0") == "1"
# DRUNPAUSE (#133): a P1-driven cart is UNPAUSABLE -- the P1 executor rewrites $F5 (the raw P1
# latch at hook time; the ROM derives pressed/held from it AFTER the hook) every hook from a
# vocabulary {none,right,left,down,A} with no START, and it runs before the stock edge-detect,
# so the pause loop's exact-compare $F5==$10 at $97D6 can never be satisfied: one stray START
# (human, script, or nav glitch) soft-locks the cart permanently. Fix: restore STOCK START
# semantics for P1 -- at the top of act_p1, if the raw latch has bit 4 set, write $F5 = $10
# (pure START, the exact byte both the pause entry and the pause exit compare against) and skip
# the synthesized command for that hook. With no controller attached the raw latch is 0 and the
# path never fires, so soak behaviour is unchanged; with one, START pauses AND unpauses exactly
# as on the stock ROM. Not emitted on DRHUMAN carts (P1 is already a passthrough there).
UNPAUSE = _os.environ.get("DRUNPAUSE", "0") == "1"
# DRSTARTGUARD (#134): guard the driver's START injection sites against landing on a match
# frame. The #131 lesson: gating a press on the mode read at HOOK time does not protect against
# the SAME frame's main loop advancing 8->4 and running the play input handler on the injected
# byte -- any mode-gated input arm must exclude the PREDECESSOR mode too. Sites:
#   1. autonav inject() -- skip the store when live $0046 reads 4 (the match frame) or 8 (its
#      predecessor; 8->4 transits within one frame). Structurally unreachable today (dispatch
#      only reaches inject from modes 0/1/7, and a menu-mode poke is re-read from hardware the
#      next frame) -- this makes it STRUCTURAL rather than incidental.
#   2. fc_clear stage-clear dismiss -- fires at mode==4 by design (RB337's blocking wait holds
#      $0046==4), but the state's FIRST hooks can still be inside a live play frame; require the
#      full-clear state to persist FC_STAB_K hooks before the first press. The wait lasts
#      seconds, so a ~4-hook arm delay cannot miss the dismiss (it can shift dismiss timing by
#      up to one 32-hook press window -- a tempo effect; see d131-wedge-discriminator-f30).
#   3. DRNAVESC -- already excludes mode 8 (intro hands-off) and fires only after ESC_N hooks of
#      a completely frozen ($0046,$F8,$0386) state, so it cannot land on a live-play or transit
#      frame by construction; at a frozen mode 4 its exact-$10 own-the-frame write is the
#      UNPAUSE idiom (recovery, not hazard). No code change -- documented + gated as-is.
STARTGUARD = _os.environ.get("DRSTARTGUARD", "0") == "1"
FC_STAB = 0x61C4      # DRSTARTGUARD site 2: hooks the full-clear state has persisted
                      # (RELOCATED 2026-08-20 from $61BB, which DRP1SLICE's SL_PH also
                      # claims -- the deriver's declared view kept one symbol per address
                      # and could not report the share; now the dup-declared check catches
                      # it. First byte of the $61C4+ free run in PRG_RAM_MAP.md; cleared
                      # every go_ai play hook, so a stale/garbage boot value only skips the
                      # arm delay once -- the pre-fix behaviour -- and never blocks a press)
FC_STAB_K = 4         # hooks (~2 frames at the 2-hook/frame play cadence) before the press

# minimum-think gate: hooks of search (WDOG2) the driver waits before committing laterally /
# locking orient. ~5 hooks/frame. Default 25 (~5f). Was 90 (~18f), a guard against the shallow-argmax
# slam back when searches were slow; with K_OPEN=255 (wait-for-DONE) + RECOMMIT (orient re-open at DONE
# if high) that guard is redundant, and at the fast ~40f silicon cadence the 18f floor was pure tempo
# loss at fast DONE (task #40 sweep: placement stays OPTIMAL at floor {90,45,25,0}; only tempo moves --
# @15f DONE land 35.8f->27.0f). 25 keeps a minimal floor as insurance if a build runs K_OPEN<255.
MIN_THINK = int(_os.environ.get("DRMINTHINK", "25"))
# DRSLAM=1 (default): CONFIDENCE-GATED SLAM. Once the capsule is column-aligned + orient-locked
# (ROT_DONE2, so the min-think floor already passed), fast-drop as soon as the published argmax has
# held stable for K hooks -- instead of idling at natural gravity until the search formally DONEs
# (~81% of a depth-3 search is confirmatory; tmp/tempo/TEMPO_DESIGN.md). SLAM REQUIRES ROTFIX: the
# min-think floor is safety layer 1 against the v1 shallow-argmax slam-suicide, so with DRROTFIX=0
# SLAM auto-disables. DRSLAM=0 rebuilds byte-exact to canonical (every add below is `if SLAM`-guarded).
SLAM = (_os.environ.get("DRSLAM", "1") != "0") and ROTFIX
# DRSLAM_MATURE (default 2, when SLAM): FAST_HI threshold on the search-latency HIGH byte (WDOGH2 =
# latency in 256-hook units). Arm the slam iff the last P2 search DONE'd in < FAST_HI*256 hooks.
# Derivation (tmp/driver_slam/round1_repro.py + tempo §2.3): warm depth-3 T_s ~= 300 hooks => WDOGH2=1;
# the cold-regression entry (an armed slam lands the pill ~106 f, before a slower DONE arrives) is
# WDOGH2=2. FAST_HI=2 is the unique 256-hook-granular threshold ABOVE warm-typical (300, arms) and
# AT/below the regression entry (530, disarms). Byte-patchable via the CMP #FAST_HI immediate.
# DRSLAM_MATURE=0 disables the gate (pre-fix slam, A/B).
#
# AUDITED 2026-08-01, and the wall-clock basis was WRONG before this. The old note read
# "512 hooks ~1.7 s", which assumed ~5 hooks/frame. The hook rate is TWO per frame -- MEASURED, by
# tracing the single NMI call site ($FFFA -> ... -> JSR $9134 -> getInputs -> addExpansionCTRL x2),
# and corroborated by working silicon (autonav's 4-hook press window only functions at 2/frame).
# So FAST_HI=2 is 512 hooks = 256 frames ~= 4.27 s, not 1.7 s.
#
# Why the audit happened: the Combo Stomper (chain180) made P2 searches ~1.83x longer, and this
# threshold was tuned against the PRE-CHAIN brain. Crossing it does not freeze -- it silently disarms
# the slam and placement falls back to the anytime path, i.e. it degrades play QUALITY invisibly. So
# it needed re-deriving against the new latency rather than inheriting. Measured worst-case searches
# vs the 4.27 s threshold:
#     MiSTer  chain180 @ 85.909 MHz   0.78 s   = 18% of threshold
#     Pocket  chain180 @ 54.669 MHz   1.23 s   = 29% of threshold  (projected)
# Both safe, so the silicon-tuned immediate SHIPS AS-IS -- no constant change. Re-audit this if the
# search latency changes again, or if a platform runs the copro slower than ~35 MHz.
FAST_HI = int(_os.environ.get("DRSLAM_MATURE", "2"))
MATURE = (FAST_HI > 0) and SLAM
# DRCOLGATE=1 (default ON with ROTFIX): the confidence-gated slam (dn_p2, below) was originally
# NO_FREEZE-only. The R47 Pocket freeze fix (2d71333) routed ROTFIX freeze-carts through the no-pin
# anytime path but did NOT extend THIS gate too -- so the now-unpinned pill soft-drops (dn_p2 -> LDY #4)
# off the ~MIN_THINK shallow argmax instead of weaving at natural gravity until the argmax is confidently
# stable. That is the R47 Pocket MISPLACEMENT ("placed the running argmax, not the converged answer").
# Extend the gate to ROTFIX -- the symmetric completion of the act-path fix at line ~838. NO_FREEZE=1
# carts are byte-IDENTICAL (the gate was already True). DRCOLGATE=0 reproduces the pre-fix soft-drop;
# DRROTFIX=0 -> COLGATE off -> canonical byte-exact.
COLGATE = ROTFIX and (_os.environ.get("DRCOLGATE", "1") != "0")
# DRRECOMMIT=1 (default ON, FREEZE carts only): the orient LATCHES at MIN_THINK (while the capsule is
# still HIGH, by design -- rotating a low/flush capsule can lock it backwards) and act_p2 never re-rotates
# after. So a slow copro whose orient converges AFTER the latch places the shallow orient forever. RECOMMIT
# re-opens the latch at DONE IFF the capsule is STILL high (Y >= CROSS_LOWY) and the converged orient
# differs -> act_p2 rotates once to the converged orient and re-latches (safe: high). On today's slow Pocket
# copro DONE lands BELOW the safe-rotate line => guaranteed no-op; it self-activates the instant the search
# converges above the line (combo-port's delta -- this is the DRIVER half that lets the delta fix the orient,
# without it a faster DONE still can't unstick the latch). Freeze-carts-only keeps the validated MiSTer AB
# (NO_FREEZE=1) byte-exact. Requires MATURE (all shipping carts have it): the block emits inside handle(2)'s
# DONE path, and only the MATURE idx==2 trampoline reaches {L}_start via a JMP -- without MATURE that path
# is a short BEQ and the extra bytes push it out of branch range, so gate on MATURE (which implies SLAM/
# ROTFIX). DRRECOMMIT=0 disables; DRSLAM=0 / DRSLAM_MATURE=0 / DRROTFIX=0 -> off -> byte-exact.
# DRRECOMMIT_NOFREEZE=1 (opt-in, default OFF): allow RECOMMIT on NO_FREEZE=1 carts too.
# The freeze-carts-only restriction above exists to keep the validated MiSTer AB cart
# byte-exact for A/B control -- it is NOT a correctness requirement. But it means MiSTer
# PLAY carts carry the orient-latch bug by design: user field report 2026-07-27, a YB pill
# placed into the corner as BY (right column, wrong colour order, never rotated twice), plus
# rare "really dumb" opening moves -- the opening is the SLOWEST search, so it is where the
# converged orient is most likely to arrive after the latch. Opt-in keeps every existing
# cart byte-identical; set this only for play carts. RECOMMIT self-gates (no-op unless DONE
# lands above CROSS_LOWY), so on a slow copro it costs nothing.
# DRPENDBOUND=1 (P0.2 fix, default OFF): bound the freeze_pending gravity pin to the settle
# window (PEND && DELAY!=0). Unbounded, a lock-while-armed pill latches PEND2 and pins the next
# capsule motionless until the STALE search DONEs or the watchdog fires (~minutes) -- the
# leading mechanism for the open MiSTer opening-stall (#56). stagnate() skips PEND/ARMED so the
# STUCK_LIM rescue can never fire during the pin.
PENDBOUND = _os.environ.get("DRPENDBOUND", "0") == "1"
# DRCOLDINIT=1 (P0.3 fix, default OFF): (a) cold-state init on ALL classes (the "anytime carts
# never pin" justification for the NO_FREEZE gate is wrong -- freeze_pending pins P2 with no
# class guard); (b) re-arm the init per MATCH (clear MATCH_ACTIVE on every menu hook, so the
# first play frame of every rematch re-runs it); (c) LASTY1/2 in the power-on init. Without
# this the strict Y>LASTY2 edge is suppressed after a topout (LASTY2 stuck at spawn row) and
# the first pill of every rematch gets NO search: it hard-drops at the PREVIOUS match's target.
COLDINIT = _os.environ.get("DRCOLDINIT", "0") == "1"
# DRSTUDYCOUNTS=1 (task #7 copro half, default OFF): the base pause path blanks shadow-OAM
# slots 8-15 (VIRUS counts 12-15, LEVEL digits 8-11); the STUDY part1 redraws text+preview but
# not the counters, so on STUDY carts the paused board shows an EMPTY virus box (user's Pocket
# photo). The driver hook runs every frame incl. pause frames ($46 stays 4 in the pause loop),
# so rebuild the 8 sprites from $0324/$03A4/$0316/$0396 every play hook: idempotent vs the
# game's own draw during play, and re-fills after the pause blank. Values/layout measured
# (study_viruscount_probe.lua): tile IS the digit, Y=$BF/$2B, X=6E/76/83/8B + 6D/75/84/8C.
STUDYCOUNTS = _os.environ.get("DRSTUDYCOUNTS", "0") == "1"
# DRSTUDY2P (task #39, default ON where STUDY is on): the copro carts ship the STUDY pause
# in v8.2 EVAC form -- part1 only, the 2P tail parts dropped because their base-ROM homes
# caused the $BC26 KIL and the $BE56 level-select garble, and the fixed bank has exactly ONE
# dead run (the 52 B part1 already occupies; measured, not assumed). Price of the evac,
# byte-proven by the 2026-08-02 Mesen probe on BOTH deployed carts: P1's preview frozen at
# its 1P position over the wrong board, P2's preview never written, STUDY unlifted -- the
# user-reported "floating pill". THE FIX LIVES WHERE THE SPACE IS: the driver hook runs
# every frame INCLUDING pause frames (the STUDYCOUNTS mechanism), so unit1 redraws the
# 2P-correct preview layout every play-mode hook. During play the game's own OAM rebuild
# owns the frame (same invisibility as the digit redraw); during pause -- where part1 runs
# ONCE at entry -- the hook's writes win from the next frame on. No base-ROM site touched,
# no KIL/garble risk, works on every copro cart.
_STUDY2P_ENV = _os.environ.get("DRSTUDY2P", "1") != "0"   # combined with STUDY below its def
# DRP1WIGGLE=1 (SPECTATOR feature, default OFF -> every existing cart byte-identical): on a
# CvC cart the P1 side is a dud -- it stacks at the spawn column and tops out with all 48
# viruses alive (user's MiSTer screen, 2026-08-01), so half the screen is dead within a
# minute. WIGGLE gives P1 a deliberately dumb but *watchable* policy: alternate a HELD LEFT
# and a HELD RIGHT for each pill's whole descent, so consecutive pills bank off opposite
# walls and the stack spreads instead of growing one tower.
#
# ★ INPUT MODEL (from the game's own code, not guessed -- the BCD lesson). The 0x37CF hook
# sits at the TAIL of addExpansionCTRL, i.e. INSIDE getInputs and BEFORE its _pressedVsHeld
# pass. That pass (disasm prg/drmario_prg_general.asm:367) is:
#       lda p1_btns_pressed,X / tay / eor p1_btns_held,X / and p1_btns_pressed,X
#       sta p1_btns_pressed,X          ; pressed = raw & ~previous-held
#       sty p1_btns_held,X             ; held    = raw
# so $F5 is the RAW pad latch and the game DERIVES both $F5 (pressed, X=0) and $F7 (held)
# from it. Therefore a HELD direction is "write $F5 = dir EVERY hook and never touch $F7":
# held stays asserted, and the pressed edge fires exactly once (the first hook), which is
# precisely a human pushing and holding the d-pad. Writing $F7 ourselves would mark the
# button already-held and kill the edge (the original autonav injection bug, line ~750).
# The direction bits must ride $F5 because fallingPill_checkXMove ($8DCF) reads
# currentP_btnsPressed only to pick "instant move vs DAS", then reads currentP_btnsHELD for
# the actual direction -- a pressed-only injection with held==0 moves NOTHING.
#
# Scope: CvC only. On a DRHUMAN cart P1 is a PERSON and the cart must never press their
# buttons (spec P0.4) -- the assert below refuses the combination rather than silently
# ignoring it. Under WIGGLE the driver OWNS P1's descent: act_p1's copro steering is
# replaced outright and freeze_pending stops pinning GRAV_P1 (a pin would stall the very
# descent we are steering). handle(1) still runs, so P1's $5000 copro traffic is unchanged.
P1WIGGLE = _os.environ.get("DRP1WIGGLE", "0") == "1"
assert not (P1WIGGLE and HUMAN_P1), (
    "DRP1WIGGLE=1 with DRHUMAN=1 is refused: P1 is a human on a DRHUMAN cart and the cart "
    "must never press their buttons (spec P0.4). Build the wiggle on a CvC cart only.")
# DRP1NATIVE=1 (SPECTATOR feature, default OFF -> every existing cart byte-identical): give P1
# the v28cs NATIVE depth-1 6502 AI, with its soft-drop stripped so it plays slowly on purpose.
# A middle rung between DRP1WIGGLE (alive but mindless) and a real copro opponent: v28cs-class
# d1 clears ~9.1% ROM-faithful / ~6.7% live at L11 -- competent, clearly beatable, watchable.
#
# ★ WHY P1 NEEDS THIS AT ALL (measured 2026-08-01, save-state PRG-RAM): the deployed core
# does NOT decode P1's copro window at $5000. Reads return open bus = the address high byte
# $50, so handle(1)'s GO is read straight back as DONE, it publishes column $50 = 80, and
# act_p1's `CMP TGT_C1 / BCC` is then ALWAYS true -> P1 held RIGHT forever and piled its whole
# stack into the right wall (pre-wiggle board grids right-half 22 / left-half 6). So under
# this flag handle(1) is DROPPED entirely: on this core it does not merely waste the ~5.4k-cycle
# board upload, it actively publishes garbage. That also frees copro1 and, conveniently, removes
# a spike that fired on the SAME new-pill edge as the native search.
#
# ★ COST, and why the obvious worry is the wrong one. The 0x37CF hook runs EXACTLY 2x per
# frame and BOTH are inside the NMI (see the hook-location note above) -- there is no main-loop
# invocation to move heavy work to. But the hook runs AFTER every PPU write in the NMI, so an
# over-long invocation eats the main loop's share of the 29780-cycle frame rather than
# corrupting the display; vblank is NOT the budget. Measured: the driver is ~400 cyc/hook
# (p95 460), and one d1 search is 16-23k cyc ONCE PER PILL. So this costs about one hitched
# frame per P1 pill (~1 in 200 at L11), and the only dangerous case is overrunning a WHOLE
# frame, so the next NMI re-enters.
#   ⚠ CORRECTION 2026-08-09: this line used to end "-- is already caught by the BUSY guard."
#   That is FALSE and was hazard 1. An overrun NMI loads PC from $FFFA and executes NOT ONE
#   BYTE of the $FF54 trampoline where the guard lives, so it re-enters main UNGUARDED. Only
#   DRRTIVEC closes it; on a cart built without that flag this cost paragraph understates the
#   risk. See the NMI-OVERRUN SILICON HAZARDS block near DRBUSYESC.
#
# ★ THE TWO-PASS AND, which is the one real trap. getInputs calls the hook twice and ANDs the
# two $F5 values, so BOTH passes of a frame must leave the SAME byte or the input vanishes
# (this is the DRNAVDWELL failure shape). v28cs's per-pill cache already guarantees it: hook 1
# sees a new pill Y, searches, and stores the key; hook 2 sees the key match, skips the search
# and reuses the same target -> identical byte. P1AI_Y is that key. Any future per-pill work
# here MUST preserve this; tests/test_p1_native.py asserts it directly.
P1NATIVE = _os.environ.get("DRP1NATIVE", "0") == "1"
assert not (P1NATIVE and HUMAN_P1), (
    "DRP1NATIVE=1 with DRHUMAN=1 is refused: P1 is a human on a DRHUMAN cart and the cart "
    "must never press their buttons (spec P0.4). Build the native P1 AI on a CvC cart only.")
assert not (P1NATIVE and P1WIGGLE), (
    "DRP1NATIVE=1 and DRP1WIGGLE=1 are mutually exclusive: both replace act_p1 outright, so "
    "one would silently win. Pick the P1 personality you want.")
P1_OWNED = P1WIGGLE or P1NATIVE   # act_p1 is replaced; the copro P1 path is not used at all
# DRP1SLICE=1 (default OFF -> byte-identical; requires DRP1NATIVE): #126 enforcement (b) for
# the P1 native search. The unsliced search runs all 15 placements + the colour-swap re-eval
# synchronously inside ONE hook -- sound cycle bound 90,012, adversarially measured 26,398,
# live-measured 19,818 (tools/nmi126/NMI126_BOUND_REPORT.md) -- which can push the whole NMI
# past the 29,780-cycle frame on tall same-colour tower boards (the near-death regime).
# Sliced: a PRG-RAM state machine runs ONE column-step per hook (a step = one v_loop or
# h_loop iteration = at most one eval_pair; the spec ceiling was two, but two steps in both
# hooks of a frame pushes the census same-frame pair bound to 36k > the 29,780 frame --
# one step keeps the whole frame provably inside budget). 8 V + 7 H + 1 swap step finish in
# <=16 hooks = 8 frames, and the result publishes to P1AI_C/P1AI_O exactly as before. Loop BODIES are verbatim transcriptions of the v18 AI's
# (tests/test_p1slice.py holds whole-chain argmax equivalence against the unsliced search,
# with zp scratch deliberately clobbered between ticks -- the game owns those bytes between
# NMIs, so everything cross-step lives in PRG-RAM and is restored per tick).
# Two documented behaviour deltas, both bounded and spectator-grade:
#   * the publish can land on hook 1 of a frame, so that frame's two $F5 passes may differ
#     and the AND eats ONE input frame per pill (the press retries next frame);
#   * the board can change mid-search (a volley landing on P1), so early steps may have seen
#     the older board -- inconsistency window <=4 frames, same class as anytime steering.
P1SLICE = _os.environ.get("DRP1SLICE", "0") == "1"
assert not (P1SLICE and not P1NATIVE), (
    "DRP1SLICE=1 without DRP1NATIVE=1 is refused: there is no P1 native search to slice.")
# state machine, allocated from the PRG_RAM_MAP free run $61BB-$61FF:
SL_PH  = 0x61BB   # phase: 0 idle, 1 vertical pass, 2 horizontal pass, 3 swap+publish
SL_COL = 0x61BC   # resume column for the current pass
SL_BEST = 0x61BD  # persisted Z_BEST  ($01)
SL_TGT = 0x61BE   # persisted Z_TARGET($00)
SL_ORI = 0x61BF   # persisted Z_BORIENT($DA)
SL_OFA = 0x61C0   # persisted best-cell offsets ($D0/$D1, the swap re-eval's input)
SL_OFB = 0x61C1
RECOMMIT = (MATURE
            and (not NO_FREEZE or _os.environ.get("DRRECOMMIT_NOFREEZE", "0") == "1")
            and (_os.environ.get("DRRECOMMIT", "1") != "0"))
# DRRELATCH=1 (default OFF -- v6c candidate): RE-LATCH-ON-CHANGE, the classes-b/c/d fix from the
# execution-fidelity census (wf_5583bec4-ed9, 2026-08-09; see the census memory note + the flip-arm
# harness mesen_copro_qa/census/census_run_flip.lua). RECOMMIT (above) re-opens the orient latch
# exactly ONCE, at DONE, inside handle() -- it fully covers stable commits (0/2644 in the census
# stable arm). But the live-publish path (nf2_* in act, below) refreshes the COLUMN from the
# running-best mailbox EVERY hook while the orient stays feasibility-locked, so when the copro's
# running best FLIPS mid-pill (congested boards) the driver adopts the post-flip COLUMN (922/922
# in the flip arm) yet keeps the PRE-flip ORIENTATION (112/922 stale adoptions) -> true backward
# horizontals at the correct column, plus real nonsensical verticals. RELATCH extends RECOMMIT's
# one-shot into on-change: whenever the live-published MAPPED orient differs from the latched
# TGT_O2 AND rotation is still safe (BOARD_Y $0386 >= CROSS_LOWY; $0386 counts UP from the floor,
# so >= means still high), adopt the new orient and re-open ROT_DONE2 -- act_p2's existing
# pre-phase then rotates toward it and re-latches through the normal p2_commit think gate (the
# SLAM stability counter resets automatically via LAST_ORI2, so a flip also re-earns its
# confidence). Below the line the committed orient is KEPT -- the CROSS_LOWY no-backwards-lock
# invariant, verbatim from RECOMMIT/ROTFIX, is preserved unconditionally. Gated on ROTFIX (the
# orient latch this re-opens only exists under ROTFIX). DRRELATCH=0 rebuilds byte-exact (nothing
# emitted; verified in tests/test_relatch.py + the v6b manifest replay).
RELATCH = ROTFIX and (_os.environ.get("DRRELATCH", "0") == "1")
# DRDISTGATE=1 (default OFF -- candidate, not yet A/B'd on silicon; see task #49's
# CART_FIX_REPORT.md and REVIEW #6.2 in dr-mario-qa-wt/experiments/eval47/PAIR_LATCH_AUDIT.md):
# neither COLGATE/RECOMMIT/SLAM reasons about *distance* -- how many columns the search's target
# is from the capsule's current column -- only about *when* to commit. tests/
# test_task49_slamarm_race.py's Test E showed a commit-6-shaped case (3-column distance, ~40-hook
# window) simply cannot complete the DAS traverse in time (needs ~96 hooks, matching REVIEW
# #6.2's own arithmetic) and, since SLAM_ARM=0 rules out an accelerated slam (Test A), the
# capsule just parks wherever WEAVE got it to when gravity locks it -- often still the spawn
# column, since 20-40 hooks after a late-converging search isn't enough for even ONE DAS edge in
# the worst case. DISTGATE bounds the STEERING target itself by DAS-reachability given the
# remaining fall budget (BOARD_Y=$0386, row-space), so lateral progress always happens toward the
# best REACHABLE column instead of chasing an argmax that will never arrive in time -- the floor
# is "closer to the true best than spawn," not "spawn," once budget > 0.
#
# ★ MIN-1 FLOOR, and why it's load-bearing (found by tests/test_task49_distgate.py's Test 3a,
# first attempt -- a genuine defect in an early version of this table, not a hypothetical one):
# a naive floor(Y * DIST_GRAVROW / DIST_DASEDGE) DROPS TO 0 while Y is still > 0, because
# DIST_DASEDGE (32) > DIST_GRAVROW (26) -- one row of remaining fall-time (26 hooks) is NOT
# enough to complete one DAS edge (32 hooks), so a straight floor() division reports "0 columns
# reachable" partway THROUGH an edge that was already promised 1 column of budget on an earlier
# hook (when Y was larger). Recomputing the clamp fresh every hook then makes the bound RETREAT
# to wherever PX2 currently sits -- which can be BEFORE the capsule has moved at all -- producing
# an artifact "alignment" with the ORIGINAL spawn column. Since STABLE_CT2 (search-answer
# stability, tracked independently since the search's target first appeared, unrelated to this
# retreat) can already be past K_CROSS by then, dn_p2 fires a confident-looking SLAM at the
# column the capsule never actually chose to commit to -- a false-confidence commit AT SPAWN,
# which is worse than the pre-DISTGATE behavior (dn_hold, no forced button) for the exact
# scenario this gate exists to help. Flooring the budget at 1 (whenever ANY row of clearance
# remains, Y>0) guarantees the clamped target is always at least 1 column from PX2 in the raw
# target's direction until Y truly hits 0 (no fall-time left at all, at which point locking
# wherever the capsule already is IS the correct, unavoidable outcome) -- so the bound can never
# retreat all the way back to "no movement was ever needed," only shrink toward "less movement
# than originally hoped," which is a real, non-pathological degradation.
#
# Table-driven (2-pass-safe, no runtime multiply/divide): DIST_TABLE[Y] = 0 if Y==0 else
# max(1, min(7, floor(Y * DIST_GRAVROW / DIST_DASEDGE))).
#
# ★ CONSTANTS MEASURED FROM SILICON FOOTAGE (2026-08-05, task #49 follow-on; see
# CART_FIX_REPORT.md's DAS/gravity-validation section for the full methodology). The FIRST
# version of these defaults (32 hooks/edge, 26 hooks/row) was NOT measured -- it inherited the
# mv_p2 comment below's "32-hook cycles = 6.4 frames per edge" figure, which itself was derived
# under the OLD "NAV_T=5*/frame" assumption (32 = 6.4 * 5) that the file's own 2026-08-01 audit
# (the "WHERE THE HOOK ACTUALLY RUNS" note, above) already corrected to 2 hooks/frame for OTHER
# constants (FAST_HI) but never revisited for this one. Converting the SAME frame-based design
# target (6.4 frames/edge) through the CORRECT 2 hooks/frame gives ~13 hooks, not 32 -- and a
# direct silicon measurement (below) landed even tighter.
#
# Tracked ~1920 frames of the m3 death-window footage (p2_60fps_death/, 60fps, the AI's own
# capsule) plus a fresh 90s/5400-frame extraction from an earlier match segment (t=120-210s,
# source ~/Videos/drmario_sessions/20260804_1955_pocket_dock.mp4, P2 crop 392x824 @ 1120,224) via
# a new P2-specific tracker (dr_mario_rl/tmp/film_review_20260804/tracker_p2_death.py, built on
# the existing tracker.py's already-validated per-frame capsule search -- confirmed independently
# correct here too: its spawn timestamps and spawn-to-lock frame counts reproduce VERDICT.md's
# six audited commits to 3 decimal places / exact frame counts without having been told them).
#   DAS repeat cadence: n=4 CLEAN steady-state lateral repeats (no rotation event, no row-advance
#   coincident with the gap) -- ALL exactly 6 frames, zero spread. A SEPARATE cluster of n=5
#   "first repeat after engaging DAS" gaps read 16 frames (one exception read 6) -- plausibly a
#   one-time engage cost distinct from the steady-state repeat rate, but the sample is too small
#   to fully characterize past "clean repeats are tight at 6 frames"; DIST_DASEDGE uses the clean
#   steady-state number, which is what governs total distance covered over a multi-column
#   traverse. 6 frames * 2 hooks/frame = 12 hooks/edge.
#   Gravity (natural fall, non-soft-drop, measured in the death-window footage specifically --
#   the context DISTGATE actually targets, near-topout/critically-stacked): n=10, dominant cluster
#   at 15 frames/row (8/10) with 2 at 16 -- mean ~15.2, call it 15. An EARLIER match segment (the
#   90s sample above) measured faster and more scattered (9-13f/row) -- unexplained (possibly
#   level/context-dependent; flagged, not resolved). Using the near-topout reading since that's
#   DISTGATE's target scenario. 15 frames/row * 2 hooks/frame = 30 hooks/row.
#
# NET EFFECT: DAS is much faster than the stale defaults assumed (12 vs 32 hooks/edge) and
# gravity is somewhat slower (30 vs 26 hooks/row) -- both push the SAME direction (more budget
# available per row of remaining fall-time). This also means REVIEW #6.2's "commit-6-shaped, needs
# ~96 hooks for 3 columns" arithmetic (and this file's own earlier tests/test_task49_slamarm_race.py
# Test E, built on the same stale 32/26 pair) used the wrong hook budget: 3 columns cost 36 hooks
# under the corrected numbers, not 96 -- worth a follow-up re-audit of that earlier "physically
# infeasible" conclusion, not done here (task #49's ORIGINAL increment is already committed/pushed;
# flagging rather than silently rewriting it).
#
# ★★ SURFACE-RELATIVE REBUILD (2026-08-09, v6c acceptance follow-on -- wf_c6d25d83 forensics).
# The FIRST DISTGATE indexed the budget by $0386 DIRECTLY -- but $0386 is FLOOR-relative Y
# (counts UP from the floor, memory dr-mario-savestate-layout), i.e. "rows until the BOTTLE
# FLOOR", not "rows until the capsule actually locks". On a filled board (height h >= 12, the
# census defect regime) the capsule locks at HIGH $0386 (>= h), so DIST_TABLE[$0386] with the
# corrected constants saturates at 7 = the whole board width and the gate NEVER RESTRICTS in
# exactly the regime it exists for: acceptance census 2026-08-09 measured class-a 29/1038
# pill-for-pill IDENTICAL to the gate-OFF arm (h>=12: 29/307 = 9.45%) -- FAILED VACUOUSLY.
# The rebuild indexes by SURFACE-RELATIVE REMAINING FALL: how many rows the capsule can still
# fall before reaching the STACK SURFACE, scanned from the live board the driver already owns
# ($0500, the same bytes it uploads to the copro). Constants and DIST_TABLE are UNCHANGED --
# only the table INDEX changed. Signal choice (CONSTRAINT, documented per the rebuild spec):
#   remaining fall = (rows strictly below the capsule's row that are fully EMPTY across the
#   column span [min(PX2,target)..max(PX2,target)]), i.e. fall to the MAX SURFACE EN ROUTE,
#   endpoints inclusive. Chosen over "target column's surface only" because a taller pillar
#   BETWEEN the capsule and the target catches the capsule first -- target-only would promise
#   fall time the capsule does not have (unsafe, over-budgets). Chosen over a whole-board max
#   because columns outside the travel span cannot intercept (over-restricts, no safety gain).
#   Conservative residual: a pillar past the CLAMPED column still shrinks the budget (span is
#   computed against the RAW target) -- costs optimality only, never promises the unreachable.
#   NOT modeled (capsule treated as a point at ($0385,$0386), consistent with every other user
#   of the pose in this driver): the horizontal partner column PX2+1 and the vertical second
#   half; empty cells are $FF *or* $00 (tile-encoding, same normalization rule as the _start
#   upload loop) and anything else reads as stack.
# Scan cost is bounded by DIST_SCANCAP (below): the table saturates at its max value by index
# DIST_SCANCAP, so scanning more than DIST_SCANCAP empty rows cannot change the budget --
# worst case 3 rows x 8 columns = 24 cell reads per hook at the default constants.
# DRDIST_FLOORREL=1 re-emits the ORIGINAL floor-relative index ($0386 -> table, no board scan).
# It exists ONLY as the killed mutant for tests/test_task49_distgate.py (house gate standard:
# the old defective indexing must demonstrably FAIL the new tests). NEVER ship it.
# DRDISTGATE=0 rebuilds byte-exact (nothing emitted; verified in tests/test_task49_distgate.py).
DISTGATE = _os.environ.get("DRDISTGATE", "0") == "1"
DIST_FLOORREL = _os.environ.get("DRDIST_FLOORREL", "0") == "1"   # TEST-ONLY mutant, see above
DIST_DASEDGE = int(_os.environ.get("DRDIST_DASEDGE", "12"))
DIST_GRAVROW = int(_os.environ.get("DRDIST_GRAVROW", "30"))
DIST_TABLE_LEN = 16   # index space is ROWS OF REMAINING FALL (0..15); 16 covers the playfield
DIST_TABLE = bytes(
    0 if y == 0 else max(1, min(7, (y * DIST_GRAVROW) // DIST_DASEDGE))
    for y in range(DIST_TABLE_LEN))
# First index at which DIST_TABLE reaches its own maximum (table is monotone nondecreasing by
# construction). Scanning deeper than this many empty rows cannot change the budget, so the
# 6502 board scan caps its row count here. max(1,...) guards a degenerate all-flat override.
DIST_SCANCAP = max(1, next(i for i in range(DIST_TABLE_LEN)
                           if DIST_TABLE[i] == DIST_TABLE[DIST_TABLE_LEN - 1]))
# Surface-scan scratch (PRG-RAM $61B1-$61B7: first free bytes past DRSTUDY2P's S2P_TTL at
# $61B0; next allocation is the trace ring at $6200). All are per-hook scratch, no state
# carried across hooks.
DG_YC   = 0x61B1   # $0386 clamped to 0..15 (defensive: table/row math assumes row-space)
DG_FALL = 0x61B2   # scanned remaining-fall rows (the new DIST_TABLE index)
DG_N    = 0x61B3   # rows left to scan = min(DG_YC, DIST_SCANCAP)
DG_OFF  = 0x61B4   # current row's board offset (row*8 + DG_LO)
DG_LO, DG_HI = 0x61B5, 0x61B6   # column span [min(PX2,target) .. max(PX2,target)]
DG_CSPAN = 0x61B7  # span width DG_HI-DG_LO+1 (1..8), inner-loop counter reload value
# DRNAVFIX=1 (default): STABILITY-GATED AUTONAV. The canonical an_title fires START the instant $04!=0;
# a cold-boot garbage-nonzero $04 (title fade-in, before menu-init) then STARTs into a 1P game. DRNAVFIX
# withholds START until VS-CPU-armed ($04!=0 AND $0727==2) has held for NAV_M consecutive hooks -- the
# same stability principle as the slam gate, applied to nav. Also un-armed no longer over-toggles past
# VS-CPU (it waits while accumulating). DRNAVFIX=0 rebuilds the byte-exact canonical nav (A/B parity).
# NAVFIX uses a LEAKY armed-stability counter (NAV_STABLE): armed -> +1 toward NAV_M, un-armed -> -1
# (NOT reset). A menu-redraw flicker (the gauntlet failure: $04/$0727 bounce ~1 hook per redraw) only
# nibbles the count, so a genuinely-sustained VS-CPU still fills it -- the consecutive-reset v1 never
# reached the threshold under flicker and the title timed out into the attract demo (2/5 cold loads).
NAVFIX = _os.environ.get("DRNAVFIX", "1") != "0"
# DRTRACE=1: DIAGNOSTIC-ONLY build. main becomes a passive tracer -- NO autonav / AI / dispatch. Every
# hook it logs ($0046 mode, $0727, $04) ON CHANGE into a 64-entry ring, so a cold boot's REAL menu-state
# evolution (power-on -> intro -> title -> demo ...) can be dumped from hardware and v4 designed against
# real data. The ring survives reset (RAM persists across core reload -- the very thing we're diagnosing),
# so boots are identified by their mode==8 entries. Written to BOTH copro window $5000 and PRG-RAM $6200.
TRACE = _os.environ.get("DRTRACE", "0") == "1"
# DRPROBE=1: instrument the FULL cart (nav + AI stay LIVE -- unlike DRTRACE which strips them). Logs
# ($0046,$0727,$04) ON CHANGE into the same $6200 ring as DRTRACE, so the CANONICAL AB cart's real
# menu-state evolution AND its per-boot EXIT/residual state (what the next boot inherits via sticky
# RAM) can be dumped from a save-state (PROVEN 2026-07-22: the copro .ss carries $6200 -- decoded a
# real ring at .ss offset 0x103508). NO on-screen render / NO PPU writes (main runs main-loop timing,
# not vblank) -> cannot corrupt scroll. DRPROBE=0 (default) rebuilds byte-exact (nothing emitted).
PROBE = _os.environ.get("DRPROBE", "0") == "1"
# NAV_M: NET armed hooks (arm minus flicker) required before START (byte-patchable). The cold-boot
# garbage window is ~5-15 hooks (menu-init), so NAV_M=24 rejects it; the leaky counter fills 24 at a
# genuine VS-CPU for any flicker interval R>=3 (net rate (R-2)/R), well inside the ~10 s title timeout.
NAV_M = int(_os.environ.get("DRNAV_M", "24"))
# DRNAV_V4 (default ON when NAVFIX): state-directed v4 nav. Root cause (silicon ring, 2026-07-22): every
# boot RESETS $0727/$04 to (1,0) -- inherited menu state is NOT the flip-var. A sticky title-idle advance
# races the nav: when the title advances fast the 32-hook $FF30 toggle window is starved and the nav never
# reaches VS-CPU -> 1P mis-land (the 1P,VS,1P sticky alternation); when it lingers the nav toggles -> VS.
# v4 DIRECTLY writes coherent VS-CPU ($0727=2,$04=1) each title hook (disasm-verified: $FF30 only ever
# touches $0727/$04, so a direct write == the toggle end-state) with ZERO window latency, holds a short
# NAV_M4 confirm, then STARTs -- beating the fast advance. DRNAV_V4=0 -> old v3 (leaky toggle + force).
NAV_V4 = NAVFIX and (_os.environ.get("DRNAV_V4", "1") != "0")
# DRFCGATE=1 (default OFF, byte-neutral when off): narrow the v4 full-clear gate from mode>=4 to
# mode==4 exactly. See the fc_no site for the mechanism -- mode 8 (the two-bottle intro) passes
# mode>=4 with VCOUNT still 0 and VSEEN inherited, so fc_clear false-fires there and the intro can
# never hand off to play. Independent of DRHOLDBOARD: HOLDBOARD is what leaves MATCH_ACTIVE set
# after a match, but ANY path that does so arms the same dead-cart loop.
FCGATE = _os.environ.get("DRFCGATE", "0") == "1"
NAV_M4 = int(_os.environ.get("DRNAV_M4", "4"))    # title hooks (2,1) held before START (short: beat the advance)
# DRNAV_HOLD (default ON with V4): reset waitFrames ($51)=0 each title hook so the attract demo NEVER trips
# (labeled-disasm confirmed: base $98FE does inc $51 / cmp #$08 / beq @toDemo, and @toDemo forces
# nbPlayers=1). This is THE fix for the mis-land; DRNAV_HOLD=0 reproduces the pre-hold 3/6 (demo wins).
NAV_HOLD = NAV_V4 and (_os.environ.get("DRNAV_HOLD", "1") != "0")
# DRNAVDWELL (default ON with V4): TITLE DWELL -- hold autonav's FIRST title START for ~DRNAVDWELL_F frames
# so the TRAINING EDITION branding is visible at every boot (else the autonav enters L11 in ~4 hooks and the
# title logo is never seen). PURE frame-count gate placed IN FRONT of the nav VS-CPU write + stability gate
# (both byte-INTACT downstream) -- does NOT touch the silicon-validated $51/mode/$04 stability logic. The $51
# demo-hold above keeps running each dwell hook so the attract demo never trips. Counts real frames via the
# game's frameCounter $43 (hook-rate-independent), saturates at DRNAVDWELL_F (no wrap), and re-arms PER BOOT
# /RESET (cold-init + the mode-8 intro block, which fires at every power-on). It deliberately does NOT re-arm
# at the START injection: that ran on the first injecting hook, so the next hook of the same press window
# re-entered the dwell hold and RTSed before inject(), narrowing the press to ONE hook -- and the game ANDs
# TWO raw passes of $F5, so a 1-hook press never registers and the title re-dwelled forever (the DRNAVDWELL
# silicon hang). GENERAL RULE: any early-RTS between the window check and inject() silently narrows the press
# below the two-pass AND threshold; injection must span the whole 4-hook window.
# Gated on NAV_V4 so the DRNAVFIX=0 byte-goldens are unaffected.
# DRNAVDWELL=0 reverts (byte-identical nav). py65: nav still lands VS-CPU, just ~DRNAVDWELL_F frames later.
NAVDWELL = NAV_V4 and (_os.environ.get("DRNAVDWELL", "1") != "0")
DWELL_FRAMES = int(_os.environ.get("DRNAVDWELL_F", "180"))   # ~3 s at 60 fps
# Phase-aware tuning table (byte-patchable immediates, DRMINTHINK-style, so per-platform tuning
# is a rebuild via env or a byte-patch). K is in HOOKS the argmax has been stable (~5 hooks/frame;
# the FPGA publishes ~1 candidate / ~10 hooks on MiSTer, ~4x slower on the 21.47MHz Pocket -> the
# gate is the PRIMARY commit there, so retune K per platform):
#   K_OPEN  : opening/mid (virus_count >= VC_ENDGAME). Default 255 = require DONE. Was 40 (aggressive),
#             but at the fast ~40f copro cadence a low K commits a PARTIAL-search argmax: min-think
#             locks orient early and the confidence slam soft-drops the shallow decoy BEFORE the
#             search converges (the strength regression, task #40 -- validated on the shipped binary:
#             unpatched lands the decoy, K=255 lands optimal at ~v2 tempo). K_CROSS still commits
#             genuinely-slow / never-DONE searches, so the anti-drift-lock escape is unaffected.
#   K_END   : endgame (virus_count < VC_ENDGAME) -- 255 = require DONE (early commits ~20% worse there).
#   K_CROSS : PAST THE FEASIBILITY CROSSOVER (still searching while the capsule is already low, Y <
#             CROSS_LOWY) -- minimal stability: DONE is physically unreachable, so commit the stable
#             argmax rather than drift-lock (TEMPO_DESIGN §2.5). This reactive net self-calibrates --
#             it never trips when the search finishes before the capsule falls (e.g. incremental-eval).
K_OPEN     = int(_os.environ.get("DRSLAM_KOPEN",  "255"))
K_END      = int(_os.environ.get("DRSLAM_KEND",   "255"))
K_CROSS    = int(_os.environ.get("DRSLAM_KCROSS", "8"))
VC_ENDGAME = int(_os.environ.get("DRSLAM_VCEND",  "10"))
# ★ VCOUNT_P1/P2 ($0324/$03A4) are BCD, not binary (proven from the game's own draw code at
# file offset 0x446: AND #$F0 / LSR x4 / AND #$0F, and from an empirical probe at L20 where
# an 84-virus board reads $84, not $54). The gate below is a plain binary CMP, so it is only
# correct while the threshold is <= 10: counts 0-9 have identical BCD and binary bytes, and
# BCD 10 is $10 = 16 which still compares >= any threshold <= 10. At 12, BCD 11 ($11 = 17)
# would compare ABOVE the threshold and silently classify the endgame as midgame.
assert VC_ENDGAME <= 10, (
    f"DRSLAM_VCEND={VC_ENDGAME} is unsafe: the virus counters are BCD and this gate is a "
    "binary CMP, so thresholds above 10 misclassify counts 11-15. Either keep it <= 10 or "
    "convert the gate to a BCD-aware comparison.")
CROSS_LOWY = int(_os.environ.get("DRSLAM_LOWY",   "8"))
VCOUNT_P1, VCOUNT_P2 = 0x0324, 0x03A4   # remaining virus counts (0 => that player cleared -> STAGE CLEAR)
W2_BASE = 0x5200
# DRPOCKET=1: single-window build (Analogue Pocket core has only the $5000 window).
# P2's copro traffic rides the $5000 mailbox instead of $5200. Requires DRHUMAN=1
# (P1 must not be using the window; with both players active they'd collide).
if _os.environ.get("DRPOCKET", "0") == "1":
    assert _os.environ.get("DRHUMAN", "0") == "1", "DRPOCKET requires DRHUMAN=1 (single window)"
    W2_BASE = 0x5000
# TUCK descriptor lives at offsets $87/$88 of P2's OWN copro window (see the W_TCOL comment
# at the TUCK EXECUTOR block above): $5087/$5088 on DRPOCKET single-window carts (unchanged
# vs the historical hardcode), $5287/$5288 on dual-window MiSTer carts.
W_TCOL, W_TROW = W2_BASE + 0x87, W2_BASE + 0x88
# if a pill sits still this many frames (while not search-frozen), force DOWN to unstick
STUCK_LIM = 60        # 1s -- continuous holds again; if truly stuck kick fast to unpark
# copro window (mapper 100)
W_BOARD, W_CA, W_GO, W_DONE, W_COL, W_OR = 0x5000, 0x5080, 0x5084, 0x5084, 0x5085, 0x5086
# NES pad bits on $F5 (pressed-this-frame): A=$80 B=$40 Sel=$20 Start=$10 U=$08 D=$04 L=$02 R=$01
B_SEL, B_START, B_LEFT, B_RIGHT = 0x20, 0x10, 0x02, 0x01

# DRHOLDBOARD=1 (task #48, default OFF -> byte-identical when off): keep BOTH bottles fully
# visible after a match ends -- inter-match STAGE CLEAR (RB24F_CHECK_WIN/RB337_STAGE_CLEAR)
# and set-final GAME OVER (L958A_TOP_7) -- until START, instead of the banner/dialog text.
# STUDY's technique (defer the pause blank by patching $978E's own body) does NOT transfer:
# unlike pause, RB337_STAGE_CLEAR (and TOP_7's RB894_FILL_PAGES) destroy the PLAYFIELD RAM
# MODEL ITSELF ($0400/$0500, fill-with-$FF + message bytes), not just the PPU nametable, and
# they do it IMMEDIATELY/synchronously the moment virus==0 or a topout is dispatched -- there
# is no START-gated checkpoint before the overwrite in either routine (read directly from the
# disassembly: RB24F_CHECK_WIN calls RB337_STAGE_CLEAR before ever touching $F5/$F7, and
# L958A_TOP_7 fills+prints before its own wait-loop). So the mechanism here is SNAPSHOT+REDRAW:
# continuously mirror both boards into PRG-RAM while a match is live (cheap relative to the
# alternative of trying to intercept a synchronous write mid-instruction), then, once a
# match-end is detected, overwrite $0400/$0500 back from the mirror and re-trigger the game's
# OWN row-redraw drain (L0300/L0380_UPDATE_ROW=$0F, the same mechanism RB337_STAGE_CLEAR/
# R96D4_GAME_OVER themselves use) every hook until the human's own START (checked the same way
# the vanilla wait-loops do: ($F5|$F7)&$10) releases it. COST: the continuous mirror is a
# 2x256B copy every "dispatch" hook (~5.9k cyc measured-equivalent instruction count, 2x/frame
# during ALL of active play) -- see FINAL_BOARD_HOLD_REPORT.md for the honest accounting; the
# existing BUSY-guard (DRBUSYESC) already covers the rare case this pushes a hook past budget.
HOLDBOARD = _os.environ.get("DRHOLDBOARD", "0") == "1"
HOLDBOARD_F = int(_os.environ.get("DRHOLDBOARD_F", "600"))   # CvC safety cap: ~10s at 60fps
# DRHOLDONCE (default OFF -> every existing cart rebuilds byte-identical): arm the final-board
# hold ONCE per match-end instead of once per hook while (virus==0 && VSEEN) stays true. See the
# fc_clear arm site for the measured thrash this removes. $61B8 is the first byte past the
# DRDISTGATE scratch ($61B1-$61B7) and below the DRTRACE/DRPROBE ring at $6200.
# ⚠ "No absolute store lands there" is NOT sufficient -- a byte-level reach census found ONE
# indexed writer that could in principle cover it: DRPRESTART's `STA PRE_LND,X` (base $61A1, so
# X>=0x17 would hit $61B8). VERIFIED BOUNDED rather than assumed: X is loaded from PRE_N, PRE_N is
# zeroed before the settle scan and INC'd at most once per column, and the scan terminates on
# `PRE_COL == 8` -- so X is 0..7 at the store and it reaches at most $61A8, 15 bytes clear of the
# latch. Filler is not proof of free, and neither is the absence of an ABSOLUTE store.
HOLDONCE = _os.environ.get("DRHOLDONCE", "0") == "1"
HOLD_ONCE = 0x61B8                         # !=0: this match-end's hold has already been armed
HOLD_ACTIVE = 0x6195                       # PRG-RAM: !=0 while the final board is held
HOLD_LASTCLK = 0x6196                      # last-seen $43 clock byte (edge-detect real frames)
HOLD_CNT = 0x6197                          # 16-bit ($6197 lo, $6198 hi): frames held so far
HOLD_BUF1, HOLD_BUF2 = 0x6300, 0x6400      # 256B mirrors of $0400 (P1) / $0500 (P2) playfields

# ---- DRPRESTART=1 (default OFF -> byte-identical when unset): GARBAGE-WINDOW PRESTART ----
# Today the ONLY search trigger is the new-pill Y edge ($0306/$0386 rising) + a 15-hook settle,
# so the entire VS garbage window -- W = 264 - 16*h frames, h = stack height of the shallowest
# garbage-hit column (ROM-derived, emulator-verified 8/8: empty 264 f, stack 6 168 f, stack 13
# 56 f, stack 15 24 f) -- is DEAD TIME, and the answer lands ~150 frames after spawn while the
# capsule is already falling at 13 f/row. DRPRESTART reclaims that window: it detects the
# garbage release, PROJECTS the settled post-garbage board in 6502, uploads the projection and
# GOes immediately, so the search overlaps the fall animation instead of following it.
#
# ★ THE TRIGGER, and why this edge and not another (read from the Rev0 disassembly, not assumed;
#   `checkReleaseAttack` $9C01 -- the Nostaljipi listing is Rev A and sits $1A higher at $9C1B):
#   attacks are buffered in the ATTACKER's OWN slot and consumed by the VICTIM.
#   `checkReleaseAttack` runs with currentP = the RECEIVER and indexes `p1_attackSize,X` with
#   X = otherPlayerRAM_addrOffset[currentP] = {p1($04): $80, p2($05): $00}.
#   => P2's INCOMING volley is buffered at $0318 (p1_attackSize) / $0329 (p1_attackColors);
#      P1's incoming volley is at $0398 / $03A9. That is the reverse of the naive reading and
#      is the single easiest thing to get backwards here.
#   The routine writes every garbage cell into row 0 of the receiver's field via
#   `sta (currentP_fieldPointer),Y` (pointer lo = $00, hi = currentP = $04/$05 => $0400/$0500 + Y)
#   and only THEN does `sta p1_attackSize,X` with A=0. The clear is the LAST write, so
#   "incoming attackSize went nonzero -> 0" observed from the NMI hook is a RELEASE-COMPLETE
#   edge by construction: every garbage byte is already in RAM when we see it. An NMI landing
#   mid-routine sees the size still nonzero and simply waits for the next hook. No torn read is
#   possible. (The alternative edges -- nextAction==pillPlaced, or diffing row 0 -- are both
#   ambiguous with the ordinary pill-lock path; this one has exactly one writer.)
#
# ★ THE PROJECTION. RAM does NOT hold the settled board during the animation: post-garbage
#   gravity is 16 FRAMES PER ROW (`checkDrop` $8C94 is gated on status==$FF, the nametable
#   row-render cursor, so a full 16-row re-render must complete between sweeps), so a driver
#   that uploads $0500 at the release frame uploads garbage FLOATING AT ROW 0 -- measured
#   elsewhere in this project as ~1/3 of deliveries instantly topping out the receiver. The
#   6502 must settle it itself. The settle is exact and cheap because of one invariant:
#   ** the pre-garbage board is already settled, so the ONLY unsupported cells are the garbage
#      singles, and they are all in row 0. ** So: for each column 0..7, if row 0 holds a
#   `singleHalfPill` ($80 | colour -- the exact tile checkReleaseAttack writes), slide it down
#   to rest on the first occupied cell. Nothing else can move.
#   Consequences worth stating, because they remove bail cases the naive design needs:
#     - We never have to work out WHICH row-0 cells are the garbage. A pre-existing settled
#       single at row 0 has support at row 1, so its slide distance is 0 = a no-op.
#     - Linked halves / viruses at row 0 are skipped by the $80 type test, and they are settled,
#       so skipping them is correct rather than merely safe.
#     - The garbage columns are {c,c+4} (size 2), {c,c+2,c+4} (size 3), {c,c+2,c+4,c+6} (size 4)
#       -- NEVER horizontally adjacent -- so the landed cells cannot interact with each other.
#   We deliberately do NOT reproduce the game's frameCounter column derivation (c =
#   frameCounter & 3 or & 1): reading row 0 gives us the columns AND the colours directly, and
#   it cannot drift from the frameCounter value that was live at the release instant.
#
# ★ THE PILL COLOURS ARE ONE STEP AHEAD OF THE NORMAL PATH -- the part that is easy to miss.
#   At prestart time `generateNextPill` has NOT yet run for the capsule we are searching for, so
#   the normal mailbox sources are stale by one: $0381/$0382 still hold the capsule that just
#   LOCKED. The capsule that will actually spawn is the current PREVIEW ($039A/$039B), and the
#   one after it is `pillsReserve[$03A7]` -- the whole 128-capsule stream is plain RAM at $0780,
#   and the counter has not been incremented yet. `colorCombination_left/right` are
#   [0,0,0,1,1,1,2,2,2] / [0,1,2,0,1,2,0,1,2], i.e. exactly (val/3, val%3), so the driver
#   computes them with a 3-iteration subtract loop instead of reaching into a ROM data table
#   from a bank it does not map. Feeding the stale pair here would be strictly WORSE than the
#   idle baseline (misinformed lookahead measured at +6.2 pills vs +0.17 for perfect knowledge).
#
# ★ BAILS (each falls back to today's exact behaviour -- we simply never GO, and since a real
#   `_start` rewrites all 128 window bytes there is no residue to undo):
#     - a settled garbage cell completes a 4-in-a-row (cascades are NOT resolved in 6502);
#     - a $B0 (clearing) or $F0 (just-emptied) tile is seen in a scanned column = the field is
#       mid-animation and the "already settled" invariant does not hold;
#     - a search is already in flight (ARMED != 0) or queued (PEND != 0) -- re-GOing a running
#       copro is the GO-storm re-entrancy family and is not worth the window;
#     - a SECOND volley arrives before the spawn (P1 can attack again while the first volley is
#       still animating): the projection is now stale, so we INVALIDATE -- tear down the
#       in-flight prestart (armed/wdog cleared, so its DONE is never read) and let the spawn
#       edge run a normal search on the live board.
# ★ SCOPE: P2 ONLY, deliberately. P2 is the copro AI on every shipping cart class (CvC leaves
#   P1 to the wiggle/native/idle paths, DRHUMAN gives P1 to a human, DRPOCKET has ONE window and
#   assigns it to P2), and on the deployed core $5000 is undecoded so handle(1) has only ever
#   published open-bus. Mirroring this for P1 is a parameterisation exercise, not a design one,
#   but it would double the emitted routine for a side no cart searches with.
PRESTART = _os.environ.get("DRPRESTART", "0") == "1"
PRE_ATK2 = 0x0318                       # P2's INCOMING volley = p1_attackSize (see the derivation above)
# PRG-RAM: $6199-$61AF is free (past DRHOLDBOARD's HOLD_CNT hi at $6198, below the
# DRTRACE/DRPROBE ring at $6200); PRE_BUF sits at $6500, clear of HOLD_BUF1/2 ($6300/$6400).
PRE_LAST2 = 0x6199                      # last-seen $0318, latched every play hook (release edge detect)
PRE_ACT2 = 0x619A                       # !=0: a prestarted search owns the NEXT P2 spawn
PRE_PREV, PRE_CUR = 0x619B, 0x619C      # trigger scratch: previous / current incoming attack size
PRE_COL, PRE_CELL, PRE_OFF, PRE_N = 0x619D, 0x619E, 0x619F, 0x61A0   # settle scratch
PRE_LND = 0x61A1                        # $61A1-$61A8: board offsets of the settled cells
PRE_I, PRE_RUN, PRE_MC, PRE_SOFF = 0x61A9, 0x61AA, 0x61AB, 0x61AC    # match-scan scratch
PRE_TMP, PRE_MIN, PRE_MAX = 0x61AD, 0x61AE, 0x61AF
PRE_BUF = 0x6500                        # 128B projected board ($6500-$657F)
# DRPRESPIPE=1 (default OFF -> byte-identical; requires DRPRESTART): #126 enforcement (b) for
# the prestart release edge. The synchronous pre_tick does copy + orphan guard + settle + match
# scan + upload + GO in ONE hook -- sound bound 22,724 for the routine, 27,960 for the hook,
# 35,687 for the release frame > the 29,780-cycle frame (NMI126_BOUND_REPORT.md verdict 4; the
# mixed8 state proves PRE_N=8 is ROM-reachable, so the analyzer cannot tighten below the frame).
# Pipelined: the release-edge hook keeps the DETECT + SNAPSHOT COPY (the copy must not slip a
# hook -- garbage falls a row per 16 frames and the settle scan keys on row 0), then a PRG-RAM
# phase byte advances one phase per hook: ph1 orphan+settle, ph2 match records 0-3, ph3 match
# records 4-7 + upload + GO. GO lands exactly 3 hooks (1.5 frames) after the edge, of a 24-264
# frame lead. Hooks run 2/frame, so two ADJACENT phases share a frame -- the match scan (11,715
# sound) is split across ph2/ph3 precisely so every adjacent-phase pair certifies under 29,780
# (tests/test_prespipe.py G4 asserts all pairs). Mid-pipeline the world can move; every phase
# entry re-checks and ABANDONS WHOLE (spec: the PRE_ACT2-teardown semantics) on any of:
#   * PRE_CUR != 0 -- a second volley was buffered; also swallow its future release edge
#     (PP_SWAL), because the synchronous path would have torn down AT that edge and started
#     nothing (its PRE_ACT2 would still be set from the commit the pipeline hasn't reached);
#   * PEND2/ARMED2 != 0 -- the P2 lock edge fired (spawn is coming) or a search started; the
#     pill falls back to the ordinary spawn-edge path. Behaviour delta vs ship: a lock edge
#     inside the 3-hook window aborts a prestart the synchronous path would have delivered.
# Commit-time reads of the preview colours ($039A/$039B/$03A7) are safe under these aborts:
# generateNextPill runs at spawn, and any spawn is preceded by the lock edge setting PEND2,
# which aborts the pipeline before a stale read.
PRESPIPE = _os.environ.get("DRPRESPIPE", "0") == "1"
assert not (PRESPIPE and not PRESTART), (
    "DRPRESPIPE=1 without DRPRESTART=1 is refused: there is no prestart release path to pipeline.")
# Allocated from the PRG_RAM_MAP free run at $61C2+ -- deliberately CLEAR of the $61BB
# claimants (SL_PH..SL_OFB/DRP1SLICE at $61BB-$61C1; FC_STAB/DRSTARTGUARD ALSO claimed $61BB
# until 2026-08-20, when it was relocated to $61C4 -- collision fixed, deriver now checks). All other cross-hook
# state (PRE_I/PRE_COL/PRE_N/PRE_LND/PRE_BUF) is already PRG-RAM and persists for free.
# PRESPIPE_Q = match records per match phase (see the driver comment). DEFAULT 3 (team-lead
# ruling 2026-08-20): 4 hooks = 2.0 frames, sound margin 4,926. Q=4 gives the spec's original
# 3-hook / 1.5-frame shape but its 1,154-cycle margin rests on a MEASURED-not-bounded game
# head (2,040) plus an estimated eps (300) -- the certificate shape this week taught us to
# distrust -- while 0.5 frame of a >=24-frame lead is noise. Any Q in 1..8 is legal and the
# census + gate certify whatever is set: the knob does not get to bypass the certificate,
# it only chooses which certificate you are asking for.
PRESPIPE_Q = int(_os.environ.get("DRPRESPIPE_Q", "3"))
assert 1 <= PRESPIPE_Q <= 8, "DRPRESPIPE_Q must be 1..8 (there are at most 8 settle records)"
PP_NM = -(-8 // PRESPIPE_Q)             # match phases needed to cover 8 records (ceil)
PP_PH = 0x61C2                          # pipeline phase: 0 idle, 1 orphan+settle, 2 match 0-3, 3 match 4-7+commit
PP_SWAL = 0x61C3                        # !=0: swallow the NEXT release edge (post-abort teardown parity)

# DRBUILDID=1 (task: "which brain am I fighting", default ON for human-profile carts): stamp a
# short build tag onto the settings screen ("2 PLAYER GAME" row 25, columns 6-14) -- the exact
# row the STUDYCOUNTS OAM-leak garbled (task #48 job 1). Deliberate choice: not sprites (would
# need re-deriving a whole alphabet in whatever CHR bank happens to be live at each candidate
# screen, and would sit in OAM real estate already owned by STUDYCOUNTS/STUDY2P) and not the
# DRNAVDWELL title dwell (transient, and a HUMAN_P1 cart's own settings screen is shown before
# EVERY match -- always-checkable in the sense the spec asks for, the title dwell is not).
# Mechanism verified against the base ROM disassembly + a live Mesen probe, not assumed:
#   - row 25 is confirmed BLANK ($FF, cols 4-27) on the vanilla settings screen (own nametable
#     dump, tools/romgen.py-built cart's print table is untouched there -- see task #48's garble
#     report) -- safe to write without colliding with any existing content.
#   - the settings-screen background font is NOT the STUDY sprite font (S/T/U/D/Y = $0D/$A0/$0C/
#     $A1/$A2, a DIFFERENT CHR bank than the settings screen's bank 5) -- it is instead A=$0A,
#     B=$0B, ..., Z=$23 (letter tile = $0A + offset-from-A) and digit tile = digit VALUE
#     directly (0-9). Derived by decoding 9 independently-placed, already-rendered strings off
#     a real nametable dump (VIRUS LEVEL / MUSIC TYPE / FEVER / CHILL / OFF / SPEED / "2 PLAYER
#     GAME") and cross-checking: EVERY letter's derived tile equals $0A+offset with zero
#     mismatches across 18 distinct letters -- not a guess.
#   - entering PLAY mode (a full-screen redraw via a DIFFERENT print table, LC5F9) completely
#     overwrites row 25 with the bottle-border graphic before any gameplay is visible (own Mesen
#     probe, byte-for-byte) -- confirmed BEFORE relying on it, not assumed by analogy to the
#     garble fix. The write is ALSO hard-gated on $0046==1 (settings only) so it structurally
#     cannot fire during play -- belt and suspenders, same class of bug as the one just fixed,
#     not repeated.
# SOURCE OF TRUTH (never hand-maintained): the tag is <=4 safe-alphabet chars from DRBUILDID_TAG
# (tools/romgen.py's `build --tag` sets this automatically from the SAME tag it records in the
# manifest -- one input, not two that could drift) + a live-computed 4-hex-nibble prefix of this
# EXACT build's own image hash. Chicken-and-egg (the hash covers a file that contains the hash):
# resolved by writing $FF PLACEHOLDER tiles at the 4 hash-nibble sites during assembly, hashing
# the COMPLETE built file with those placeholders still in place (this "hash of image with stamp
# masked to a fixed sentinel" IS the standard trick -- placeholder-before-hash is equivalent to
# masking, just computed in the natural build order instead of a separate mask-then-hash pass),
# then patching only those 4 already-known byte offsets in the already-written file afterward.
# The patched bytes are pure display data (no code depends on their value), so the patch cannot
# perturb anything the hash is meant to fingerprint -- the same reasoning that already lets the
# mapper-byte patch at the end of main() happen post-hoc.
BUILDID = _os.environ.get("DRBUILDID", "1" if HUMAN_P1 else "0") != "0"
_BID_SAFE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_BID_TAG_RAW = "".join(c for c in _os.environ.get("DRBUILDID_TAG", "").upper() if c in _BID_SAFE_CHARS)
BUILDID_TAG = (_BID_TAG_RAW + "XXXX")[:4]           # pad/truncate to exactly 4 safe-alphabet chars
BID_PPU_ADDR = 0x2000 + 25 * 32 + 6                 # nametable 0, row 25, col 6 ($2326)


def _bid_tile(ch):
    """Settings-screen background font tile for one safe-alphabet character (see the DRBUILDID
    flag comment for the derivation). ch must be in _BID_SAFE_CHARS."""
    assert ch in _BID_SAFE_CHARS, f"DRBUILDID: {ch!r} is not in the verified safe alphabet"
    return (ord(ch) - ord("0")) if ch.isdigit() else (0x0A + ord(ch) - ord("A"))

# DRSTUDY=1 -> "study pause": freeze game logic on pause but keep the last gameplay frame
# rendered instead of the vanilla blank+"PAUSE". Default ON for human carts (DRHUMAN=1) so a
# paused board can be studied. Mechanism (base pause routine at CPU $978E; verified on base
# drmario.nes in Mesen — see tmp/study_pause/): the routine blanks the background ($2001 bit3),
# fills OAM with $FF, draws "PAUSE", then spins on $B654 whose tail re-clears OAM every frame.
# We keep background rendering ON, and swap the two pause frame-waits $B654 -> $B670 (identical
# wait WITHOUT the OAM-clear tail) so the sprites in the buffer at pause entry stay put; the
# entry OAM-clear is NOP'd. The falling capsule + bottle + viruses are in the buffer at pause
# entry, so they persist. The pause loop's draw call ($97D3) is repointed to STUDY_BLOB at $D2CC
# (a 5-part trampoline routine in dead padding free in base AND v28cs) which (1) reconnects the
# "STUDY" text by setting $42=$80 then JSR $88F6 so the 5 letters land in OAM slots 32-36 (ABOVE
# every capsule/preview, so BOTH players' capsules in 2P/VS stay put), and (2) HAND-DRAWS the
# next-pill preview(s) — P1 (slots 37-38, colors $031A/$031B) always, and P2 (slots 39-40, colors
# $039A/$039B) in 2P/VS — each at its mode-correct position ($0727). See STUDY_BLOB below.
#   NOTE (validation basis): base-ROM change is Mesen-proven (paused frame shows bottle+viruses+
#   capsule+preview, frozen, clean resume). The copro carts are mapper 100 (not Mesen-emulable);
#   DRSTUDY applies the SAME asserted byte patches + blob to the v28cs image (which already
#   carries 2 of the 5 edits from a prior partial attempt — the patch is idempotent). Dr.Mario /
#   magnifier sprites are still not restored (decor built by the skipped main-loop phase). The
#   carts run in VS-CPU mode; pause-reachability and 2P preview correctness are NOT emulator-
#   verified. $D2CC-$D2FF must be confirmed dead in any deployed binary before surgical patching.
STUDY = _os.environ.get("DRSTUDY", "1" if HUMAN_P1 else "0") != "0"
STUDY2P = STUDY and _STUDY2P_ENV                     # driver-side 2P pause tail (see DRSTUDY2P above)
# Anchor on the pause loop's START/$F7 check (LDA $F5;CMP #$10;BEQ;LDA $F7;CMP #$F0;BEQ) —
# these bytes are NEVER touched by the edits, so the locator stays valid + idempotent even
# after patching (all 5 edits sit just before/after this window, never inside it).
STUDY_ANCHOR = bytes.fromhex("a5f5c910f00ca5f7c9f0f0b7")
STUDY_EDITS = [   # (rel-to-anchor, [accepted originals], replacement, note)
    (-0x20, [bytes.fromhex("2054b6")], bytes.fromhex("2070b6"), "entry wait $B654->$B670 (no OAM clear)"),
    (-0x1D, [bytes.fromhex("a916"), bytes.fromhex("a91e")], bytes.fromhex("a91e"), "keep background rendering ON"),
    (-0x12, [bytes.fromhex("2094b8"), bytes.fromhex("eaeaea")], bytes.fromhex("eaeaea"), "drop entry OAM clear"),
    (-0x03, [bytes.fromhex("20f688"), bytes.fromhex("eaeaea")], bytes.fromhex("20ccd2"), "draw STUDY letters + preview (JSR $D2CC)"),
    (0x0C, [bytes.fromhex("2054b6")], bytes.fromhex("2070b6"), "loop wait $B654->$B670 (no OAM clear)"),
]
# STUDY-draw routine (v3.2) — reconnects "STUDY" text AND hand-draws BOTH players' next-pill previews
# during pause, WITHOUT disturbing any frozen capsule, in 1P / 2-player / VS layouts. STUDY -> OAM
# slots 32-36, P1 preview -> 37-38, P2 preview (2P/VS only) -> 39-40 — all ABOVE the slot-15 gameplay
# buffer max, so BOTH players' capsules (slots 0-3 in 2P/VS) are byte-untouched. Both players consume
# the shared pill sequence at different rates, so P2's next pill ($039A/$039B) differs from P1's
# ($031A/$031B) and must show separately (the game itself draws both, $87DA/$87FE).
# A mode-correct 2-preview draw + a 2P/VS STUDY lift don't fit one dead run, so it is a 5-part trampoline through dead
# padding free in base AND v28cs (part1 in the fixed bank; parts 2-4 in bank0, where the pause routine
# already runs so they are always mapped):
#   part1 @ $D2CC: $42=$80; JSR $88F6 (STUDY -> 32-36); write P1 tiles+attr (37-38) and the 1P-default
#     P1 position (Y=$45 X=$BE/$C6, the right box); JMP part2.
#   part2 @ $9FF8: LDY $0727; DEY; BEQ RTS  (1P -> keep part1's defaults, no P2). Else (2P/VS) set
#     Y=$33 for all four preview slots (37-40) and P1 X=$38/$40 (above P1's board); JMP part3a.
#   part3a @ $A371: P2 preview tiles ($60|$039A / $70|$039B) + attr into slots 39-40; JMP part3b.
#   part3b @ $BE56: P2 preview X=$B8/$C0 (above P2's board, mirroring the game's $87FE draw); RTS.
# Tiles = $60|colorA / $70|colorB (game's own preview $8772 uses template+color via ADC, never masks
# -> raw colors are 0-2 and $60|c == $60+c). STUDY_BLOB (part1) fills the whole 52-byte $D2CC run so
# it covers any prior v2/v3/v3.1 blob when upgrading an already-patched image in place.
#   NOTE (validation basis): base-ROM change is Mesen-proven in 1P, 2P and VS-CPU (paused frame keeps
#   both capsules + STUDY + BOTH mode-correct previews showing each player's actual next pill, frozen,
#   clean resume). The copro carts are mapper 100 (not Mesen-emulable); DRSTUDY applies the SAME
#   asserted byte patches + blobs, and the 2P base test reproduces the cart's both-capsules-in-buffer
#   layout. All five dead runs must be confirmed dead in any deployed binary before surgical patching.
STUDY_BLOB_CPU  = 0xD2CC   # part1  (fixed bank; duplicated by expand at file 0x52DC / 0xD2DC)
STUDY_BLOB2_CPU = 0x9FF8   # part2  (bank0; single copy, file 0x2008)
STUDY_BLOB3_CPU = 0xA371   # part3a (bank0; single copy, file 0x2381)
STUDY_BLOB4_CPU = 0xBE56   # part3b (bank0; single copy, file 0x3E66)
STUDY_BLOB5_CPU = 0xBC26   # part3c (bank0; single copy, file 0x3C36) — 2P/VS STUDY lift
# In 2P/VS the "1P/2P/LEVEL" header box's topmost pixel row is screen row 18 (measured in Mesen).
# STUDY at the base Y=$0F (sprite rows 16-23) overlaps it, so in 2P/VS ONLY we lift the 5 STUDY
# letters' OAM Y to $08 (sprite rows 9-16) — clears the header (1-px gap above row 18) and stays
# below scanline 8 (survives an NTSC top-8-line CRT trim). 1P keeps $0F (its top is clear).
STUDY_2P_Y = 0x08
STUDY_BLOB = bytes.fromhex(                          # part1 — exactly 52 B (fills the $D2CC run)
    "A980" "8542" "20F688"            # LDA #$80; STA $42; JSR $88F6   (STUDY -> slots 32-36)
    "AD1A03" "0960" "8D9502"          # LDA $031A; ORA #$60; STA $0295 (P1 slot37 tile = left half)
    "AD1B03" "0970" "8D9902"          # LDA $031B; ORA #$70; STA $0299 (P1 slot38 tile = right half)
    "A902" "8D9602" "8D9A02"          # LDA #$02; STA $0296; STA $029A (P1 attr, both halves)
    "A945" "8D9402" "8D9802"          # LDA #$45; STA $0294; STA $0298 (P1 Y = 69, 1P default)
    "A9BE" "8D9702"                   # LDA #$BE; STA $0297            (P1 slot37 X = 190, 1P)
    "A9C6" "8D9B02"                   # LDA #$C6; STA $029B            (P1 slot38 X = 198, 1P)
    "4CF89F")                         # JMP $9FF8  -> part2
STUDY_BLOB2 = bytes.fromhex(                         # part2 @ $9FF8 (34 B)
    "AC2707" "88" "F01B"              # LDY $0727; DEY; BEQ +27 (1P -> RTS, keep part1 defaults)
    "A933" "8D9402" "8D9802" "8D9C02" "8DA002"   # LDA #$33; STA Y of slots 37,38,39,40 (all = 51)
    "A938" "8D9702"                   # LDA #$38; STA $0297 (P1 slot37 X = 56, 2P/VS)
    "A940" "8D9B02"                   # LDA #$40; STA $029B (P1 slot38 X = 64, 2P/VS)
    "4C71A3"                          # JMP $A371 -> part3a
    "60")                             # RTS (1P lands here)
STUDY_BLOB3 = bytes.fromhex(                         # part3a @ $A371 (27 B) — P2 tiles + attr
    "AD9A03" "0960" "8D9D02"          # LDA $039A; ORA #$60; STA $029D (P2 slot39 tile = left half)
    "AD9B03" "0970" "8DA102"          # LDA $039B; ORA #$70; STA $02A1 (P2 slot40 tile = right half)
    "A902" "8D9E02" "8DA202"          # LDA #$02; STA $029E; STA $02A2 (P2 attr, both halves)
    "4C56BE")                         # JMP $BE56 -> part3b
STUDY_BLOB4 = bytes.fromhex(                         # part3b @ $BE56 (13 B) — P2 X, then part3c
    "A9B8" "8D9F02"                   # LDA #$B8; STA $029F (P2 slot39 X = 184, above P2 board)
    "A9C0" "8DA302"                   # LDA #$C0; STA $02A3 (P2 slot40 X = 192)
    "4C26BC")                         # JMP $BC26 -> part3c (2P/VS STUDY lift)
STUDY_BLOB5 = bytes.fromhex(                         # part3c @ $BC26 (18 B) — lift STUDY in 2P/VS
    "A9%02X" % STUDY_2P_Y +           # LDA #$08  (2P/VS STUDY Y; clears the header box)
    "8D8002" "8D8402" "8D8802" "8D8C02" "8D9002"  # STA Y of STUDY slots 32,33,34,35,36
    "60")                             # RTS  (only reached in 2P/VS; 1P returns at part2)
# Prior blobs accepted as overwritable so an already-patched image upgrades in place.
OLD_STUDY_BLOB_V2 = bytes.fromhex(   # v2: preview only, slots 2-3, no STUDY text (47 B)
    "AD1A03" "2903" "0960" "8D0902" "AD1B03" "2903" "0970" "8D0D02"
    "A945" "8D0802" "8D0C02" "A902" "8D0A02" "8D0E02" "A9BE" "8D0B02" "A9C6" "8D0F02" "60")
OLD_STUDY_BLOB_V3 = bytes.fromhex(   # v3.0: STUDY slots 2-6 + preview slots 7-8, fixed 1P pos (50 B)
    "A908" "8542" "20F688" "AD1A03" "0960" "8D1D02" "AD1B03" "0970" "8D2102"
    "A945" "8D1C02" "8D2002" "A902" "8D1E02" "8D2202" "A9BE" "8D1F02" "A9C6" "8D2302" "60")
OLD_STUDY_BLOB_V31 = bytes.fromhex(  # v3.1 part1 @ $D2CC (34 B code, was $00-padded to 50)
    "A980" "8542" "20F688" "AD1A03" "0960" "8D9502" "AD1B03" "0970" "8D9902"
    "A902" "8D9602" "8D9A02" "4CF89F")
OLD_STUDY_BLOB2_V31 = bytes.fromhex( # v3.1 part2 @ $9FF8 (31 B)
    "A945" "A2BE" "AC2707" "88" "F004" "A933" "A238"
    "8D9402" "8D9802" "8E9702" "8A" "18" "6908" "8D9B02" "60")
OLD_STUDY_BLOB4_V32 = bytes.fromhex( # v3.2 part3b @ $BE56 (11 B, ended RTS instead of JMP part3c)
    "A9B8" "8D9F02" "A9C0" "8DA302" "60")

# v8.2 EVAC: the 2P-study tail ($9FF8/$A371/$BE56/$BC26) sits on LIVE RB6C2_PRINT printing tables +
# an LDA $9FF8,X data table -> read-as-data every draw -> part3c $BC26 mis-parse -> $0301 KIL; part3b
# $BE56 -> level-select junk.  v8.2 keeps part1 (STUDY + P1 preview) ending RTS, drops blobs 2-5, and
# the caller restores the 4 sites to base.  See FREE_SPACE_MAP.md / dr-mario-te-freeze-rootcause.
OLD_STUDY_BLOB_EVAC_V82 = STUDY_BLOB[:-3] + bytes.fromhex("60FFFF")   # v8.2 evac: part1 incl. P1 preview
# EVAC v2 (task #39, probe round 2): the pause loop calls the repointed draw ($97D3 -> $D2CC)
# EVERY spin iteration -- not once at entry (both $B654 waits are patched precisely because the
# loop re-runs the draw). So an evac part1 that writes the P1 preview re-stomps its 1P-default
# position over the DRSTUDY2P driver fix every paused frame (Mesen-proven: slots 39/40 fixed,
# 37/38 stomped back each frame). The driver now owns slots 37-40 in 2P, and in 1P the game's
# own paused buffer already shows the preview, so part1 shrinks to just the STUDY letters:
#   LDA #$80; STA $42; JSR $88F6; RTS   (8 B; padded to fill the audited 52 B run)
OLD_STUDY_BLOB_EVAC_V2 = bytes.fromhex("A9808542" "20F688" "60") + b"\xFF" * 44   # v2: letters-only
# EVAC v3 (task #39, probe round 3): even letters-only part1 stomps the driver's STUDY Y-lift
# every pause frame -- $88F6 writes ALL FOUR OAM bytes per letter from its own template, Y
# included. Same clobber pattern, last remaining field. So part1 retires completely (bare RTS;
# the repointed draw call needs a safe target, nothing more) and the DRIVER draws the letters
# too: tiles/X are static (probe-dumped), Y is mode-correct ($0F in 1P per the original
# design, $08 in 2P clear of the header). One writer, zero races, slots 32-40 driver-owned.
OLD_STUDY_BLOB_EVAC_V3 = b"\x60" + b"\xFF" * 51   # EVAC v3: bare RTS (the leak-era part1)
# EVAC v4 (STUDY2P leak fix, 2026-08-08 field defect "flickers + STUDY on top in play"): the
# s2p driver block drew STUDY + previews at visible Y on EVERY play hook, betting the game's
# OAM rebuild would overwrite them -- but in VS play the game owns ZERO sprites and R8712 only
# pads from the sprite high-water mark, so nothing ever cleaned slots 32-40 and the letters
# rendered over live play continuously (Mesen: ~35k/35k play frames on the byte-exact field
# cart 3e7c6ed9). Fix = give the s2p block a real pause detector. MEASURED call pattern of
# this blob on that cart (two independent instrumented runs, exec counter at $D2CC):
#   - exactly 1 call per UNPAUSED play frame (35,080/35,082; the misses are single-frame,
#     at the mode-8 -> 4 transition), from the repointed draw site on the frame path;
#   - ZERO calls while the real pause loop spins ($978E ticking 1/frame);
#   - ZERO calls in menus / title / intro.
# (The older "the pause loop re-runs the draw every spin frame" note above described the
# probe-era standalone behaviour; on this copro cart the pause spin provably never reaches it.)
# So part1 is a PLAY-FRAME HEARTBEAT: it tops up S2P_TTL every live frame, and the s2p hook
# (2x/frame in NMI, which keeps running during the pause spin) decrements it. TTL drains to 0
# only when the frame path stops calling us -- i.e. a mode-4 blocking wait: the pause loop
# (draw STUDY: that IS the feature) or STAGE CLEAR's own wait (excluded via HOLD_ACTIVE).
S2P_TTL = 0x61B0      # PRG-RAM heartbeat TTL ($6199-$61AF = DRPRESTART; $6200 = trace ring)
S2P_TTL_N = 4         # top-up: 2 hook-decs/frame vs max measured heartbeat gap = 1 frame
STUDY_BLOB_EVAC = (bytes([0xA9, S2P_TTL_N,                      # LDA #S2P_TTL_N
                          0x8D, S2P_TTL & 0xFF, S2P_TTL >> 8,   # STA S2P_TTL
                          0x60])                                # RTS
                   + b"\xFF" * 46)                              # pad the audited 52 B run


class StudyPatchError(Exception):
    pass


def apply_study_pause(rom, evac=False):
    """Apply the DRSTUDY 'study pause' byte patches to a Dr. Mario PRG image in place.
    Idempotent + asserted: locate the pause routine by a stable anchor, verify each target holds
    an accepted original (base) OR the already-patched value (v28cs / re-run), place the preview
    blob in dead padding (asserting it is filler or already the blob), and fail loudly on
    anything else. Returns the count of edits actually written (edits + blob)."""
    if rom[4] != 2:
        raise StudyPatchError(f"DRSTUDY: expected a 32KB-PRG image (2 banks), got {rom[4]}")
    a = rom.find(STUDY_ANCHOR)
    if a < 0:
        raise StudyPatchError("DRSTUDY: pause-routine anchor not found (unexpected ROM)")
    if rom.find(STUDY_ANCHOR, a + 1) >= 0:
        raise StudyPatchError("DRSTUDY: pause-routine anchor is ambiguous (multiple matches)")
    for rel, accepted, after, note in STUDY_EDITS:          # verify all before writing any
        off = a + rel
        got = bytes(rom[off:off + len(after)])
        if got != after and got not in accepted:
            raise StudyPatchError(
                f"DRSTUDY: 0x{off:X} ({note}): got {got.hex()}, expected one of "
                + "/".join(b.hex() for b in accepted + [after]))
    # 5 blob targets, each in a confirmed dead run; every one must be free (or already ours, or a
    # prior blob we are upgrading in place). (cpu, blob, dead-run-size, [accepted prior prefixes])
    if evac:                                               # v8.2: part1 (RTS) only; no 2P tail
        targets = [
            (STUDY_BLOB_CPU, STUDY_BLOB_EVAC, 52,
             [OLD_STUDY_BLOB_V2, OLD_STUDY_BLOB_V3, OLD_STUDY_BLOB_V31, STUDY_BLOB,
              OLD_STUDY_BLOB_EVAC_V82, OLD_STUDY_BLOB_EVAC_V2, OLD_STUDY_BLOB_EVAC_V3]),
        ]
    else:
        targets = [
            (STUDY_BLOB_CPU,  STUDY_BLOB,  52, [OLD_STUDY_BLOB_V2, OLD_STUDY_BLOB_V3, OLD_STUDY_BLOB_V31]),
            (STUDY_BLOB2_CPU, STUDY_BLOB2, 38, [OLD_STUDY_BLOB2_V31]),
            (STUDY_BLOB3_CPU, STUDY_BLOB3, 28, []),
            (STUDY_BLOB4_CPU, STUDY_BLOB4, 24, [OLD_STUDY_BLOB4_V32]),
            (STUDY_BLOB5_CPU, STUDY_BLOB5, 22, []),
        ]
    def _overwritable(reg, blob, olds):
        if reg[:len(blob)] == blob or set(reg) <= {0x00, 0xFF}:              # already ours / pristine
            return True
        return any(reg[:len(o)] == o and set(reg[len(o):]) <= {0x00, 0xFF} for o in olds)  # prior blob
    for cpu, blob, dead, olds in targets:                  # verify all before writing any
        off = 16 + (cpu - 0x8000)
        reg = bytes(rom[off:off + dead])
        if not _overwritable(reg, blob, olds):
            raise StudyPatchError(f"DRSTUDY: blob target 0x{off:X} (${cpu:04X}) not free: {reg[:8].hex()}...")
    written = 0
    for rel, accepted, after, note in STUDY_EDITS:
        off = a + rel
        if bytes(rom[off:off + len(after)]) != after:
            rom[off:off + len(after)] = after
            written += 1
    for cpu, blob, dead, olds in targets:                  # each blob fills from the run start; a
        off = 16 + (cpu - 0x8000)                          # longer blob fully covers any shorter prior
        if bytes(rom[off:off + len(blob)]) != blob:
            rom[off:off + len(blob)] = blob
            written += 1
    return written


def build_main(level=11, speed=1):
    a = Asm6502(UNIT1_CPU)

    if TRACE:
        # ================= DIAGNOSTIC TRACER (no AI/nav) =================
        # Log ($0046,$0727,$04) ON CHANGE into a 64-entry x 3-byte ring at $5000 (copro window) mirrored
        # to $6200 (PRG-RAM). Header (both regions): +0xC0 write-index, +0xC1/C2 change-count lo/hi,
        # +0xC3..C5 the LIVE ($0046,$0727,$04) every hook, +0xC6 magic 0x54('T'). State in PRG-RAM $6186+.
        TR_IDX, TR_CNT, TR_L0, TR_L1, TR_L2, TR_MAG = 0x6186, 0x6187, 0x6189, 0x618A, 0x618B, 0x618C
        RING0, RING1 = 0x5000, 0x6200
        a.label("main")
        a.ins16("LDA_abs", TR_MAG); a.ins("CMP_imm", 0x5A); a.br("BEQ", "tr_go")   # lazy init (once ever)
        a.ins("LDA_imm", 0x5A); a.ins16("STA_abs", TR_MAG)
        a.ins("LDA_imm", 0); a.ins16("STA_abs", TR_IDX); a.ins16("STA_abs", TR_CNT); a.ins16("STA_abs", TR_CNT + 1)
        a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", TR_L0); a.ins16("STA_abs", TR_L1); a.ins16("STA_abs", TR_L2)
        a.label("tr_go")
        for r in (RING0, RING1):                                   # LIVE snapshot every hook + magic
            a.ins16("LDA_abs", 0x0046); a.ins16("STA_abs", r + 0xC3)
            a.ins16("LDA_abs", 0x0727); a.ins16("STA_abs", r + 0xC4)
            a.ins("LDA_zp", 0x04); a.ins16("STA_abs", r + 0xC5)
            a.ins("LDA_imm", 0x54); a.ins16("STA_abs", r + 0xC6)
        # --- ON-SCREEN render (the only read channel is a screenshot). main runs from the NMI ($800A)
        # with PPUSTATUS($2002) bit7 still SET; the ~4 main-loop calls/frame have it CLEAR, so gating on
        # bit7 renders ONLY in vblank -> PPU writes never hit active rendering, and the NMI resets scroll
        # right after us ($801F) so no scroll corruption. Font: hex nibble N == background tile $0N (bank 0,
        # confirmed). Row 2 (past overscan): MODE $0046 | $0727 | $04 | change-count | write-index, hex.
        a.ins16("LDA_abs", 0x2002); a.br("BPL", "tr_nppu")
        for lo, src in ((0x42, 0x0046), (0x45, 0x0727), (0x48, None), (0x4C, TR_CNT), (0x4F, TR_IDX)):
            a.ins("LDA_imm", 0x20); a.ins16("STA_abs", 0x2006)          # PPUADDR hi = $20
            a.ins("LDA_imm", lo); a.ins16("STA_abs", 0x2006)           # PPUADDR lo -> $2040(row2)+col
            if src is None:
                a.ins("LDA_zp", 0x04)                                   # $04 is zero-page
            else:
                a.ins16("LDA_abs", src)
            a.jsr("tr_hex")                                             # write the 2 hex tiles
        a.label("tr_nppu")
        a.ins16("LDA_abs", 0x0046); a.ins16("CMP_abs", TR_L0); a.br("BNE", "tr_log")   # change detect
        a.ins16("LDA_abs", 0x0727); a.ins16("CMP_abs", TR_L1); a.br("BNE", "tr_log")
        a.ins("LDA_zp", 0x04); a.ins16("CMP_abs", TR_L2); a.br("BNE", "tr_log")
        a.ins("RTS")
        a.label("tr_log")
        a.ins16("LDX_abs", TR_IDX)                                 # write entry at RING+IDX (both regions)
        for r in (RING0, RING1):
            a.ins16("LDA_abs", 0x0046); a.ins16("STA_absX", r + 0)
            a.ins16("LDA_abs", 0x0727); a.ins16("STA_absX", r + 1)
            a.ins("LDA_zp", 0x04); a.ins16("STA_absX", r + 2)
        a.ins16("LDA_abs", TR_IDX); a.ins("CLC"); a.ins("ADC_imm", 3)   # advance IDX by 3, wrap at 192
        a.ins("CMP_imm", 192); a.br("BCC", "tr_iok"); a.ins("LDA_imm", 0); a.label("tr_iok")
        a.ins16("STA_abs", TR_IDX); a.ins16("STA_abs", RING0 + 0xC0); a.ins16("STA_abs", RING1 + 0xC0)
        a.ins16("LDA_abs", 0x0046); a.ins16("STA_abs", TR_L0)     # remember last-logged
        a.ins16("LDA_abs", 0x0727); a.ins16("STA_abs", TR_L1)
        a.ins("LDA_zp", 0x04); a.ins16("STA_abs", TR_L2)
        a.ins16("INC_abs", TR_CNT); a.br("BNE", "tr_c"); a.ins16("INC_abs", TR_CNT + 1); a.label("tr_c")
        for r in (RING0, RING1):
            a.ins16("LDA_abs", TR_CNT); a.ins16("STA_abs", r + 0xC1)
            a.ins16("LDA_abs", TR_CNT + 1); a.ins16("STA_abs", r + 0xC2)
        a.ins("RTS")
        a.label("tr_hex")     # A = byte -> two background tiles via $2007 (nibble N -> hex-font tile $0N)
        a.ins("PHA"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins16("STA_abs", 0x2007)
        a.ins("PLA"); a.ins("AND_imm", 0x0F); a.ins16("STA_abs", 0x2007); a.ins("RTS")
        return a.assemble(), a.labels

    # ================= per-frame entry =================
    a.label("main")
    DIST_TABLE_ADDR = None
    if DISTGATE:
        # Emit DIST_TABLE as raw data immediately, jumped over -- never executed as code. Captured
        # here (not after the routine) so DIST_TABLE_ADDR is a concrete int by the time mv_p2 (far
        # below) needs it: a.label() records the byte offset the instant it's called, so this does
        # not depend on the assembler's two-pass fixup resolution the way a JMP/branch target does.
        a.jmp("dist_table_end")
        a.label("dist_table")
        DIST_TABLE_ADDR = UNIT1_CPU + a.labels["dist_table"]
        a.raw(*DIST_TABLE)
        a.label("dist_table_end")
    # PRG-RAM power-on init (SDRAM boots as garbage): magic byte at NAV_MAGIC
    a.ins16("LDA_abs", NAV_MAGIC); a.ins("CMP_imm", 0xA5)
    if PRESTART or STUDY2P:
        # DRPRESTART's two extra init stores push this skip past the +-127 relative-branch range
        # (measured: 128; STUDY2P's S2P_TTL store adds 3 more). Invert-and-JMP, the same idiom
        # the TUCK/nf2_untorn sites use -- gated so a build with both knobs off keeps the
        # original short branch and stays byte-identical.
        a.br("BNE", "do_init"); a.jmp("inited"); a.label("do_init")
    else:
        a.br("BEQ", "inited")
    a.ins("LDA_imm", 0xA5); a.ins16("STA_abs", NAV_MAGIC)
    a.ins("LDA_imm", 0); a.ins16("STA_abs", ARMED); a.ins16("STA_abs", NAV_T)
    a.ins16("STA_abs", STK1); a.ins16("STA_abs", STK2); a.ins16("STA_abs", MATCH_ACTIVE)
    a.ins16("STA_abs", WDOG); a.ins16("STA_abs", WRETRY)
    a.ins16("STA_abs", ARMED2); a.ins16("STA_abs", WDOG2); a.ins16("STA_abs", WRETRY2)
    a.ins16("STA_abs", WDOGH1); a.ins16("STA_abs", WDOGH2)
    a.ins16("STA_abs", SEED1); a.ins16("STA_abs", SEED2)
    a.ins16("STA_abs", VSEEN1); a.ins16("STA_abs", VSEEN2)
    if ROTFIX:
        a.ins16("STA_abs", ROT_DONE2)                       # A==0 here: orient-commit latch clear
    if SLAM:
        a.ins16("STA_abs", LAST_COL2); a.ins16("STA_abs", LAST_ORI2)   # A==0: argmax-stability state
        a.ins16("STA_abs", STABLE_CT2)
    if MATURE:
        a.ins16("STA_abs", SLAM_ARM); a.ins16("STA_abs", LAST_LAT)   # A==0: slam disarmed, no latency yet
    if NAVFIX:
        a.ins16("STA_abs", NAV_STABLE); a.ins16("STA_abs", NAV_1P)   # A==0: nav stability + 1P diag latch
    if NAVDWELL:
        a.ins16("STA_abs", DWELL_CNT); a.ins16("STA_abs", DWELL_LAST)   # A==0: title-dwell fresh at power-on
    if PRESTART:
        # A==0. PRE_ACT2 boot-garbage would be catastrophic in exactly the DRHUMAN-PEND1 way: a
        # nonzero value makes the FIRST spawn edge believe a prestart already owns the pill, so it
        # never sets PEND2 and the capsule falls with no search behind it.
        a.ins16("STA_abs", PRE_ACT2); a.ins16("STA_abs", PRE_LAST2)
        if PRESPIPE:
            # A==0. PP_PH boot-garbage would dispatch a phase against an un-copied PRE_BUF on
            # the first play hook; PP_SWAL garbage would eat the first real release edge.
            a.ins16("STA_abs", PP_PH); a.ins16("STA_abs", PP_SWAL)
    if STUDY2P:
        # A==0. Boot-garbage S2P_TTL is only a bounded nuisance (a nonzero value decays 2/frame
        # while blanking, the safe direction), but init it with the rest of the sticky-PRG-RAM
        # class so the first-ever pause is answerable immediately.
        a.ins16("STA_abs", S2P_TTL)
    if COLDINIT:
        a.ins16("STA_abs", LASTY1); a.ins16("STA_abs", LASTY2)   # A==0: no suppressed first edge from garbage
        a.ins16("STA_abs", PEND1); a.ins16("STA_abs", PEND2)
        a.ins16("STA_abs", DELAY1); a.ins16("STA_abs", DELAY2)
    if P1WIGGLE:
        # A==0. The FIRST pill's spawn edge toggles this before act_p1 ever reads it, so
        # pill 1 holds RIGHT and pill 2 LEFT. Which wall leads is arbitrary, but pin the
        # seed here: tests/test_p1_wiggle.py asserts the exact landing sequence.
        a.ins16("STA_abs", WIG_DIR)
    if P1NATIVE:
        # A==0: P1AI_Y=0 so the first pill (Y=15) trips the new-pill edge and gets a real
        # search; P1AI_O=0 = the horizontal spawn orient, so no rotation is demanded before
        # the first search has run.
        a.ins16("STA_abs", P1AI_Y); a.ins16("STA_abs", P1AI_O)
    a.ins("LDA_imm", 3)                                     # sane targets pre-first-publish
    if P1NATIVE:
        a.ins16("STA_abs", P1AI_C)                          # centre column until the first search
    a.ins16("STA_abs", TGT_C1); a.ins16("STA_abs", TGT_O1)
    a.ins16("STA_abs", TGT_C2); a.ins16("STA_abs", TGT_O2)
    a.ins("LDA_imm", 2); a.ins16("STA_abs", TURN)          # fair-serve round-robin seed
    a.label("inited")
    if PROBE and not TRACE:
        # ===== DRPROBE: continuous ($0046,$0727,$04) ring log (nav+AI stay live; no render) =====
        # Same on-disk layout as the DRTRACE ring so tests/decode_trace.py reads it unchanged: 64x3B
        # ring at $6200, header +0xC0 write-idx, +0xC1/C2 count, +0xC3..C5 live snapshot, +0xC6 magic.
        # Read via save-state ($6200 is captured). Logs on CHANGE -> captures menu transitions AND the
        # post-game EXIT/residual (the last entries before the next boot inherits them via sticky RAM).
        PR_IDX, PR_CNT, PR_L0, PR_L1, PR_L2, PR_MAG = 0x6186, 0x6187, 0x6189, 0x618A, 0x618B, 0x618C
        RINGP = 0x6200
        a.ins16("LDA_abs", PR_MAG); a.ins("CMP_imm", 0x5A); a.br("BEQ", "pr_go")   # lazy init (once ever)
        a.ins("LDA_imm", 0x5A); a.ins16("STA_abs", PR_MAG)
        a.ins("LDA_imm", 0); a.ins16("STA_abs", PR_IDX); a.ins16("STA_abs", PR_CNT); a.ins16("STA_abs", PR_CNT + 1)
        a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", PR_L0); a.ins16("STA_abs", PR_L1); a.ins16("STA_abs", PR_L2)
        a.label("pr_go")
        a.ins16("LDA_abs", 0x0046); a.ins16("STA_abs", RINGP + 0xC3)   # live snapshot + magic every hook
        a.ins16("LDA_abs", 0x0727); a.ins16("STA_abs", RINGP + 0xC4)
        a.ins("LDA_zp", 0x04); a.ins16("STA_abs", RINGP + 0xC5)
        a.ins("LDA_imm", 0x54); a.ins16("STA_abs", RINGP + 0xC6)
        a.ins16("LDA_abs", 0x0046); a.ins16("CMP_abs", PR_L0); a.br("BNE", "pr_log")   # change detect
        a.ins16("LDA_abs", 0x0727); a.ins16("CMP_abs", PR_L1); a.br("BNE", "pr_log")
        a.ins("LDA_zp", 0x04); a.ins16("CMP_abs", PR_L2); a.br("BEQ", "pr_done")
        a.label("pr_log")
        a.ins16("LDX_abs", PR_IDX)
        a.ins16("LDA_abs", 0x0046); a.ins16("STA_absX", RINGP + 0)
        a.ins16("LDA_abs", 0x0727); a.ins16("STA_absX", RINGP + 1)
        a.ins("LDA_zp", 0x04); a.ins16("STA_absX", RINGP + 2)
        a.ins16("LDA_abs", PR_IDX); a.ins("CLC"); a.ins("ADC_imm", 3)   # advance idx, wrap at 192
        a.ins("CMP_imm", 192); a.br("BCC", "pr_iok"); a.ins("LDA_imm", 0); a.label("pr_iok")
        a.ins16("STA_abs", PR_IDX); a.ins16("STA_abs", RINGP + 0xC0)
        a.ins16("LDA_abs", 0x0046); a.ins16("STA_abs", PR_L0)
        a.ins16("LDA_abs", 0x0727); a.ins16("STA_abs", PR_L1)
        a.ins("LDA_zp", 0x04); a.ins16("STA_abs", PR_L2)
        a.ins16("INC_abs", PR_CNT); a.br("BNE", "pr_c"); a.ins16("INC_abs", PR_CNT + 1); a.label("pr_c")
        a.ins16("LDA_abs", PR_CNT); a.ins16("STA_abs", RINGP + 0xC1)
        a.ins16("LDA_abs", PR_CNT + 1); a.ins16("STA_abs", RINGP + 0xC2)
        a.label("pr_done")
    a.ins16("INC_abs", NAV_T)                               # tick every hook call (autonav only ticked in menus)
    if HOLDBOARD:
        # RESTORE + RELEASE: runs FIRST, every hook, ahead of the mode split entirely -- HOLD_ACTIVE
        # can be true while $0046 reads 4 (STAGE CLEAR's own blocking wait) OR 5/6/7 (the topout ->
        # TOP_5 -> TOP_7 GAME OVER sequence), and this must win the race against BOTH of those
        # screens' own destructive writes on every single hook, not just the one that armed it.
        a.ins16("LDA_abs", HOLD_ACTIVE); a.br("BEQ", "hb_skip")
        a.ins("LDX_imm", 0)
        a.label("hb_restore_lp")
        a.ins16("LDA_absX", HOLD_BUF1); a.ins16("STA_absX", 0x0400)
        a.ins16("LDA_absX", HOLD_BUF2); a.ins16("STA_absX", 0x0500)
        a.ins("INX"); a.br("BNE", "hb_restore_lp")
        # re-trigger the game's OWN row-redraw drain (same mechanism RB337_STAGE_CLEAR and
        # R96D4_GAME_OVER themselves use) so the restored RAM actually reaches the PPU.
        a.ins("LDA_imm", 0x0F); a.ins16("STA_abs", 0x0300); a.ins16("STA_abs", 0x0380)
        # release on the human's own START -- read exactly like the vanilla wait-loops do
        # (($F5|$F7)&$10), so the SAME press that satisfies the game's own blocking loop
        # satisfies ours; no double-press, no injected button on a HUMAN_P1 cart.
        a.ins("LDA_zp", 0xF5); a.ins("ORA_zp", 0xF7); a.ins("AND_imm", 0x10); a.br("BEQ", "hb_no_start")
        a.label("hb_release")
        # RTS immediately -- own the whole hook, like fc_clear's fc_ret. MATCH_ACTIVE is being
        # cleared THIS instant; if the rest of main() below ran afterward in the SAME hook, it
        # would read MATCH_ACTIVE==0 and go_ai would treat this as "first frame of a NEW match"
        # (re-arming SLAM_ARM/cold-state/VSEEN etc. mid-release) -- caught by test_holdboard.py's
        # scenario A2, which failed exactly this way with a plain fall-through/jmp.
        a.ins("LDA_imm", 0); a.ins16("STA_abs", HOLD_ACTIVE); a.ins16("STA_abs", MATCH_ACTIVE)
        a.ins("RTS")
        a.label("hb_no_start")
        if not HUMAN_P1:
            # CvC safety cap: a nav cart auto-presses START almost immediately (autonav's own
            # mode==7 / fc_clear's not-HUMAN_P1 injection), so this rarely fires in practice --
            # but it is the hold's ONLY release path if that injection is ever skipped/late for
            # any reason, so the soak rig cannot wedge on a hold that never sees a press.
            a.ins("LDA_zp", 0x43); a.ins16("CMP_abs", HOLD_LASTCLK); a.br("BEQ", "hb_no_tick")
            a.ins16("STA_abs", HOLD_LASTCLK)
            a.ins16("INC_abs", HOLD_CNT); a.br("BNE", "hb_cnt_ok"); a.ins16("INC_abs", HOLD_CNT + 1)
            a.label("hb_cnt_ok")
            a.ins16("LDA_abs", HOLD_CNT + 1); a.ins("CMP_imm", (HOLDBOARD_F >> 8) & 0xFF)
            a.br("BCC", "hb_no_tick"); a.br("BNE", "hb_release")
            a.ins16("LDA_abs", HOLD_CNT); a.ins("CMP_imm", HOLDBOARD_F & 0xFF); a.br("BCC", "hb_no_tick")
            a.jmp("hb_release")
            a.label("hb_no_tick")
        a.label("hb_skip")
    if NAVESC and not HUMAN_P1:
        # ---- DRNAVESC stuck-screen escape (task #38; see flag block for the full rationale).
        # Runs EVERY hook, ahead of the mode split, so mode-3 holes and mode-4 round-waits are
        # both covered. Fires only after ESC_N hooks (~10 s) with ($0046,$F8,$0386) frozen --
        # $0386 changes every frame of real play, so live matches structurally cannot trip it.
        a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 0x08); a.br("BEQ", "esc_rst")   # intro: hands off
        a.ins16("CMP_abs", ESC_S0); a.br("BNE", "esc_new")
        a.ins("LDA_zp", 0xF8); a.ins16("CMP_abs", ESC_S1); a.br("BNE", "esc_new")
        a.ins16("LDA_abs", 0x0386); a.ins16("CMP_abs", ESC_S2); a.br("BNE", "esc_new")
        a.ins16("INC_abs", ESC_CTL); a.br("BNE", "esc_chk"); a.ins16("INC_abs", ESC_CTH)
        a.label("esc_chk")
        a.ins16("LDA_abs", ESC_CTH); a.ins("CMP_imm", (ESC_N >> 8) & 0xFF); a.br("BCC", "esc_done")
        a.br("BNE", "esc_win")                                # CTH > hi(N): inside/past window (reset caps it)
        a.ins16("LDA_abs", ESC_CTL); a.ins("CMP_imm", ESC_N & 0xFF); a.br("BCC", "esc_done")
        a.label("esc_win")
        # CT >= N: 4-hook press window [N, N+4), then reset to re-arm another full period.
        a.ins16("LDA_abs", ESC_CTL); a.ins("SEC"); a.ins("SBC_imm", ESC_N & 0xFF)
        a.ins("CMP_imm", 4); a.br("BCS", "esc_rst")           # window over -> re-arm
        a.ins("LDA_imm", B_START); a.ins("STA_zp", 0xF5)      # inject START (raw latch ONLY, never $F7)
        a.ins16("STA_abs", 0x6148)                            # DBG: last injected (shared with nav inject)
        a.ins16("INC_abs", 0x614B)                            # DBG: inject count
        a.ins("RTS")                                          # OWN THE FRAME: no downstream $F5 writer
        a.label("esc_new")
        a.ins16("LDA_abs", 0x0046); a.ins16("STA_abs", ESC_S0)
        a.ins("LDA_zp", 0xF8); a.ins16("STA_abs", ESC_S1)
        a.ins16("LDA_abs", 0x0386); a.ins16("STA_abs", ESC_S2)
        a.label("esc_rst")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", ESC_CTL); a.ins16("STA_abs", ESC_CTH)
        a.label("esc_done")
    if STALLWD:
        # ---- DRSTALLWD play-mode P2 stall watchdog (task #40 follow-up; see the flag block above
        # for the full rationale). Same tier as NAVESC above (runs every hook, ahead of the mode
        # split), but keys off P2's game-owned pose instead of the driver's own search-state scratch.
        a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 0x04); a.br("BNE", "swd_rst")   # not play -> re-arm
        a.ins16("LDA_abs", VCOUNT_P2); a.br("BEQ", "swd_rst")                        # P2 cleared -> re-arm
        a.ins16("LDA_abs", 0x0385); a.ins16("CMP_abs", SWD_S0); a.br("BNE", "swd_new")
        a.ins16("LDA_abs", 0x0386); a.ins16("CMP_abs", SWD_S1); a.br("BNE", "swd_new")
        a.ins16("LDA_abs", 0x03A5); a.ins16("CMP_abs", SWD_S2); a.br("BNE", "swd_new")
        a.ins16("INC_abs", SWD_CTL); a.br("BNE", "swd_chk"); a.ins16("INC_abs", SWD_CTH)
        a.label("swd_chk")
        a.ins16("LDA_abs", SWD_CTH); a.ins("CMP_imm", (STALLWD_N >> 8) & 0xFF); a.br("BCC", "swd_done")
        a.br("BNE", "swd_fire")                               # CTH > hi(N): past the window
        a.ins16("LDA_abs", SWD_CTL); a.ins("CMP_imm", STALLWD_N & 0xFF); a.br("BCC", "swd_done")
        a.label("swd_fire")
        # STUCK >= N hooks: SCOPED reset -- re-arm handle(2)'s _start gate against the LIVE board
        # without disturbing ROT_DONE2 / STABLE_CT2 / TGT_C2 / TGT_O2 (a still-good orientation
        # commit or running argmax survives; only the wedged ARMED/WDOG/PEND/DELAY quintet moves).
        a.ins("LDA_imm", 0)
        a.ins16("STA_abs", ARMED2); a.ins16("STA_abs", WDOG2); a.ins16("STA_abs", WDOGH2)
        a.ins16("STA_abs", DELAY2)                            # skip the settle wait: board is unchanged
        a.ins("LDA_imm", 1); a.ins16("STA_abs", PEND2)
        a.jmp("swd_rst")                                      # re-arm: full grace window before refiring
        a.label("swd_new")
        a.ins16("LDA_abs", 0x0385); a.ins16("STA_abs", SWD_S0)
        a.ins16("LDA_abs", 0x0386); a.ins16("STA_abs", SWD_S1)
        a.ins16("LDA_abs", 0x03A5); a.ins16("STA_abs", SWD_S2)
        a.label("swd_rst")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", SWD_CTL); a.ins16("STA_abs", SWD_CTH)
        a.label("swd_done")
    if STUDY2P:
        # ---- DRSTUDY2P: driver-owned pause previews, ALL play modes (task #39; see flag block).
        # PRE-DISPATCH placement is load-bearing: it must run on 1P human hooks too ($04==0 never
        # reaches the play path), and during pause $46 stays 4. Part1 (EVAC v2) draws ONLY the
        # STUDY letters now -- probe round 2 proved the pause loop re-runs the draw call EVERY
        # spin frame, so any preview part1 wrote would stomp this block's writes each frame.
        # The driver therefore owns slots 37-40 outright: 1P layout when $0727==1, 2P when ==2.
        # entry: the block is >127B, out of relative-branch range -- short-branch over a JMP.
        a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 0x04); a.br("BEQ", "s2p_go")
        a.jmp("s2p_no")
        a.label("s2p_go")
        # ---- PAUSE GATE (leak fix; see the EVAC v4 comment at STUDY_BLOB_EVAC). The old block
        # drew unconditionally on every mode-4 hook, betting "the game's OAM rebuild runs after
        # this hook" -- FALSE in VS play (game sprite count 0, R8712 only pads from the sprite
        # high-water mark), so STUDY+previews rendered over live play on ~every frame (the
        # 2026-08-08 Pocket field defect). Now part1 ($D2CC) tops up S2P_TTL once per UNPAUSED
        # play frame and this hook decrements it: TTL>0 = live play -> blank slots 32-40 and
        # skip; TTL==0 = the frame path stopped in a mode-4 blocking wait = the pause loop ->
        # draw. MATCH_ACTIVE!=0 excludes the first play hook of a match (heartbeat not yet
        # started); HOLD_ACTIVE!=0 excludes STAGE CLEAR's own mode-4 blocking wait while the
        # final board is held (drawing STUDY over the held board would be a new artifact).
        a.ins16("LDA_abs", S2P_TTL); a.br("BEQ", "s2p_stale")
        a.ins16("DEC_abs", S2P_TTL)
        a.jmp("s2p_blank")
        a.label("s2p_stale")
        a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BEQ", "s2p_blank")
        if HOLDBOARD:
            a.ins16("LDA_abs", HOLD_ACTIVE); a.br("BNE", "s2p_blank")
        a.jmp("s2p_draw")
        a.label("s2p_blank")
        # Single owner of slots 32-40 in play: park them offscreen (Y=$FF) every hook, so a
        # pause's own draws (and any boot garbage in the shadow) are cleaned the moment play
        # resumes -- there is no other cleaner (that absence is the root cause).
        a.ins("LDA_imm", 0xFF)
        for slot in range(32, 41):
            a.ins16("STA_abs", 0x0200 + slot * 4)
        a.jmp("s2p_no")
        a.label("s2p_draw")
        # STUDY letters (part1 is the heartbeat now -- EVAC v4): tiles/X static per the probe's
        # OAM dump, attr 0; Y is mode-correct below ($0F in 1P, STUDY_2P_Y in 2P).
        for slot, (tile, x) in zip((32, 33, 34, 35, 36),
                                   ((0x0D, 0x70), (0xA0, 0x78), (0x0C, 0x80),
                                    (0xA1, 0x88), (0xA2, 0x90))):
            base = 0x0200 + slot * 4
            a.ins("LDA_imm", tile); a.ins16("STA_abs", base + 1)
            a.ins("LDA_imm", x); a.ins16("STA_abs", base + 3)
        a.ins("LDA_imm", 0x00)
        for slot in (32, 33, 34, 35, 36):
            a.ins16("STA_abs", 0x0200 + slot * 4 + 2)                                   # attr 0
        a.ins16("LDA_abs", 0x031A); a.ins("ORA_imm", 0x60); a.ins16("STA_abs", 0x0295)  # P1 L tile
        a.ins16("LDA_abs", 0x031B); a.ins("ORA_imm", 0x70); a.ins16("STA_abs", 0x0299)  # P1 R tile
        a.ins("LDA_imm", 0x02)                                                          # P1 attr
        a.ins16("STA_abs", 0x0296); a.ins16("STA_abs", 0x029A)
        a.ins16("LDA_abs", 0x0727); a.ins("CMP_imm", 2); a.br("BEQ", "s2p_2p")
        a.ins("LDA_imm", 0x0F)                                                          # 1P: letters Y=$0F
        a.ins16("STA_abs", 0x0280); a.ins16("STA_abs", 0x0284); a.ins16("STA_abs", 0x0288)
        a.ins16("STA_abs", 0x028C); a.ins16("STA_abs", 0x0290)
        a.ins("LDA_imm", 0x45)                                                          # 1P: Y=$45
        a.ins16("STA_abs", 0x0294); a.ins16("STA_abs", 0x0298)
        a.ins("LDA_imm", 0xBE); a.ins16("STA_abs", 0x0297)                              # 1P X (right box)
        a.ins("LDA_imm", 0xC6); a.ins16("STA_abs", 0x029B)
        a.jmp("s2p_no")
        a.label("s2p_2p")
        a.ins16("LDA_abs", 0x039A); a.ins("ORA_imm", 0x60); a.ins16("STA_abs", 0x029D)  # P2 L tile
        a.ins16("LDA_abs", 0x039B); a.ins("ORA_imm", 0x70); a.ins16("STA_abs", 0x02A1)  # P2 R tile
        a.ins("LDA_imm", 0x02)                                                          # P2 attr
        a.ins16("STA_abs", 0x029E); a.ins16("STA_abs", 0x02A2)
        a.ins("LDA_imm", 0x33)                                                          # Y all 4
        a.ins16("STA_abs", 0x0294); a.ins16("STA_abs", 0x0298)
        a.ins16("STA_abs", 0x029C); a.ins16("STA_abs", 0x02A0)
        a.ins("LDA_imm", 0x38); a.ins16("STA_abs", 0x0297)                              # P1 X L
        a.ins("LDA_imm", 0x40); a.ins16("STA_abs", 0x029B)                              # P1 X R
        a.ins("LDA_imm", 0xB8); a.ins16("STA_abs", 0x029F)                              # P2 X L
        a.ins("LDA_imm", 0xC0); a.ins16("STA_abs", 0x02A3)                              # P2 X R
        a.ins("LDA_imm", STUDY_2P_Y)                                                    # STUDY lift
        a.ins16("STA_abs", 0x0280); a.ins16("STA_abs", 0x0284); a.ins16("STA_abs", 0x0288)
        a.ins16("STA_abs", 0x028C); a.ins16("STA_abs", 0x0290)
        a.label("s2p_no")
    # ---- full-clear auto-advance (mode-independent): a player's virus count ($0324/$03A4) hit 0
    # => STAGE CLEAR screen. Inject START (press window) to advance it so the demo LOOPS instead
    # of halting. Gated by MATCH_ACTIVE (set once play dispatched) so boot-init count==0 can't
    # false-trigger (which would wreck the boot state machine). ----
    if NAV_V4:
        # v4 FIX (the REAL mis-land cause -- silicon+py65 confirmed 2026-07-23): the full-clear auto-advance
        # is mode-INDEPENDENT and gated only by MATCH_ACTIVE, which is INHERITED != 0 at a cold boot (the
        # power-on init that clears it runs once-ever via the sticky magic; the mode-8 intro that also clears
        # it never runs at boot). At the title (virus counts read 0, VSEEN inherited from the prior game) it
        # FALSE-fires, injects START, and RTSs -- SKIPPING the autonav entirely -> the title advances to a
        # 1P game (nbPlayers never gets set to 2). Gate it to play/post (mode>=4) so it can never fire in the
        # menus. py65-confirmed: inherited MATCH_ACTIVE=1 -> nbPlayers stays 1 (1P); gated -> autonav runs -> VS.
        # DRFCGATE (2026-08-09): mode>=4 is TOO WIDE -- mode 8 is the two-bottle INTRO, and 8>=4
        # passes. During the intro the board is still being built, so VCOUNT reads 0 while VSEEN
        # is inherited from the previous match -> fc_clear FALSE-FIRES on every hook and the intro
        # can never hand off to play. Measured: once MATCH_ACTIVE survives a match, the cart loops
        # 0->1->2->3->8->0 forever and never reaches mode 4 again -- dead until a power cycle.
        # STAGE CLEAR, the state this gate exists to dismiss, is a blocking wait that holds
        # $0046 == 4 throughout (RB24F_CHECK_WIN, per the disassembly), so mode==4 EXACTLY is the
        # correct gate and loses no coverage. BCC->BNE is the same instruction width, so
        # DRFCGATE=0 stays byte-identical to the pre-fix build.
        a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 0x04)
        a.br("BNE" if FCGATE else "BCC", "fc_no")
    a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BEQ", "fc_no")
    a.ins16("LDA_abs", VCOUNT_P1); a.br("BNE", "fc_chk2")
    a.ins16("LDA_abs", VSEEN1); a.br("BNE", "fc_clear")     # P1==0 counts only if it was ever >0
    a.label("fc_chk2")
    a.ins16("LDA_abs", VCOUNT_P2); a.br("BNE", "fc_no")
    a.ins16("LDA_abs", VSEEN2); a.br("BEQ", "fc_no")
    a.label("fc_clear")                                     # full clear -> own the frame (skip normal dispatch)
    if HOLDBOARD:
        # ARM (inter-match path): fires on EVERY hook that reaches fc_clear, i.e. every hook of
        # the STAGE CLEAR wait (mode stays 4 the whole time -- RB24F_CHECK_WIN is its own
        # blocking routine, confirmed from the disassembly), not just the press-window hooks
        # below. Idempotent: only the FIRST such hook actually arms. Does NOT touch MATCH_ACTIVE
        # (fc_clear's own gate depends on it staying set for the whole wait -- clearing it here
        # would make the NEXT hook fall through to go_ai's match-START init mid-STAGE-CLEAR).
        # ⚠ DRHOLDONCE (default OFF -> byte-inert): the HOLD_ACTIVE guard below is idempotent only
        # WHILE THE HOLD IS UP. The moment the human's START releases it, HOLD_ACTIVE goes 0 while
        # (virus==0 && VSEEN) is still true, so the very next hook re-arms -- and because STAGE
        # CLEAR is a blocking wait that keeps $0046 == 4, all of that happens INSIDE LIVE PLAY.
        # Measured on v8plain-hb1 with the release press supplied: 23 of 25 arms in mode 4,
        # thrashing (arm f2635 rel f2641, arm f2643 rel f2644, arm f2646 rel f2651, ...), costing
        # 3 completed matches and 23 searches per 18,000 frames against 20 and 155 at HOLDBOARD=0.
        # HOLD_ONCE latches "this match-end has already been served". It is cleared only on the
        # go_ai play path, which cannot run during the clear (fc_clear owns the frame and RTSs),
        # so it survives the whole STAGE CLEAR wait and resets when real play resumes.
        if HOLDONCE:
            a.ins16("LDA_abs", HOLD_ONCE); a.br("BNE", "hb_fc_armed")
        a.ins16("LDA_abs", HOLD_ACTIVE); a.br("BNE", "hb_fc_armed")
        a.ins("LDA_imm", 1); a.ins16("STA_abs", HOLD_ACTIVE)
        if HOLDONCE:
            a.ins16("STA_abs", HOLD_ONCE)          # A still 1: one arm per match-end
        a.ins("LDA_imm", 0); a.ins16("STA_abs", HOLD_CNT); a.ins16("STA_abs", HOLD_CNT + 1)
        a.ins("LDA_zp", 0x43); a.ins16("STA_abs", HOLD_LASTCLK)
        a.label("hb_fc_armed")
    if STARTGUARD:
        # #134 site 2: the full-clear state's FIRST hooks can still be inside a live play frame
        # (the pause check reachable on the injected byte); require the state to persist
        # FC_STAB_K hooks before the first press. RB337's blocking wait holds mode 4 for
        # seconds, so the arm delay cannot miss the dismiss. FC_STAB is cleared every go_ai
        # play hook, so it counts THIS match-end's fc hooks only.
        a.ins16("LDA_abs", FC_STAB); a.ins("CMP_imm", FC_STAB_K); a.br("BCS", "fcg_ok")
        a.ins16("INC_abs", FC_STAB); a.jmp("fc_ret")
        a.label("fcg_ok")
    a.ins16("LDA_abs", NAV_T); a.ins("AND_imm", 0x1F); a.ins("CMP_imm", 4); a.br("BCS", "fc_ret")
    if not HUMAN_P1:
        # $F5 is P1's controller latch. On a HUMAN_P1 cart P1 is a PERSON, so injecting
        # START here presses the human's button for them (spec P0.4). The human dismisses
        # their own STAGE CLEAR; the AI is P2 and never needed this.
        a.label("fc_press")             # gate instrumentation anchor (the actual press store)
        a.ins("LDA_imm", B_START); a.ins("STA_zp", 0xF5)    # inject START to dismiss STAGE CLEAR
    a.label("fc_ret"); a.ins("RTS")
    a.label("fc_no")
    a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 0x04)
    if PRESTART:
        # DRPRESTART's per-match init sits inside the go_ai block this branch skips over, which
        # takes the span past +-127 on the DRCOLDINIT arms (measured: 138). Invert-and-JMP; gated
        # so a DRPRESTART=0 build keeps the original short branch and stays byte-identical.
        a.br("BEQ", "is_play"); a.jmp("not_play"); a.label("is_play")
    else:
        a.br("BNE", "not_play")
    a.ins("LDA_zp", 0x04); a.br("BNE", "go_ai")            # $04 != 0 -> VS-CPU AI
    if NAVFIX:
        # DIAGNOSTIC: play-mode with $04==0 AND $0727==1 = a 1P game or the attract demo = the nav
        # did NOT land VS-CPU. Latch NAV_1P (persists this cold boot) so a gauntlet can read it.
        a.ins16("LDA_abs", 0x0727); a.ins("CMP_imm", 1); a.br("BNE", "np_1p_done")
        a.ins("LDA_imm", 1); a.ins16("STA_abs", NAV_1P)
        a.label("np_1p_done")
    a.ins("RTS")
    a.label("go_ai")
    if STARTGUARD:
        # #134 site 2 reset: any hook that reaches live-play dispatch proves we are NOT in the
        # full-clear wait, so the fc arm counter starts from zero at every match end.
        a.ins("LDA_imm", 0); a.ins16("STA_abs", FC_STAB)
    if MATURE:
        # EXPLICIT GAME-START INIT: on the first play frame of a match (MATCH_ACTIVE still 0), disarm
        # the slam -- the first pill has no prior search latency, and the cold $5200 window holds no
        # validated result yet, so it plays canonical anytime until the first fast DONE arms it.
        a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BNE", "ga_slam_ok")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", SLAM_ARM)
        a.label("ga_slam_ok")
    if COLDINIT or not NO_FREEZE:
        # COLD-STATE INIT (freeze carts only): PEND1/2, DELAY1/2, LASTY1/2 are NOT in the power-on init
        # (boot garbage). On a freeze cart, garbage PEND2 makes freeze_pending pin GRAV_P2 on the first
        # frames and garbage LASTY2 mis-fires the pill-lock edge. Clear them on the first play frame of a
        # match (MATCH_ACTIVE==0) so the first capsule starts from a known state. Anytime carts (NO_FREEZE)
        # never pin so they don't need it (and stay byte-exact) -- this is the sibling of the 2026-07-18
        # PEND1-gate fix, but it clears the actual state instead of only guarding P1's pin.
        a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BNE", "ga_cold_ok")
        a.ins("LDA_imm", 0)
        a.ins16("STA_abs", PEND1); a.ins16("STA_abs", PEND2)
        a.ins16("STA_abs", DELAY1); a.ins16("STA_abs", DELAY2)
        a.ins16("STA_abs", LASTY1); a.ins16("STA_abs", LASTY2)
        if COLDINIT:
            # SOFT-RELAUNCH stall (P2.2 mechanism): PRG-RAM persists across a core relaunch, so a
            # stale ARMED2=1 makes handle() wait on a copro that is not searching -- the FIRST pill
            # pins until the STALE watchdog trips (minutes). Clear the search state per match too;
            # a genuinely stale in-flight search is torn down safely (the next GO resets the copro).
            a.ins16("STA_abs", ARMED2); a.ins16("STA_abs", WDOG2); a.ins16("STA_abs", WDOGH2)
            a.ins16("STA_abs", WRETRY2)
            if not HUMAN_P1:
                a.ins16("STA_abs", ARMED); a.ins16("STA_abs", WDOG); a.ins16("STA_abs", WDOGH1)
                a.ins16("STA_abs", WRETRY)
        a.label("ga_cold_ok")
    if PRESTART:
        # PER-MATCH re-init (own block, not folded into the COLDINIT one above, which is gated on
        # `COLDINIT or not NO_FREEZE` and so is absent from anytime carts). PRG-RAM persists across
        # a core relaunch and across matches, so a PRE_ACT2 left set by an aborted match would
        # silently swallow the next match's first search. PRE_LAST2 is seeded from the LIVE counter
        # rather than zeroed so a stale nonzero value cannot manufacture a phantom release edge.
        a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BNE", "ga_pre_ok")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", PRE_ACT2)
        if PRESPIPE:
            # A==0. Same persistence argument as PRE_ACT2: a pipeline aborted by a match end
            # would otherwise resume phases against a dead board next match; a stale swallow
            # would eat the new match's first release edge.
            a.ins16("STA_abs", PP_PH); a.ins16("STA_abs", PP_SWAL)
        a.ins16("LDA_abs", PRE_ATK2); a.ins16("STA_abs", PRE_LAST2)
        a.label("ga_pre_ok")
    if STUDY2P:
        # PER-MATCH: pre-arm the pause-gate heartbeat on the first play hook (the same hook
        # sets MATCH_ACTIVE below, and s2p runs BEFORE this point in the hook). Without this,
        # hook #2 of the first play frame sees MATCH_ACTIVE=1 with the $D2CC heartbeat not yet
        # started (it first runs in this frame's MAIN LOOP, after the NMI) -> a 1-frame STUDY
        # flash at round start (measured: exactly 1 frame in a 32.4k-frame soak, f=234).
        a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BNE", "s2p_ma_ok")
        a.ins("LDA_imm", S2P_TTL_N); a.ins16("STA_abs", S2P_TTL)
        a.label("s2p_ma_ok")
    if USE_SEEDS:
        a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BNE", "ga_on")  # first play frame of this match:
        a.ins16("LDA_abs", NAV_T); a.ins("ORA_imm", 0x01); a.ins16("STA_abs", SEED1)   # root seed
        a.ins("EOR_imm", 0xA4); a.ins16("STA_abs", SEED2)       # bit0 kept -> both odd, distinct
        a.label("ga_on")
    if HOLDONCE:
        # DRHOLDONCE reset. This runs on the go_ai play path, which fc_clear pre-empts (it owns the
        # frame and RTSs), so it CANNOT run during the STAGE CLEAR wait -- the latch survives the
        # whole clear and only resets once real play is actually running again. That is what makes
        # the arm fire once per match-END rather than once per hook.
        a.ins("LDA_imm", 0); a.ins16("STA_abs", HOLD_ONCE)
    a.ins("LDA_imm", 1); a.ins16("STA_abs", MATCH_ACTIVE)   # play started -> arm full-clear detect
    a.ins16("LDA_abs", VCOUNT_P1); a.br("BEQ", "ga_v2"); a.ins("LDA_imm", 1); a.ins16("STA_abs", VSEEN1)
    a.label("ga_v2")
    a.ins16("LDA_abs", VCOUNT_P2); a.br("BEQ", "ga_vd"); a.ins("LDA_imm", 1); a.ins16("STA_abs", VSEEN2)
    a.label("ga_vd")
    a.jmp("dispatch")
    a.label("not_play")
    if HOLDBOARD:
        # ARM (set-final / topout path): a topout leaves VCOUNT nonzero for the losing player, so
        # fc_clear's virus==0 check never fires -- L46_TOP_STATE instead transitions 4->5->7
        # (TOP_5 does book-keeping then jumps to TOP_7, which is its own blocking GAME OVER wait,
        # confirmed from the disassembly). We land here on that FIRST non-4 hook with MATCH_ACTIVE
        # still set from the just-ended match. Unlike the fc_clear arm, this DOES need MATCH_ACTIVE
        # cleared afterward (own action, not left to DRCOLDINIT) -- otherwise, once the hold
        # releases and HOLD_ACTIVE goes back to 0, the NEXT idle menu hook would see MATCH_ACTIVE
        # still nonzero and re-arm a hold with nothing to hold (a stale snapshot, forever, at the
        # title screen). Idempotent: HOLD_ACTIVE!=0 (already armed via fc_clear or a prior pass
        # through here) skips straight past.
        a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BEQ", "hb_np_skip")
        a.ins16("LDA_abs", HOLD_ACTIVE); a.br("BNE", "hb_np_skip")
        a.ins("LDA_imm", 1); a.ins16("STA_abs", HOLD_ACTIVE)
        a.ins("LDA_imm", 0); a.ins16("STA_abs", HOLD_CNT); a.ins16("STA_abs", HOLD_CNT + 1)
        a.ins("LDA_zp", 0x43); a.ins16("STA_abs", HOLD_LASTCLK)
        a.label("hb_np_skip")
    if BUILDID:
        # Stamp the settings screen only (see the DRBUILDID flag comment for the full mechanism
        # + the row-25/font/overwrite evidence). Self-contained mode check -- does not depend on
        # A holding $0046 from anything earlier in this hook.
        a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 1); a.br("BNE", "bid_skip")
        a.ins("LDA_imm", (BID_PPU_ADDR >> 8) & 0xFF); a.ins16("STA_abs", 0x2006)
        a.ins("LDA_imm", BID_PPU_ADDR & 0xFF); a.ins16("STA_abs", 0x2006)
        a.label("bid_tag0")          # anchor for tests: first tag-char LDA_imm opcode
        for _ch in BUILDID_TAG:
            a.ins("LDA_imm", _bid_tile(_ch)); a.ins16("STA_abs", 0x2007)
        a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", 0x2007)          # space
        for _i in range(4):
            # PLACEHOLDER $FF -- patched post-build in main() once the content hash is known
            # (see the DRBUILDID flag comment). The label marks the LDA_imm's OPCODE byte; the
            # operand (the byte actually patched) is one byte further, resolved from this same
            # `labels` dict by main() after build_main() returns -- no second source of truth
            # for the offset.
            a.label(f"bid_hash{_i}")
            a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", 0x2007)
        a.label("bid_skip")
    if STUDY and STUDYCOUNTS:
        # GARBLE FIX (user-reported, tape f0075.jpg): STUDYCOUNTS (above, in "dispatch") writes
        # live digit sprites into OAM slots 8-15 every PLAY-mode hook ($0046==4), but previously
        # did nothing on any other mode -- neither redraw nor blank. The base ROM's per-frame OAM
        # hygiene (R8712 @ $8712) is NOT an unconditional clear: it only pads the shadow buffer
        # from THAT SCREEN's own sprite high-water-mark ($42) onward, so a screen using few of its
        # own sprites (e.g. the "2 PLAYER GAME" settings/level-select screen) can leave slots 8-15
        # holding a stale frame of digit tiles, rendered as garbage. The ROM's own settings-screen
        # print table is verified byte-identical to vanilla (tools/romgen.py diff), so this is a
        # runtime OAM leak, not a table collision. Fix: on every non-play hook, explicitly move
        # all 8 digit sprites off-screen (Y=$FF -- the same idiom R8712 and this driver already
        # use). One writer now owns the whole slot-8-15 lifecycle: draw-when-valid (dispatch) or
        # blank-always (here) -- no reliance on the game's own bookkeeping to happen to cover them.
        a.ins("LDA_imm", 0xFF)
        for _slot in (8, 9, 10, 11, 12, 13, 14, 15):
            a.ins16("STA_abs", 0x0200 + _slot * 4)
        a.ins16("LDA_abs", 0x0046)                          # restore A = mode for the CMP below
    a.ins("CMP_imm", 0x08); a.br("BNE", "menus")
    # intro mode ONLY happens at power-on/reset: re-arm the autonav (PRG-RAM persists across
    # soft core relaunches, so the NAV_MAGIC one-time init does NOT re-run -> stale NAV_T killed
    # the nav and the title idled into attract mode). Zeroing here makes every boot nav cleanly.
    a.ins("LDA_imm", 0); a.ins16("STA_abs", NAV_T); a.ins16("STA_abs", MATCH_ACTIVE)
    a.ins16("STA_abs", VSEEN1); a.ins16("STA_abs", VSEEN2)
    if NAVFIX:
        a.ins16("STA_abs", NAV_STABLE)                      # A==0: fresh confirm count each boot
    if NAVDWELL:
        a.ins16("STA_abs", DWELL_CNT)                       # A==0: fresh boot -> re-arm the title dwell
    if NAVFIX and not NAV_V4:
        # v3 ONLY: force the 1P baseline here. Silicon showed mode 8 RE-ENTERS during the title, so this
        # re-fires and fights the toggles (the 5/5-stuck regression). v4 needs no baseline -- it writes
        # coherent VS-CPU directly at the title (and inherited $0727/$04 are reset to (1,0) every boot).
        a.ins("LDA_imm", 1); a.ins16("STA_abs", 0x0727)     # $0727 = 1 (1P player-mode)
        a.ins("LDA_imm", 0); a.ins("STA_zp", 0x04)          # $04 = 0 (VS flag clear -> coherent 1P)
    a.ins("RTS")                                            # intro/init: hands off otherwise
    a.label("menus")
    if COLDINIT:
        # left play -> the next match must re-run the cold-state init (rematch after topout
        # keeps LASTY2 at the spawn row, suppressing the first pill's search edge)
        a.ins("LDA_imm", 0); a.ins16("STA_abs", MATCH_ACTIVE)
    a.jsr("autonav")
    a.ins("LDA_zp", 0x04); a.br("BEQ", "m_done")
    a.ins("LDA_zp", 0xF5); a.ins("STA_zp", 0xF6)            # VS: mirror P1->P2 (level cursor)
    a.label("m_done"); a.ins("RTS")

    # ============ autonav: direct state + $F5-only START injection (ZERO input) ============
    # SELECT-equivalent: JSR $FF30 (hack's own toggle; touches only $0727/$04/$06F1) until
    # $04==1. Levels: force $0316/$0396/$96=11 in mode 1. STARTs: inject $F5=$10 in a press
    # window. KEY: inject $F5 ONLY -- the read routine ANDs two raw passes (hook fires in
    # both, value survives) then computes newly-pressed = raw & ~held($F7); writing $F7 too
    # marks the button already-held and zeroes the edge (the original injection bug).
    # Window (NAV_T & $1F) < 4: pressed ~1 frame in ~6 (hook ~5 calls/frame), then released.
    def inject(bits):
        a.label("inj_guard")            # gate instrumentation anchor (labels emit no bytes)
        if STARTGUARD:
            # #134 site 1: never let an injected press be live on a frame whose main loop can
            # run the play input handler -- mode 4 is the match frame itself, and mode 8 is its
            # PREDECESSOR (the 8->4 transit happens later in the SAME frame, after this hook --
            # the #131 lesson). Re-read the LIVE mode at the store, not any cached copy.
            a.ins16("LDA_abs", 0x0046)
            a.ins("CMP_imm", 0x04); a.br("BEQ", "inj_skip")
            a.ins("CMP_imm", 0x08); a.br("BEQ", "inj_skip")
        a.label("inj_sta")              # gate instrumentation anchor (the actual press store)
        a.ins("LDA_imm", bits); a.ins("STA_zp", 0xF5)
        a.ins16("STA_abs", 0x6148)                          # DBG: last injected
        a.ins16("INC_abs", 0x614B)                          # DBG: inject count
        if STARTGUARD:
            a.label("inj_skip")
    a.label("autonav")
    a.ins16("LDA_abs", 0x0046)
    if NAV_V4:
        # v4: re-establish coherent VS-CPU ($0727=2,$04=1) at EVERY menu hook (modes 0-3), not just the
        # title. Silicon ring: the mis-land boots' title advances in ~1 hook and the 0->1 transition RESETS
        # $0727=1 -- the SAME 0->1->2->3->8->4 flow runs for both VS and 1P boots (not a separate demo path),
        # so re-writing (2,1) every menu hook survives each transition and the game commits VS at intro/play.
        a.ins("CMP_imm", 0x04); a.br("BCS", "an_v4_notmenu")   # mode>=4 (play/intro8/post7): not a menu
        a.ins("LDA_imm", 2); a.ins16("STA_abs", 0x0727)
        a.ins("LDA_imm", 1); a.ins("STA_zp", 0x04)
        a.ins16("LDA_abs", 0x0046)                             # reload mode for the dispatch below
        a.label("an_v4_notmenu")
    a.ins("CMP_imm", 0x00); a.br("BEQ", "an_title")
    a.ins("CMP_imm", 0x01); a.br("BEQ", "an_lvl")
    a.ins("CMP_imm", 0x07); a.br("BEQ", "an_start")         # post-match: START -> rematch
    a.ins("RTS")
    a.label("an_title")
    # VS-CPU landing gate. $FF30 cycles three states: 1P ($0727=1,$04=0) -> 2P-human
    # ($0727=2,$04=0) -> VS-CPU ($0727=2,$04=1). $04 is the ONLY discriminator that
    # isolates VS-CPU; $0727==2 is ALSO true at 2P-human. Gating START on $0727==2 (the
    # 992682f "deterministic-nav" experiment) fires START one toggle early, INTO 2P-human,
    # where $04==0 leaves the play-dispatch AI dormant (see "LDA $04; BNE go_ai" above) ->
    # neither board is ever uploaded, DONE never fires, both capsules stagnate. That is the
    # v4 AB-cart regression. Gate on $04 (BEQ->toggle past 2P-human, land on VS-CPU): this
    # is the emission that ALL shipped/validated carts use (Pocket + AB); $0727==2 never
    # shipped. NOTE (DRNAVFIX=0): keep this a byte-exact "LDA $04; BEQ; JMP" 7-byte block -- any
    # change here shifts the whole downstream driver and reopens the byte-divergence from the
    # deployed reference carts.
    if NAV_V4:
        # v4 STATE-DIRECTED + TITLE-HOLD (silicon + labeled-disasm confirmed): the mis-land is the ATTRACT
        # DEMO, not $04. The title mode-0 loop (base $98FE) increments waitFrames ($51) every 256 frames and
        # at waitFrames==demoStart_delay($08) runs @toDemo, which FORCES nbPlayers($0727)=1 -> 1P. waitFrames
        # is reset ONLY by UP/DOWN/SELECT; the nav uses $FF30 direct-writes (never those) so waitFrames rides
        # STICKY across boots -- on the mis-land boots it's inherited near 8 and the demo trips before the nav
        # commits VS. FIX: reset waitFrames=0 every title hook (what a cursor press does) so the demo NEVER
        # trips -> the title holds indefinitely and the nav always reaches VS. Then write coherent VS-CPU
        # ($0727=2,$04=1) directly (disasm-verified: $FF30 touches only these two), hold NAV_M4 hooks, START.
        if NAV_HOLD:
            a.ins("LDA_imm", 0); a.ins("STA_zp", 0x51)      # waitFrames = 0 -> demo never trips (title HOLD)
        # ORDER MATTERS -- 2026-07-29 fix. The dwell gate USED TO SIT HERE, in front of the
        # coherent-VS-CPU writes below. Those writes exist precisely because the title loop
        # RESETS $0727 on every transition, so only re-writing (2,1) on EVERY hook survives.
        # Gating them behind the dwell defeated that invariant: the state never stuck,
        # NAV_STABLE could never hold, and each START that did fire re-armed the dwell for
        # another DWELL_FRAMES -- so the title held FOREVER (observed 110+ s on silicon, vs
        # the ~3 s the dwell intends). Symptom looked like "autonav is dead".
        # The state maintenance now runs unconditionally; the dwell delays ONLY the START.
        a.ins("LDA_imm", 2); a.ins16("STA_abs", 0x0727)     # $0727 (nbPlayers) = 2
        a.ins("LDA_imm", 1); a.ins("STA_zp", 0x04)          # $04 = 1  -> coherent VS-CPU, set every title hook
        if NAVDWELL:
            # TITLE DWELL (see DRNAVDWELL): hold the START for ~DWELL_FRAMES real frames so the
            # branded logo shows. Counted off the game's frameCounter $43 (hook-rate-independent),
            # saturating so it cannot wrap.
            a.ins("LDA_zp", 0x43); a.ins16("CMP_abs", DWELL_LAST); a.br("BEQ", "dwell_chk")   # same frame -> check
            a.ins16("STA_abs", DWELL_LAST)                                                     # new frame seen
            a.ins16("LDA_abs", DWELL_CNT); a.ins("CMP_imm", DWELL_FRAMES); a.br("BCS", "dwell_chk")  # saturate
            a.ins16("INC_abs", DWELL_CNT)
            a.label("dwell_chk")
            a.ins16("LDA_abs", DWELL_CNT); a.ins("CMP_imm", DWELL_FRAMES); a.br("BCS", "dwell_done")  # elapsed->nav
            a.ins("RTS")                                                                       # holding: logo shown
            a.label("dwell_done")
        a.ins16("LDA_abs", NAV_STABLE); a.ins("CMP_imm", NAV_M4); a.br("BCS", "an_start")  # confirmed -> START
        a.ins16("INC_abs", NAV_STABLE); a.ins("RTS")        # holding VS, climbing the confirm
    elif NAVFIX:
        # LEAKY STABILITY-GATED START. armed = ($04 != 0) AND ($0727 == 2) -- the conjunction (not
        # $0727 alone, the v4 2P-human trap) uniquely identifies VS-CPU AND rejects a garbage $04 that
        # lacks $0727==2. armed -> NAV_STABLE toward NAV_M; un-armed -> DECREMENT (not reset), so a
        # menu-redraw flicker only nibbles the count while a genuinely-sustained VS-CPU fills it (the
        # consecutive-reset v1 never filled under flicker -> title timed out into the attract demo).
        # START only at NAV_STABLE>=NAV_M. While NAV_STABLE>0 a flicker does NOT toggle (so it can't
        # over-toggle past VS-CPU); only a truly un-VS-CPU state (NAV_STABLE==0) toggles onward.
        a.ins("LDA_zp", 0x04); a.br("BEQ", "an_unarmed")
        a.ins16("LDA_abs", 0x0727); a.ins("CMP_imm", 2); a.br("BNE", "an_unarmed")
        a.ins16("LDA_abs", NAV_STABLE); a.ins("CMP_imm", NAV_M); a.br("BCS", "an_start")  # at NAV_M -> START
        a.ins16("INC_abs", NAV_STABLE); a.ins("RTS")        # armed, climbing -> wait (no toggle)
        a.label("an_unarmed")
        a.ins16("LDA_abs", NAV_STABLE); a.br("BEQ", "an_untog")   # ==0 -> genuinely not at VS-CPU
        a.ins16("DEC_abs", NAV_STABLE); a.ins("RTS")        # leak a flicker off VS-CPU -> do NOT toggle
        a.label("an_untog")
        a.ins16("LDA_abs", NAV_T); a.ins("AND_imm", 0x1F); a.ins("CMP_imm", 1); a.br("BEQ", "an_tog_go")
        a.ins("RTS")
        a.label("an_tog_go")
        a.jsr(0xFF30); a.ins("RTS")                          # ONE toggle per window toward VS-CPU
    else:
        a.ins("LDA_zp", 0x04); a.br("BEQ", "an_tog")
        a.jmp("an_start")
        a.label("an_tog")
        a.ins16("LDA_abs", NAV_T); a.ins("AND_imm", 0x1F); a.ins("CMP_imm", 1); a.br("BEQ", "an_tog_go")
        a.ins("RTS")
        a.label("an_tog_go")
        a.jsr(0xFF30)                                       # ONE toggle per window (game needs a
        a.ins("RTS")                                        #  frame between mode inits; the $04
                                                            #  gate above lands VS-CPU deterministically)
    a.label("an_lvl")
    if not HUMAN_P1:
        # spec P0.4: on a human cart the PERSON chooses the level/speed on the select screen.
        # Forcing $0316/$45 here silently overrides their choice mid-navigation. Falls through
        # to an_start, which is itself inert for human carts.
        a.ins("LDA_imm", level)
        a.ins16("STA_abs", 0x0316)                          # P1 level
        a.ins16("STA_abs", 0x0396)                          # P2 level (+$80 struct offset)
        a.ins("STA_zp", 0x96)                               # live cursor (cosmetic)
        a.ins("LDA_imm", speed); a.ins("STA_zp", 0x45)      # force game speed (0=LOW,1=MED,2=HI)
    a.label("an_start")
    a.ins16("LDA_abs", NAV_T); a.ins("AND_imm", 0x1F); a.ins("CMP_imm", 4); a.br("BCC", "an_st_go")
    a.ins("RTS")
    a.label("an_st_go")
    if not HUMAN_P1:
        # spec P0.4: autonav drives the menus by pressing P1's buttons. On a human cart the
        # human IS P1 and navigates for themselves -- injecting here fights them for control
        # (measured 7/40 hooks). Leave an_st_go as a bare RTS so the nav path is inert.
        inject(B_START)
    a.label("an_st_ret")                # gate instrumentation anchor (both inject paths converge here)
    # NOTE: do NOT re-arm DWELL_CNT here. This runs on the FIRST hook that injects START, so the
    # next hook of the SAME press window re-enters the dwell hold and RTSes before inject() --
    # the press lasts one hook. The game ANDs TWO raw passes of $F5, so a 1-hook press can never
    # register and the title re-dwells forever. Re-arm lives in the mode-8 intro block instead.
    a.ins("RTS")

    # ================= play-mode CPU-vs-CPU driver (time-shared FPGA) =================
    a.label("dispatch")
    if HOLDBOARD:
        # Continuously mirror both boards while a match is live and pre-clear (dispatch is only
        # reached before either player's virus count has hit 0 -- see fc_clear above), so the
        # hold-arm code below always has a same-frame-fresh "last good" snapshot to fall back to
        # (RB337_STAGE_CLEAR/TOP_7 destroy $0400/$0500 synchronously, before this hook can react
        # to the SAME frame's transition -- see the DRHOLDBOARD flag comment).
        a.ins("LDX_imm", 0)
        a.label("hb_snap_lp")
        a.ins16("LDA_absX", 0x0400); a.ins16("STA_absX", HOLD_BUF1)
        a.ins16("LDA_absX", 0x0500); a.ins16("STA_absX", HOLD_BUF2)
        a.ins("INX"); a.br("BNE", "hb_snap_lp")
    if STUDY and STUDYCOUNTS:
        # STUDY counter redraw (see DRSTUDYCOUNTS). Stack-free: ones stays in A, tens in X.
        # ★ THE TWO COUNTERS USE DIFFERENT ENCODINGS -- do not share a digit splitter.
        # Proven from the BASE GAME's own draw/clamp code in drmario_v28cs.nes, which is the
        # authority (it produces the number the player sees):
        #   VIRUS $0324 is BCD  -- @0x446: LDA $0324 / AND #$F0 / LSR x4 / STA $2007, then
        #                          AND #$0F for the ones. Nibble extraction, never a divide.
        #   LEVEL $0316 is BINARY -- @0x1992: LDA $0316 / CMP #$15 / LDA #$14 / STA $0316
        #                          clamps to 0x14 = 20 DECIMAL. A BCD clamp would be #$20.
        # Splitting the BCD virus byte with a binary divide-by-10 renders 0x48 ("48" viruses
        # at L11) as "72" -- the exact user-reported 48 -> 72. It gets worse with level:
        # L15 (64) -> 100 and L20 (84) -> 132, which also overflows the 2-digit field.
        for (csrc, sa, sb, xa, xb, ytop, tag, bcd) in (
                (0x0324, 12, 13, 0x6E, 0x76, 0xBF, "v1", True),
                (0x03A4, 14, 15, 0x83, 0x8B, 0xBF, "v2", True),
                (0x0316, 8, 9, 0x6D, 0x75, 0x2B, "l1", False),
                (0x0396, 10, 11, 0x84, 0x8C, 0x2B, "l2", False)):
            if bcd:
                # nibble extract: no loop, no backward branch -- which also retires the
                # BCC-onto-JMP hazard entirely for these two counters.
                a.ins16("LDA_abs", csrc); a.ins("AND_imm", 0x0F)
                a.ins16("STA_abs", 0x0200 + sb * 4 + 1)              # ones tile
                a.ins16("LDA_abs", csrc)
                for _ in range(4):
                    a.ins("LSR_A")                                   # high nibble -> tens
                a.ins16("STA_abs", 0x0200 + sa * 4 + 1)              # tens tile
            else:
                a.ins16("LDA_abs", csrc); a.ins("LDX_imm", 0)
                a.label(f"sc_{tag}")
                a.ins("CMP_imm", 10); a.br("BCC", f"sc_{tag}_d")
                a.ins("SBC_imm", 10); a.ins("INX"); a.jmp(f"sc_{tag}")
                a.label(f"sc_{tag}_d")
                a.ins16("STA_abs", 0x0200 + sb * 4 + 1)              # ones tile
                a.ins("TXA"); a.ins16("STA_abs", 0x0200 + sa * 4 + 1)  # tens tile
            a.ins("LDA_imm", ytop)
            a.ins16("STA_abs", 0x0200 + sa * 4); a.ins16("STA_abs", 0x0200 + sb * 4)
            a.ins("LDA_imm", 1)
            a.ins16("STA_abs", 0x0200 + sa * 4 + 2); a.ins16("STA_abs", 0x0200 + sb * 4 + 2)
            a.ins("LDA_imm", xa); a.ins16("STA_abs", 0x0200 + sa * 4 + 3)
            a.ins("LDA_imm", xb); a.ins16("STA_abs", 0x0200 + sb * 4 + 3)
    # ---- pill-lock edge detect (both players) ----
    a.ins16("LDA_abs", 0x0306); a.ins16("CMP_abs", LASTY1)
    a.br("BCC", "no_p1_new"); a.br("BEQ", "no_p1_new")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", PEND1)
    a.ins("LDA_imm", 15); a.ins16("STA_abs", DELAY1)        # ~3 frames settle before upload
    a.ins("LDA_imm", 0); a.ins16("STA_abs", WRETRY)
    if P1WIGGLE:
        # SPECTATOR WIGGLE: flip the hold direction for the pill that just spawned. AND #1
        # after the EOR so power-on garbage in PRG-RAM can only ever land on 0 or 1 (act_p1
        # then maps those to LEFT/RIGHT) -- a raw EOR of the direction BITS could latch
        # LEFT|RIGHT together, which the game accepts and which cancels to no net movement.
        a.ins16("LDA_abs", WIG_DIR); a.ins("EOR_imm", 0x01); a.ins("AND_imm", 0x01)
        a.ins16("STA_abs", WIG_DIR)
    a.label("no_p1_new")
    a.ins16("LDA_abs", 0x0306); a.ins16("STA_abs", LASTY1)
    a.ins16("LDA_abs", 0x0386); a.ins16("CMP_abs", LASTY2)
    a.br("BCC", "no_p2_new"); a.br("BEQ", "no_p2_new")
    if PRESTART:
        # A prestart already owns this capsule: its search was launched against the PROJECTED
        # post-garbage board with THIS capsule's colours, so queueing a second one would either
        # double-search the same pill or (worse) re-GO a copro that is still running -- the
        # GO-storm re-entrancy family. Skip PEND2/DELAY2 only; every other per-pill reset below
        # still runs. When the prestart has already DONE'd, PEND2==0 also means act_p2's settle
        # guard opens on the FIRST hook of the fall, which is the whole point: the answer is
        # already published in TGT_C2/TGT_O2 instead of arriving ~7.5 frames + a search later.
        a.ins16("LDA_abs", PRE_ACT2); a.br("BNE", "p2_pre_own")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", PEND2)
    a.ins("LDA_imm", 15); a.ins16("STA_abs", DELAY2)        # ~3 frames settle before upload
    if PRESTART:
        a.label("p2_pre_own")
    a.ins("LDA_imm", 0)
    if PRESTART:
        a.ins16("STA_abs", PRE_ACT2)                        # A==0: consumed (or was never set)
    a.ins16("STA_abs", WRETRY2 if WRETRY_FIX else WRETRY)   # FIX(B): reset P2's latch per P2 pill (was WRETRY=P1)
    if ROTFIX:
        a.ins16("STA_abs", ROT_DONE2)                       # A==0 here: new P2 pill -> re-enter pre-phase
    if SLAM:
        a.ins16("STA_abs", STABLE_CT2)                      # A==0: new pill -> argmax must re-prove stability
    if MATURE:
        # LOCK-WHILE-ARMED: this pill locked while its search was still ARMED (never DONE'd) -> the
        # search can't keep pace with the fall -> disarm so the next pill plays canonical anytime.
        a.ins16("LDA_abs", ARMED2); a.br("BEQ", "p2_lockok")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", SLAM_ARM)
        a.label("p2_lockok")
    a.label("no_p2_new")
    a.ins16("LDA_abs", 0x0386); a.ins16("STA_abs", LASTY2)
    if PRESTART:
        # Runs BEFORE handle(2) so a prestart issued this hook starts its watchdog on this hook,
        # exactly as a normal `_start` does. Body lives past freeze_pending (JSR-only territory).
        a.jsr("pre_tick")

    # ---- stagnation detect: pill not moving while not search-frozen -> count up ----
    def stagnate(px, py, sx, sy, cnt, armed, pend, tag):
        a.ins16("LDA_abs", px); a.ins16("CMP_abs", sx); a.br("BNE", f"mvd_{tag}")
        a.ins16("LDA_abs", py); a.ins16("CMP_abs", sy); a.br("BNE", f"mvd_{tag}")
        # Skip while PENDING (waiting for its search -> would force-drop in the spawn center)
        # or while being SEARCHED (frozen). Only a genuinely wedged pill should force-drop.
        a.ins16("LDA_abs", pend); a.br("BNE", f"sk_{tag}")
        a.ins16("LDA_abs", armed); a.br("BNE", f"sk_{tag}")
        a.label(f"cnt_{tag}")
        a.ins16("INC_abs", cnt)
        a.jmp(f"sk_{tag}")
        a.label(f"mvd_{tag}")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", cnt)
        a.ins16("LDA_abs", px); a.ins16("STA_abs", sx)
        a.ins16("LDA_abs", py); a.ins16("STA_abs", sy)
        a.label(f"sk_{tag}")
    stagnate(0x0305, 0x0306, STKX1, STKY1, STK1, ARMED, PEND1, "s1")
    stagnate(0x0385, 0x0386, STKX2, STKY2, STK2, ARMED2, PEND2, "s2")

    # ---- DUAL-COPRO search: each player drives its OWN coprocessor; both run in parallel.
    # No time-sharing => no WHICH / fair-serving / pending-wait. handle() emitted per player.
    def handle(idx, wbase, board_src, colsrcs, armed, wdog, wretry, pend, delay, tgt_c, tgt_o, wdogh, seedsrc):
        wgo, wdone, wcol, wor = wbase + 0x84, wbase + 0x84, wbase + 0x85, wbase + 0x86
        L = f"h{idx}"
        a.ins16("LDA_abs", delay); a.br("BEQ", f"{L}_dz"); a.ins16("DEC_abs", delay)   # settle timer
        a.label(f"{L}_dz")
        a.ins16("LDA_abs", armed)                               # not searching -> maybe start
        if MATURE and idx == 2:
            a.br("BNE", f"{L}_armed"); a.jmp(f"{L}_start"); a.label(f"{L}_armed")  # trampoline (maturity code widens the span)
        else:
            a.br("BEQ", f"{L}_start")
        a.ins16("LDA_abs", wdone)
        if TUCK and idx == 2:
            # far branch: TUCK's D1/D2 fix bytes (both gated behind `if TUCK and idx==2`,
            # elsewhere in this function) push {L}_search out of the +-127 relative-branch
            # range. Invert-and-JMP, same idiom as the nf2_untorn site above ("rel too far").
            # Gated so a DRTUCK=0 (or P1/idx==1) build keeps the ORIGINAL short branch and
            # stays byte-identical -- this fix must not cost bytes on carts that never asked
            # for it.
            a.br("BNE", f"{L}_wdone_ok"); a.jmp(f"{L}_search"); a.label(f"{L}_wdone_ok")
        else:
            a.br("BEQ", f"{L}_search")    # DONE==0 -> still searching
        # publish result: best_col + orient4 -> game orient map {0xFF/0:3, 1:1, 2:0, 3:2}
        # ★ PUBLISHED-COLUMN SANITY GUARD (unconditional -- every cart, every core). The
        # playfield is 8 wide, so any column >= 8 is not a result, it is noise. Without this
        # the driver trusts whatever the window returns, and on a core that does NOT decode a
        # copro window the reads are OPEN BUS = the address high byte: $5085 yields $50 = 80.
        # act_* then compares pillX (0-7) against 80, the BCC is always taken, and that player
        # holds ONE direction for the rest of the match -- which is exactly what happened to P1
        # on NES_tuckmb_20260731 (measured 2026-08-01: TGT_C1=$50, whole stack in the right
        # wall, 48 viruses alive). It read as "the AI is stupid" for weeks; it was an
        # undecoded address. On a bad read we now KEEP the previous target and still clear
        # ARMED/WDOG below, so the driver neither adopts the garbage nor spins re-reading it.
        # This costs 5 bytes per handle() and protects every future core revision.
        a.ins16("LDA_abs", wcol)
        a.ins("CMP_imm", 8); a.br("BCC", f"{L}_colok")
        a.jmp(f"{L}_badcol")            # via JMP: the span to the teardown exceeds branch range
        a.label(f"{L}_colok")
        a.ins16("STA_abs", tgt_c)
        if TUCK and idx == 2:
            # latch the tuck descriptor alongside the column, from the SAME published result
            a.ins16("LDA_abs", W_TCOL); a.ins16("STA_abs", TUCK_C2)
            # D1 FIX: tuck_scan publishes a BOARD ROW (0 = top); the executor compares it
            # against $0386, which the game stores as 15 - row (meatfighter DrMarioAI.java:69,
            # `y = 15 - readCPU(CURRENT_Y)`). Convert here so TUCK_R2 is in $0386's own units --
            # without this the raw row reads as a near-top trigger and the switch barely fires,
            # or fires at the wrong point in the fall (dr-mario-tuck-executor-gap D1).
            a.ins("LDA_imm", 15); a.ins("SEC"); a.ins16("SBC_abs", W_TROW)
            a.ins16("STA_abs", TUCK_R2)
            if TUCKGUARD:
                # ---- DRTUCKGUARD (task #102): CART-SIDE FALL-BUDGET VETO --------------------
                # The executor is blameless -- 23/23 tucks completed whenever the descriptor left
                # room to move. The harm is entirely in the DESCRIPTOR: tuck-v1 (what the Pocket
                # core publishes) scans r = fc..ra with ra = first_occ(approach)-1, so it can put
                # the trigger at EXACTLY the approach column's resting row -> zero remaining fall
                # -> DRDISTGATE clamps the lateral move to nothing -> the capsule STRANDS in the
                # approach column. Measured 4/4 on engaged pills.
                #
                # Refuse an approach whose remaining fall cannot pay for the lateral trip:
                #     free rows strictly below the trigger, in the FINAL column
                #         >=  |approach - final| + 2
                # One row per column of travel is the DAS-free lower bound; +2 is the margin every
                # one of the 23 completions had. A veto sets TUCK_C2 <- $FF, which the executor
                # already reads as "no tuck" and steers straight to the final column -- i.e. the
                # exact pre-tuck behaviour, so a veto can never be worse than not tucking.
                #
                # Makes ANY descriptor stream safe (v1, v3, or a future firmware whose selection
                # we do not control) -- strictly more robust than fixing selection in firmware.
                # Straight-line, ZERO _sel calls (the executor adds no bank traffic and that
                # property must survive), one bounded 16-row loop, one indexed READ.
                a.ins16("LDA_abs", TUCK_C2); a.ins("CMP_imm", 0xFF); a.br("BEQ", "tg_ok")
                a.ins16("LDA_abs", TUCK_C2); a.ins("SEC"); a.ins16("SBC_abs", tgt_c)
                a.br("BCS", "tg_abs")
                a.ins("EOR_imm", 0xFF); a.ins("CLC"); a.ins("ADC_imm", 1)
                a.label("tg_abs")
                a.ins("CLC"); a.ins("ADC_imm", 2); a.ins16("STA_abs", TG_NEED)
                a.ins("LDA_imm", 15); a.ins("SEC"); a.ins16("SBC_abs", TUCK_R2)
                a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
                a.ins("CLC"); a.ins16("ADC_abs", tgt_c); a.ins16("STA_abs", TG_OFF)
                a.ins("LDY_imm", 0)
                a.label("tg_lp")
                a.ins16("LDA_abs", TG_OFF); a.ins("CLC"); a.ins("ADC_imm", 8)
                a.ins16("STA_abs", TG_OFF)
                a.ins("CMP_imm", 128); a.br("BCS", "tg_done")      # past the floor
                a.ins("TAX"); a.ins16("LDA_absX", 0x0500)
                a.br("BEQ", "tg_free")                             # $00 = empty
                a.ins("CMP_imm", 0xFF); a.br("BNE", "tg_done")     # occupied -> stop
                a.label("tg_free")
                a.ins("INY"); a.jmp("tg_lp")
                a.label("tg_done")
                # no CPY_abs in this assembler's table -- move the count into A and CMP.
                a.ins("TYA"); a.ins16("CMP_abs", TG_NEED); a.br("BCS", "tg_ok")
                a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", TUCK_C2)   # VETO -> straight to final
                a.label("tg_ok")
        a.ins16("LDA_abs", wor); a.ins("CMP_imm", 0xFF); a.br("BNE", f"{L}_map")
        a.ins("LDA_imm", 3); a.jmp(f"{L}_pst")
        a.label(f"{L}_map")
        a.ins("CMP_imm", 0); a.br("BNE", f"{L}_m1"); a.ins("LDA_imm", 3); a.jmp(f"{L}_pst")
        a.label(f"{L}_m1"); a.ins("CMP_imm", 1); a.br("BNE", f"{L}_m2"); a.ins("LDA_imm", 1); a.jmp(f"{L}_pst")
        a.label(f"{L}_m2"); a.ins("CMP_imm", 2); a.br("BNE", f"{L}_m3"); a.ins("LDA_imm", 0); a.jmp(f"{L}_pst")
        a.label(f"{L}_m3"); a.ins("LDA_imm", 2)
        a.label(f"{L}_pst"); a.ins16("STA_abs", tgt_o)
        if idx == 2 and RECOMMIT:
            # CONVERGED-ORIENT RECOMMIT (see DRRECOMMIT): converged orient is now in tgt_o. If the orient
            # was latched early to a shallow running argmax AND the capsule is still high enough to rotate
            # safely, re-open the latch so act_p2 rotates once to the converged orient. Too-low => keep the
            # committed orient (the no-backwards-lock invariant). Slow copro => DONE below the line => no-op.
            a.ins16("LDA_abs", ROT_DONE2); a.br("BEQ", f"{L}_rcdone")     # not latched -> nothing to redo
            a.ins16("LDA_abs", 0x0386); a.ins("CMP_imm", CROSS_LOWY); a.br("BCC", f"{L}_rcdone")  # low->keep
            a.ins16("LDA_abs", tgt_o); a.ins16("CMP_abs", 0x03A5); a.br("BEQ", f"{L}_rcdone")     # already ok
            a.ins("LDA_imm", 0); a.ins16("STA_abs", ROT_DONE2)           # re-open -> act_p2 re-rotates
            a.label(f"{L}_rcdone")
        if MATURE and idx == 2:
            # MATURITY GATE: capture this search's latency (WDOGH2 high byte) BEFORE it is zeroed below,
            # and arm the slam iff the search was FAST (< FAST_HI*256 hooks) -- a fast DONE means its
            # stable argmax is the converged answer; a slow one is a not-yet-refined intermediate.
            a.ins16("LDA_abs", wdogh); a.ins16("STA_abs", LAST_LAT)
            a.ins("CMP_imm", FAST_HI); a.br("BCS", "mat_slow")     # WDOGH2 >= FAST_HI -> slow -> disarm
            a.ins("LDA_imm", 1); a.ins16("STA_abs", SLAM_ARM); a.jmp("mat_done")
            a.label("mat_slow"); a.ins("LDA_imm", 0); a.ins16("STA_abs", SLAM_ARM)
            a.label("mat_done")
        a.label(f"{L}_badcol")   # rejected column lands here: teardown WITHOUT adopting the result
        a.ins("LDA_imm", 0); a.ins16("STA_abs", armed); a.ins16("STA_abs", wdog); a.ins16("STA_abs", wdogh)
        a.jmp(f"{L}_done")
        a.label(f"{L}_search")           # 16-bit watchdog: d3 searches take seconds; abandon ~30s, re-queue once
        a.ins16("INC_abs", wdog); a.br("BNE", f"{L}_wl"); a.ins16("INC_abs", wdogh)
        a.label(f"{L}_wl")
        a.ins16("LDA_abs", wdogh); a.ins("CMP_imm", WDOG_HI_LIM); a.br("BCS", f"{L}_wto"); a.jmp(f"{L}_done"); a.label(f"{L}_wto")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", armed); a.ins16("STA_abs", wdog); a.ins16("STA_abs", wdogh)
        if MATURE and idx == 2:
            a.ins16("STA_abs", SLAM_ARM)                       # A==0: search timed out (slowest) -> disarm
        if PRESTART and idx == 2:
            # A==0. A timed-out prestart published nothing, so it must not go on owning the next
            # spawn -- otherwise the spawn edge would skip PEND2 and the capsule would steer to
            # the PREVIOUS pill's target. (The ~4-minute timeout cannot fire inside a <=264-frame
            # garbage window, so this is insurance against the retry path, not a live case.)
            a.ins16("STA_abs", PRE_ACT2)
        a.ins16("LDA_abs", wretry); a.br("BEQ", f"{L}_rt"); a.jmp(f"{L}_done"); a.label(f"{L}_rt")
        a.ins("LDA_imm", 1); a.ins16("STA_abs", wretry); a.ins16("STA_abs", pend)
        a.jmp(f"{L}_done")
        a.label(f"{L}_start")            # start a search: upload board+colors to THIS copro, GO
        a.ins16("LDA_abs", pend); a.br("BNE", f"{L}_st1"); a.jmp(f"{L}_done"); a.label(f"{L}_st1")
        a.ins16("LDA_abs", delay); a.br("BEQ", f"{L}_st2"); a.jmp(f"{L}_done"); a.label(f"{L}_st2")
        if TUCK and idx == 2:
            # D2 FIX: invalidate only when a search ACTUALLY starts (pend/delay checks above
            # already passed). Emitted BEFORE those checks, this ran on EVERY frame with
            # armed==0 -- the whole descent, including the frame immediately after the
            # descriptor was published -- so the executor read 0xFF and never steered
            # (dr-mario-tuck-executor-gap D2; matches QA/fpga/copro/tuck_validation/
            # d2_invalidation_fix.patch, applied here as-is). PROVEN by differential: the
            # SAME test with THIS code reverted to the old placement fails "1 of 40 frames"
            # (the documented signature) -- see commit message.
            a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", TUCK_C2)
        a.ins("LDX_imm", 0)
        # NES playfield empties are 0xFF *or* 0x00 (per tile-encoding); the copro parser only
        # treats 0xFF as empty, so a 0x00 cell reads as a PHANTOM yellow pill -> the color-heavy
        # depth-3 endgame eval corrupts once mid-game clears create 0x00 cells (walls at ~20;
        # sim never sees it -- faithful_to_nes always emits 0xFF). Normalize 0x00 -> 0xFF here.
        a.label(f"{L}_cp")
        a.ins16("LDA_absX", board_src); a.br("BNE", f"{L}_cpnz")   # non-zero -> store as-is
        a.ins("LDA_imm", 0xFF)                                      # 0x00 -> empty
        a.label(f"{L}_cpnz")
        a.ins16("STA_absX", wbase)
        a.ins("INX"); a.ins("CPX_imm", 128); a.br("BNE", f"{L}_cp")
        for k, src in enumerate(colsrcs):
            if k == 0:      # cA carries seed low nibble (<<4)
                a.ins16("LDA_abs", seedsrc)
                a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
                a.ins16("STA_abs", TMPSEED)
                a.ins16("LDA_abs", src); a.ins("AND_imm", 0x0F); a.ins16("ORA_abs", TMPSEED)
            elif k == 1:    # cB carries seed high nibble
                a.ins16("LDA_abs", seedsrc); a.ins("AND_imm", 0xF0); a.ins16("STA_abs", TMPSEED)
                a.ins16("LDA_abs", src); a.ins("AND_imm", 0x0F); a.ins16("ORA_abs", TMPSEED)
            else:
                a.ins16("LDA_abs", src); a.ins("AND_imm", 0x0F)
            a.ins16("STA_abs", wbase + 0x80 + k)
        a.ins16("STA_abs", wgo)          # GO: write to +$84 pulses copro reset, clears DONE
        a.ins("LDA_imm", 1); a.ins16("STA_abs", armed)
        a.ins("LDA_imm", 0); a.ins16("STA_abs", pend)
        if not WRETRY_FIX:
            a.ins16("STA_abs", wretry)                      # FIX(A): dropping this keeps the re-queue-once latch
        a.ins16("STA_abs", wdog); a.ins16("STA_abs", wdogh)
        a.label(f"{L}_done")
    if not HUMAN_P1 and not P1NATIVE:
        # (DRP1NATIVE drops P1's copro search entirely -- see the flag note: on the deployed
        #  core $5000 is undecoded, so this only ever published open-bus garbage.)
        handle(1, 0x5000, 0x0400, [0x0301, 0x0302, 0x031A, 0x031B], ARMED, WDOG, WRETRY, PEND1, DELAY1, TGT_C1, TGT_O1, WDOGH1, SEED1)
    handle(2, W2_BASE, 0x0500, [0x0381, 0x0382, 0x039A, 0x039B], ARMED2, WDOG2, WRETRY2, PEND2, DELAY2, TGT_C2, TGT_O2, WDOGH2, SEED2)
    a.jmp("act")

    # freeze QUEUED players too: a pill whose search hasn't run yet must not fall unguided
    # (time-sharing wait was letting pills drop 2-4 rows before their target arrived ->
    # unreachable columns -> bad placements). Called from act below.
    a.label("freeze_pending")
    if not HUMAN_P1 and not P1_OWNED:
        # (DRP1WIGGLE / DRP1NATIVE builds also skip it: both own P1's descent outright, so a
        #  search-driven gravity pin would freeze the capsule mid-slide -- and neither reads
        #  P1's copro target, so there is nothing to wait for. Under DRP1NATIVE handle(1) is
        #  not even emitted, which would leave PEND1 latched at 1 forever -> a permanent pin.)
        # (DRHUMAN builds MUST skip this: handle(1) never runs, so PEND1 is uninitialized
        #  boot garbage — nonzero garbage pinned P1's gravity forever = capsule stuck at top,
        #  observed on Pocket hardware 2026-07-18.)
        a.ins16("LDA_abs", PEND1); a.br("BEQ", "fp_p2")
        if PENDBOUND:
            a.ins16("LDA_abs", DELAY1); a.br("BEQ", "fp_p2")   # settle window closed -> no pin
        a.ins("LDA_imm", 0); a.ins16("STA_abs", GRAV_P1)
    a.label("fp_p2")
    a.ins16("LDA_abs", PEND2); a.br("BEQ", "fp_done")
    if PENDBOUND:
        a.ins16("LDA_abs", DELAY2); a.br("BEQ", "fp_done")     # settle window closed -> no pin
    a.ins("LDA_imm", 0); a.ins16("STA_abs", GRAV_P2)
    a.label("fp_done")
    a.ins("RTS")

    if PRESTART:
        # ================= DRPRESTART: garbage-window prestart (P2) =================
        # Emitted here because everything past `jmp("act")` above is reachable only by JSR.
        # See the DRPRESTART flag comment for the trigger derivation, the settle invariant,
        # the one-step-ahead colour sourcing, and the bail list.

        # ---- pre_run: 4-in-a-row scanner along one axis -----------------------------------
        # in : PRE_MC = colour (0..2), PRE_MIN = first offset, PRE_MAX = last offset (inclusive),
        #      PRE_TMP = step (1 = along a row, 8 = down a column)
        # out: PRE_MC = $FF iff a run of 4 was found (sentinel doubles as the return flag, so the
        #      caller needs no extra byte and the routine can bail out of its own loop early).
        # A cell participates iff its LOW nibble equals the colour -- viruses ($D0|c) and every
        # pill-half type ($40..$A0 | c) all match on colour exactly as the game's own scan does,
        # and $FF (empty) is excluded for free because its low nibble is $F, never 0..2.
        a.label("pre_run")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", PRE_RUN)
        a.ins16("LDA_abs", PRE_MIN); a.ins16("STA_abs", PRE_SOFF)
        a.label("pr_l")
        a.ins16("LDX_abs", PRE_SOFF)
        a.ins16("LDA_absX", PRE_BUF); a.ins("AND_imm", 0x0F)
        a.ins16("CMP_abs", PRE_MC); a.br("BNE", "pr_rst")
        a.ins16("INC_abs", PRE_RUN)
        a.ins16("LDA_abs", PRE_RUN); a.ins("CMP_imm", 4); a.br("BCC", "pr_nx")
        a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", PRE_MC); a.ins("RTS")
        a.label("pr_rst")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", PRE_RUN)
        a.label("pr_nx")
        a.ins16("LDA_abs", PRE_SOFF); a.ins16("CMP_abs", PRE_MAX); a.br("BEQ", "pr_end")
        a.ins("CLC"); a.ins16("ADC_abs", PRE_TMP); a.ins16("STA_abs", PRE_SOFF)
        a.jmp("pr_l")
        a.label("pr_end")
        a.ins("RTS")

        # ---- pre_tick: called once per play hook ------------------------------------------
        a.label("pre_tick")
        a.ins16("LDA_abs", PRE_ATK2); a.ins16("STA_abs", PRE_CUR)
        a.ins16("LDA_abs", PRE_LAST2); a.ins16("STA_abs", PRE_PREV)
        a.ins16("LDA_abs", PRE_CUR); a.ins16("STA_abs", PRE_LAST2)   # latch for the next hook
        if PRESPIPE:
            # Pipeline active -> the whole idle/edge path is skipped this hook; the latch above
            # still ran, so pp_disp's abort checks see a FRESH PRE_CUR. (census scenario handles:
            # 'into pp_disp' isolates the edge hook; 'into ppd_skip' forces a phase hook.)
            a.ins16("LDA_abs", PP_PH); a.br("BEQ", "ppd_skip")
            a.jmp("pp_disp")
            a.label("ppd_skip")
        a.ins16("LDA_abs", PRE_CUR); a.br("BEQ", "pt_zero")
        a.ins("RTS")                                    # still buffered: not released yet
        a.label("pt_zero")
        a.ins16("LDA_abs", PRE_PREV); a.br("BNE", "pt_edge")
        a.ins("RTS")                                    # was already 0: no edge
        a.label("pt_edge")
        # --- RELEASE EDGE: every garbage byte is already in $0500 row 0 (the size clear is the
        #     LAST write checkReleaseAttack performs, so this observation cannot be torn).
        if PRESPIPE:
            # Post-abort teardown parity: an abort that saw a SECOND volley buffered set
            # PP_SWAL; consume that volley's edge here exactly as the synchronous teardown
            # would have (it would have found PRE_ACT2 still set and started nothing).
            a.ins16("LDA_abs", PP_SWAL); a.br("BEQ", "pp_nsw")
            a.ins("LDA_imm", 0); a.ins16("STA_abs", PP_SWAL)
            a.ins("RTS")
            a.label("pp_nsw")
        a.ins16("LDA_abs", PRE_ACT2); a.br("BEQ", "pt_try")
        # SECOND VOLLEY before the spawn: the projection we already searched is stale. Tear the
        # in-flight prestart down -- with ARMED2 cleared, handle(2) routes to `_start` and never
        # reads the copro's (now meaningless) DONE, and the next real GO resets the copro anyway.
        # The spawn edge then behaves exactly as it does today.
        a.ins("LDA_imm", 0)
        a.ins16("STA_abs", PRE_ACT2); a.ins16("STA_abs", ARMED2)
        a.ins16("STA_abs", WDOG2); a.ins16("STA_abs", WDOGH2)
        a.ins("RTS")
        a.label("pt_try")
        a.ins16("LDA_abs", ARMED2); a.br("BEQ", "pt_g1")
        a.ins("RTS")                                    # a search is already running -> never re-GO
        a.label("pt_g1")
        a.ins16("LDA_abs", PEND2); a.br("BEQ", "pt_g2")
        a.ins("RTS")                                    # a search is already queued -> leave it
        a.label("pt_g2")

        # ---- copy $0500 -> PRE_BUF, normalising $00 -> $FF (same reason as _start's loop:
        #      the copro parser treats only $FF as empty and a $00 cell reads as a phantom pill)
        a.ins("LDX_imm", 0)
        a.label("pt_cp")
        a.ins16("LDA_absX", 0x0500); a.br("BNE", "pt_cpnz")
        a.ins("LDA_imm", 0xFF)
        a.label("pt_cpnz")
        a.ins16("STA_absX", PRE_BUF)
        a.ins("INX"); a.ins("CPX_imm", 128); a.br("BNE", "pt_cp")
        if PRESPIPE:
            # Edge hook ends with the snapshot taken; the orphan guard opens phase 1 next hook.
            a.ins("LDA_imm", 1); a.ins16("STA_abs", PP_PH)
            a.ins("RTS")
            a.label("pp_ph1")

        # ---- orphan guard (MUST run as a separate pass, before anything moves) --------------
        # checkReleaseAttack writes row 0 with a plain `sta` and no occupancy test, so a volley
        # can DESTROY one half of a capsule locked at the top and leave its partner pointing at a
        # cell that is now a garbage single. That state is outside both models: the faithful sim's
        # `_bodies()` follows the link non-reciprocally and glues the orphan to the GARBAGE, then
        # drops the two as a rigid pair (its own comment calls the case "shouldn't happen" -- the
        # unconditional row-0 write is exactly what makes it happen); the ROM's `checkDrop` instead
        # walks LEFT from a rightHalfPill looking for a leftHalfPill and, once the neighbour has
        # itself fallen away, keeps walking off the end of the row. Measured 15/200 divergences,
        # 100% of them this case and nothing else. Neither model is trustworthy here, so we BAIL --
        # and we bail on ALL of them, including the ~40/200 where the two happen to agree, because
        # agreeing by luck is not a reason to trust a projection.
        a.ins("LDA_imm", 0); a.ins16("STA_abs", PRE_COL)
        a.label("pt_og")
        a.ins16("LDX_abs", PRE_COL)
        a.ins16("LDA_absX", PRE_BUF); a.ins("CMP_imm", 0xFF); a.br("BEQ", "pt_og_r1")
        a.ins("AND_imm", 0xF0)
        a.ins("CMP_imm", 0x60); a.br("BNE", "pt_og_n60")      # leftHalf: rightHalf must be at c+1
        a.ins16("LDA_abs", PRE_COL); a.ins("CMP_imm", 7); a.br("BEQ", "pt_og_bail")
        a.ins16("LDX_abs", PRE_COL); a.ins("INX")
        a.ins16("LDA_absX", PRE_BUF); a.ins("AND_imm", 0xF0)
        a.ins("CMP_imm", 0x70); a.br("BNE", "pt_og_bail")
        a.jmp("pt_og_r1")
        a.label("pt_og_n60")
        a.ins("CMP_imm", 0x70); a.br("BNE", "pt_og_n70")      # rightHalf: leftHalf must be at c-1
        a.ins16("LDA_abs", PRE_COL); a.br("BEQ", "pt_og_bail")
        a.ins16("LDX_abs", PRE_COL); a.ins("DEX")
        a.ins16("LDA_absX", PRE_BUF); a.ins("AND_imm", 0xF0)
        a.ins("CMP_imm", 0x60); a.br("BNE", "pt_og_bail")
        a.jmp("pt_og_r1")
        a.label("pt_og_n70")
        a.ins("CMP_imm", 0x40); a.br("BNE", "pt_og_n40")      # topHalf: bottomHalf must be below
        a.ins16("LDA_abs", PRE_COL); a.ins("CLC"); a.ins("ADC_imm", 8); a.ins("TAX")
        a.ins16("LDA_absX", PRE_BUF); a.ins("AND_imm", 0xF0)
        a.ins("CMP_imm", 0x50); a.br("BNE", "pt_og_bail")
        a.jmp("pt_og_r1")
        a.label("pt_og_n40")
        a.ins("CMP_imm", 0x50); a.br("BEQ", "pt_og_bail")     # bottomHalf at row 0: partner off-board
        a.ins("CMP_imm", 0x90); a.br("BEQ", "pt_og_bail")     # middleVer/middleHor: 3+ cell capsules
        a.ins("CMP_imm", 0xA0); a.br("BEQ", "pt_og_bail")     # are outside this projection's model
        a.label("pt_og_r1")
        # row 1: a bottomHalf here is the other way the same overwrite shows up (a VERTICAL
        # capsule occupying rows 0-1 whose top half was the cell the volley landed on).
        a.ins16("LDA_abs", PRE_COL); a.ins("CLC"); a.ins("ADC_imm", 8); a.ins("TAX")
        a.ins16("LDA_absX", PRE_BUF); a.ins("AND_imm", 0xF0)
        a.ins("CMP_imm", 0x50); a.br("BNE", "pt_og_nx")
        a.ins16("LDX_abs", PRE_COL)
        a.ins16("LDA_absX", PRE_BUF); a.ins("AND_imm", 0xF0)
        a.ins("CMP_imm", 0x40); a.br("BEQ", "pt_og_nx")
        a.label("pt_og_bail")
        a.jmp("pt_bail")
        a.label("pt_og_nx")
        a.ins16("INC_abs", PRE_COL)
        a.ins16("LDA_abs", PRE_COL); a.ins("CMP_imm", 8); a.br("BEQ", "pt_settle")
        a.jmp("pt_og")
        a.label("pt_settle")

        # ---- settle: slide every row-0 singleHalfPill down onto the stack -------------------
        a.ins("LDA_imm", 0); a.ins16("STA_abs", PRE_N); a.ins16("STA_abs", PRE_COL)
        a.label("pt_col")
        a.ins16("LDX_abs", PRE_COL)
        a.ins16("LDA_absX", PRE_BUF); a.ins("CMP_imm", 0xFF); a.br("BEQ", "pt_ncol")
        a.ins16("STA_abs", PRE_CELL)
        a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0x80); a.br("BEQ", "pt_drop")
        a.jmp("pt_ncol")            # linked half / virus: already settled, and never garbage
        a.label("pt_drop")
        a.ins("TXA"); a.ins16("STA_abs", PRE_OFF)       # landing offset, starts at row 0
        a.label("pt_dn")
        a.ins16("LDA_abs", PRE_OFF); a.ins("CLC"); a.ins("ADC_imm", 8)
        a.ins("CMP_imm", 128); a.br("BCS", "pt_land")   # next row is off the floor -> rest here
        a.ins("TAX")
        a.ins16("LDA_absX", PRE_BUF); a.ins("CMP_imm", 0xFF); a.br("BEQ", "pt_fall")
        # occupied -- but first reject the two MID-ANIMATION tile types. $FF was peeled off above,
        # which matters: $FF & $F0 == $F0 would otherwise trip the just-emptied test on every
        # empty cell.
        a.ins("AND_imm", 0xF0)                          # (invert-and-JMP: pt_bail is out of branch range)
        a.ins("CMP_imm", 0xB0); a.br("BNE", "pt_nb0")   # clearedPillOrVirus: clear still animating
        a.jmp("pt_bail")
        a.label("pt_nb0")
        a.ins("CMP_imm", 0xF0); a.br("BNE", "pt_nf0")   # fieldPosJustEmptied: ditto
        a.jmp("pt_bail")
        a.label("pt_nf0")
        a.jmp("pt_land")
        a.label("pt_fall")
        a.ins("TXA"); a.ins16("STA_abs", PRE_OFF)
        a.jmp("pt_dn")
        a.label("pt_land")
        a.ins16("LDA_abs", PRE_OFF); a.ins16("CMP_abs", PRE_COL); a.br("BEQ", "pt_rec")
        a.ins16("LDX_abs", PRE_COL); a.ins("LDA_imm", 0xFF); a.ins16("STA_absX", PRE_BUF)
        a.ins16("LDX_abs", PRE_OFF); a.ins16("LDA_abs", PRE_CELL); a.ins16("STA_absX", PRE_BUF)
        a.label("pt_rec")
        # Record it even when it did not move: a column already full to row 0 leaves the garbage
        # AT row 0, and that cell still has to pass the match check.
        a.ins16("LDX_abs", PRE_N)
        a.ins16("LDA_abs", PRE_OFF); a.ins16("STA_absX", PRE_LND)
        a.ins16("INC_abs", PRE_N)
        a.label("pt_ncol")
        a.ins16("INC_abs", PRE_COL)
        a.ins16("LDA_abs", PRE_COL); a.ins("CMP_imm", 8)
        a.br("BEQ", "pp_s_done" if PRESPIPE else "pt_match")
        a.jmp("pt_col")
        if PRESPIPE:
            # Phase 1 ends: seed the resumable match index (the synchronous path zeroes it at
            # pt_match's head; here it must survive the hook boundary in PRG-RAM).
            a.label("pp_s_done")
            a.ins("LDA_imm", 0); a.ins16("STA_abs", PRE_I)
            a.ins("LDA_imm", 2); a.ins16("STA_abs", PP_PH)
            a.ins("RTS")

        # ---- match check: bail if any settled cell completes a 4-run ------------------------
        # Cascades are explicitly NOT resolved in 6502; a match means the board the game will
        # actually spawn onto is not the board we projected, so we hand the pill back to the
        # ordinary spawn-edge path.
        # ONE SOURCE OF TRUTH for the per-record computation: both arms emit these bytes from
        # the same helper, so the pipelined arm cannot drift from the synchronous one by a
        # hand transcription (rule 11: the input a fix depends on must not be re-typed).
        # Only the CONTROL FLOW around it differs -- the synchronous arm jumps straight to
        # pt_bail on a 4-run, the pipelined arm returns with PRE_MC == $FF for its driver.
        def emit_pre_record(lbl_col, on_match):
            a.ins16("LDX_abs", PRE_I)
            a.ins16("LDA_absX", PRE_LND); a.ins16("STA_abs", PRE_OFF)
            a.ins16("LDX_abs", PRE_OFF)
            a.ins16("LDA_absX", PRE_BUF); a.ins("AND_imm", 0x0F); a.ins16("STA_abs", PRE_MC)
            a.ins16("LDA_abs", PRE_OFF); a.ins("AND_imm", 0xF8); a.ins16("STA_abs", PRE_MIN)  # row scan
            a.ins("CLC"); a.ins("ADC_imm", 7); a.ins16("STA_abs", PRE_MAX)
            a.ins("LDA_imm", 1); a.ins16("STA_abs", PRE_TMP)
            a.jsr("pre_run")
            # A row match leaves PRE_MC == $FF, which is NOT a colour: the column scan must not
            # be entered with it as pre_run's input, so the early-out is load-bearing in both arms.
            a.ins16("LDA_abs", PRE_MC); a.ins("CMP_imm", 0xFF); a.br("BNE", lbl_col)
            on_match()
            a.label(lbl_col)
            a.ins16("LDA_abs", PRE_OFF); a.ins("AND_imm", 0x07); a.ins16("STA_abs", PRE_MIN)  # col scan
            a.ins("CLC"); a.ins("ADC_imm", 120); a.ins16("STA_abs", PRE_MAX)
            a.ins("LDA_imm", 8); a.ins16("STA_abs", PRE_TMP)
            a.jsr("pre_run")

        if not PRESPIPE:
            a.label("pt_match")
            a.ins("LDA_imm", 0); a.ins16("STA_abs", PRE_I)
            a.label("pt_mchk")
            a.ins16("LDA_abs", PRE_I); a.ins16("CMP_abs", PRE_N); a.br("BCC", "pt_mgo")
            a.jmp("pt_commit")
            a.label("pt_mgo")
            emit_pre_record("pt_mv", lambda: a.jmp("pt_bail"))
            a.ins16("LDA_abs", PRE_MC); a.ins("CMP_imm", 0xFF); a.br("BNE", "pt_mnx")
            a.jmp("pt_bail")
            a.label("pt_mnx")
            a.ins16("INC_abs", PRE_I)
            a.jmp("pt_mchk")
        else:
            # ---- pipelined match scan: one record subroutine, quota-bounded drivers ---------
            # PRESPIPE_Q records per match phase. The pair -- not the phase -- is the real
            # constraint (two hooks run per NMI), and the TOTAL work is fixed, so the worst
            # adjacent pair shrinks only by adding phases, never by rebalancing between two:
            #   Q=3 (DEFAULT) -> 4 hooks (2.0 frames), margin 4,926
            #   Q=4 -> 3 hooks (1.5 frames), the spec's original budget, margin 1,154
            # The quota is on the INDEX, not on PRE_N, so the pipeline is a FIXED number of
            # hooks whatever PRE_N is -- a latency the gate asserts exactly.
            a.label("pp_rec")
            emit_pre_record("pp_rcol", lambda: a.ins("RTS"))   # PRE_MC == $FF: caller bails
            a.ins("RTS")

            def match_driver(head, quota, done):
                a.label(head)
                if quota is not None:
                    a.ins16("LDA_abs", PRE_I); a.ins("CMP_imm", quota); a.br("BCS", done)
                a.ins16("LDA_abs", PRE_I); a.ins16("CMP_abs", PRE_N); a.br("BCS", done)
                a.jsr("pp_rec")
                a.ins16("LDA_abs", PRE_MC); a.ins("CMP_imm", 0xFF); a.br("BNE", f"{head}_nx")
                a.jmp("pt_bail")                                # 4-run: hand the pill back
                a.label(f"{head}_nx")
                a.ins16("INC_abs", PRE_I)
                a.jmp(head)

            # Phases 2..(1+PP_NM) are the match phases; the last one falls into commit.
            # (No separate phase label on a driver head: a head carrying two labels makes the
            # census bound key depend on emission order -- the driver head IS the entry.)
            for k in range(PP_NM):
                ph = 2 + k
                last = (k == PP_NM - 1)
                quota = None if last else (k + 1) * PRESPIPE_Q
                match_driver(f"pp_m{ph}", quota, f"pp_m{ph}_done")
                a.label(f"pp_m{ph}_done")
                if last:
                    a.jmp("pt_commit")
                else:
                    a.ins("LDA_imm", ph + 1); a.ins16("STA_abs", PP_PH)
                    a.ins("RTS")

        # ---- commit: upload the projection, fill the mailbox, GO ----------------------------
        a.label("pt_commit")
        a.ins("LDX_imm", 0)
        a.label("pt_up")
        a.ins16("LDA_absX", PRE_BUF); a.ins16("STA_absX", W2_BASE)
        a.ins("INX"); a.ins("CPX_imm", 128); a.br("BNE", "pt_up")
        # cA/cB = the PREVIEW ($039A/$039B) -- the capsule that will actually spawn, since
        # generateNextPill has not run yet -- carrying the tie-break seed nibbles exactly as
        # handle()'s colour loop does.
        a.ins16("LDA_abs", SEED2)
        a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
        a.ins16("STA_abs", TMPSEED)
        a.ins16("LDA_abs", 0x039A); a.ins("AND_imm", 0x0F); a.ins16("ORA_abs", TMPSEED)
        a.ins16("STA_abs", W2_BASE + 0x80)
        a.ins16("LDA_abs", SEED2); a.ins("AND_imm", 0xF0); a.ins16("STA_abs", TMPSEED)
        a.ins16("LDA_abs", 0x039B); a.ins("AND_imm", 0x0F); a.ins16("ORA_abs", TMPSEED)
        a.ins16("STA_abs", W2_BASE + 0x81)
        # nA/nB = colorCombination_{left,right}[pillsReserve[p2_pillsCounter]] = (val/3, val%3).
        # The reserve is 128 bytes of plain RAM at $0780 and the counter has NOT been incremented
        # for the upcoming spawn, so this is the capsule after the one we are searching for. The
        # tables live in a ROM bank the driver does not map, hence the 3-iteration divide (reserve
        # values are 0..8 by construction: generatePillsReserve reduces mod 9).
        a.ins16("LDX_abs", 0x03A7)
        a.ins16("LDA_absX", 0x0780)
        a.ins("LDX_imm", 0)
        a.label("pt_dv")
        a.ins("CMP_imm", 3); a.br("BCC", "pt_dvd")
        a.ins("SEC"); a.ins("SBC_imm", 3); a.ins("INX")
        a.jmp("pt_dv")
        a.label("pt_dvd")
        a.ins16("STA_abs", PRE_TMP)                                   # remainder = nB
        a.ins("TXA"); a.ins("AND_imm", 0x0F); a.ins16("STA_abs", W2_BASE + 0x82)
        a.ins16("LDA_abs", PRE_TMP); a.ins("AND_imm", 0x0F); a.ins16("STA_abs", W2_BASE + 0x83)
        a.ins16("STA_abs", W2_BASE + 0x84)      # GO: any write to +$84 pulses reset + clears DONE
        a.ins("LDA_imm", 1); a.ins16("STA_abs", ARMED2); a.ins16("STA_abs", PRE_ACT2)
        a.ins("LDA_imm", 0)
        a.ins16("STA_abs", PEND2); a.ins16("STA_abs", WDOG2); a.ins16("STA_abs", WDOGH2)
        # WRETRY2 is deliberately left alone: it is a once-per-PILL latch and this search belongs
        # to a pill that has not spawned yet (same reasoning as WRETRY_FIX's dropped clear).
        a.label("pt_bail")
        if PRESPIPE:
            # THE single pipeline exit. Every terminal path -- commit (falls through from
            # above), 4-run bail, orphan bail, mid-animation bail, and pp_abort -- passes
            # here, so clearing the phase in one place is what makes "no path leaves the
            # machine armed" checkable by inspection rather than by enumeration.
            a.ins("LDA_imm", 0); a.ins16("STA_abs", PP_PH)
        a.ins("RTS")

    if PRESTART and PRESPIPE:
        # ---- pipeline dispatcher: runs INSTEAD of the idle/edge path while PP_PH != 0 ------
        a.label("pp_disp")
        # ABORT CHECKS, re-evaluated at EVERY phase entry (the world moves between hooks):
        # (1) a second volley is buffered -> the projection under construction is stale.
        #     Swallow that volley's own release edge as well, because the synchronous path
        #     reaching it would have found PRE_ACT2 set (its commit already done) and torn
        #     down without starting anything -- so ship also gets no search for volley 2.
        a.ins16("LDA_abs", PRE_CUR); a.br("BEQ", "pp_d1")
        a.ins("LDA_imm", 1); a.ins16("STA_abs", PP_SWAL)
        a.jmp("pt_bail")
        a.label("pp_d1")
        # (2) the P2 lock edge fired (spawn imminent) or a search is already running: the
        #     ordinary spawn-edge path owns this capsule now.
        a.ins16("LDA_abs", PEND2); a.br("BEQ", "pp_d2")
        a.jmp("pt_bail")
        a.label("pp_d2")
        a.ins16("LDA_abs", ARMED2); a.br("BEQ", "pp_d3")
        a.jmp("pt_bail")
        a.label("pp_d3")
        a.ins16("LDA_abs", PP_PH)
        for ph in range(1, 2 + PP_NM):
            a.ins("CMP_imm", ph); a.br("BNE", f"pp_d3_{ph}")
            a.jmp("pp_ph1" if ph == 1 else f"pp_m{ph}")
            a.label(f"pp_d3_{ph}")
        a.jmp("pt_bail")                        # out-of-range phase byte: disarm, never dispatch

    if P1NATIVE and P1SLICE:
        # ================= DRP1SLICE: the sliced P1 search (JSR-only zone) =================
        # One TICK = restore cross-step state from PRG-RAM into the v18 AI's zp scratch,
        # run TWO column-steps, save the state back. The zp bytes are the game's between
        # NMIs, so nothing cross-step may live there (tests/test_p1slice.py clobbers them
        # between ticks to prove it). Step bodies are VERBATIM transcriptions of the v18
        # v_loop / h_loop iteration bodies (patch_vs_cpu.build_v18_ai); the swap step tail-
        # calls the existing swap_eval and publishes.
        _p1lab = build_p1_native()[1]
        _LAND, _EVAL = _p1lab["land_col"], _p1lab["eval_pair"]
        a.label("p1s_tick")
        a.ins16("LDA_abs", SL_BEST); a.ins("STA_zp", 0x01)     # Z_BEST
        a.ins16("LDA_abs", SL_TGT); a.ins("STA_zp", 0x00)      # Z_TARGET
        a.ins16("LDA_abs", SL_ORI); a.ins("STA_zp", 0xDA)      # Z_BORIENT
        a.ins16("LDA_abs", SL_OFA); a.ins("STA_zp", 0xD0)      # best OFFA (swap input)
        a.ins16("LDA_abs", SL_OFB); a.ins("STA_zp", 0xD1)      # best OFFB
        a.ins16("LDA_abs", SL_COL); a.ins("STA_zp", 0x6B)      # Z_COL
        a.ins16("LDA_abs", 0x0301); a.ins("ORA_imm", 0x4C); a.ins("STA_zp", 0xD2)  # tiles,
        a.ins16("LDA_abs", 0x0302); a.ins("ORA_imm", 0x4C); a.ins("STA_zp", 0xD3)  # as search_entry
        a.jsr("p1s_one")
        a.ins("LDA_zp", 0x01); a.ins16("STA_abs", SL_BEST)
        a.ins("LDA_zp", 0x00); a.ins16("STA_abs", SL_TGT)
        a.ins("LDA_zp", 0xDA); a.ins16("STA_abs", SL_ORI)
        a.ins("LDA_zp", 0xD0); a.ins16("STA_abs", SL_OFA)
        a.ins("LDA_zp", 0xD1); a.ins16("STA_abs", SL_OFB)
        a.ins("LDA_zp", 0x6B); a.ins16("STA_abs", SL_COL)
        a.ins("RTS")

        a.label("p1s_one")                       # one column-step, dispatched on phase
        a.ins16("LDA_abs", SL_PH)
        a.ins("CMP_imm", 1); a.br("BEQ", "p1s_v")
        a.ins("CMP_imm", 2); a.br("BEQ", "p1s_h")
        a.ins("CMP_imm", 3); a.br("BEQ", "p1s_sw")
        a.ins("RTS")

        a.label("p1s_v")                         # == one v_loop iteration ==
        a.ins("LDX_zp", 0x6B); a.jsr(_LAND); a.br("BCS", "p1s_vnext")
        a.ins("LDA_zp", 0x6F); a.br("BEQ", "p1s_vnext")        # no room above (orig: BNE/JMP)
        a.ins("LDA_zp", 0x6E); a.ins("SEC"); a.ins("SBC_imm", 0x08); a.ins("STA_zp", 0x6D)
        a.ins("DEC_zp", 0x6F)
        a.ins("LDA_imm", 0x01); a.ins("STA_zp", 0xD9)
        a.jsr(_EVAL)
        a.label("p1s_vnext")
        a.ins("INC_zp", 0x6B); a.ins("LDA_zp", 0x6B); a.ins("CMP_imm", 0x08)
        a.br("BCC", "p1s_vret")
        a.ins("LDA_imm", 2); a.ins16("STA_abs", SL_PH)         # -> H pass
        a.ins("LDA_imm", 0); a.ins("STA_zp", 0x6B)
        a.label("p1s_vret"); a.ins("RTS")

        a.label("p1s_h")                         # == one h_loop iteration ==
        a.ins("LDX_zp", 0x6B); a.jsr(_LAND); a.br("BCS", "p1s_hnext")
        a.ins("LDA_zp", 0x6E); a.ins("STA_zp", 0x6D)
        a.ins("LDA_zp", 0x6F); a.ins("PHA")
        a.ins("INC_zp", 0x6B); a.ins("LDX_zp", 0x6B); a.jsr(_LAND); a.ins("DEC_zp", 0x6B)
        a.br("BCS", "p1s_hpull")
        a.ins("PLA"); a.ins("CMP_zp", 0x6F); a.br("BCC", "p1s_hleft")
        a.ins("LDA_zp", 0x6F)
        a.label("p1s_hleft"); a.ins("STA_zp", 0x6F)
        a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
        a.ins("CLC"); a.ins("ADC_zp", 0x6B); a.ins("STA_zp", 0x6D)
        a.ins("CLC"); a.ins("ADC_imm", 0x01); a.ins("STA_zp", 0x6E)
        a.ins("LDA_imm", 0x00); a.ins("STA_zp", 0xD9)
        a.jsr(_EVAL)
        a.jmp("p1s_hnext")
        a.label("p1s_hpull"); a.ins("PLA")
        a.label("p1s_hnext")
        a.ins("INC_zp", 0x6B); a.ins("LDA_zp", 0x6B); a.ins("CMP_imm", 0x07)
        a.br("BCC", "p1s_hret")
        a.ins("LDA_imm", 3); a.ins16("STA_abs", SL_PH)         # -> swap+publish
        a.label("p1s_hret"); a.ins("RTS")

        a.label("p1s_sw")                        # == swap re-eval + publish ==
        a.jsr(P1SWAP_CPU)                        # v18's search_done tail-call, as a JSR
        a.ins("LDA_zp", 0x00); a.ins16("STA_abs", P1AI_C)
        a.ins("LDA_zp", 0xDA); a.ins16("STA_abs", P1AI_O)
        a.ins("LDA_imm", 0); a.ins16("STA_abs", SL_PH)         # idle until the next spawn
        a.ins("RTS")

    # (time-shared d_start / start_p1 / start_p2 removed: handle() above starts each player's
    #  search on its own copro.)

    # ---- act: steer BOTH players toward their published targets ----
    a.label("act")
    a.jsr("freeze_pending")
    # P2 first (only if we're not currently freezing it)
    a.ins16("LDA_abs", ARMED2)
    if RELATCH:
        # far branch: the RELATCH block below pushes act_p2 past +-127. Invert-and-JMP, the same
        # idiom as nf2_untorn / the TUCK {L}_wdone_ok fix ("rel too far"). Gated so DRRELATCH=0
        # keeps the ORIGINAL short branch and stays byte-identical.
        a.br("BNE", "act_p2_armd"); a.jmp("act_p2"); a.label("act_p2_armd")
    else:
        a.br("BEQ", "act_p2")                              # not searching P2 -> steer it
    if NO_FREEZE or ROTFIX:
        # ANYTIME (NO_FREEZE, or ANY ROTFIX shipping cart): refresh TGT from the LIVE mailbox and keep
        # steering during the search -- NEVER pin GRAV_P2 while ARMED (the fairness rework). The legacy
        # `else` below pins GRAV_P2=0 for the WHOLE search; on the Pocket (freeze cart, 4x-slower copro)
        # a heavy R47 first-pill depth-3 search then holds the pin for seconds..minutes (WDOG=~4min) = the
        # R47 Pocket HARD-FREEZE. ROTFIX carts fall under live gravity + weave toward the running argmax
        # instead (copro live-publishes; orient=0xFF = no result yet -> nf2_hold, also no pin under ROTFIX).
        # Scratch = $616C/$616D free driver RAM (NOT zp $DB/$DC = v28cs eval scratch).
        a.ins16("LDA_abs", W2_BASE + 0x86); a.ins("CMP_imm", 0xFF); a.br("BEQ", "nf2_hold")
        a.ins16("STA_abs", 0x616C)
        a.ins16("LDA_abs", W2_BASE + 0x85); a.ins16("STA_abs", 0x616D)
        a.ins16("LDA_abs", W2_BASE + 0x86); a.ins16("CMP_abs", 0x616C)         # re-read: detect torn read
        if ROTFIX:
            a.br("BEQ", "nf2_untorn"); a.jmp("act_p1"); a.label("nf2_untorn")  # torn: keep old TGT (rel too far)
        else:
            a.br("BNE", "act_p1")                                              # torn read: keep old TGT
        # ★ SECOND SANITY GUARD, and the one that actually mattered. handle()'s guard is not
        # enough: THIS path re-reads the live mailbox every hook and writes TGT_C2 directly,
        # so on an undecoded window it re-adopted the open-bus column ($52 for the $5200
        # window) immediately after handle() had rejected it. Caught only because the gate
        # row simulates the dead window rather than trusting the guard -- the matrix reported
        # TGT_C2=82 with the handle() guard already in. A bad column here means "no usable
        # candidate", so fall through to nf2_hold: steer nothing this hook (no pin, the
        # capsule keeps falling) rather than chase noise.
        a.ins16("LDA_abs", 0x616D)
        a.ins("CMP_imm", 8); a.br("BCC", "nf2_colok")
        a.jmp("nf2_hold")
        a.label("nf2_colok")
        a.ins16("STA_abs", TGT_C2)                               # column: always refine (anytime)
        if ROTFIX:
            # FEASIBILITY-GATED retarget: refine the ORIENT only while pre-phase (orient not yet
            # committed). Once ROT_DONE2 latches, keep the committed orient so a late candidate
            # cannot rotate a low/flush capsule and lock it backwards.
            # (DRRELATCH re-routes the latched case to nf2_rl_chk below: same lock by default,
            #  but a CHANGED published orient may re-open it while still above CROSS_LOWY.)
            a.ins16("LDA_abs", ROT_DONE2); a.br("BNE", "nf2_rl_chk" if RELATCH else "nf2_col_only")
            # MAP copro orient -> game orient here, exactly as handle() does at DONE
            # ({0:3,1:1,2:0,3:2}; 0xFF already peeled off to nf2_hold). The live mailbox is
            # copro-space; storing it UNMAPPED made the orient-lock freeze a wrong-game orient,
            # so P2 placed mis-oriented and cleared ~nothing (MiSTer A/B 2026-07-19). v2era masks
            # this by rotating raw in-flight then self-correcting when handle() maps at DONE; the
            # lock commits before DONE, so the live path must map too.
            a.ins16("LDA_abs", 0x616C)
            a.ins("CMP_imm", 0); a.br("BNE", "nf2_o1"); a.ins("LDA_imm", 3); a.jmp("nf2_ost")
            a.label("nf2_o1"); a.ins("CMP_imm", 1); a.br("BNE", "nf2_o2"); a.ins("LDA_imm", 1); a.jmp("nf2_ost")
            a.label("nf2_o2"); a.ins("CMP_imm", 2); a.br("BNE", "nf2_o3"); a.ins("LDA_imm", 0); a.jmp("nf2_ost")
            a.label("nf2_o3"); a.ins("LDA_imm", 2)
            a.label("nf2_ost"); a.ins16("STA_abs", TGT_O2)
            a.label("nf2_col_only")
        else:
            a.ins16("LDA_abs", 0x616C); a.ins16("STA_abs", TGT_O2)
        a.jmp("act_p2")                                     # weave-steer toward the live target
        a.label("nf2_hold")
        # no candidate published yet. FAIRNESS: under ROTFIX the capsule keeps FALLING under
        # live gravity (no pin) -- we only WITHHOLD steering until there is a move to make.
        # DRROTFIX=0 keeps the legacy brief freeze (byte-identical to the deployed carts).
        a.ins("LDA_imm", 0)
        if not ROTFIX:
            a.ins16("STA_abs", GRAV_P2)
        a.ins("STA_zp", 0xF6); a.ins("STA_zp", 0xF8); a.jmp("act_p1")
        if RELATCH:
            # RE-LATCH-ON-CHANGE (DRRELATCH -- see the flag comment above). Reached only with
            # ROT_DONE2 latched. The COLUMN was already refined above (TGT_C2 <- $616D, the
            # untorn snapshot); decide whether the latched ORIENT may follow the flip too.
            a.label("nf2_rl_chk")
            # Safety line FIRST: below CROSS_LOWY a rotation can lock the capsule backwards, so
            # keep the committed orient unconditionally (the no-backwards-lock invariant).
            a.ins16("LDA_abs", 0x0386); a.ins("CMP_imm", CROSS_LOWY); a.br("BCS", "nf2_rl_hi")
            a.jmp("act_p2")                              # low -> keep committed orient, column-only
            a.label("nf2_rl_hi")
            # MAP copro orient -> game orient ({0:3,1:1,2:0,3:2}), same table as nf2_o*/handle();
            # 0xFF ("no result") never reaches here -- it was peeled off to nf2_hold above. The
            # comparison MUST be in game space: TGT_O2 is stored MAPPED (8d7ba75).
            a.ins16("LDA_abs", 0x616C)
            a.ins("CMP_imm", 0); a.br("BNE", "nf2_rl1"); a.ins("LDA_imm", 3); a.jmp("nf2_rlst")
            a.label("nf2_rl1"); a.ins("CMP_imm", 1); a.br("BNE", "nf2_rl2"); a.ins("LDA_imm", 1); a.jmp("nf2_rlst")
            a.label("nf2_rl2"); a.ins("CMP_imm", 2); a.br("BNE", "nf2_rl3"); a.ins("LDA_imm", 0); a.jmp("nf2_rlst")
            a.label("nf2_rl3"); a.ins("LDA_imm", 2)
            a.label("nf2_rlst"); a.ins16("CMP_abs", TGT_O2); a.br("BNE", "nf2_rl_go")
            a.jmp("act_p2")                              # published orient unchanged -> keep latch
            a.label("nf2_rl_go")
            a.ins16("STA_abs", TGT_O2)                   # adopt the POST-flip orientation ...
            a.ins("LDA_imm", 0); a.ins16("STA_abs", ROT_DONE2)   # ... re-open: act_p2 rotates,
            a.jmp("act_p2")                              # then re-latches via p2_commit's gate
    else:
        a.ins("LDA_imm", 0); a.ins16("STA_abs", GRAV_P2)       # searching P2 -> freeze + skip steer
        a.ins("STA_zp", 0xF6); a.ins("STA_zp", 0xF8); a.jmp("act_p1")
    a.label("act_p2")
    if ROTFIX:
        # SETTLE GUARD: while a new pill is PENDING (search not started, TGT still stale from the
        # previous pill) WITHHOLD steering so no stale target/orient is adopted. Gravity during
        # PEND2 is handled by freeze_pending (deployed; the ~3-frame settle sits inside the spawn
        # no-fall window) -- we do NOT pin GRAV_P2 here (fairness: no extra world-stop).
        a.ins16("LDA_abs", PEND2); a.br("BEQ", "act_p2_go")
        a.ins("LDA_imm", 0); a.ins("STA_zp", 0xF6); a.ins("STA_zp", 0xF8); a.jmp("act_p1")
        a.label("act_p2_go")
        if SLAM:
            # ARGMAX-STABILITY TRACKER (past the PEND settle guard, so no stale-target counting):
            # count hooks the published (column, MAPPED orient) has held unchanged. TGT_O2 is the
            # game-mapped orient (8d7ba75) -- compare the MAPPED value so a copro-space orient wobble
            # isn't miscounted. Reset on any change; saturate at 0xFE so K_END=0xFF means "never via
            # stability" (DONE-only). Feeds the dn_p2 confidence gate below.
            a.ins16("LDA_abs", TGT_C2); a.ins16("CMP_abs", LAST_COL2); a.br("BNE", "p2_st_chg")
            a.ins16("LDA_abs", TGT_O2); a.ins16("CMP_abs", LAST_ORI2); a.br("BNE", "p2_st_chg")
            a.ins16("LDA_abs", STABLE_CT2); a.ins("CMP_imm", 0xFE); a.br("BCS", "p2_st_done")
            a.ins16("INC_abs", STABLE_CT2); a.jmp("p2_st_done")
            a.label("p2_st_chg")                            # argmax moved -> record + reset the counter
            a.ins16("LDA_abs", TGT_C2); a.ins16("STA_abs", LAST_COL2)
            a.ins16("LDA_abs", TGT_O2); a.ins16("STA_abs", LAST_ORI2)
            a.ins("LDA_imm", 0); a.ins16("STA_abs", STABLE_CT2)
            a.label("p2_st_done")
    a.ins16("LDA_abs", STK2); a.ins("CMP_imm", STUCK_LIM); a.br("BCC", "act_p2_n")
    a.ins("LDY_imm", 0x04); a.ins("STY_zp", 0xF6); a.jmp("act_p1")   # stuck: force drop
    a.label("act_p2_n")
    # steer-then-drop, CONTINUOUS holds (v28cs DAS handles repeat). Pulsed windows parked
    # pills near the top on hardware because (with NAV_T=5*/frame) 32-hook cycles = 6.4
    # frames per edge -> 25s to move 4 cols -> pill hovered forever.
    if ROTFIX:
        # ROTATION PRE-PHASE + MINIMUM-THINK gate (orient not yet committed) -- all under LIVE
        # gravity (FAIRNESS north star: the AI never pins gravity to buy time; it plays under the
        # same fall a human does):
        #  - orient != target -> press A to rotate toward TGT_O2 (no pin). Rotations land in the
        #    first natural fall-steps -- the honest budget. If a late-game fall is too fast to
        #    finish, that is the same constraint a human faces (we do NOT stop the world for it).
        #  - orient reached -> WITHHOLD lateral + orient-lock until the think gate opens: DONE
        #    (ARMED2==0) or WDOG2 >= MIN_THINK hooks (below that the argmax is a shallow guess).
        #    During the gate the capsule keeps FALLING (no pin); we simply do not ACT yet.
        #  - at the gate: LATCH ROT_DONE2 (orient locked) and fall through to the column phase.
        # (ROT_DONE2 set => this whole block is skipped: orient stays put, only the column moves.
        #  That is the feasibility lock -- a late candidate can't re-rotate a low/flush capsule.)
        a.ins16("LDA_abs", ROT_DONE2); a.br("BNE", "mv_p2")           # committed -> column only
        a.ins16("LDA_abs", 0x03A5); a.ins16("CMP_abs", TGT_O2); a.br("BEQ", "p2_orient_ok")
        if ROTDIR:
            # DRROTDIR: SHORTEST-DIRECTION rotation. The executor has always pressed only A, and
            # A is DEC $A5 in the ROM ($8E2B), so the orient ring is walked one way only: from
            # spawn (game orient 0) target 3 costs 1 rotation, 2 costs 2, and **1 costs 3**. B is
            # INC $A5 in the same handler, so the far side is one press away.
            #   delta = (TGT_O2 - $03A5) & 3, and delta != 0 here (the CMP above peeled that off)
            #   delta 1 -> B (CW, 1 press)      delta 3 -> A (CCW, 1 press)
            #   delta 2 -> 2 presses either way; keep A so the 180 path is bit-for-bit the old one
            # Measured cost of the old behaviour (constant-orient ladder, paired seeds, cart
            # 9fefaedb): 77.79 / 78.99 / 80.48 / 81.07 f/pill at 0/1/2/3 CCW rotations = ~1.09
            # frames per rotation. So this is worth ~2.2 f/pill on the delta-1 orient and nothing
            # on the other three -- which is exactly what makes it gateable: three arms MUST NOT
            # move.
            # ---- TEST-ONLY MUTANTS (DRROTDIR_MUT). Same precedent as DRDIST_FLOORREL above:
            # kept buildable solely so PREREG_ROTDIR's mutant table can be demonstrated to FAIL
            # (killed-mutant discipline). NEVER ship a cart with DRROTDIR_MUT != none.
            if ROTDIR_MUT == "m2":            # RETIRED, EQUIVALENT TO m1 -- see below
                a.ins16("LDA_abs", 0x03A5); a.ins("SEC"); a.ins16("SBC_abs", TGT_O2)
            else:
                a.ins16("LDA_abs", TGT_O2); a.ins("SEC"); a.ins16("SBC_abs", 0x03A5)
            a.ins("AND_imm", 0x03)
            if ROTDIR_MUT != "m2b":           # m2b: press B UNCONDITIONALLY (no delta test)
                _mcmp = {"m1": 0x03, "m2": 0x01, "m4": 0x05}.get(ROTDIR_MUT, 0x01)
                a.ins("CMP_imm", _mcmp); a.br("BNE", "p2_rot_ccw")    # delta 2 or 3 -> A (CCW)
            if ROTDIR_MUT == "m3b":           # m3b: mark B ALREADY-HELD -> the press edge is dead
                a.ins("LDA_imm", 0x40); a.ins("STA_zp", 0xF8)
            elif ROTDIR_MUT != "m3":          # m3: RETIRED, UNKILLABLE -- see below
                a.ins("LDA_imm", 0x00); a.ins("STA_zp", 0xF8)         # edge (held=0) so B rotates,
            a.ins("LDA_imm", 0x40); a.ins("STA_zp", 0xF6); a.jmp("act_p1")   # B = CW = INC $A5
            if ROTDIR_MUT != "m2b":
                a.label("p2_rot_ccw")
        a.ins("LDA_imm", 0x00); a.ins("STA_zp", 0xF8)                # edge (held=0) so A rotates,
        a.ins("LDA_imm", 0x80); a.ins("STA_zp", 0xF6); a.jmp("act_p1")   # under live gravity, no pin
        a.label("p2_orient_ok")                                       # orient reached; think gate:
        a.ins16("LDA_abs", ARMED2); a.br("BEQ", "p2_commit")         # DONE -> commit
        a.ins16("LDA_abs", WDOGH2); a.br("BNE", "p2_commit")         # >256 hooks searched -> commit
        if SLAM:
            # SPEED-AWARE MIN-THINK: past the feasibility crossover (capsule already low while still
            # searching, Y < CROSS_LOWY) the min-think floor would let the pill LAND before it opens
            # -> the orient never locks and the column gate never runs = drift-lock. The orient is
            # ALREADY at target here (past the CMP above), so committing merely LATCHES it (no low
            # rotation -> DRROTFIX's no-backwards-lock invariant holds) and hands the descent to the
            # confidence gate -- which is the PRIMARY commit mechanism under fast/slow-silicon gravity.
            if MATURE:
                a.ins16("LDA_abs", SLAM_ARM); a.br("BEQ", "p2_esc_skip")  # search not keeping pace: min-think only
            a.ins16("LDA_abs", 0x0386); a.ins("CMP_imm", CROSS_LOWY); a.br("BCC", "p2_commit")
            if MATURE:
                a.label("p2_esc_skip")
        a.ins16("LDA_abs", WDOG2); a.ins("CMP_imm", MIN_THINK); a.br("BCS", "p2_commit")
        a.ins("LDA_imm", 0); a.ins("STA_zp", 0xF6); a.ins("STA_zp", 0xF8)   # gate closed: no ACT,
        a.jmp("act_p1")                                              # but NO pin -- capsule falls
        a.label("p2_commit")
        a.ins("LDA_imm", 1); a.ins16("STA_abs", ROT_DONE2)           # orient LOCKED -> begin descent
    else:
        a.ins16("LDA_abs", 0x03A5); a.ins16("CMP_abs", TGT_O2); a.br("BEQ", "mv_p2")
        a.ins("LDA_imm", 0); a.ins16("STA_abs", GRAV_P2)
        a.ins("LDA_imm", 0x00); a.ins("STA_zp", 0xF8)
        a.ins("LDA_imm", 0x80); a.ins("STA_zp", 0xF6); a.jmp("act_p1")
    a.label("mv_p2")
    if TUCK:
        # TUCK: choose THIS hook's target column by height. $0386 counts UP from the floor,
        # so "still high" is Y > TUCK_R2. BEQ/BCC both mean at-or-below the trigger.
        a.ins16("LDA_abs", TUCK_C2); a.ins("CMP_imm", 0xFF); a.br("BEQ", "mv_p2_final")
        a.ins16("LDA_abs", 0x0386); a.ins16("CMP_abs", TUCK_R2); a.br("BEQ", "mv_p2_final")
        a.br("BCC", "mv_p2_final")
        a.ins16("LDA_abs", TUCK_C2); a.jmp("mv_p2_have")      # still high -> approach column
        a.label("mv_p2_final")
        a.ins16("LDA_abs", TGT_C2)                            # low enough -> slide to final
        a.label("mv_p2_have")
        a.ins16("STA_abs", EFF_C2)
    _EC = EFF_C2 if TUCK else TGT_C2
    if DISTGATE:
        # DRDISTGATE (see the flag comment above; REVIEW #6.2 + the SURFACE-RELATIVE REBUILD
        # note): clamp _EC to the columns that are DAS-reachable from PX2 ($0385) given the
        # remaining fall budget, instead of steering toward a target that will never arrive in
        # time. Substituting EFF_DIST2 for _EC here means EVERYTHING below (alignment check,
        # WEAVE steering, dn_p2's confidence gate) is unchanged code, now just reading a
        # distance-bounded target.
        #   budget = DIST_TABLE[remaining_fall]  where remaining_fall = fully-empty rows
        #   strictly below the capsule across the span [min(PX2,_EC)..max(PX2,_EC)] of the LIVE
        #   board $0500 (capped at DIST_SCANCAP -- deeper rows can't change the budget). $0386
        #   counts UP from the floor, so board row = 15 - $0386 and "below" = higher offsets.
        if DIST_FLOORREL:
            # ---- TEST-ONLY MUTANT (DRDIST_FLOORREL=1): the ORIGINAL, census-refuted floor-
            # relative index, budget = DIST_TABLE[min($0386, len-1)]. Kept buildable solely so
            # tests/test_task49_distgate.py can demonstrate the old indexing FAILS the new
            # tests (killed-mutant discipline). NEVER ship this arm.
            a.ins16("LDA_abs", 0x0386)
            a.ins("CMP_imm", DIST_TABLE_LEN)
            a.br("BCC", "dg_yok")
            a.ins("LDA_imm", DIST_TABLE_LEN - 1)
            a.label("dg_yok")
            a.ins("TAX")
            a.ins16("LDA_absX", DIST_TABLE_ADDR)
            a.ins16("STA_abs", DG_BUDGET)
        else:
            # ---- surface-relative remaining fall (the shipping arm) ----
            # DG_YC = min($0386, 15) -- defensive clamp, the row math below assumes 0..15
            a.ins16("LDA_abs", 0x0386); a.ins("CMP_imm", 16); a.br("BCC", "dg_yok")
            a.ins("LDA_imm", 15)
            a.label("dg_yok"); a.ins16("STA_abs", DG_YC)
            a.ins("LDA_imm", 0); a.ins16("STA_abs", DG_FALL)
            # rows to scan: DG_N = min(DG_YC, DIST_SCANCAP); 0 -> capsule at the floor, no scan
            a.ins16("LDA_abs", DG_YC); a.ins("CMP_imm", DIST_SCANCAP); a.br("BCC", "dg_nok")
            a.ins("LDA_imm", DIST_SCANCAP)
            a.label("dg_nok"); a.ins16("STA_abs", DG_N)
            a.ins("CMP_imm", 0); a.br("BEQ", "dg_scand")
            # span [DG_LO..DG_HI] = [min(PX2,_EC)..max(PX2,_EC)] -- the RAW target's span (see
            # the flag comment: en-route max, endpoints inclusive)
            a.ins16("LDA_abs", _EC); a.ins16("CMP_abs", 0x0385); a.br("BCS", "dg_spr")
            a.ins16("STA_abs", DG_LO)
            a.ins16("LDA_abs", 0x0385); a.ins16("STA_abs", DG_HI); a.jmp("dg_spd")
            a.label("dg_spr")
            a.ins16("STA_abs", DG_HI)
            a.ins16("LDA_abs", 0x0385); a.ins16("STA_abs", DG_LO)
            a.label("dg_spd")
            a.ins16("LDA_abs", DG_HI); a.ins("SEC"); a.ins16("SBC_abs", DG_LO)
            a.ins("CLC"); a.ins("ADC_imm", 1); a.ins16("STA_abs", DG_CSPAN)
            # first row below the capsule: row = (15 - DG_YC) + 1 = 16 - DG_YC; offset = row*8
            # + DG_LO. DG_YC >= 1 here, so row <= 15 and offset <= 120+DG_LO <= 127: no carry.
            a.ins("LDA_imm", 16); a.ins("SEC"); a.ins16("SBC_abs", DG_YC)
            a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
            a.ins("CLC"); a.ins16("ADC_abs", DG_LO); a.ins16("STA_abs", DG_OFF)
            a.label("dg_row")
            a.ins16("LDA_abs", DG_OFF); a.ins("TAX")           # X walks the row's span cells
            a.ins16("LDY_abs", DG_CSPAN)                       # Y = cells left in this row
            a.label("dg_cell")
            a.ins16("LDA_absX", 0x0500)
            a.br("BEQ", "dg_ce")                               # $00 = empty (tile-encoding)
            a.ins("CMP_imm", 0xFF); a.br("BNE", "dg_scand")    # not $FF either -> STACK: stop,
            a.label("dg_ce")                                   #   DG_FALL is final
            a.ins("INX"); a.ins("DEY"); a.br("BNE", "dg_cell")
            a.ins16("INC_abs", DG_FALL)                        # whole row empty -> 1 more row of fall
            a.ins16("DEC_abs", DG_N); a.br("BEQ", "dg_scand")  # scanned enough (cap/floor reached)
            a.ins16("LDA_abs", DG_OFF); a.ins("CLC"); a.ins("ADC_imm", 8); a.ins16("STA_abs", DG_OFF)
            a.jmp("dg_row")
            a.label("dg_scand")
            a.ins16("LDA_abs", DG_FALL); a.ins("TAX")          # DG_FALL <= DIST_SCANCAP < len
            a.ins16("LDA_absX", DIST_TABLE_ADDR)
            a.ins16("STA_abs", DG_BUDGET)
        #   direction: _EC (target) vs PX2 -- unsigned CMP is safe, both are 0..7
        a.ins16("LDA_abs", _EC); a.ins16("CMP_abs", 0x0385); a.br("BCS", "dg_right")
        # --- LEFTWARD: target < PX2. EFF = max(target, floor) where floor = max(0, PX2-budget) ---
        a.ins16("LDA_abs", 0x0385); a.ins("SEC"); a.ins16("SBC_abs", DG_BUDGET)
        a.br("BCS", "dg_l_ok")                      # no borrow -> PX2-budget stayed >= 0
        a.ins("LDA_imm", 0)                          # borrowed -> floor at column 0
        a.label("dg_l_ok")
        a.ins16("STA_abs", EFF_DIST2)                # tentatively: floor
        a.ins16("LDA_abs", _EC); a.ins16("CMP_abs", EFF_DIST2); a.br("BCS", "dg_l_reach")
        a.jmp("dg_done")                              # target < floor -> EFF_DIST2 already = floor
        a.label("dg_l_reach")
        a.ins16("STA_abs", EFF_DIST2)                # target reachable (A still = target from CMP)
        a.jmp("dg_done")
        a.label("dg_right")
        # --- RIGHTWARD/equal: target >= PX2. EFF = min(target, ceil) where ceil = min(7, PX2+budget) ---
        a.ins16("LDA_abs", 0x0385); a.ins("CLC"); a.ins16("ADC_abs", DG_BUDGET)
        a.ins("CMP_imm", 8); a.br("BCC", "dg_r_ok")
        a.ins("LDA_imm", 7)                           # ceil at the last column
        a.label("dg_r_ok")
        a.ins16("STA_abs", EFF_DIST2)                 # tentatively: ceil
        a.ins16("LDA_abs", EFF_DIST2); a.ins16("CMP_abs", _EC); a.br("BCS", "dg_r_reach")
        a.jmp("dg_done")                               # ceil < target -> EFF_DIST2 already = ceil
        a.label("dg_r_reach")
        a.ins16("LDA_abs", _EC); a.ins16("STA_abs", EFF_DIST2)   # target reachable
        a.label("dg_done")
        _EC = EFF_DIST2
    a.ins16("LDA_abs", 0x0385); a.ins16("CMP_abs", _EC); a.br("BEQ", "dn_p2")
    if not USE_WEAVE:
        a.ins("LDA_imm", 0); a.ins16("STA_abs", GRAV_P2)  # baseline: freeze at spawn row (slide-only)
    # WEAVE: skip the freeze -> the pill falls at natural gravity WHILE sliding toward the
    # target, weaving down-and-over past columns blocked at the spawn row. DAS shift-rate
    # (~1 col/6f) >> drop-rate (~1 row/16f), so it reaches the target column well before landing.
    a.ins("LDY_imm", 0x01); a.ins16("LDA_abs", 0x0385); a.ins16("CMP_abs", _EC); a.br("BCC", "st_p2")
    a.ins("LDY_imm", 0x02); a.jmp("st_p2")
    a.label("dn_p2")
    if NO_FREEZE or COLGATE:
        # ANYTIME + CONFIDENCE-GATED SLAM. Column-aligned here, and ROT_DONE2 is guaranteed set
        # (act_p2_n only reaches mv_p2/dn_p2 after the orient-lock), so the min-think floor +
        # rotation-complete preconditions already hold. DONE still slams (the shipped ceiling);
        # otherwise slam once the published argmax has been stable for a phase-dependent K hooks.
        a.ins16("LDA_abs", ARMED2); a.br("BEQ", "dn_p2_go")       # DONE -> slam (unchanged ceiling)
        if SLAM:
            # PHASE-AWARE K (TEMPO_DESIGN §8), two axes:
            #  feasibility -- reactive crossover: still searching while the capsule is already low
            #    (Y < CROSS_LOWY) => DONE won't arrive in time, commit on minimal stability K_CROSS.
            #  safety -- virus_count: endgame (vc < VC_ENDGAME) uses K_END (255 = require DONE);
            #    opening/mid uses the aggressive K_OPEN. Feasibility dominates (checked first).
            # If the argmax column later CHANGES, nf2 refreshes TGT_C2 + zeroes STABLE_CT2, so the
            # next hook is un-aligned -> mv_p2 re-steers and the slam self-aborts (no latch needed).
            if MATURE:
                a.ins16("LDA_abs", SLAM_ARM); a.br("BEQ", "dn_hold")  # search not keeping pace: DONE-wait only
            a.ins16("LDA_abs", 0x0386); a.ins("CMP_imm", CROSS_LOWY); a.br("BCC", "dn_slam_cross")
            a.ins16("LDA_abs", VCOUNT_P2); a.ins("CMP_imm", VC_ENDGAME); a.br("BCC", "dn_slam_end")
            a.ins16("LDA_abs", STABLE_CT2); a.ins("CMP_imm", K_OPEN); a.br("BCS", "dn_p2_go")
            a.jmp("dn_hold")
            a.label("dn_slam_cross")                             # low + still searching -> feasibility K
            a.ins16("LDA_abs", STABLE_CT2); a.ins("CMP_imm", K_CROSS); a.br("BCS", "dn_p2_go")
            a.jmp("dn_hold")
            a.label("dn_slam_end")                               # endgame -> conservative K (255=DONE-only)
            a.ins16("LDA_abs", STABLE_CT2); a.ins("CMP_imm", K_END); a.br("BCS", "dn_p2_go")
            a.label("dn_hold")
        a.ins("LDY_imm", 0x00); a.jmp("st_p2")                    # hold: no button, fall at gravity
        a.label("dn_p2_go")
    a.ins("LDY_imm", 0x04)
    a.label("st_p2"); a.ins("STY_zp", 0xF6)
    a.label("act_p1")
    if UNPAUSE and not HUMAN_P1:
        # #133 fix: restore STOCK START semantics for P1. $F5 still holds the ROM's raw pad
        # read at this point (the hook runs inside the read routine, before the edge-detect,
        # and nothing upstream of act_p1 writes $F5 on the go_ai path), so bit 4 here is a REAL
        # controller START. Write $F5 = $10 exactly -- the byte the pause loop's exact-compare
        # at $97D6 requires -- and skip the synthesized command for this hook. Both hook passes
        # of a held press take this path, so the value survives the ROM's two-pass AND; the
        # ROM's own pressed/held derivation then gives a proper edge (pause on press, unpause
        # on re-press). With no controller attached bit 4 is never set and this is dead code.
        a.ins("LDA_zp", 0xF5); a.ins("AND_imm", 0x10); a.br("BEQ", "unp_no")
        a.ins("LDA_imm", 0x10); a.ins("STA_zp", 0xF5); a.jmp("act_done")
        a.label("unp_no")
    if HUMAN_P1:
        a.jmp("act_done")                                   # human P1: never touch $F5/$F7/GRAV_P1
    elif P1WIGGLE:
        # SPECTATOR WIGGLE (see DRP1WIGGLE): P1's whole policy is "hold one direction for this
        # pill". Write the RAW latch $F5 every hook and leave $F7 alone -- the game's own
        # _pressedVsHeld pass turns that into held=dir with a single pressed edge on the first
        # hook, which is what fallingPill_checkXMove needs to DAS the capsule to the wall. No
        # gravity pin anywhere on this path, so the capsule falls at the natural rate while it
        # slides. This REPLACES the copro steering below: the P1 search still runs (handle(1)
        # is untouched) but its target is deliberately ignored -- the point is a dumb spread.
        a.ins16("LDA_abs", WIG_DIR); a.br("BEQ", "wig_left")
        a.ins("LDA_imm", B_RIGHT); a.jmp("wig_hold")
        a.label("wig_left"); a.ins("LDA_imm", B_LEFT)
        a.label("wig_hold"); a.ins("STA_zp", 0xF5)
        a.jmp("act_done")
    elif P1NATIVE:
        # ---- NATIVE d1 AI for P1 (see DRP1NATIVE) -- the P1 mirror of v28cs's $FF54 wrapper.
        # PER-PILL CACHE (and the two-pass AND guarantee): search only when P1's pill Y has
        # RISEN above the last Y we saw, i.e. a new capsule spawned. Hook 1 of a frame does the
        # search and then stores the key; hook 2 finds the key equal, skips, and reuses the same
        # P1AI_C/P1AI_O -- so both passes write an IDENTICAL $F5 and survive the AND.
        if P1SLICE:
            # spawn edge ARMS the sliced search instead of running it; the tick below then
            # advances it two column-steps per hook until the swap step publishes.
            a.ins16("LDA_abs", 0x0306); a.ins16("CMP_abs", P1AI_Y)
            a.br("BCC", "p1s_noarm"); a.br("BEQ", "p1s_noarm")
            a.ins("LDA_imm", 1); a.ins16("STA_abs", SL_PH)          # phase = V pass
            a.ins("LDA_imm", 0)
            a.ins16("STA_abs", SL_COL); a.ins16("STA_abs", SL_BEST)
            a.ins16("STA_abs", SL_ORI); a.ins16("STA_abs", SL_OFA); a.ins16("STA_abs", SL_OFB)
            a.ins("LDA_imm", 3); a.ins16("STA_abs", SL_TGT)         # search_entry's defaults
            a.label("p1s_noarm")
            a.ins16("LDA_abs", 0x0306); a.ins16("STA_abs", P1AI_Y)
            a.ins16("LDA_abs", SL_PH); a.br("BEQ", "p1s_idle")
            a.jsr("p1s_tick")
            a.label("p1s_idle")
        else:
            a.ins16("LDA_abs", 0x0306); a.ins16("CMP_abs", P1AI_Y)
            a.br("BCC", "p1n_nosearch"); a.br("BEQ", "p1n_nosearch")
            a.jsr(build_p1_native()[1]["search_entry"])          # JSR the mirrored search (abs)
            a.ins("LDA_zp", 0x00); a.ins16("STA_abs", P1AI_C)   # Z_TARGET -> ours NOW ($00 is
            a.ins("LDA_zp", 0xDA); a.ins16("STA_abs", P1AI_O)   # CTRL_exp1, rewritten every read)
            a.label("p1n_nosearch")
            a.ins16("LDA_abs", 0x0306); a.ins16("STA_abs", P1AI_Y)
        # ORIENT phase: press A until the capsule matches the searched orientation. $F7 is
        # cleared first so each hook reads as a FRESH press edge -- without that, held==raw
        # from the previous hook makes pressed==0 and rotation stops after one step. (This is
        # the same idiom act_p2 uses on $F8/$F6, and it does NOT contradict the wiggle's
        # "never write $F7": there we WANT held to persist so DAS accumulates; here we want a
        # repeating edge.)
        a.ins16("LDA_abs", 0x0325); a.ins16("CMP_abs", P1AI_O); a.br("BEQ", "p1n_col")
        a.ins("LDA_imm", 0x00); a.ins("STA_zp", 0xF7)
        a.ins("LDA_imm", 0x80); a.ins("STA_zp", 0xF5); a.jmp("act_done")
        # COLUMN phase: steer toward the searched column.
        a.label("p1n_col")
        a.ins16("LDA_abs", 0x0305); a.ins16("CMP_abs", P1AI_C); a.br("BEQ", "p1n_aligned")
        a.ins("LDY_imm", B_RIGHT); a.br("BCC", "p1n_store")   # pillX < target -> RIGHT
        a.ins("LDY_imm", B_LEFT); a.jmp("p1n_store")
        a.label("p1n_aligned")
        # ★ THE DOWN-STRIP (the whole point of "deliberately slow"): v28cs puts LDY #$04 here
        # to soft-drop the moment the column is reached. LDY #$00 presses nothing, so the
        # capsule finishes its descent at natural gravity and P1 plays at a watchable pace.
        a.ins("LDY_imm", 0x00)
        a.label("p1n_store"); a.ins("STY_zp", 0xF5)
        a.jmp("act_done")
    # skip P1 acting if we're currently searching for P1
    a.ins16("LDA_abs", ARMED); a.br("BEQ", "act_p1_go")    # not searching P1 -> steer it
    a.ins("LDA_imm", 0); a.ins16("STA_abs", GRAV_P1)       # searching P1 -> freeze + skip steer
    a.ins("STA_zp", 0xF5); a.ins("STA_zp", 0xF7); a.jmp("act_done")
    a.label("act_p1_go")
    a.ins16("LDA_abs", STK1); a.ins("CMP_imm", STUCK_LIM); a.br("BCC", "act_p1_n")
    a.ins("LDY_imm", 0x04); a.ins("STY_zp", 0xF5); a.jmp("act_done")  # stuck: force drop
    a.label("act_p1_n")
    a.ins16("LDA_abs", 0x0325); a.ins16("CMP_abs", TGT_O1); a.br("BEQ", "mv_p1")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", GRAV_P1)
    a.ins("LDA_imm", 0x00); a.ins("STA_zp", 0xF7)
    a.ins("LDA_imm", 0x80); a.ins("STA_zp", 0xF5); a.jmp("act_done")
    a.label("mv_p1")
    a.ins16("LDA_abs", 0x0305); a.ins16("CMP_abs", TGT_C1); a.br("BEQ", "dn_p1")
    if not USE_WEAVE:
        a.ins("LDA_imm", 0); a.ins16("STA_abs", GRAV_P1)  # baseline: freeze at spawn row (slide-only)
    # WEAVE: skip the freeze -> pill falls while sliding, weaving down-and-over (see mv_p2).
    a.ins("LDY_imm", 0x01); a.ins16("LDA_abs", 0x0305); a.ins16("CMP_abs", TGT_C1); a.br("BCC", "st_p1")
    a.ins("LDY_imm", 0x02); a.jmp("st_p1")
    a.label("dn_p1"); a.ins("LDY_imm", 0x04)
    a.label("st_p1"); a.ins("STY_zp", 0xF5)
    a.label("act_done")
    a.ins("RTS")
    return a.assemble(), a.labels


def build_p1_native():
    """(ai_bytes, ai_labels, swap_bytes) for the P1-MIRRORED copy of the v28cs depth-1 AI.

    The v28cs AI is still resident in every copro cart at $FB00 (only its 5-byte head is
    repointed), but it reads P2's board $0500 and P2's colours $0381/$0382, so it cannot serve
    P1 as-is. Re-emitting it with the P1 addresses is 11 substitutions and ~550 bytes of the
    ~14.8 KB free in unit1 -- cheaper and far safer than the alternative of copying P1's board
    into $0500 around a call, which would corrupt P2's live board if the NMI re-entered
    mid-copy. Deterministic, so callers may invoke it freely instead of threading it through.
    """
    from patch_vs_cpu import build_v18_ai, build_swap_eval
    body, labels = build_v18_ai(P1AI_CPU, with_rotation=True, color_swap=True,
                                board=0x0400, ca=0x0301, cb=0x0302, swap_cpu=P1SWAP_CPU)
    return body, labels, build_swap_eval(P1SWAP_CPU, labels["eval_pair"])


def _sel(w, value):
    if MMC1RST:
        # HAZARD 2 (see the DRMMC1RST flag block): MMC1 has ONE shift register shared by all four
        # registers and the base game clocks a 5-write $DFFF sequence from the MAIN loop every
        # frame. An NMI landing mid-sequence makes this PRG sequence complete with mixed bits ->
        # unit 0 maps -> the JSR $8000 below hits the base soft-entry -> full RAM wipe with BUSY
        # latched. A bit-7 write re-zeros the shift counter, so the sequence below is self-aligning
        # no matter how many bits the interrupted main-thread sequence had already shifted in.
        w.ins("LDA_imm", 0x80)
        w.ins("STA_abs", PRG_REG & 0xFF, (PRG_REG >> 8) & 0xFF)
    w.ins("LDA_imm", value)
    for i in range(5):
        w.ins("STA_abs", PRG_REG & 0xFF, (PRG_REG >> 8) & 0xFF)
        if i < 4:
            w.ins("LSR_A")


def build_wrapper(main_cpu):
    """Trampoline (every frame, all modes): [re-entry guard] -> bank2 -> JSR main -> bank0 -> RTS."""
    w = Asm6502(WRAP_CPU)
    if REENTRY_GUARD:
        # RE-ENTRANCY GUARD (see BUSY): bail if the driver is already running so the NMI can't re-enter and
        # corrupt the shared state (the GO-storm freeze). BEFORE _sel, so a re-entrant bail never touches the
        # bank. Bootstrap: BUSY is uninit PRG-RAM, so on cold boot (NAV_MAGIC != $A5, before main's init sets
        # it) force BUSY=0 -- else a garbage-set BUSY would bail forever = deadlock.
        w.ins16("LDA_abs", NAV_MAGIC); w.ins("CMP_imm", 0xA5); w.br("BEQ", "w_warm")
        w.ins("LDA_imm", 0); w.ins16("STA_abs", BUSY)             # cold boot -> clear garbage BUSY
        if BUSYESC:
            w.ins16("STA_abs", BUSYSKP)                           # A==0: garbage streak count too
        w.label("w_warm")
        w.ins16("LDA_abs", BUSY); w.br("BEQ", "w_run")            # free -> enter
        if BUSYESC:
            # STALE-BUSY ESCAPE (DRBUSYESC, see flag block): a warm-inherited BUSY=1 (core reload
            # mid-invocation) would bail here FOREVER -- nothing outside this guard ever clears it.
            # 255 CONSECUTIVE bails (~2 s) cannot be genuine re-entrancy (1-2 hooks): force-free.
            w.ins16("INC_abs", BUSYSKP)
            w.ins16("LDA_abs", BUSYSKP); w.ins("CMP_imm", 0xFF); w.br("BCC", "w_bail")
            w.ins("LDA_imm", 0); w.ins16("STA_abs", BUSY); w.ins16("STA_abs", BUSYSKP)
            w.br("BEQ", "w_run")                                  # A==0 -> Z: branch-always into the body
            w.label("w_bail")
        w.ins("RTS")                                              # already running -> bail (no bank touch)
        w.label("w_run")
        if BUSYESC:
            w.ins("LDA_imm", 0); w.ins16("STA_abs", BUSYSKP)      # successful entry resets the streak
        w.ins("LDA_imm", 1); w.ins16("STA_abs", BUSY)            # mark running
    _sel(w, 2)
    w.jsr(main_cpu)
    _sel(w, 0)
    if REENTRY_GUARD:
        w.ins("LDA_imm", 0); w.ins16("STA_abs", BUSY)            # clear -> next hook may run
    w.ins("RTS")
    return w.assemble()


def main():
    import os
    global OUT
    level = int(os.environ.get("DRLEVEL", "11"))
    speed = int(os.environ.get("DRSPEED", "1"))
    if level != 11 or speed != 1:
        OUT = f"drmario_copro_L{level}s{speed}.nes"
    unit1, labels = build_main(level, speed)
    print(f"LEVEL={level} SPEED={speed} -> {OUT}")
    main_cpu = UNIT1_CPU + labels["main"]
    print(f"unit-1 main: {len(unit1)} B at ${UNIT1_CPU:04X}; main=${main_cpu:04X}")
    bank = bytearray(b"\x00" * 0x4000)
    bank[0:len(unit1)] = unit1
    if P1NATIVE:
        p1ai, p1lab, p1swap = build_p1_native()
        assert UNIT1_CPU + len(unit1) <= P1AI_CPU, (
            f"build_main output reaches ${UNIT1_CPU + len(unit1):04X}, which would collide with "
            f"the P1 native AI at ${P1AI_CPU:04X}. Move P1AI_CPU up.")
        assert P1AI_CPU + len(p1ai) <= P1SWAP_CPU, "P1 AI overruns its swap_eval"
        assert P1SWAP_CPU + len(p1swap) <= UNIT1_CPU + 0x4000, "P1 swap_eval overruns the bank"
        bank[P1AI_CPU - UNIT1_CPU:P1AI_CPU - UNIT1_CPU + len(p1ai)] = p1ai
        bank[P1SWAP_CPU - UNIT1_CPU:P1SWAP_CPU - UNIT1_CPU + len(p1swap)] = p1swap
        print(f"DRP1NATIVE: P1 d1 AI {len(p1ai)} B at ${P1AI_CPU:04X} "
              f"(search_entry ${p1lab['search_entry']:04X}), swap_eval {len(p1swap)} B at "
              f"${P1SWAP_CPU:04X}; handle(1) dropped, soft-drop stripped")

    if RTIVEC:
        # DRRTIVEC part 1 of 3 -- the DRIVER-BANK PROBE BYTE. The shield in the shared high half
        # decides "is the driver bank mapped low?" by reading this address: $40 here, $00 in base
        # bank 0. Value $40 is itself an RTI, so even a stray vector straight to $A02E is inert.
        _probe = RTIVEC_PROBE - UNIT1_CPU
        assert UNIT1_CPU + len(unit1) <= RTIVEC_PROBE, (
            f"driver body reaches ${UNIT1_CPU + len(unit1):04X}, colliding with the DRRTIVEC probe "
            f"byte at ${RTIVEC_PROBE:04X}")
        if P1NATIVE:
            assert P1SWAP_CPU + len(p1swap) <= RTIVEC_PROBE, (
                f"P1 swap_eval reaches ${P1SWAP_CPU + len(p1swap):04X}, colliding with the DRRTIVEC "
                f"probe byte at ${RTIVEC_PROBE:04X}")
        assert bank[_probe] == 0, (
            f"DRRTIVEC probe site ${RTIVEC_PROBE:04X} is not free in the driver bank "
            f"(holds {bank[_probe]:#04x})")
        bank[_probe] = RTIVEC_MAGIC
        print(f"DRRTIVEC: driver-bank probe ${RTIVEC_PROBE:04X} <- {RTIVEC_MAGIC:#04x}")

    wrap = build_wrapper(main_cpu)
    print(f"trampoline: {len(wrap)} B at ${WRAP_CPU:04X}")
    assert WRAP_CPU + len(wrap) <= 0xFFD2, "wrapper overflows the dead-v17 window"

    rom = bytearray(open(V28CS, "rb").read())
    assert rom[4] == 2
    rom[WRAP_FILE:WRAP_FILE + len(wrap)] = wrap
    HOOK_FILE = 0x37CF
    assert rom[HOOK_FILE] == 0x4C and rom[HOOK_FILE + 1] == 0x00 and rom[HOOK_FILE + 2] == 0xFB, \
        "expected v28cs hook JMP $FB00 at 0x37CF"
    # blob head: STA $F6; LDA $04; BNE... -> STA $F6; JMP $FF54  (trampoline runs every frame)
    assert rom[BLOB_FILE:BLOB_FILE + 6] == bytes.fromhex("85f6a504d003"), \
        "unexpected v28cs blob head"
    rom[BLOB_FILE:BLOB_FILE + 5] = bytes([0x85, 0xF6, 0x4C, 0x54, 0xFF])
    print("blob head repointed: STA $F6; JMP $FF54 (every frame, all modes)")

    if VERFIX:
        # #129 stock-ROM fix (see the DRVERFIX flag block). Anchor = checkVerMatch's row step
        # (LDA $5A / CLC / ADC #$08 / STA $5A / LDA $5A) plus the unbounded wrap test
        # (AND #$F8 / BEQ). Located by content, verified unique, originals asserted before any
        # write; the BEQ's target byte is untouched (same branch, real bound).
        _vf_anchor = bytes.fromhex("a55a186908855aa55a29f8f0")
        _vf_i = rom.find(_vf_anchor)
        assert _vf_i >= 0, "DRVERFIX: checkVerMatch anchor not found in base image"
        assert rom.find(_vf_anchor, _vf_i + 1) < 0, "DRVERFIX: checkVerMatch anchor not unique"
        _vf_off = _vf_i + 9                                  # the AND #$F8 / BEQ opcode bytes
        assert bytes(rom[_vf_off:_vf_off + 3]) == bytes.fromhex("29f8f0"), \
            "DRVERFIX: unexpected bytes at edit site"
        rom[_vf_off:_vf_off + 3] = bytes.fromhex("c980b0")   # CMP #$80 / BCS (same length+target)
        print(f"DRVERFIX: checkVerMatch vertical scan bounded "
              f"(AND #$F8/BEQ -> CMP #$80/BCS) at file offset 0x{_vf_off:04X}")

    if STUDY:
        # v8.2 EVAC: keep part1 ($D2CC STUDY + P1 preview, RTS), drop the 2P tail, and restore the 4
        # tail sites to their pre-study (vanilla) bytes so the title/settings/$A346 printing tables +
        # the LDA $9FF8,X table draw clean (kills the $BC26 KIL + the $BE56 level-select junk).
        _evac = [(0x2008, 34), (0x2381, 27), (0x3E66, 13), (0x3C36, 18)]   # $9FF8 $A371 $BE56 $BC26
        _saved = [(o, bytes(rom[o:o + l])) for o, l in _evac]
        n = apply_study_pause(rom, evac=True)
        for o, orig in _saved:
            rom[o:o + len(orig)] = orig
        print(f"DRSTUDY v8.2 EVAC: part1-only ($D2CC RTS); tail $9FF8/$A371/$BE56/$BC26 -> base; {n} edit(s)")

    if RTIVEC:
        # DRRTIVEC part 2 of 3 -- the BANK-DISCRIMINATING NMI SHIELD, emitted into BANK 1, i.e. the
        # high half, which expand_prg.py duplicates into PRG index 1 AND index 3. Putting it in the
        # SHARED half (rather than index 3 only) is what makes the fix survive DRMMC1RST forcing PRG
        # mode 3: in mode 3 the base game itself runs with index 3 at $C000, so the shield must give
        # the RIGHT answer for both banks, not just ours. See the DRRTIVEC flag block.
        _b1 = 0x4010                                   # file offset of CPU $C000 in the 2-bank image
        _sh = _b1 + (NMI_SHIELD_CPU - 0xC000)
        _base_nmi = rom[_b1 + 0x3FFA] | (rom[_b1 + 0x3FFB] << 8)
        _base_irq = rom[_b1 + 0x3FFE] | (rom[_b1 + 0x3FFF] << 8)
        assert _base_nmi == 0x8005 and _base_irq == 0x8035, (
            f"base vectors moved (NMI ${_base_nmi:04X} IRQ ${_base_irq:04X}); the shield hard-codes "
            "the game's NMI entry and assumes its IRQ handler is a bare RTI")
        assert rom[0x10 + (0x8035 - 0x8000)] == 0x40, (
            "base IRQ handler $8035 is not a bare RTI, so pointing the driver unit's IRQ vector at "
            "the shield's RTI byte is no longer semantics-preserving")
        assert rom[0x10 + (RTIVEC_PROBE - 0x8000)] != RTIVEC_MAGIC, (
            f"base bank 0 holds {RTIVEC_MAGIC:#04x} at ${RTIVEC_PROBE:04X} -- the probe cannot tell "
            "the two banks apart any more")
        # FREE_SPACE_MAP.md SHARED-FREE run $CEEC-$CEFC (17 B, 0 refs, past every RB6C2_PRINT
        # table -- all 21 terminate at or before $CEBA). Filler is NOT proof of free, so this
        # asserts the map's run rather than "it looked like padding".
        assert all(b in (0x00, 0xFF) for b in rom[_sh:_b1 + (0xCEFC - 0xC000) + 1]), (
            f"${NMI_SHIELD_CPU:04X}-$CEFC is not filler any more -- someone else allocated it")
        # ⚠ v6e A-CLOBBER FIX. The first shield DESTROYED THE ACCUMULATOR: it opened with
        # `LDA $A02E` and fell through to `JMP $8005`, so the game's NMI handler -- which opens
        # PHA and closes PLA -- pushed and faithfully restored the ALREADY-CORRUPTED A, and the
        # interrupted main-loop code resumed with a wrong accumulator, silently, on every NMI the
        # shield handled. It only bites when DRMMC1RST is also on (mode 3 hard-fixes $C000-$FFFF
        # to index 3, whose NMI vector IS the shield) -- i.e. exactly the shipping combination.
        # Multi-match gates could not see it: match counts and abort counts are insensitive to a
        # corrupted register. Save/restore A around the probe on BOTH exits. No flag save needed --
        # NMI hardware pushes P and RTI restores it. 15 B, still inside the 17-byte free run.
        #   $CEEC 48        PHA
        #   $CEED AD 2E A0  LDA $A02E
        #   $CEF0 C9 40     CMP #$40
        #   $CEF2 D0 03     BNE $CEF7
        #   $CEF4 68        PLA        ; driver bank mapped: absorb this NMI, A intact
        #   $CEF5 40        RTI
        #   $CEF6 40        RTI        ; <- IRQ vector target (IRQ pushes no A, so bare RTI)
        #   $CEF7 68        PLA        ; base bank mapped: hand to the game, A intact
        #   $CEF8 4C 05 80  JMP $8005
        shield = bytes([0x48,                                          # PHA
                        0xAD, RTIVEC_PROBE & 0xFF, RTIVEC_PROBE >> 8,  # LDA $A02E
                        0xC9, RTIVEC_MAGIC,                            # CMP #$40
                        0xD0, 0x03,                                    # BNE -> the PLA/JMP tail
                        0x68,                                          # PLA
                        0x40,                                          # RTI (overrun absorbed)
                        0x40,                                          # RTI <- IRQ vector target
                        0x68,                                          # PLA
                        0x4C, _base_nmi & 0xFF, _base_nmi >> 8])       # JMP $8005
        assert NMI_SHIELD_CPU + len(shield) - 1 <= 0xCEFC, "shield overruns the $CEEC free run"
        rom[_sh:_sh + len(shield)] = shield
        RTIVEC_RTI_CPU = NMI_SHIELD_CPU + 10           # the IRQ-path RTI inside the shield
        print(f"DRRTIVEC: NMI shield {len(shield)} B at ${NMI_SHIELD_CPU:04X} (shared high half), "
              f"RTI at ${RTIVEC_RTI_CPU:04X}")

    tmp = OUT + ".2bank"
    open(tmp, "wb").write(rom)
    expand(tmp, OUT, new_bank_bytes=bytes(bank))
    import os
    os.remove(tmp)
    out = bytearray(open(OUT, "rb").read())
    out[6] = (out[6] & 0x0F) | 0x40      # mapper 100 = 0x64
    out[7] = (out[7] & 0x0F) | 0x60
    if RTIVEC:
        # DRRTIVEC part 3 of 3 -- repoint the DRIVER UNIT's vectors. Index 3 is unit 1's high half
        # (expand_prg.py's second copy of orig bank 1); index 1 is unit 0's and is LEFT ALONE, so a
        # DRMMC1RST=0 cart's ordinary game NMI is bit-for-bit unchanged -- index 3 is only mapped
        # while prg_bank=2, i.e. only inside a driver invocation.
        _i3 = 0x10 + 3 * 0x4000
        _i1 = 0x10 + 1 * 0x4000
        assert out[_i3 + 0x3FFA:_i3 + 0x3FFC] == bytes([0x05, 0x80]), "unit-1 NMI vector is not $8005"
        assert out[_i3 + 0x3FFE:_i3 + 0x4000] == bytes([0x35, 0x80]), "unit-1 IRQ vector is not $8035"
        assert out[_i3 + 0x3FFC:_i3 + 0x3FFE] == bytes([0x00, 0xFF]), "unit-1 RESET vector is not $FF00"
        # $FFFC/$FFFD (RESET) IS DELIBERATELY LEFT ALONE. MMC1 powers up in PRG mode 3, so at cold
        # boot $C000-$FFFF IS index 3 regardless of the PRG register -- expand_prg.py's docstring
        # depends on exactly that to boot. Repointing RESET bricks power-on.
        _rti = NMI_SHIELD_CPU + 10          # v6e: IRQ-path RTI moved by the PHA/PLA fix
        out[_i3 + 0x3FFA], out[_i3 + 0x3FFB] = NMI_SHIELD_CPU & 0xFF, NMI_SHIELD_CPU >> 8
        out[_i3 + 0x3FFE], out[_i3 + 0x3FFF] = _rti & 0xFF, _rti >> 8
        assert out[_i1:_i1 + 0x4000] != out[_i3:_i3 + 0x4000], "DRRTIVEC did not change index 3"
        _delta = sum(1 for a, b in zip(out[_i1:_i1 + 0x4000], out[_i3:_i3 + 0x4000]) if a != b)
        assert _delta == 4, f"index 1 and index 3 differ in {_delta} bytes, expected exactly the 4 vector bytes"
        print(f"DRRTIVEC: unit-1 vectors NMI->${NMI_SHIELD_CPU:04X} IRQ->${_rti:04X} "
              f"(RESET untouched; unit-0 vectors untouched; idx1 vs idx3 delta = {_delta} B)")
    open(OUT, "wb").write(out)
    print(f"wrote {OUT} (mapper 100, AUTO-NAV VS-CPU L11, FPGA coprocessor)")

    if BUILDID:
        # DRBUILDID stamp patch -- see the flag comment for the full mechanism. `unit1`'s bytes
        # land in the final expanded image at file offset 0x8010 + (offset within unit1): the
        # header is 16B, then unit 0 is bank0+bank1 (2*0x4000) untouched ahead of it, then `bank`
        # (== unit1, padded to 0x4000) is next -- verified empirically against a real build (the
        # first byte of the "dispatch" label matched at exactly this computed offset) before
        # this patch step was trusted with real writes.
        UNIT1_FILE_BASE = 0x10 + 2 * 0x4000
        cart = bytearray(open(OUT, "rb").read())
        digest = hashlib.md5(bytes(cart)).hexdigest()[:4].upper()   # placeholders still $FF here
        for _i, _hexch in enumerate(digest):
            off = UNIT1_FILE_BASE + labels[f"bid_hash{_i}"] + 1     # +1: past the LDA_imm opcode
            assert cart[off] == 0xFF, (
                f"DRBUILDID: patch site {off:#x} (bid_hash{_i}) held {cart[off]:#x}, expected the "
                "$FF placeholder -- offset math is wrong, refusing to write a stamp that could be "
                "landing on live code")
            cart[off] = _bid_tile(_hexch)
        open(OUT, "wb").write(cart)
        print(f"DRBUILDID stamp: {BUILDID_TAG} {digest} (settings screen row 25, cols 6-14)")

    # One line, printed last, greppable and JSON-parseable: every DR* knob this build actually
    # consulted and what it resolved to (see the DR_ENV_SNAPSHOT comment near `import os as _os`
    # for why this is the provenance fix, not just a debug aid). None-valued entries would mean
    # some call site passed no default (verified: none currently do) -- dropped defensively
    # rather than emitted, since a manifest field can't hold something a future replay can't set
    # as an env var string anyway.
    _snapshot = {k: v for k, v in sorted(DR_ENV_SNAPSHOT.items()) if v is not None}
    print("##DRFLAGSNAPSHOT## " + json.dumps(_snapshot))


if __name__ == "__main__":
    main()
