"""Tables for RESULT_LULU_20261005.md, generated from the banked outputs (no hand transcription):
summary_lulu_20261005.json, why_lulu_20261005.json, ai_lulu_20261005.json, replaysum_lulu_20261005.json.
Usage: python tables_lulu_20261005.py                 -> print every block
       python tables_lulu_20261005.py TEMPLATE OUT.md -> OUT = TEMPLATE with each TABLE_<NAME> / FILES line replaced"""
import io
import json
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
J = lambda n: json.load(open(os.path.join(HERE, n)))
S = J("summary_lulu_20261005.json"); W = {g["game"]: g for g in J("why_lulu_20261005.json")["games"]}
AI = {g["game"]: g for g in J("ai_lulu_20261005.json")["games"]} if os.path.exists(os.path.join(HERE, "ai_lulu_20261005.json")) else {}
RS = J("replaysum_lulu_20261005.json") if os.path.exists(os.path.join(HERE, "replaysum_lulu_20261005.json")) else {}
G = S["games"]; R = {r["game"]: r for r in S["results"]}
ORDER = ["m1g1", "m1g2", "m1g3", "m1g4", "m1g5", "m2g1", "m2g2", "m2g3", "m2g4"]
name = lambda g: g.upper().replace("G", " G")
B = {}


def t(hdr, rows):
    print("| " + " | ".join(hdr) + " |"); print("|" + "---|" * len(hdr))
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")


def block(key):
    def deco(f):
        buf = io.StringIO()
        with redirect_stdout(buf):
            f()
        B[key] = buf.getvalue().rstrip("\n")
        return f
    return deco


@block("TABLE_D1")
def _():
    t(["game", "play window (s)", "length (s)", "result", "final lulu/AI (HUD)", "winner", "quick read"],
      [[name(g["game"]), f"{R[g['game']]['t0_first_spawn']:.1f}–{R[g['game']]['t_end']:.1f}", g["dur_s"],
        {"cleared": ("lulu cleared" if g["winner"] == "lulu" else "AI cleared")}.get(g["how"], g["how"]),
        "%02d/%02d" % tuple(g["final_lulu_ai"]), g["winner"], R[g["game"]]["quick_read"]] for g in G])


@block("TABLE_D2")
def _():
    t(["game", "lulu pills (hidden)", "lulu gate exact/garbage/unexpl.", "AI pills (hidden)", "AI gate", "repairs lulu", "repairs AI"],
      [[name(g["game"]), f"{g['pills']['lulu']} ({g['hidden_spawns']['lulu']})",
        f"{g['gate']['lulu']['exact']}/{g['gate']['lulu']['garbage']}/{g['gate']['lulu']['unexplained']} of {g['gate']['lulu']['steps']}",
        f"{g['pills']['ai']} ({g['hidden_spawns']['ai']})",
        f"{g['gate']['ai']['exact']}/{g['gate']['ai']['garbage']}/{g['gate']['ai']['unexplained']} of {g['gate']['ai']['steps']}",
        ", ".join(f"{k} {v}" for k, v in g["repairs"]["lulu"].items()) or "–",
        ", ".join(f"{k} {v}" for k, v in g["repairs"]["ai"].items()) or "–"] for g in G])


@block("TABLE_PACE")
def _():
    f = lambda d, k: (f"{d[k]['viruses_per_min']} / {d[k]['pills_per_min']}" if k in d else "–")
    t(["game", "lulu 0–60 s", "60–120 s", "≥120 s", ">30 left", "13–30 left", "≤12 left", "whole game", "AI 0–60 s", "AI whole game"],
      [[name(g["game"])] + [f(g["pace"]["lulu"], k) for k in ("0-60s", "60-120s", ">=120s", ">30 left", "13-30 left", "<=12 left", "all")]
       + [f(g["pace"]["ai"], "0-60s"), f(g["pace"]["ai"], "all")] for g in G])
    print()

    def pooled(seat, k):
        sec = sum(g["pace"][seat][k]["seconds"] for g in G if k in g["pace"][seat])
        v = sum(g["pace"][seat][k]["viruses"] for g in G if k in g["pace"][seat])
        pl = sum(g["pace"][seat][k]["pills"] for g in G if k in g["pace"][seat])
        return f"{v / sec * 60:.2f} / {pl / sec * 60:.1f} ({sec / 60:.1f} min)"
    t(["pooled, 9 games", "0–60 s", "60–120 s", "≥120 s", ">30 left", "13–30 left", "≤12 left", "whole game"],
      [["dr. lulu" if s == "lulu" else "AI"] + [pooled(s, k) for k in ("0-60s", "60-120s", ">=120s", ">30 left", "13-30 left", "<=12 left", "all")]
       for s in ("lulu", "ai")])


