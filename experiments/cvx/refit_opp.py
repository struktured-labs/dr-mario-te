"""Opponent resolution incl. the 2026-10 corrected send fits (couch tracker bug: same-colour consecutive spawns were read
as garbage volleys, inflating the 202609 fits ~2x; experiments/couch_forensics/RESULT_SENDS_REFIT_202610.md).

  owner202610  Owner202609 class on owner_fit_202610.json (2.36 volleys/min L11, sizes 89/8/3%)
  lulu202610   Lulu202609 class on lulu_fit_202610.json (2.56 volleys/min, PROVISIONAL n=2 games)
  anything else -> opp_run.make_opponent (owner0804, owner202609, lulu202609, striker*)
Race volley rates (vs_race lam, volleys/min) for the same refits: LAM_OWNER_202610 = 2.36, LAM_LULU_202610 = 2.56.
⚠ Only gaps / size pmf / p_double come from the fit; the classes' COLUMN model is unchanged (2-cell: 23% one column),
although the refit found 2-cell sends always land in two columns 4 apart.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FITS = os.path.join(HERE, "..", "couch_forensics")
LAM_OWNER_202610 = 2.36
LAM_LULU_202610 = 2.56


def make_opponent(name):
    if name == "owner202610":
        import opp_owner202609 as O9
        o = O9.Owner202609(fit_path=os.path.join(FITS, "owner_fit_202610.json")); o.name = name
        return o
    if name == "lulu202610":
        import opp_lulu202609 as L9
        o = L9.Lulu202609(fit_path=os.path.join(FITS, "lulu_fit_202610.json")); o.name = name
        return o
    import opp_run as OR
    return OR.make_opponent(name)
