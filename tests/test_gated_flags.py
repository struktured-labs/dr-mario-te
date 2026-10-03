#!/usr/bin/env python3
"""Regression: the suppressed-flag guard's DECLARED gate defaults must match the emitter's REAL ones.

_GATED_FLAGS (patch_cartridge_copro.py) refuses a build when a requested default-off flag's gate is off. It
decides "gate off" from the gate's declared default when the gate is not in the env. DEFECT (found 2026-10-03
while adding DRSTUDYEND): the DRSTUDYCOUNTS entry declared DRSTUDY's default as "0", but the emitter resolves
STUDY = env DRSTUDY, default "1" if DRHUMAN=1 else "0". So a human cart that leaves DRSTUDY unset -- STUDY on,
counters emitted -- was REFUSED as "suppressed": a false refusal, the mirror image of the 2026-09-03 silent
suppression the guard exists for.

  R1 THE DEFECT: DRHUMAN=1, DRSTUDY unset, DRSTUDYCOUNTS=1 builds; it is byte-identical to the same build with
     DRSTUDY=1 explicit, and differs from DRSTUDYCOUNTS=0 (the counters really are emitted).
  R2 THE GUARD STILL GUARDS: DRHUMAN=1, DRSTUDY=0, DRSTUDYCOUNTS=1 refuses, naming DRSTUDYCOUNTS (the
     2026-09-03 d07d6329 defect stays caught); DRALLOW_GATED=1 overrides it loudly.
  R3 NON-HUMAN DEFAULT: DRHUMAN unset, DRSTUDY unset, DRSTUDYCOUNTS=1 refuses (STUDY defaults OFF there).
  R4 EVERY DRSTUDY-GATED ENTRY mirrors the emitter: for DRHUMAN in {0, 1}, each _GATED_FLAGS entry whose gate is
     DRSTUDY declares the same default the emitter's STUDY resolves to -- so the next such entry cannot regress.

Run: python tests/test_gated_flags.py   (needs the untracked drmario_v28cs.nes)
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(REPO, "tmp", "gated_flags_test")
COUCH_ENV = os.path.join(REPO, "experiments", "cvx", "sota_20260927_couch_flags.env")


def couch(**over):
    flags = dict(kv.split("=", 1) for kv in open(COUCH_ENV).read().split())
    for k, v in over.items():
        if v is None:
            flags.pop(k, None)
        else:
            flags[k] = str(v)
    return flags


def run(flags, args=("patch_cartridge_copro.py",)):
    env = {k: v for k, v in os.environ.items() if not k.startswith("DR")}
    env.update(flags)
    return subprocess.run([sys.executable, *args], cwd=REPO, env=env, capture_output=True, text=True)


def build(name, flags):
    r = run(flags)
    if r.returncode != 0:
        return None, r
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, f"{name}.nes")
    os.replace(os.path.join(REPO, "drmario_copro.nes"), path)
    return open(path, "rb").read(), r


def main():
    fails = []
    # R1
    implicit, r = build("human_study_unset", couch(DRSTUDY=None, DRSTUDYCOUNTS="1"))
    explicit, _ = build("human_study_1", couch(DRSTUDY="1", DRSTUDYCOUNTS="1"))
    nocount, _ = build("human_study_1_nocounts", couch(DRSTUDY="1", DRSTUDYCOUNTS="0"))
    if implicit is None:
        fails.append("R1 FAIL: DRHUMAN=1 + DRSTUDY unset + DRSTUDYCOUNTS=1 was REFUSED (false refusal):\n    "
                     + "\n    ".join(l for l in r.stdout.splitlines() if "SUPPRESSED" in l or "REFUSING" in l))
    elif implicit != explicit or explicit == nocount:
        fails.append(f"R1 FAIL: implicit==explicit {implicit == explicit}, counters emitted {explicit != nocount}")
    else:
        print("R1 PASS  human cart, DRSTUDY unset + DRSTUDYCOUNTS=1 builds == DRSTUDY=1 explicit; counters emitted")
    # R2
    _, r = build("human_study_0", couch(DRSTUDY="0", DRSTUDYCOUNTS="1"))
    over, r2 = build("human_study_0_allow", couch(DRSTUDY="0", DRSTUDYCOUNTS="1", DRALLOW_GATED="1"))
    if r.returncode == 0 or "##SUPPRESSED-FLAG## DRSTUDYCOUNTS" not in r.stdout:
        fails.append("R2 FAIL: DRSTUDY=0 + DRSTUDYCOUNTS=1 was not refused")
    elif over is None or "DRALLOW_GATED=1 set" not in r2.stdout:
        fails.append("R2 FAIL: DRALLOW_GATED=1 did not override loudly")
    else:
        print("R2 PASS  DRSTUDY=0 + DRSTUDYCOUNTS=1 refuses (names DRSTUDYCOUNTS); DRALLOW_GATED=1 overrides loudly")
    # R3
    _, r = build("cvc_study_unset", {"DRSTUDYCOUNTS": "1"})
    if r.returncode == 0 or "##SUPPRESSED-FLAG## DRSTUDYCOUNTS" not in r.stdout:
        fails.append(f"R3 FAIL: non-human cart, DRSTUDY unset + DRSTUDYCOUNTS=1 was not refused (rc={r.returncode})")
    else:
        print("R3 PASS  non-human cart, DRSTUDY unset + DRSTUDYCOUNTS=1 refuses (STUDY defaults OFF)")
    # R4
    probe = ("import json, patch_cartridge_copro as d; "
             "print(json.dumps({'study': d.STUDY, 'entries': [e[:4] for e in d._GATED_FLAGS if e[1] == 'DRSTUDY']}))")
    for human in ("0", "1"):
        r = run({"DRHUMAN": human}, args=("-c", probe))
        info = json.loads(r.stdout.strip().splitlines()[-1])
        want = "1" if info["study"] else "0"
        bad = [e for e in info["entries"] if e[3] != want]
        if bad:
            fails.append(f"R4 FAIL: DRHUMAN={human}: STUDY defaults to {want} but entries declare {bad}")
        else:
            print(f"R4 PASS  DRHUMAN={human}: STUDY default {want}; all {len(info['entries'])} DRSTUDY-gated entries agree")
    if fails:
        print("\n".join(fails))
        print("FAIL test_gated_flags")
        sys.exit(1)
    print("ALL PASS test_gated_flags")


if __name__ == "__main__":
    main()
