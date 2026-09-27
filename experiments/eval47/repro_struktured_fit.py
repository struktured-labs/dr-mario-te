"""Re-run bursty_model.fit_struktured_20260804() and cache its fit_summary.

Reads 1497 film-review frames, so it is deliberately run ONCE here rather than
inside the notebook (the box carries heavy live jobs; the notebook must stay
I/O-light). Output is consumed by player_stats_notebook.py.
"""
import json
import os
import sys
import time

EVAL47 = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
OUT = os.path.join(EVAL47, "results", "struktured_20260804_pooled_fit.json")

sys.path.insert(0, EVAL47)
import bursty_model  # noqa: E402

t0 = time.time()
model = bursty_model.fit_struktured_20260804()
elapsed = time.time() - t0

summary = json.loads(json.dumps(model.fit_summary(), default=str))
summary["_provenance"] = {
    "source": "bursty_model.fit_struktured_20260804()",
    "module": os.path.join(EVAL47, "bursty_model.py"),
    "film_review_dir": bursty_model.FILM_REVIEW_DIR_DEFAULT,
    "python": sys.executable,
    "elapsed_s": round(elapsed, 1),
    "generated_by": "experiments/eval47/repro_struktured_fit.py",
    "scope": "POOLED (both sides' events; see STYLE_ENSEMBLE_V1.md 6a)",
}
with open(OUT, "w") as fh:
    json.dump(summary, fh, indent=2)

print(f"elapsed={elapsed:.1f}s -> {OUT}")
for k in ("n_matches", "n_volleys", "n_clears"):
    print(f"  {k}={summary.get(k)}")
print("  p_within_k 4-6:", summary.get("p_within_k", {}).get("4-6"))
print("  p_within_k 7-10:", summary.get("p_within_k", {}).get("7-10"))
