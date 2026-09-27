#!/usr/bin/env python3
"""Defect cases for analyze_framedense.py -- the VERDICT SCRIPT gets the killed-mutant
treatment too (gate standard: "extend it to the ANALYSIS code, not only the kernel";
a verdict script that has only ever seen one real table has never been shown to
discriminate either).

Every case is a synthetic hooks.csv + framedense.log straddling a registered boundary.
Run: python3 tools/gate/test_analyze_framedense.py
"""
import os, shutil, tempfile, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_framedense as A

HDR = ("frame,mode,tgt_o2,tgt_c2,tuck_c2,tuck_r2,stable_ct2,last_ori2,rot_done2,armed2,"
       "c0381,c0382,px0385,py0386,b0387,ori03a5,pub_or,pub_dbl,pub_frame,store_pc,store_n,"
       "served_or,elig,anom\n")


def row(f, o2=3, st=20, tc=255, tr=16, cA=0x51, cB=0xA1, pub=0, py=10):
    return (f"{f},4,{o2},3,{tc},{tr},{st},0,1,0,{cA},{cB},3,{py},0,0,{pub},1,{f},4660,1,"
            f"{pub},0,0\n")


def build(d, rows, arm, extra=None):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "hooks.csv"), "w") as fh:
        fh.write(HDR)
        fh.writelines(rows)
    fields = dict(tag="t", arm=arm, cart="c", cartid="x", nonce="n", w="$5200", tfind="synth",
                  frames=len(rows), mode4=len(rows), pills=1, goes=1, dones=1, dblsearch=1,
                  tuckpub=0, stores=1, pc_ok=1, pc_fail=0, matches_started=1, matches_ended=0,
                  clean_ends=0, ABORT_4to0=0, dblrows=0, settledrows=0,
                  N=0, k_naive=0, k_strict=0, k_pubodd=0, N_tuckrow=0, k_tuckrow=0,
                  csvrows=len(rows), stalls=0, resets=0, resetmode="reset", N_ply=0, k_ply=0,
                  orientknob=-1)
    if extra:
        fields.update(extra)
    with open(os.path.join(d, "framedense.log"), "w") as fh:
        fh.write("SUMMARY " + " ".join(f"{k}={v}" for k, v in fields.items()) + "\n")


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case("k=0 at N=3000 -> CLOSED-BENIGN")
def _(d):
    build(d, [row(i) for i in range(3000)], "A")
    a = A.analyse(f"{d}/hooks.csv")
    assert a["N"] == 3000 and a["k_strict"] == 0, a
    return A.verdict("A", a)[0] == "CLOSED-BENIGN"


@case("k=0 at N=2999 -> UNDERPOWERED (the N>=3000 half of the band is load-bearing)")
def _(d):
    build(d, [row(i) for i in range(2999)], "A")
    return A.verdict("A", A.analyse(f"{d}/hooks.csv"))[0] == "UNDERPOWERED"


@case("k=1 at N=3000 -> RARE-REAL")
def _(d):
    rows = [row(i) for i in range(2999)] + [row(9999, o2=1)]
    build(d, rows, "A")
    a = A.analyse(f"{d}/hooks.csv")
    assert a["k_strict"] == 1, a
    return A.verdict("A", a)[0] == "RARE-REAL"


@case("k/N just above 0.5% -> REAL")
def _(d):
    rows = [row(i) for i in range(2984)] + [row(9000 + i, o2=2) for i in range(16)]
    build(d, rows, "A")
    a = A.analyse(f"{d}/hooks.csv")
    assert a["k_strict"] / a["N"] > 0.005, a
    return A.verdict("A", a)[0] == "REAL"


@case("k/N just below 0.5% -> RARE-REAL, not REAL")
def _(d):
    rows = [row(i) for i in range(2985)] + [row(9000 + i, o2=2) for i in range(15)]
    build(d, rows, "A")
    a = A.analyse(f"{d}/hooks.csv")
    assert a["k_strict"] / a["N"] <= 0.005, a
    return A.verdict("A", a)[0] == "RARE-REAL"


