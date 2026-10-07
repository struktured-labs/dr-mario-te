"""STEER14 SLAM-GATE CALIBRATION against the cart (a16-mt-build lane's chained + garbage Mesen replays on V11 timelines).

  python steer14_slamcal.py rule     the cart's slam rule, re-derived from patch_cartridge_copro.py (dn_p2), checked
                                     frame by frame on every replayed pill  -> steer14/slamcal/rule.txt
  python steer14_slamcal.py model    the corrected steer model (steer_model.execute(slam=...)) on the same pills, same
                                     publish schedules, vs the cart's commit / laterals-done / DOWN / lock frames, and
                                     the MIN_THINK 6 f -> 2 f lock-frame change  -> steer14/slamcal/model.txt
Inputs (read-only, outside the repo): dr_mario_rl/tmp/a16mt/execfid/runs/<game>_{f2p,mt2}_v11_chain_garb/lateflip_*.log
(the per-frame cart trace) and dr_mario_rl/tmp/a16mt/cases/<game>_v11_chain_garb.lua (boards, pills, schedules).
f2p = FAIR2PLUS 5a1695da (DRMINTHINK 12 = 6 f); mt2 = the same cart with DRMINTHINK 4 (2 f), 170f179d. Both:
DRSLAM KOPEN 32 / KEND 255 / KCROSS 8 / LOWY 8 / VCEND 10 / MATURE 2, DRLATEGUARD, DRTAPP 2 (cart build logs).

THE CART RULE (dn_p2, patch_cartridge_copro.py ~L4098): once column-aligned (x == the DISTGATE effective column) and
orient-locked (ROT_DONE2), DOWN is held iff
    the search is DONE (ARMED2 == 0)
 or SLAM_ARM and STABLE_CT2 >= K, K = KCROSS if ROM Y < LOWY, else KEND if vcount < VCEND, else KOPEN,
where STABLE_CT2 counts hooks (2 per frame) since the driver's target last changed (reset on a change and at a new
pill) and saturates at 254 (KEND 255 = DONE only). Otherwise no button: the capsule falls at natural gravity.
Per-pill rows are banked to steer14/slamcal/pills.jsonl (R101).
"""
import os, re, sys, json, glob, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = "/home/struktured/projects/dr_mario_rl/tmp/a16mt/execfid/runs"
CASES = "/home/struktured/projects/dr_mario_rl/tmp/a16mt/cases"
OUT = os.path.join(HERE, "steer14", "slamcal")
KOPEN, KEND, KCROSS, LOWY, VCEND = 32, 255, 8, 8, 10
TRE = re.compile(r"(\w+)=([^ |]+)")


def parse_log(path):
    P = {}
    for l in open(path, errors="replace"):
        tag = l.split(" ", 1)[0]
        if tag not in ("T", "INJECT", "LAND", "GARB"):
            continue
        m = re.match(r"\w+ p(\d+) ", l)
        if not m:
            continue
        p = int(m.group(1)); d = P.setdefault(p, {"T": []})
        kv = dict(TRE.findall(l))
        if tag == "T":
            fr = {"f": int(kv["f"]), "y": int(kv["y"]), "x": int(kv["x"]), "rot": int(kv["rot"]), "na": int(kv["na"]),
                  "tgt": tuple(map(int, kv["tgt"].split(","))), "rd2": int(kv["rd2"]), "arm": int(kv["arm"]),
                  "pend": int(kv["pend"]), "eff": int(kv["eff"]), "lg": tuple(map(int, kv["lg"].split(","))),
                  "pad": int(kv["pad"], 16), "held": int(kv["held"], 16), "mb": tuple(map(int, kv["mb"].split(","))),
                  "sa": int(kv["sa"]), "st": int(kv["st"]), "hv": int(kv["hv"])}
            d["T"].append(fr)
        elif tag == "INJECT":
            d["inj"] = {"spu": int(kv["spu"]), "vc": int(kv["vc"]), "done_f": float(kv["done_f"]),
                        "npubs": int(kv["sched_pubs"])}
        elif tag == "LAND":
            d["land"] = {"f": int(kv["f"]), "x": int(kv["x"]), "y": int(kv["y"]), "rot": int(kv["rot"]),
                         "action": int(kv["action"]), "cosim_final": int(kv["cosim_final"])}
        elif tag == "GARB":
            d["garb_before"] = True
    return P


