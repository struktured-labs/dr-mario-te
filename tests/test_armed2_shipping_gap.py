#!/usr/bin/env python3
"""Day-mission part 2: prove the stale-ARMED2 soft-relaunch defect (P2.2) on the ACTUAL shipping
MiSTer human-vs-Stomper flag set (roms/manifests/mister-human-studycounts.json), not the generic
3-flag `mister_human` stand-in test_cart_matrix.py already covers.

BACKGROUND (see driver-nav commit history + patch_cartridge_copro.py's own comments): the fix for
this defect family already exists and is already tested -- DRPENDBOUND (P0.2), DRCOLDINIT (P0.3/
P2.2), DRSTALLWD (task #40 generalization), DRWRETRY are all coded, flagged, and proven by
test_stallwd.py and test_cart_matrix.py's defect_p2.2/fixed_p2.2 rows. What was missing is
narrower than "write the fix": `roms/manifests/mister-human-studycounts.json` (tag commit ea2f6b7,
message "human-vs-Stomper MiSTer cart (full armor + pausefix + MiSTer tempo)") sets DRBUSYESC,
DRPENDBOUND, DRSTALLWD, DRWRETRY -- but NOT DRCOLDINIT. Since this profile has DRNOFREEZE=1, and
the P0.3/P2.2 reset block in patch_cartridge_copro.py is gated `if COLDINIT or not NO_FREEZE:`,
`not NO_FREEZE` is False here too -- so the ENTIRE match-start reset (PEND1/PEND2/DELAY1/DELAY2/
LASTY1/LASTY2, and under COLDINIT specifically ARMED2/WDOG2/WDOGH2/WRETRY2) is skipped entirely
on the cart the human actually plays against on MiSTer, despite the commit message's "full armor"
claim. This is the actual, concrete gap -- not a missing fix, a missing flag on one manifest.

Reuses test_cart_matrix.py's build() and defect_p22_relaunch() UNCHANGED (does not modify that
file) -- this is a new, narrowly-scoped script proving the SAME validated mechanism against the
SPECIFIC real shipping flags, which the shared CLASSES table's generic `mister_human` stand-in
(only DRHUMAN/DRNOFREEZE/DRRECOMMIT_NOFREEZE) does not exercise.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_cart_matrix as M  # noqa: E402  -- reuse build()/defect_p22_relaunch(), not copied

# exact flags from roms/manifests/mister-human-studycounts.json (git ea2f6b7), MINUS DRCOLDINIT
# (the gap) for the OFF/shipping-as-is arm.
SHIPPING_FLAGS_NO_COLDINIT = {
    "DRBUSYESC": "1", "DRHUMAN": "1", "DRMINTHINK": "12", "DRNAVDWELL": "0",
    "DRNOFREEZE": "1", "DRPENDBOUND": "1", "DRRECOMMIT_NOFREEZE": "1",
    "DRSLAM_KOPEN": "32", "DRSTALLWD": "1", "DRSTUDYCOUNTS": "1", "DRWRETRY": "1",
}
FIXED_FLAGS = dict(SHIPPING_FLAGS_NO_COLDINIT, DRCOLDINIT="1")

_ALL_DR_ENV = tuple(k for k in os.environ if k.startswith("DR")) + M._FLAGS + (
    "DRBUSYESC", "DRMINTHINK", "DRSTALLWD", "DRSTUDYCOUNTS", "DRWRETRY", "DRCOLDINIT",
)


def clean_build(flags):
    for k in set(_ALL_DR_ENV):
        os.environ.pop(k, None)
    return M.build(dict(flags))


results = []


def check(name, ok, detail):
    results.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


print("=" * 78)
print("Stale-ARMED2 soft-relaunch (P2.2), on the REAL mister-human-studycounts shipping flags")
print("=" * 78)

P_off, u_off, L_off = clean_build(SHIPPING_FLAGS_NO_COLDINIT)
healthy_off = M.defect_p22_relaunch(P_off, u_off, L_off)
check("AS-SHIPPED (no DRCOLDINIT): defect REPRODUCES -- first pill after relaunch does NOT "
      "search promptly", not healthy_off,
      f"defect_p22_relaunch()={healthy_off} (want False = unhealthy = defect present)")

P_on, u_on, L_on = clean_build(FIXED_FLAGS)
healthy_on = M.defect_p22_relaunch(P_on, u_on, L_on)
check("WITH DRCOLDINIT=1: CURED -- first pill after relaunch searches promptly",
      healthy_on, f"defect_p22_relaunch()={healthy_on} (want True = healthy)")

# byte-exactness: DRCOLDINIT defaults to "0" (off) already, so unset == explicit "0" -- confirm
# on THIS exact profile rather than assume it from the flag's general default.
for k in set(_ALL_DR_ENV):
    os.environ.pop(k, None)
c_unset = M.build(dict(SHIPPING_FLAGS_NO_COLDINIT))[1]        # [1] = unit1 (assembled bytes)
for k in set(_ALL_DR_ENV):
    os.environ.pop(k, None)
c_explicit_off = M.build(dict(SHIPPING_FLAGS_NO_COLDINIT, DRCOLDINIT="0"))[1]
check("DRCOLDINIT unset == explicit '0' (byte-exact, same shipping profile)",
      bytes(c_unset) == bytes(c_explicit_off), f"{len(c_unset)} bytes each")

print()
n_ok = sum(1 for _, ok in results if ok)
print(f"==== {n_ok}/{len(results)} checks passed ====")
sys.exit(0 if n_ok == len(results) else 1)