@case("arm B at 19% -> VOID")
def _(d):
    rows = [row(i, o2=1) for i in range(190)] + [row(1000 + i) for i in range(810)]
    build(d, rows, "B")
    return A.verdict("B", A.analyse(f"{d}/hooks.csv"))[0] == "VOID"


@case("arm B at 21% -> CONTROL-OK")
def _(d):
    rows = [row(i, o2=1) for i in range(210)] + [row(1000 + i) for i in range(790)]
    build(d, rows, "B")
    return A.verdict("B", A.analyse(f"{d}/hooks.csv"))[0] == "CONTROL-OK"


@case("EXCLUSION RULE binds: a live descriptor (TUCK_C2!=$FF) is OUT of the denominator")
def _(d):
    rows = [row(i) for i in range(100)] + [row(500 + i, o2=1, tc=4, tr=9) for i in range(50)]
    build(d, rows, "A")
    a = A.analyse(f"{d}/hooks.csv")
    # if condition 4 were dropped, N would be 150 and k 50.
    return a["N"] == 100 and a["k_strict"] == 0 and a["N_tuckrow"] == 50 and a["k_tuckrow"] == 50


@case("JUST-CONSUMED window (TUCK_C2==$FF, TUCK_R2!=16) is OUT too -- the asymmetric reset")
def _(d):
    rows = [row(i) for i in range(100)] + [row(500 + i, o2=1, tc=255, tr=9) for i in range(50)]
    build(d, rows, "A")
    a = A.analyse(f"{d}/hooks.csv")
    return a["N"] == 100 and a["k_strict"] == 0


@case("CONDITION 5 binds: odd-published anomalies go to k_pubodd, never k_strict")
def _(d):
    rows = [row(i) for i in range(100)] + [row(500 + i, o2=1, pub=3) for i in range(20)]
    build(d, rows, "A")
    a = A.analyse(f"{d}/hooks.csv")
    return a["k_naive"] == 20 and a["k_strict"] == 0 and a["k_pubodd"] == 20


@case("DOUBLE test masks to the LOW NIBBLE ($51 vs $A1 IS a double; $51 vs $A2 is not)")
def _(d):
    rows = [row(i, cA=0x51, cB=0xA1) for i in range(50)] + \
           [row(500 + i, cA=0x51, cB=0xA2) for i in range(50)]
    build(d, rows, "A")
    return A.analyse(f"{d}/hooks.csv")["N"] == 50


@case("SETTLE gate binds: STABLE_CT2 < 8 is out of the denominator")
def _(d):
    rows = [row(i, st=7, o2=1) for i in range(50)] + [row(500 + i, st=8) for i in range(50)]
    build(d, rows, "A")
    a = A.analyse(f"{d}/hooks.csv")
    return a["N"] == 50 and a["k_strict"] == 0


@case("TGT_O2 == 0 or 3 is NEVER an anomaly (the invariant's own definition)")
def _(d):
    rows = [row(i, o2=0) for i in range(50)] + [row(500 + i, o2=3) for i in range(50)]
    build(d, rows, "A")
    return A.analyse(f"{d}/hooks.csv")["k_naive"] == 0


@case("a SUMMARY-less log is a hard failure, never a zero")
def _(d):
    build(d, [row(i) for i in range(10)], "A")
    open(f"{d}/framedense.log", "w").write("framedense start tag=t\n")
    try:
        A.load_summary(f"{d}/framedense.log")
    except SystemExit:
        return True
    return False


def main():
    tmp = tempfile.mkdtemp(prefix="fdtest_")
    npass = nfail = 0
    try:
        for i, (name, fn) in enumerate(CASES):
            d = os.path.join(tmp, f"c{i}")
            try:
                ok = fn(d)
            except AssertionError as e:
                ok = False
                name += f"  [assert: {e}]"
            print(("PASS  " if ok else "FAIL  ") + name)
            npass += bool(ok); nfail += (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{npass} passed, {nfail} failed")
    sys.exit(1 if nfail else 0)


if __name__ == "__main__":
    main()
