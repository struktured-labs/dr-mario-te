"""PROPH window per arm from lateflip_probe replay logs: for the PROPH-armed pills (PROPH_DIR != 0 at the spawn), the
frame of the first valid copro publication, the commit (ROT_DONE2), the lateral presses before each, and the first frame
P2's gravity counter reads >= 2 (frames are lateflip_probe's f = endFrames since the spawn).
  proph_window.py LOGDIR TAG [TAG ...]        (logs at LOGDIR/<TAG>/lateflip_<TAG>.log)"""
import re, sys, os, statistics as st, collections
T = re.compile(r"^T p(\d+) f=(\d+) y=(\d+) x=(\d+) rot=(\d+) na=(\d+) grav=(\d+) \| tgt=(\d+),(\d+) rd2=(\d+) arm=(\d+) pend=(\d+) dly=(\d+) eff=(\d+) bud=(\d+) fall=(\d+) proph=(\w+) lg=(\d+),(\d+) \| pad=(\w+) held=(\w+) \| mb=(-?\d+),(-?\d+),(\d+) k=(-?\d+)")
def per_case(log):
    cases = collections.defaultdict(list)
    for l in open(log, errors="replace"):
        m = T.match(l)
        if m:
            g = m.groups(); cases[int(g[0])].append(dict(f=int(g[1]), y=int(g[2]), x=int(g[3]), grav=int(g[6]), rd2=int(g[9]),
                arm=int(g[10]), pend=int(g[11]), proph=int(g[16], 16), pad=int(g[19], 16), mbo=int(g[22]), k=int(g[24])))
    return cases
for tag in sys.argv[2:]:
    C = per_case(os.path.join(sys.argv[1], tag, f"lateflip_{tag}.log"))
    pub, cmt, presses, lat_before, first_grav2 = [], [], [], [], []
    for p, fr in C.items():
        if not fr or fr[0]["proph"] == 0:
            continue
        # first frame the driver sees a valid publication of THIS pill's search (armed, orient != $FF) or DONE
        fp = next((x["f"] for x in fr if x["pend"] == 0 and x["k"] >= 0 and x["mbo"] != 255), None)
        fc = next((x["f"] for x in fr if x["rd2"] == 1), None)
        fg = next((x["f"] for x in fr if x["grav"] >= 2), None)
        lateral = [x["f"] for x in fr if x["pad"] & 0x03]
        pr = [f for f in lateral if fp is None or f < fp]
        pub.append(fp); cmt.append(fc); presses.append(len(pr)); first_grav2.append(fg)
        lat_before.append(len([f for f in lateral if fc is None or f < fc]))
    n = len(pub)
    md = lambda a: st.median([v for v in a if v is not None]) if any(v is not None for v in a) else None
    print(f"{tag}: PROPH-armed pills {n} | first valid publication f median {md(pub)} | commit f median {md(cmt)} | "
          f"PROPH lateral presses before publication median {md(presses)} (dist {sorted(collections.Counter(presses).items())}) | "
          f"lateral presses before commit median {md(lat_before)} | gravity counter first >=2 at f median {md(first_grav2)}")
