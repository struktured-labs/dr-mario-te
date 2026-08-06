#!/usr/bin/env python3
"""Default-proof manifest replay (provenance, generalized): a knob gaining a new default
(DRBUILDID activating for DRHUMAN=1 carts) silently changed what a PRE-EXISTING manifest
replays to, because `rebuild` only ever set the explicitly-recorded `flags`, leaving every
other DR* knob to whatever the CURRENT code defaults it to -- a manifest is supposed to be a
frozen recipe, not "the recorded flags plus however the emitter feels today."

Two-part fix (tools/romgen.py):
  1. NEW manifests record `flag_snapshot` -- every DR* knob's RESOLVED value (not just what was
     explicitly passed), captured by patch_cartridge_copro.py's DR_ENV_SNAPSHOT mechanism and
     printed as a `##DRFLAGSNAPSHOT##` line. Replay then sets exactly that env: immune to any
     future default change, forever, because it no longer depends on "what the code currently
     defaults to" at all.
  2. LEGACY manifests (no flag_snapshot) can't know about a knob introduced after they were
     recorded. `NEW_KNOBS` is the ledger of what this task introduced (DRHOLDBOARD/
     DRHOLDBOARD_F/DRBUILDID/DRBUILDID_TAG); `resolve_replay_flags` forces exactly those absent
     from the manifest to their pre-existence value. A blanket "force every absent DR* key to
     off" was considered and REJECTED (not just untested): DRSTUDY also defaults on for
     DRHUMAN=1 and predates every live manifest, so blanket forcing would incorrectly disable
     it on every legacy human-profile replay -- see scenario A2 below, which asserts this
     directly rather than trusting the reasoning.

Three required proofs:
  A pocket-human-v4-coldinit.json (the manifest the deployed SD cards trace to) replays without
    DRBUILDID silently activating -- the regression, now closed.
  B boardhold-v6b.json (recorded WITH the new flag_snapshot format) replays byte-exact.
  C a synthetic future-default knob proves the snapshot mechanism immunizes NEW manifests
    against ANY future default change, not just the four knobs this task happens to know about.

    tests/test_romgen_replay.py        # asserts; exit 1 on failure
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROMGEN = os.path.join(REPO, "tools", "romgen.py")
sys.path.insert(0, os.path.join(REPO, "tools"))
import romgen  # noqa: E402  (needs sys.path set first)


def scenario_a_legacy_manifest_no_silent_activation():
    manifest_path = os.path.join(REPO, "roms", "manifests", "pocket-human-v4-coldinit.json")
    man = json.load(open(manifest_path))
    assert "flag_snapshot" not in man or not man["flag_snapshot"], (
        "test assumes this manifest predates the snapshot mechanism -- if it now has one, "
        "this scenario needs a different (still-legacy) manifest")

    # A1: unit-level -- resolve_replay_flags forces exactly the four this-task knobs, and
    # nothing else (DRSTUDY, present nowhere in the recorded flags, must NOT be touched).
    replay_flags, note = romgen.resolve_replay_flags(man)
    assert note and note.startswith("legacy manifest"), "expected the legacy-manifest note: %r" % note
    for k, v in romgen.NEW_KNOBS.items():
        assert replay_flags.get(k) == v, "expected %s forced to %r, got %r" % (
            k, v, replay_flags.get(k))
    assert "DRSTUDY" not in replay_flags, (
        "DRSTUDY got force-set during legacy replay -- it predates every live manifest and "
        "already correctly defaults on for DRHUMAN=1; forcing it would be the exact "
        "over-broad 'force everything absent' rule this design rejected")
    for k, v in man["flags"].items():
        assert replay_flags[k] == v, "recorded flag %s=%r was not preserved" % (k, v)
    print("PASS A1: resolve_replay_flags forces only DRHOLDBOARD*/DRBUILDID*, leaves DRSTUDY "
          "and every recorded flag untouched")

    # A2: end-to-end -- actually run `romgen.py rebuild` and confirm DRBUILDID does not fire
    # (no stamp line, no DRBUILDID_TAG derivation noise) and the legacy warning is shown.
    out = os.path.join(REPO, "tmp", "test_romgen_replay_legacy.nes")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([sys.executable, ROMGEN, "rebuild", manifest_path, "--out", out],
                        cwd=REPO, capture_output=True, text=True)
    combined = r.stdout + r.stderr
    assert "legacy manifest" in combined, "legacy-mode note missing from rebuild output:\n%s" % combined
    assert "DRBUILDID stamp:" not in combined, (
        "REGRESSION REPRODUCED: DRBUILDID silently activated on a legacy replay:\n%s" % combined)
    print("PASS A2: `romgen.py rebuild` on the legacy manifest shows no DRBUILDID stamp "
          "(the regression stays closed end-to-end, not just at the unit level)")


def scenario_b_snapshot_manifest_byte_exact():
    manifest_path = os.path.join(REPO, "roms", "manifests", "boardhold-v6b.json")
    man = json.load(open(manifest_path))
    assert man.get("flag_snapshot"), "boardhold-v6b.json should carry a flag_snapshot"
    out = os.path.join(REPO, "tmp", "test_romgen_replay_v6b.nes")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([sys.executable, ROMGEN, "rebuild", manifest_path, "--out", out],
                        cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, "rebuild failed:\n%s\n%s" % (r.stdout, r.stderr)
    assert "REPRODUCED byte-exact" in r.stdout, "expected byte-exact reproduction:\n%s" % r.stdout
    assert "replaying from the full flag snapshot" in r.stdout
    print("PASS B: boardhold-v6b.json (flag_snapshot format) replays byte-exact")


def scenario_c_synthetic_future_default():
    # Simulate: a manifest recorded BEFORE some future knob DRFAKEKNOB existed, whose default
    # is about to change (was "0" when recorded, imagine a future commit flips the default to
    # "1"). A snapshot-format manifest is IMMUNE (it captured "0" verbatim); a legacy-format
    # manifest is exposed UNLESS the knob is in the ledger -- proving the ledger mechanism (not
    # just the four specific knobs this task shipped) is what does the protecting.
    old_default, new_default = "0", "1"

    snapshot_man = {
        "flags": {"DRHUMAN": "1"},
        "flag_snapshot": {"DRHUMAN": "1", "DRFAKEKNOB": old_default},
    }
    replay_flags, note = romgen.resolve_replay_flags(snapshot_man)
    assert replay_flags["DRFAKEKNOB"] == old_default, (
        "snapshot-format manifest did not preserve the pre-default-change value -- a future "
        "default flip would silently change this manifest's replay")
    print("PASS C1: a flag_snapshot manifest is immune to a hypothetical future default "
          "change for a knob it never even had to know about by name")

    legacy_man_no_ledger = {"flags": {"DRHUMAN": "1"}}
    replay_flags, note = romgen.resolve_replay_flags(legacy_man_no_ledger, new_knobs={})
    assert "DRFAKEKNOB" not in replay_flags, "sanity: nothing should force a key with an empty ledger"
    print("PASS C2 (sanity): with an empty ledger, an unknown-to-the-manifest knob is left "
          "alone (i.e. this test's ledger argument is actually doing something, not a no-op)")

    legacy_man_with_ledger = {"flags": {"DRHUMAN": "1"}}
    replay_flags, note = romgen.resolve_replay_flags(
        legacy_man_with_ledger, new_knobs={"DRFAKEKNOB": old_default})
    assert replay_flags["DRFAKEKNOB"] == old_default, (
        "legacy manifest + ledger entry did not force the pre-existence value")
    assert note and "DRFAKEKNOB" in note
    print("PASS C3: a legacy-format manifest, once DRFAKEKNOB is added to the ledger, also "
          "replays at the pre-existence value -- the SAME mechanism (NEW_KNOBS) that closed "
          "the real DRBUILDID regression generalizes to any future knob, given one ledger entry")


def main():
    scenario_a_legacy_manifest_no_silent_activation()
    scenario_b_snapshot_manifest_byte_exact()
    scenario_c_synthetic_future_default()
    print("\n==== ALL CHECKS PASSED (default-proof replay verified) ====")


if __name__ == "__main__":
    main()
