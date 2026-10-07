"""STEER14 worker-guard killed-mutant check (PREREG_STEER14 sec. 2). Each mutant must make jit_guard() exit 5.
  m_sha     GUARD_SHA wrong                                   -> sha mismatch
  m_vk      the A16 decider built WITHOUT its vk 16 gate     -> mid_diff == 0 (the gate is dead)  [sha check disabled]
  m_meta    the anytime META returns a different final        -> meta_bad > 0                      [sha check disabled]
  control   unmodified, sha check ON                          -> must PASS
"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
import steer14_run as R
import rules_steer10 as R10
import anytime13 as AT

SHA = R.GUARD_SHA


def attempt(name):
    try:
        g = R.jit_guard()
        return 0, g
    except SystemExit as e:
        return e.code, None


ok = True
rc, g = attempt("control"); ok &= rc == 0
print(f"control (sha {SHA}): rc {rc} {g}")
R.GUARD_SHA = "0" * 16
rc, _ = attempt("m_sha"); ok &= rc == 5; print(f"m_sha: rc {rc} -> {'KILLED' if rc == 5 else 'SURVIVED'}")
R.GUARD_SHA = None
mk = R10.make
R10.make = lambda rule=None: mk({k: v for k, v in (rule or {}).items() if k != "vk"})
rc, _ = attempt("m_vk"); ok &= rc == 5; print(f"m_vk: rc {rc} -> {'KILLED' if rc == 5 else 'SURVIVED'}")
R10.make = mk
run0 = AT.Meta.run
AT.Meta.run = lambda self, dec, board, cur, nxt, k, allowed=None: ((lambda a, r: ((a + 1) % 32 if a is not None else a, r))(*run0(self, dec, board, cur, nxt, k, allowed)))
rc, _ = attempt("m_meta"); ok &= rc == 5; print(f"m_meta: rc {rc} -> {'KILLED' if rc == 5 else 'SURVIVED'}")
AT.Meta.run = run0
R.GUARD_SHA = SHA
print("STEER14 GUARD MUTANTS", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
