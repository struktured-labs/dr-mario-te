#!/usr/bin/env python3
"""Maps a CANDLIST entry's orientation (tuck_scan_v3's own ring: H=0,V=1,RH=2,RV=3, see
tuck_scan_v3_ref.py) to the o4 value (test_depth2.py's convention: 0-1=VERTICAL,
2-3=HORIZONTAL) that D_BO/S_BEST_O must carry when a tuck candidate wins -- the driver's
existing pill-rotation steering consumes D_BO as an o4 value, so publishing the raw
tuck-ring orient there would be silently wrong (a real trap: these are DIFFERENT encodings
used elsewhere in this same codebase for genuinely different purposes -- flagged during
stage-2 scratch work when a test initially used o4=0 expecting horizontal and got vertical
instead, see test_tuck_score.py's test_clearing() comment).

DERIVATION (not guessed -- cross-checked against wr_cmd's CMD4 colour-swap rule in
test_search_d3.attach_engine_emu, the SAME rule _e_node's real RTL implements):
  ta, tb = (cb, ca) if (o4 & 1) else (ca, cb)     # applied to (offa, offb) = (top,bottom)
                                                    # for vertical, (left,right) for horizontal
tuck_scan_v3_ref._FLIP = {H:0, V:1, RH:1, RV:0}  (flip=0 -> cell0 gets colour A)
  VERTICAL:   cell0 = top (offa).    o4=0 (even) -> top=ca=A  (flip 0) -> RV (flip 0)
                                      o4=1 (odd)  -> top=cb=B  (flip 1) -> V  (flip 1)
  HORIZONTAL: cell0 = left (offa).   o4=2 (even) -> left=ca=A (flip 0) -> H  (flip 0)
                                      o4=3 (odd)  -> left=cb=B (flip 1) -> RH (flip 1)
So: H->2, V->1, RH->3, RV->0.
"""
from __future__ import annotations

H, V, RH, RV = 0, 1, 2, 3

TUCK_ORIENT_TO_O4 = {H: 2, V: 1, RH: 3, RV: 0}
O4_TABLE = [TUCK_ORIENT_TO_O4[o] for o in (H, V, RH, RV)]   # index by tuck orient 0..3 -> o4


def _self_check():
    """Cross-check the derivation directly against wr_cmd's own colour rule (no
    re-derivation -- literally the same formula test_search_d3.attach_engine_emu uses) and
    tuck_scan_v3_ref's _FLIP, for representative colours, both orientation classes."""
    fails = 0
    ca, cb = 1, 2   # arbitrary, distinct
    for orient in (H, V, RH, RV):
        o4 = TUCK_ORIENT_TO_O4[orient]
        # wr_cmd rule, as the executor's rotation would produce for this o4:
        ta_wr, tb_wr = (cb, ca) if (o4 & 1) else (ca, cb)
        # tuck_scan_v3_ref's _FLIP rule, as land_place_at actually wrote:
        flip = {H: 0, V: 1, RH: 1, RV: 0}[orient]
        ta_tuck, tb_tuck = (ca, cb) if flip == 0 else (cb, ca)
        ok = (ta_wr, tb_wr) == (ta_tuck, tb_tuck)
        tag = "H V RH RV".split()[orient]
        print(f"  [{tag}] o4={o4}: wr_cmd-style=({ta_wr},{tb_wr}) "
              f"tuck-flip-style=({ta_tuck},{tb_tuck})  {'OK' if ok else 'FAIL'}")
        if not ok:
            fails += 1
    return fails


if __name__ == "__main__":
    import sys
    fails = _self_check()
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'}")
    sys.exit(0 if fails == 0 else 1)