@block("TABLE_SENDS")
def _():
    sz = lambda d: " ".join(f"{k}:{v}" for k, v in sorted(d.items()))
    t(["game", "lulu volleys/min", "lulu cells/min", "lulu sizes", "lulu ROM ok/checkable", "lulu first send (s)",
       "AI volleys/min", "AI cells/min", "AI sizes", "AI ROM ok/checkable", "AI first send (s)"],
      [[name(g["game"]), g["lulu_sends"]["volleys_per_min"], g["lulu_sends"]["cells_per_min"], sz(g["lulu_sends"]["recv_by_ai_sizes"]),
        f"{g['lulu_sends']['rom_column_rule']['conform']}/{sum(g['lulu_sends']['rom_column_rule'].values())}", round(g["lulu_sends"]["first_send_s"], 1),
        g["ai_sends"]["volleys_per_min"], g["ai_sends"]["cells_per_min"], sz(g["ai_sends"]["recv_by_lulu_sizes"]),
        f"{g['ai_sends']['rom_column_rule']['conform']}/{sum(g['ai_sends']['rom_column_rule'].values())}", round(g["ai_sends"]["first_send_s"], 1)]
       for g in G])


@block("TABLE_DEATHS")
def _():
    rows = []
    for g in G:
        L = g.get("lane_at_death")
        if not L:
            continue
        d = g["death"]["lulu" if L["seat"] == "lulu" else "ai"]
        ex = [(r, c) for r, c, _ in d["cells_arrived_after_last_placement"]]
        adj = any((r, c + 1) in ex or (r + 1, c) in ex for r, c in ex)
        # fair_20261004.death's pill test needs SAME-colour neighbours; ROM garbage is never adjacent (rom_attack_rule), so an
        # adjacent new pair at row 0 is the seat's own next capsule locked at the top (10/05 M1 G4: p146 y|r at (0,2)-(0,3))
        after = ("own next capsule locked at row 0: " + str(d["cells_arrived_after_last_placement"])) if adj else \
            (f"garbage {d['plug_by_garbage_after_last_placement']} (volley cells {d['cells_arrived_after_last_placement']})"
             if d["plug_by_garbage_after_last_placement"] else "–")
        rows.append([name(g["game"]), "dr. lulu" if L["seat"] == "lulu" else "AI", "%02d/%02d" % tuple(g["final_lulu_ai"]), d["plug"],
                     after, d["plug_present_before"] or "–",
                     L["lane"]["3"]["by_provenance"], L["lane"]["4"]["by_provenance"]])
    t(["game", "who topped out", "final", "spawn cells plugged", "what arrived after the last tracked pill", "already occupied (own pill)",
       "col 3 above top virus (P own, G garbage)", "col 4 above top virus"], rows)


@block("TABLE_AI")
def _():
    rows = []
    for g in ORDER:
        a = AI.get(g)
        if not a:
            rows.append([name(g), "–", "(co-sim / Mesen not run)", "", "", "", "", ""]); continue
        rows.append([name(g), a["pills"], f"{a['silicon_eq_brain']} ({a['pct']}%)",
                     " ".join(f"{k}:{v}" for k, v in a["labels"].items() if k != "MATCH"),
                     " ".join(f"{k}:{v}" for k, v in a["cosim"].items()),
                     f"{a['prev_target']} of {a['after_garbage_pills']}",
                     f"{a['silicon_only_misses']} of {a['misses']}" if a.get("replay_fair") else "–",
                     f"{a['copro_final_eq_brain']}/{a['with_cosim']}"])
    t(["game", "AI pills", "silicon == faithful brain", "misses by label", "co-sim category of silicon's landing",
       "previous-target / pills after a garbage window", "silicon-only misses", "copro final == python brain"], rows)


