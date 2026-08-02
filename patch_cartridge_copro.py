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
W_TCOL, W_TROW = 0x5087, 0x5088   # copro publishes the tuck descriptor here (0xFF = none)   # TITLE DWELL: frames dwelt at the title + last frameCounter($43) seen
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
TUCK = _os.environ.get("DRTUCK", "0") == "1"   # tuck executor (see TUCK_C2 above)
REENTRY_GUARD = _os.environ.get("DRREENTRY", "1") != "0"
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
# frame per P1 pill (~1 in 200 at L11), and the only dangerous case -- overrunning a WHOLE
# frame, so the next NMI re-enters -- is already caught by the BUSY guard.
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
RECOMMIT = (MATURE
            and (not NO_FREEZE or _os.environ.get("DRRECOMMIT_NOFREEZE", "0") == "1")
            and (_os.environ.get("DRRECOMMIT", "1") != "0"))
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
# if a pill sits still this many frames (while not search-frozen), force DOWN to unstick
STUCK_LIM = 60        # 1s -- continuous holds again; if truly stuck kick fast to unpark
# copro window (mapper 100)
W_BOARD, W_CA, W_GO, W_DONE, W_COL, W_OR = 0x5000, 0x5080, 0x5084, 0x5084, 0x5085, 0x5086
# NES pad bits on $F5 (pressed-this-frame): A=$80 B=$40 Sel=$20 Start=$10 U=$08 D=$04 L=$02 R=$01
B_SEL, B_START, B_LEFT, B_RIGHT = 0x20, 0x10, 0x02, 0x01

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
STUDY_BLOB_EVAC = b"\x60" + b"\xFF" * 51


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
              OLD_STUDY_BLOB_EVAC_V82, OLD_STUDY_BLOB_EVAC_V2]),
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
    # PRG-RAM power-on init (SDRAM boots as garbage): magic byte at NAV_MAGIC
    a.ins16("LDA_abs", NAV_MAGIC); a.ins("CMP_imm", 0xA5); a.br("BEQ", "inited")
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
    if STUDY2P:
        # ---- DRSTUDY2P: driver-owned pause previews, ALL play modes (task #39; see flag block).
        # PRE-DISPATCH placement is load-bearing: it must run on 1P human hooks too ($04==0 never
        # reaches the play path), and during pause $46 stays 4. Part1 (EVAC v2) draws ONLY the
        # STUDY letters now -- probe round 2 proved the pause loop re-runs the draw call EVERY
        # spin frame, so any preview part1 wrote would stomp this block's writes each frame.
        # The driver therefore owns slots 37-40 outright: 1P layout when $0727==1, 2P when ==2.
        # Invisible in play (the game's OAM rebuild runs after this hook); owns the pause.
        a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 0x04); a.br("BNE", "s2p_no")
        # STUDY letters (part1 is a bare RTS now -- EVAC v3): tiles/X static per the probe's
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
        a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 0x04); a.br("BCC", "fc_no")
    a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BEQ", "fc_no")
    a.ins16("LDA_abs", VCOUNT_P1); a.br("BNE", "fc_chk2")
    a.ins16("LDA_abs", VSEEN1); a.br("BNE", "fc_clear")     # P1==0 counts only if it was ever >0
    a.label("fc_chk2")
    a.ins16("LDA_abs", VCOUNT_P2); a.br("BNE", "fc_no")
    a.ins16("LDA_abs", VSEEN2); a.br("BEQ", "fc_no")
    a.label("fc_clear")                                     # full clear -> own the frame (skip normal dispatch)
    a.ins16("LDA_abs", NAV_T); a.ins("AND_imm", 0x1F); a.ins("CMP_imm", 4); a.br("BCS", "fc_ret")
    if not HUMAN_P1:
        # $F5 is P1's controller latch. On a HUMAN_P1 cart P1 is a PERSON, so injecting
        # START here presses the human's button for them (spec P0.4). The human dismisses
        # their own STAGE CLEAR; the AI is P2 and never needed this.
        a.ins("LDA_imm", B_START); a.ins("STA_zp", 0xF5)    # inject START to dismiss STAGE CLEAR
    a.label("fc_ret"); a.ins("RTS")
    a.label("fc_no")
    a.ins16("LDA_abs", 0x0046); a.ins("CMP_imm", 0x04); a.br("BNE", "not_play")
    a.ins("LDA_zp", 0x04); a.br("BNE", "go_ai")            # $04 != 0 -> VS-CPU AI
    if NAVFIX:
        # DIAGNOSTIC: play-mode with $04==0 AND $0727==1 = a 1P game or the attract demo = the nav
        # did NOT land VS-CPU. Latch NAV_1P (persists this cold boot) so a gauntlet can read it.
        a.ins16("LDA_abs", 0x0727); a.ins("CMP_imm", 1); a.br("BNE", "np_1p_done")
        a.ins("LDA_imm", 1); a.ins16("STA_abs", NAV_1P)
        a.label("np_1p_done")
    a.ins("RTS")
    a.label("go_ai")
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
    if USE_SEEDS:
        a.ins16("LDA_abs", MATCH_ACTIVE); a.br("BNE", "ga_on")  # first play frame of this match:
        a.ins16("LDA_abs", NAV_T); a.ins("ORA_imm", 0x01); a.ins16("STA_abs", SEED1)   # root seed
        a.ins("EOR_imm", 0xA4); a.ins16("STA_abs", SEED2)       # bit0 kept -> both odd, distinct
        a.label("ga_on")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", MATCH_ACTIVE)   # play started -> arm full-clear detect
    a.ins16("LDA_abs", VCOUNT_P1); a.br("BEQ", "ga_v2"); a.ins("LDA_imm", 1); a.ins16("STA_abs", VSEEN1)
    a.label("ga_v2")
    a.ins16("LDA_abs", VCOUNT_P2); a.br("BEQ", "ga_vd"); a.ins("LDA_imm", 1); a.ins16("STA_abs", VSEEN2)
    a.label("ga_vd")
    a.jmp("dispatch")
    a.label("not_play")
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
        a.ins("LDA_imm", bits); a.ins("STA_zp", 0xF5)
        a.ins16("STA_abs", 0x6148)                          # DBG: last injected
        a.ins16("INC_abs", 0x614B)                          # DBG: inject count
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
    # NOTE: do NOT re-arm DWELL_CNT here. This runs on the FIRST hook that injects START, so the
    # next hook of the SAME press window re-enters the dwell hold and RTSes before inject() --
    # the press lasts one hook. The game ANDs TWO raw passes of $F5, so a 1-hook press can never
    # register and the title re-dwells forever. Re-arm lives in the mode-8 intro block instead.
    a.ins("RTS")

    # ================= play-mode CPU-vs-CPU driver (time-shared FPGA) =================
    a.label("dispatch")
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
    a.ins("LDA_imm", 1); a.ins16("STA_abs", PEND2)
    a.ins("LDA_imm", 15); a.ins16("STA_abs", DELAY2)        # ~3 frames settle before upload
    a.ins("LDA_imm", 0)
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
        a.ins16("LDA_abs", wdone); a.br("BEQ", f"{L}_search")    # DONE==0 -> still searching
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
            a.ins16("LDA_abs", W_TROW); a.ins16("STA_abs", TUCK_R2)
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
        a.ins16("LDA_abs", wretry); a.br("BEQ", f"{L}_rt"); a.jmp(f"{L}_done"); a.label(f"{L}_rt")
        a.ins("LDA_imm", 1); a.ins16("STA_abs", wretry); a.ins16("STA_abs", pend)
        a.jmp(f"{L}_done")
        a.label(f"{L}_start")            # start a search: upload board+colors to THIS copro, GO
        if TUCK and idx == 2:
            # a new search invalidates any tuck from the PREVIOUS pill. Without this, stale
            # descriptor bytes would steer the next capsule to a pocket that no longer exists
            # -- the same class of bug as the uninitialised PEND/LASTY cold-state defect (P0.3).
            a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", TUCK_C2)
        a.ins16("LDA_abs", pend); a.br("BNE", f"{L}_st1"); a.jmp(f"{L}_done"); a.label(f"{L}_st1")
        a.ins16("LDA_abs", delay); a.br("BEQ", f"{L}_st2"); a.jmp(f"{L}_done"); a.label(f"{L}_st2")
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

    # (time-shared d_start / start_p1 / start_p2 removed: handle() above starts each player's
    #  search on its own copro.)

    # ---- act: steer BOTH players toward their published targets ----
    a.label("act")
    a.jsr("freeze_pending")
    # P2 first (only if we're not currently freezing it)
    a.ins16("LDA_abs", ARMED2); a.br("BEQ", "act_p2")      # not searching P2 -> steer it
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
            a.ins16("LDA_abs", ROT_DONE2); a.br("BNE", "nf2_col_only")
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
        w.label("w_warm")
        w.ins16("LDA_abs", BUSY); w.br("BEQ", "w_run"); w.ins("RTS")   # already running -> bail (no bank touch)
        w.label("w_run")
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

    tmp = OUT + ".2bank"
    open(tmp, "wb").write(rom)
    expand(tmp, OUT, new_bank_bytes=bytes(bank))
    import os
    os.remove(tmp)
    out = bytearray(open(OUT, "rb").read())
    out[6] = (out[6] & 0x0F) | 0x40      # mapper 100 = 0x64
    out[7] = (out[7] & 0x0F) | 0x60
    open(OUT, "wb").write(out)
    print(f"wrote {OUT} (mapper 100, AUTO-NAV VS-CPU L11, FPGA coprocessor)")


if __name__ == "__main__":
    main()