def parse_cases(path):
    """the .lua case table -> list of dicts (board 128 bytes, cur, spu, vc, sched pubs [(t, col, o4)], done_f)"""
    txt = open(path).read()
    out = []
    for m in re.finditer(r"\{p=(\d+),.*?board=\{([^}]*)\}.*?cur=\{(\d+),(\d+)\}.*?spu=(\d+), vc=(\d+).*?"
                         r"sched=\{pubs=\{(.*?)\}, done_f=([\d.]+), final=\{(\d+),(\d+)\}", txt, re.S):
        pubs = [tuple(float(v) for v in x.split(",")) for x in re.findall(r"\{([\d.]+,\d+,\d+)\}", m.group(7))]
        out.append({"p": int(m.group(1)), "board": [int(v) for v in m.group(2).split(",")],
                    "cur": (int(m.group(3)), int(m.group(4))), "spu": int(m.group(5)), "vc": int(m.group(6)),
                    "pubs": [(t, int(c), int(o)) for t, c, o in pubs], "done_f": float(m.group(8)),
                    "final": (int(m.group(9)), int(m.group(10)))})
    return {c["p"]: c for c in out}


def events(d):
    T = d["T"]
    if not T or "land" not in d:
        return None
    go = next((t["f"] for t in T if t["arm"] == 1), None)
    commit = next((t["f"] for t in T if t["rd2"] == 1), None)
    down = next((t["f"] for t in T if t["held"] & 4), None)
    lx = d["land"]["x"]
    lat = None
    for t in T:
        if t["x"] == lx:
            if lat is None:
                lat = t["f"]
        else:
            lat = None
    done = next((t["f"] for t in T if go is not None and t["f"] > go and t["arm"] == 0), None)
    return {"go": go, "commit": commit, "lat_done": lat, "down": down, "lock": d["land"]["f"], "done": done}


def rule_down(t, vc, k=KOPEN):
    """the cart rule on one traced frame (state as printed)"""
    if not (t["rd2"] == 1 and t["x"] == t["eff"]):
        return False
    if t["arm"] == 0:
        return True
    if t["sa"] == 0:
        return False
    K = KCROSS if t["y"] < LOWY else (KEND if vc < VCEND else k)
    return t["st"] >= K + 1 and K < 255


def games():
    out = []
    for g in sorted({os.path.basename(p).split("_")[0] for p in glob.glob(f"{RUNS}/*_f2p_v11_chain_garb")}):
        f2p = glob.glob(f"{RUNS}/{g}_f2p_v11_chain_garb/lateflip_*.log")
        mt2 = glob.glob(f"{RUNS}/{g}_mt2_v11_chain_garb/lateflip_*.log")
        cs = f"{CASES}/{g}_v11_chain_garb.lua"
        if f2p and mt2 and os.path.exists(cs):
            out.append((g, f2p[0], mt2[0], cs))
    return out