@block("TABLE_RACE")
def _():
    ts = ["30", "60", "90", "120", "150", "180", "210", "240"]
    t(["game", "winner"] + [f"{x} s" for x in ts] + ["AI longest stall", "AI→her cells/min", "her→AI cells/min", "loser's finishing deficit"],
      [[name(g), "dr. lulu" if W[g]["winner"] == "lulu" else "AI"] + ["%d/%d" % tuple(W[g]["race_lulu_ai"][x]) if x in W[g]["race_lulu_ai"] else "" for x in ts] +
       [f"{W[g]['ai_longest_stall']['seconds']} s at {W[g]['ai_longest_stall']['viruses']} ({W[g]['ai_longest_stall']['pills']} pills)",
        W[g]["garbage_to_lulu_per_min"], W[g]["garbage_to_ai_per_min"],
        (f"{'her' if W[g]['finishing_deficit']['loser'] == 'lulu' else 'AI'} {W[g]['finishing_deficit']['viruses_left']} left"
         + (f", ~{round(W[g]['finishing_deficit']['seconds_still_needed_at_that_rate'])} s more at own last-60-s pace"
            if W[g]['finishing_deficit']['seconds_still_needed_at_that_rate'] else ", no clear in its last 60 s"))] for g in ORDER])


@block("TABLE_WINLOSS")
def _():
    X = J("why_lulu_20261005.json")["her_wins_vs_losses"]
    lab = {"ai_longest_stall_s": "AI longest stall (s)", "lead_at_60s_ai_minus_lulu_viruses": "AI lead at 60 s (viruses)",
           "lead_at_120s_ai_minus_lulu_viruses": "AI lead at 120 s", "lulu_vpm_0_60": "her viruses/min, 0–60 s",
           "ai_vpm_0_60": "AI viruses/min, 0–60 s", "lulu_vpm_all": "her viruses/min, whole game", "ai_vpm_all": "AI viruses/min, whole game",
           "garbage_to_lulu_per_min": "AI garbage to her (cells/min)", "garbage_to_ai_per_min": "her garbage to AI",
           "ai_silicon_eq_brain_pct": "AI silicon == brain (%)"}
    t(["factor", "her wins (M1 G2, M1 G4, M2 G3)", "mean", "her losses (M1 G1, M1 G3, M1 G5, M2 G1, M2 G2, M2 G4)", "mean"],
      [[lab.get(k, k), v["her_wins"], v["mean_wins"], v["her_losses"], v["mean_losses"]] for k, v in X.items()])


@block("TABLE_REPLAYSUM")
def _():
    t(["game", "actual", "start points", "AI wins under perfect execution", "AI loses", "undecided (capsules run out)", "AI viruses left when undecided"],
      [[name(g), RS[g]["actual"], RS[g]["starts"], RS[g]["classes"].get("AI-WIN", 0), RS[g]["classes"].get("AI-LOSS", 0),
        RS[g]["classes"].get("OPEN", 0), (f"median {sorted(RS[g]['open_viruses_at_end'])[len(RS[g]['open_viruses_at_end']) // 2]}, range "
                                          f"{min(RS[g]['open_viruses_at_end'])}–{max(RS[g]['open_viruses_at_end'])}") if RS[g]["open_viruses_at_end"] else "–"]
       for g in ORDER if g in RS])


