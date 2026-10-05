"""Per-pill landing comparison of several execfid/lateflip probe logs (same case file): which landings differ, and
landing == silicon / == copro final / hybrids (a straight-drop landing that is none of the published candidates)."""
import json, sys
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "lateflip"))
import parse_lateflip as PL


def main():
    pub = sys.argv[1]; logs = sys.argv[2:]
    P = {t["p"]: t for t in map(json.loads, open(pub))}
    L = [PL.load(x) for x in logs]
    names = [x.split("/")[-2] for x in logs]
    for k, (n, C) in enumerate(zip(names, L)):
        tot = sum(1 for p in C if C[p]["land"]); sil = sum(1 for p in C if C[p]["land"] and str(C[p]["land"]["act"]) == C[p]["land"]["sil"])
        fin = sum(1 for p in C if C[p]["land"] and C[p]["land"]["act"] == C[p]["land"]["fin"])
        hyb = sum(1 for p in C if C[p]["land"] and p in P and C[p]["land"]["act"] != P[p]["final"][2]
                  and C[p]["land"]["act"] not in [x[3] for x in P[p]["pubs"]])
        print(f"{n:28s} n={tot} ==silicon {sil} ==copro-final {fin} hybrid(not any publish) {hyb}")
    ps = sorted(set().union(*[set(C) for C in L]))
    for p in ps:
        acts = [C[p]["land"]["act"] if p in C and C[p]["land"] else None for C in L]
        if len(set(acts)) > 1:
            l0 = next(C[p]["land"] for C in L if p in C and C[p]["land"])
            print(f"  p{p}: silicon a{l0['sil']} final a{l0['fin']} | " + " | ".join(f"{n}: a{a}" for n, a in zip(names, acts)))


main()