def rule():
    os.makedirs(OUT, exist_ok=True)
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    out("CART SLAM RULE (dn_p2) vs the traced DOWN input, frame by frame, every replayed pill (" + ", ".join(
        f"{g}" for g, *_ in games()) + ")")
    tot = {"frames": 0, "agree": 0, "pills": 0, "first_down_agree": 0, "first_down_n": 0, "sa0": 0, "stuck": 0}
    cls = {}
    rows = []
    for g, f2p, mt2, cs in games():
        for arm, path in (("f2p", f2p), ("mt2", mt2)):
            P = parse_log(path)
            for p, d in sorted(P.items()):
                if "inj" not in d or "land" not in d or not d["T"]:
                    continue
                vc = d["inj"]["vc"]
                ev = events(d)
                pred_first = None
                for t in d["T"]:
                    pr = rule_down(t, vc)
                    ob = bool(t["held"] & 4)
                    tot["frames"] += 1; tot["agree"] += int(pr == ob)
                    tot["sa0"] += int(t["sa"] == 0)
                    if pr and pred_first is None:
                        pred_first = t["f"]
                tot["pills"] += 1
                if ev["down"] is not None or pred_first is not None:
                    tot["first_down_n"] += 1; tot["first_down_agree"] += int(ev["down"] == pred_first)
                # what opened the gate at the observed first DOWN
                why = "none"
                if ev["down"] is not None:
                    t = next(t for t in d["T"] if t["f"] == ev["down"])
                    why = ("done" if t["arm"] == 0 else ("cross" if t["y"] < LOWY else ("end" if vc < VCEND else "open"))
                           if t["rd2"] and t["x"] == t["eff"] else "other")
                cls[(arm, why)] = cls.get((arm, why), 0) + 1
                rows.append({"game": g, "arm": arm, "p": p, "vc": vc, "spu": d["inj"]["spu"], "done_f": d["inj"]["done_f"],
                             "why": why, **ev, "pred_down": pred_first, "land": d["land"]})
    out(f"  frames {tot['frames']}: rule == traced DOWN on {tot['agree']} ({100 * tot['agree'] / tot['frames']:.2f} %); "
        f"frames with SLAM_ARM 0: {tot['sa0']}")
    out(f"  pills {tot['pills']}: FIRST DOWN frame predicted exactly on {tot['first_down_agree']}/{tot['first_down_n']} "
        f"({100 * tot['first_down_agree'] / max(1, tot['first_down_n']):.1f} %)")
    for arm in ("f2p", "mt2"):
        out(f"  {arm}: first-DOWN trigger " + ", ".join(f"{w} {n}" for (a, w), n in sorted(cls.items()) if a == arm))
    # MIN_THINK: commit / laterals / DOWN / lock change, same-landing pills
    R = {(r["game"], r["arm"], r["p"]): r for r in rows}
    d = {"commit": [], "lat_done": [], "down": [], "lock": []}; same = 0; diff = 0
    for (g, a, p), r in R.items():
        if a != "f2p" or (g, "mt2", p) not in R:
            continue
        q = R[(g, "mt2", p)]
        if r["land"]["action"] != q["land"]["action"] or r["land"]["y"] != q["land"]["y"]:
            diff += 1; continue
        same += 1
        for k in d:
            if r[k] is not None and q[k] is not None:
                d[k].append(q[k] - r[k])
    out(f"  MIN_THINK 6 f -> 2 f on the cart (mt2 - f2p, same-landing pills {same}, different landing {diff}): " + "; ".join(
        f"{k} {np.mean(v):+.2f} f (n {len(v)})" for k, v in d.items()))
    with open(os.path.join(OUT, "pills.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    open(os.path.join(OUT, "rule.txt"), "w").write("\n".join(lines) + "\n")


def model_pill(case, d, mt, slam_on, delta=0.0, g0=2):
    """the steer model on one replayed pill, in TRACE frames (the model's gravity origin G0 = 2 == the trace's: first
    natural drop at f = thr + 2), GO = the cart's traced GO, commit gate GO + MT, the case's own publish schedule and
    co-sim DONE (exactly what the replay injected), SLAM_ARM = the traced value at the pill's first frame."""
    import steer_model as SM
    import steer8_run as S8
    t = S8.ARMS["fD_bdepD"]["t"]
    st = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True, trace=True)
    st.proph_end_f = t["p_end"]; st.dg_extra = None; st.ledge_commit = bool(t["ledge_c"]); st.proph_first_end = t["p_first"]
    T = d["T"]
    go = next(x["f"] for x in T if x["arm"] == 1)
    st.v = T[0]["hv"]
    b = case["board"]
    color = [[0 if b[r * 8 + c] == 255 else 1 for c in range(8)] for r in range(16)]
    sched = [(int(math.ceil(go + tt - 1e-9)), (o4 ^ 2) * 8 + col) for tt, col, o4 in case["pubs"]]
    fin = sched[-1][1]
    slam = None
    if slam_on:
        slam = {"done": int(math.ceil(go + case["done_f"] + delta - 1e-9)), "armed": T[0]["sa"] == 1, "vc": case["vc"]}
    # DOWN parity: the cart's soft-drop lowers on frames of the traced parity (frameCounter is exogenous)
    par = None
    for a, bb in zip(T, T[1:]):
        if bb["held"] & 4 and bb["y"] < a["y"]:
            par = bb["f"] % 2; break
    ph = 1 if par is None else (1 - par) % 2          # model lowers on (f + ph) odd
    SM.G0_CHOICES = (g0, g0)
    ex = st.execute(color, fin, case["spu"] * 10, t_act=go + mt, phase=ph, sched=sched, slam=slam)
    down = next((x[0] for x in ex["trace"] if x[5] & 4), None)
    return {"commit": ex["lg"]["commit_f"], "down": down, "lock": ex["lock_f"], "action": ex["var"] * 8 + ex["col"],
            "row": ex["cells"][1][0] if ex["var"] >= 2 else ex["cells"][0][0], "go": go}


def model():
    import import_pin; import_pin.pin()
    os.makedirs(OUT, exist_ok=True)
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    R = {}
    for g, f2p, mt2, cs in games():
        C = parse_cases(cs)
        for arm, path, mt in (("f2p", f2p, 6), ("mt2", mt2, 2)):
            P = parse_log(path)
            for p, d in sorted(P.items()):
                if p not in C or "land" not in d or not d["T"] or not any(x["arm"] == 1 for x in d["T"]):
                    continue                                   # prestart pills (answer ready at the edge) excluded
                ev = events(d)
                row = {"ev": ev, "land": d["land"], "vc": C[p]["vc"], "sa": d["T"][0]["sa"]}
                for lab, on, dl in (("old", False, 0.0), ("new", True, 0.0), ("new5", True, 0.5)):
                    row[lab] = model_pill(C[p], d, mt, on, dl)
                R[(g, arm, p)] = row
    out(f"STEER MODEL vs CART on the replayed pills (prestart pills excluded): {len(R)} pill-runs")
    out("  old = STEER13 model (DOWN as soon as aligned); new = + the DRSLAM gate (DONE frame = ceil(GO + done_f));"
        " new5 = DONE + 0.5 f (hook order)")
    for lab in ("old", "new", "new5"):
        for arm in ("f2p", "mt2"):
            xs = [r for (g, a, p), r in R.items() if a == arm]
            dd = [r[lab]["down"] - r["ev"]["down"] for r in xs if r[lab]["down"] is not None and r["ev"]["down"] is not None]
            dl = [r[lab]["lock"] - r["ev"]["lock"] for r in xs if r[lab]["lock"] is not None]
            land = np.mean([r[lab]["action"] == r["land"]["action"] for r in xs])
            out(f"  {lab:4s} {arm}: DOWN start model - cart mean {np.mean(dd):+.2f} f, exact {100 * np.mean(np.array(dd) == 0):.1f} %, "
                f"|d|<=1 {100 * np.mean(np.abs(dd) <= 1):.1f} % (n {len(dd)}); LOCK model - cart mean {np.mean(dl):+.2f} f, "
                f"exact {100 * np.mean(np.array(dl) == 0):.1f} %, |d|<=1 {100 * np.mean(np.abs(dl) <= 1):.1f} %, "
                f"|d|<=3 {100 * np.mean(np.abs(dl) <= 3):.1f} % (n {len(dl)}); landing == cart {100 * land:.1f} %")
    out("  MIN_THINK 6 f -> 2 f, lock-frame change on the SAME pills (mt2 - f2p), cart vs model:")
    for lab in ("cart", "old", "new", "new5"):
        ds = []
        for (g, a, p), r in R.items():
            if a != "f2p" or (g, "mt2", p) not in R:
                continue
            q = R[(g, "mt2", p)]
            if lab == "cart":
                if r["land"]["action"] == q["land"]["action"]:
                    ds.append(q["ev"]["lock"] - r["ev"]["lock"])
            elif r[lab]["lock"] is not None and q[lab]["lock"] is not None and r[lab]["action"] == q[lab]["action"]:
                ds.append(q[lab]["lock"] - r[lab]["lock"])
        out(f"    {lab:5s} {np.mean(ds):+.2f} f (n {len(ds)}, share changed {100 * np.mean(np.array(ds) != 0):.1f} %)")
    for key in (("m2g2", "f2p", 60), ("m2g2", "mt2", 60)):
        if key in R:
            r = R[key]
            out(f"  example {key}: cart commit f{r['ev']['commit']} laterals-done f{r['ev']['lat_done']} DOWN f{r['ev']['down']} "
                f"lock f{r['ev']['lock']} | new model commit f{r['new']['commit']} DOWN f{r['new']['down']} lock "
                f"f{r['new']['lock']} | old model DOWN f{r['old']['down']} lock f{r['old']['lock']}")
    with open(os.path.join(OUT, "model_pills.jsonl"), "w") as fh:
        for (g, a, p), r in sorted(R.items()):
            fh.write(json.dumps({"game": g, "arm": a, "p": p, **{k: v for k, v in r.items()}}) + "\n")
    open(os.path.join(OUT, "model.txt"), "w").write("\n".join(lines) + "\n")


def nes_board(b):
    """the 128 NES playfield bytes -> FaithfulBoard (inverse of cosim_farm.cosim.board_to_nes)"""
    from drmario.faithful_game import FaithfulBoard, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT
    lk = {0x4: LINK_DOWN, 0x5: LINK_UP, 0x6: LINK_RIGHT, 0x7: LINK_LEFT}
    B = FaithfulBoard(16, 8)
    for i, v in enumerate(b):
        r, c = divmod(i, 8)
        if v == 0xFF:
            continue
        B.color[r, c] = (v & 0x0F) + 1
        if v >> 4 == 0xD:
            B.is_virus[r, c] = True
        else:
            B.link[r, c] = lk.get(v >> 4, 0)
    return B


def gap_parts(case, land):
    """place the landed capsule on the case board, resolve: (ROM y of the landing, clear steps, cascade fall rows)"""
    from drmario.faithful_game import LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT
    import steer_model as SM
    import vs_race as V
    B = nes_board(case["board"])
    a, bcol = case["cur"][0] + 1, case["cur"][1] + 1
    var, x, row = land["action"] // 8, land["x"], 15 - land["y"]
    (r0, c0), (r1, c1) = SM.cells(x, row, SM.ROT_OF_VAR[var])
    first, second = (a, bcol) if var in (0, 2) else (bcol, a)
    for (r, c), col, ln in (((r0, c0), first, LINK_RIGHT if var < 2 else LINK_DOWN),
                            ((r1, c1), second, LINK_LEFT if var < 2 else LINK_UP)):
        if r >= 0:
            B.color[r, c] = col; B.link[r, c] = ln; B.is_virus[r, c] = False
    falls = V._cascade_falls(B)
    return land["y"], len(falls), sum(falls)


def gapfit():
    """the lock -> next-edge gap the SLAM_ARM disarm compares DONE against (chained replays, f2p, no garbage between)"""
    import import_pin; import_pin.pin()
    clk = json.load(open(os.path.join(HERE, "steer11", "clock_couch11.json")))
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    rows = []
    for g, f2p, mt2, cs in games():
        C = parse_cases(cs)
        inj, garb = {}, set()
        for l in open(f2p, errors="replace"):
            m = re.match(r"INJECT p(\d+) at f=(\d+)", l)
            if m:
                inj[int(m.group(1))] = int(m.group(2))
            m = re.match(r"GARB p(\d+) ", l)
            if m:
                garb.add(int(m.group(1)))
        P = parse_log(f2p)
        for p in sorted(P):
            q = p - 1
            if q not in P or "land" not in P[q] or p not in inj or q not in inj or q not in C or p in garb:
                continue
            gap = inj[p] - inj[q] - P[q]["land"]["f"]
            y, steps, cf = gap_parts(C[q], P[q]["land"])
            pred = max(12, 24 - y) + clk["step"] * steps + clk["cfall"] * cf
            rows.append((gap, pred, steps, cf, y))
    A = np.array(rows, float)
    for lab, s in (("no clear", A[:, 2] == 0), ("clears", A[:, 2] > 0)):
        e = A[s, 1] - A[s, 0]
        out(f"  gap {lab}: n {s.sum()}, observed p50 {np.median(A[s, 0]):.0f}, model - cart mean {e.mean():+.2f} sd {e.std():.2f}, "
            f"|e|<=1 {100 * np.mean(np.abs(e) <= 1):.1f} %")
    X = np.c_[A[A[:, 2] > 0, 2], A[A[:, 2] > 0, 3]]
    yv = A[A[:, 2] > 0, 0] - np.maximum(12, 24 - A[A[:, 2] > 0, 4])
    co = np.linalg.lstsq(X, yv, rcond=None)[0]
    out(f"  refit on the clearing pills: {co[0]:.2f} f/step, {co[1]:.2f} f/cascade row (couch11: {clk['step']:.2f}, {clk['cfall']:.2f})")
    open(os.path.join(OUT, "gap.txt"), "w").write("\n".join(lines) + "\n")
    return co


if __name__ == "__main__":
    os.chdir(HERE)
    sys.path.insert(0, HERE)
    {"rule": rule, "model": model, "gapfit": gapfit}[sys.argv[1]]()