@block("TABLE_D7")
def _():
    rows = []
    tot = {"n": 0, "fair_fin": 0, "fair_hyb": 0, "plus_fin": 0, "plus_hyb": 0, "sil": 0, "plus_sil": 0, "pt": 0, "pt_rep": 0, "pt_fix": 0}
    for g in ORDER:
        a = AI.get(g)
        if not a or not a.get("replay_fair") or not a.get("replay_fairplus"):
            rows.append([name(g), "not run (trimmed)", "", "", "", "", ""]); continue
        f, p = a["replay_fair"], a["replay_fairplus"]
        rows.append([name(g), f["n"], f"{f['eq_final']} ({100 * f['eq_final'] / f['n']:.0f}%)", f["hybrid"],
                     f"{p['eq_final']} ({100 * p['eq_final'] / p['n']:.0f}%)", p["hybrid"],
                     f"{a['prev_target']} → FAIR reproduces {a['prev_target_mesen_fair_reproduces']}, FAIRPLUS lands final {a['prev_target_fairplus_lands_final']}"])
        tot["n"] += f["n"]; tot["fair_fin"] += f["eq_final"]; tot["fair_hyb"] += f["hybrid"]; tot["plus_fin"] += p["eq_final"]
        tot["plus_hyb"] += p["hybrid"]; tot["pt"] += a["prev_target"]; tot["pt_rep"] += a["prev_target_mesen_fair_reproduces"]
        tot["pt_fix"] += a["prev_target_fairplus_lands_final"]
    if tot["n"]:
        rows.append(["**total**", tot["n"], f"**{tot['fair_fin']}** ({100 * tot['fair_fin'] / tot['n']:.0f}%)", f"**{tot['fair_hyb']}**",
                     f"**{tot['plus_fin']}** ({100 * tot['plus_fin'] / tot['n']:.0f}%)", f"**{tot['plus_hyb']}**",
                     f"{tot['pt']} → {tot['pt_rep']} / {tot['pt_fix']}"])
    t(["game", "AI pills replayed", "FAIR dbbb5007: landing == copro final", "FAIR hybrids", "FAIRPLUS 5b3d8183: == copro final",
       "FAIRPLUS hybrids", "silicon previous-target pills"], rows)


@block("FILES")
def _():
    print("""- **Code:**
  - `lulu_20261005.py` (track | hudtpl | results | analyze [game] | merge | fit)
  - `cases_lulu_20261005.py` (per-AI-pill cases with the faithful brain)
  - `ai_lulu_20261005.py` (fidelity labels, co-sim categories, previous-target census with same-colour aliasing, Mesen FAIR/FAIRPLUS)
  - `m1g4_lulu_20261005.py` (stall | replay | replay_early | report)
  - `replay_lulu_20261005.py` + `replaysum_lulu_20261005.py` (brain-only replays)
  - `stall_lulu_20261005.py`
  - `seed_lulu_20261005.py`
  - `why_lulu_20261005.py`
  - `tables_lulu_20261005.py`
  - `geom_lulu_20261005.json`, `hud_templates_lulu_20261005.json`
- **Banked cases:**
  - `cases_lulu_20261005_lulu_pills.jsonl`, `cases_lulu_20261005_ai_pills.jsonl` (both seats per pill: runs / sent / cascade)
  - `cases_lulu_20261005_volleys.jsonl` (every send with its matched received volley and ROM-column check, both directions)
  - `cases_ai_<game>_lulu_20261005.jsonl` (per AI pill: board, capsules, silicon vs faithful brain, category, trajectory, garbage)
  - `cases_ai_fidelity_lulu_20261005.jsonl` (labels + Mesen FAIR/FAIRPLUS per pill)
  - `cases_ai_misses_lulu_20261005.jsonl` (**every AI miss** with board, trajectory, publish timeline, Mesen FAIR/FAIRPLUS/delayed
    landings and the `silicon_only` flag)
  - `pubtrace_<game>_lulu_20261005.jsonl` (co-sim publish timelines, fw 1488e158, seed 0)
  - `replay_*_lulu_20261005.jsonl`, `cases_stall_*_lulu_20261005.jsonl`, `cases_seed_lulu_20261005.jsonl`
- **Summaries:**
  - `summary_lulu_20261005.json`, `ai_lulu_20261005.json`, `why_lulu_20261005.json`, `replaysum_lulu_20261005.json`
  - `stall_*_lulu_20261005.json`, `seed_lulu_20261005.json`
  - **`lulu_fit_202610b.json`**
- **Not committed:**
  - Per-frame reads, raw tracks, Mesen logs and frames: `~/projects/dr_mario_rl/tmp/lulu_20261005/fx/`.
  - Clips (private): `~/projects/dr_mario_rl/tmp/lulu_20261005/clips/`.""")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        s = open(sys.argv[1]).read()
        for k, v in B.items():
            s = s.replace(k, v)
        open(sys.argv[2], "w").write(s)
        left = [w for w in s.split() if w.startswith("TABLE_")]
        print("filled", sys.argv[2], "unfilled:", left)
    else:
        for k, v in B.items():
            print(f"=== {k}\n{v}\n")
