"""Vendored-mode identity test for experiments/cvx/vendor (DRM_VENDOR=1).

1. Every vendored module is byte-identical to its recorded source (when the source exists on this
   machine), except bursty_model.py, whose only change is the snapshot loader.
2. The owner-fit snapshot behaves exactly like the footage fit: same parameters, same
   fire_probability over all clear sizes, same sample() over a seed x pill grid.
3. Games: fixed games in DRM_VENDOR=1 reproduce the md5 fingerprints recorded from the original
   modules by this week's exactness gates (vs_race, gate (b) owner model, live adaptive race, dose).

Run from anywhere:  python experiments/cvx/tests_vendor_identity.py [--games-only]
In a clean clone (originals absent) steps 1-2 are skipped and step 3 is the whole proof.
"""
import hashlib, json, os, subprocess, sys

CVX = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(CVX, "vendor")
PY = sys.executable

# Fingerprints recorded 2026-09-23/24 from the ORIGINAL (non-vendored) modules.
GAMES = {
    "vs_race holes80+h80chain180 lam3.3 seed36734":
        ("import vs_race as V\nout=[V.play(36734,a,3.3) for a in ('holes80','h80chain180')]",
         "65d279f4fdd3896b989fc371a1f36383"),
    "gate_b fw_winner+fw_holes80 owner-model seed36734":
        ("import gate_b as G, vs_race as V, bursty_model as BM\nm=BM.fit_struktured_20260804()\n"
         "out=[G.play(36734,None,m,choose=V._decider(a)) for a in ('fw_winner','fw_holes80')]",
         "62172807194b59857aa71e32f2303620"),
    "vs_race_adaptive fw180+press_cruise lam6 M177 seed36734":
        ("import vs_race_adaptive as A\nout=[A.play_live(36734,p,6.0,177.0) for p in ('fw180','press_cruise')]",
         "e0d8ab164495c20eb2053f90d4ec9eab"),
    "vs_race fw_winner+fw540 lam6 seed36734":
        ("import vs_race as V\nout=[V.play(36734,a,6.0) for a in ('fw_winner','fw540')]",
         "91b87f08eab1ef23434727776c000b00"),
}


def _md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def check_files():
    man = json.load(open(os.path.join(VENDOR, "VENDOR_MANIFEST.json")))
    ok = True
    for name, e in man.items():
        src, dst = e["source"], os.path.join(VENDOR, e["vendored"])
        if not os.path.exists(src):
            print(f"  skip  {name}: original not on this machine"); continue
        same = _md5(src) == _md5(dst)
        if name == "bursty_model":
            print(f"  {'PATCH' if not same else 'SAME '} {name} (snapshot loader expected)"); continue
        print(f"  {'OK   ' if same else 'DIFF '} {name}"); ok &= same
    return ok


def check_snapshot():
    code = ("import sys,os,json,random; sys.path.insert(0,%r); import import_pin; import_pin.pin()\n"
            "import bursty_model as BM\nm=BM.fit_struktured_20260804()\n"
            "fp=[m.fire_probability(s) for s in range(0,21)]\n"
            "sm=[m.sample(s,p) for s in (1,36734,40134,99991) for p in range(0,300,7)]\n"
            "print(json.dumps([sorted(vars(m).keys()), m.volley_sizes, m.gap_samples, m.p_within_k, fp, sm], default=str))") % CVX
    outs = {}
    for mode in ("0", "1"):
        env = dict(os.environ, DRM_VENDOR=mode)
        r = subprocess.run([PY, "-c", code], capture_output=True, text=True, env=env, cwd=CVX)
        if r.returncode != 0:
            print(r.stderr[-800:]); return False
        outs[mode] = r.stdout.strip().splitlines()[-1]
    same = outs["0"] == outs["1"]
    print(f"  {'OK' if same else 'DIFF'}  owner-fit snapshot (DRM_VENDOR=1) vs footage fit (DRM_VENDOR=0)")
    return same


def check_games():
    ok = True
    for label, (body, want) in GAMES.items():
        code = ("import sys,json,hashlib; sys.path.insert(0,%r)\n%s\n"
                "print(hashlib.md5(json.dumps(out,sort_keys=True).encode()).hexdigest())") % (CVX, body)
        env = dict(os.environ, DRM_VENDOR="1")
        env.setdefault("NUMBA_CACHE_DIR", os.path.join(CVX, "..", "..", "tmp", "nbcache_vendor"))
        r = subprocess.run([PY, "-c", code], capture_output=True, text=True, env=env, cwd=CVX)
        got = r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else "ERROR"
        if got == "ERROR":
            print(r.stderr[-1200:])
        match = got == want
        print(f"  {'OK  ' if match else 'FAIL'} {label}: {got}")
        ok &= match
    return ok


if __name__ == "__main__":
    games_only = "--games-only" in sys.argv
    results = []
    if not games_only:
        print("1. vendored files vs originals"); results.append(check_files())
        print("2. owner-fit snapshot identity"); results.append(check_snapshot())
    print("3. game fingerprints under DRM_VENDOR=1 (recorded from the original modules)")
    results.append(check_games())
    print("VENDOR_IDENTITY_PASS" if all(results) else "VENDOR_IDENTITY_FAIL")
    sys.exit(0 if all(results) else 1)
