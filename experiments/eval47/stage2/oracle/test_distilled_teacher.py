#!/usr/bin/env python3
"""Identity and killed-mutant checks for the compact teacher runtime."""
from __future__ import annotations

import copy
import os

import numpy as np

import distilled_teacher_arm as D
import oracle_arm as O
import oracle_teacher_distill as T


def initial_decision(seed=61000):
    from fb import FB
    import root_search as RS

    C, model = O.init_rig("exo_lulu")
    env = O.make_env(seed, C["level"])
    fb = FB.from_board(env.board)
    col, vir = RS.board_flat_from_fb(fb)
    vals = O._champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                           int(env.nxt.a), int(env.nxt.b), C["w"], C["fl"],
                           C["wt"], C["ws"])
    legal = [int(a) for a in O.CHAMP_ORDER if np.isfinite(vals[int(a)])]
    ranked = sorted(range(len(legal)),
                    key=lambda i: (-vals[legal[i]], i))[:O.TOPK]
    cands = [legal[i] for i in ranked]
    rec = {
        "seed": seed, "ply": 0, "col": np.asarray(col, dtype=np.int8),
        "vir": np.asarray(vir, dtype=np.int8),
        "cur": (int(env.cur.a), int(env.cur.b)),
        "nxt": (int(env.nxt.a), int(env.nxt.b)),
        "cands": np.asarray(cands, dtype=np.int8),
        "cand_vals": np.asarray([vals[a] for a in cands]),
        "teacher_rank": 0, "was_flip": 0,
        "viruses_pre": int(env.board.virus_count()),
        "maxh_pre": int(O.heights(env.board.color).max()),
        "d_spawn_h_pre": int(max(O.heights(env.board.color)[3:5])),
        "n_legal": len(legal), "progress_delta": None,
        "survival_delta": None,
    }
    return C, model, env, rec


def main():
    if not os.environ.get("DR_LULU_FIT"):
        raise SystemExit("DR_LULU_FIT is required")
    bundle = D.load_policy()
    _C, _model, env, rec = initial_decision()

    # T1: online four-row expansion is byte/numerically identical to the
    # corpus builder used to fit the artifact.
    Xref, names_ref, *_ = T.feature_matrix([rec])
    Xdref, dnames_ref = T.decision_matrix(Xref, names_ref)
    expand, _all32, fl = T.S2F.build_expander()
    X, names, Xd, dnames = D.decision_features(
        env, rec["col"], rec["vir"], rec["cands"], rec["cand_vals"],
        rec["n_legal"], expand, fl)
    assert names == names_ref
    assert dnames == dnames_ref
    assert np.array_equal(X, Xref)
    assert np.array_equal(Xd, Xdref[0])

    # T2: sklearn-free traversal reaches the frozen high-virus leaf.
    doc = bundle["true"]
    row = np.zeros(len(doc["decision_feature_names"]), dtype=np.float64)
    j = doc["decision_feature_names"].index("base_viruses_pre")
    row[j] = 8
    right = D.tree_score(doc["flip_tree"], row)
    row[j] = 2
    left = D.tree_score(doc["flip_tree"], row)
    assert right > left

    # T3 killed mutant: reversing every branch cannot masquerade as the same
    # tree on the named probe.  This demonstrates the traversal check can fail.
    mutant = copy.deepcopy(doc["flip_tree"])
    mutant["nodes"][0]["left"], mutant["nodes"][0]["right"] = (
        mutant["nodes"][0]["right"], mutant["nodes"][0]["left"])
    row[j] = 8
    assert D.tree_score(mutant, row) != D.tree_score(doc["flip_tree"], row)

    # T4 killed mutant: a reordered feature contract is rejected before play.
    bad = copy.deepcopy(bundle)
    bad["true"]["candidate_feature_names"][0:2] = reversed(
        bad["true"]["candidate_feature_names"][0:2])
    arm = D.DistilledTeacherArm(bad, "true")
    try:
        arm._check_feature_contract(names, dnames)
    except RuntimeError as exc:
        assert "feature contract" in str(exc)
    else:
        raise AssertionError("mutated feature contract was accepted")

    print("PASS T1 feature identity")
    print("PASS T2 frozen tree traversal")
    print("PASS T3 reversed-branch mutant killed")
    print("PASS T4 feature-contract mutant killed")


if __name__ == "__main__":
    main()
