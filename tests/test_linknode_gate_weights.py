"""Contracts for the HSV / DIST gates' linknode level that need no Verilator and no combo_term tree.

Each gate lives in its own directory with same-named helper modules (common, pyleaf, rtlparse),
so each check runs in a fresh interpreter rooted in that gate's directory.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GATES = {g: os.path.join(ROOT, "experiments", g, "gate") for g in ("hsv", "dist")}


def _run(gate, code):
    r = subprocess.run([sys.executable, "-c", code], cwd=GATES[gate], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


_WEIGHTS = r"""
import json, gate as G
out = {"default": G.parse_chain_weights(None), "with255": G.parse_chain_weights("0,45,90,135,255"),
       "hex": G.parse_chain_weights("0x87"), "label135": G.chain_weight_label(135),
       "label255": G.chain_weight_label(255), "label7": G.chain_weight_label(7)}
for bad in ("256", "-1", "x", " , "):
    try:
        G.parse_chain_weights(bad)
    except ValueError:
        out["rej_" + bad] = True
print(json.dumps(out))
"""


def test_chain_weights_default_includes_540_and_255_is_opt_in():
    for gate in GATES:
        o = _run(gate, _WEIGHTS)
        assert o["default"] == [0, 45, 90, 135], gate
        assert o["with255"] == [0, 45, 90, 135, 255], gate
        assert o["hex"] == [135]
        assert "540" in o["label135"] and "1020" in o["label255"] and "28" in o["label7"]
        for bad in ("256", "-1", "x", " , "):
            assert o.get("rej_" + bad), (gate, bad)


_EXPECTED = r"""
import json, gate as G
# one synthetic legal, non-winning record: parent and child both carry a high spawn-column virus
# at row 0, col 4 (HSV) and a lone virus at row 15, col 0 (a DIST target candidate)
board = ["ff"] * 128
board[0 * 8 + 4] = "d1"
board[15 * 8 + 0] = "d0"
rec = board + ["0", "0", "0", "1", "1"] + ["1", "2", "2", "2", "500", "4000", "0"] + board
body = rec * 9
out = {}
for name, defs in (("plain", []), ("hsv", ["DRHSV", "DRLEV_VNPF"]), ("dist", ["DRHSV", "DRDIST"])):
    try:
        recs, st = G.link_expected(body, 9, defs)
        out[name] = {"sco": [r[138] for r in recs], "len": [len(r) for r in recs],
                     "tgt": [r[-1] for r in recs] if len(recs[0]) > 268 else None, "st": st}
    except ValueError as e:
        out[name] = {"err": str(e)}
try:
    G.link_expected(body, 9, ["DRDIST"])
except ValueError as e:
    out["dist_without_hsv"] = str(e)
print(json.dumps(out))
"""


def test_spec_terms_adjust_only_the_leaf_score():
    o = _run("hsv", _EXPECTED)
    assert o["plain"]["sco"] == ["4000"] * 9 and o["plain"]["st"]["sco_changed"] == 0
    # HSV: one high spawn-column virus -> -512, inside the s16 combine; imm/chain untouched
    assert o["hsv"]["sco"] == [str(4000 - 512)] * 9
    assert o["hsv"]["st"]["hsv_nonzero"] == 9 and o["hsv"]["st"]["chained_and_term"] == 9
    assert set(o["hsv"]["len"]) == {268}
    assert "dist" in o["dist"]["err"].lower()          # the HSV gate does not model DIST

    d = _run("dist", _EXPECTED)
    assert d["hsv"]["sco"] == [str(4000 - 512)] * 9
    st = d["dist"]["st"]
    assert set(d["dist"]["len"]) == {269}               # a target token is appended
    tg = [int(x) for x in d["dist"]["tgt"]]
    assert tg[0] == 0 and tg[8] == 0                    # k % 8 == 0 -> no target
    assert all(t & 0x80 for t in tg[1:8])
    assert st["d_nonzero"] >= 1 and st["tgt_valid"] == 7
    for s, t in zip(d["dist"]["sco"], tg):
        assert int(s) <= 4000 - 512                    # D only ever subtracts
        if not t & 0x80:
            assert int(s) == 4000 - 512
    assert "DRHSV" in d["dist_without_hsv"]


def test_tb_summary_parser():
    text = """
=========== LINK/CHAIN NODE CO-SIM ===========
cases            : 7282   (legal+checked 7089)   DRCHAIN dose 540
PASS             : 7282/7282
  legal mismatch : 0
  cells          : 0
  viruses        : 0
  CHAIN depth    : 0
  imm            : 0
  sco            : 3
  win            : 0
  COLOUR plane   : 0
  LINK plane     : 0
cases with chain > 1 : 133

OVERALL: PASS
"""
    code = "import json, gate as G; print(json.dumps(G.parse_tb_summary(%r)))" % text
    for gate in GATES:
        s = _run(gate, code)
        assert s["cases"] == 7282 and s["checked"] == 7089 and s["pass"] == 7282
        assert s["chained"] == 133 and s["bad_sco"] == 3 and s["bad_imm"] == 0
        assert s["bad_colour"] == 0 and s["bad_link"] == 0 and s["overall_pass"] is True
