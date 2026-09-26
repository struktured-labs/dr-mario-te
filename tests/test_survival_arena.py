"""Survival-screen contracts that do not need a full level-11 search."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experiments", "cvx"))

import survival_arena as S  # noqa: E402


def test_wilson_covers_published_kc40():
    lo, hi = S.wilson_interval(246, 600)
    assert lo < 0.41 < hi
    assert 0.0 <= lo < hi <= 1.0


def test_mcnemar_balanced_is_one_and_one_sided_is_small():
    assert S.mcnemar_p(0, 0) == 1.0
    assert S.mcnemar_p(5, 5) == 1.0
    assert S.mcnemar_p(0, 10) < 0.01


def test_legacy_arm_is_refused_without_flag():
    try:
        S.parse_arm("holes80")
    except S.ArmError as e:
        assert "fw_holes80" in str(e)
    else:
        raise AssertionError("holes80 was accepted as a shipping screen")
    spec = S.parse_arm("holes80", allow_legacy=True)
    assert spec["theta400_search"] is False
    assert spec["chain"] == 0 and spec["strand"] == 0


def test_firmware_arm_is_theta400():
    spec = S.parse_arm("fw_holes80")
    assert spec["theta400_search"] is True
    assert spec["leaf"] == "winholes80"
    assert spec["chain"] == 180 and spec["strand"] == 20
    assert spec["shipped_leaf"] is False
    shipped = S.parse_arm("fw_winner")
    assert shipped["shipped_leaf"] is True
    S.assert_screenable(spec)
    try:
        S.assert_screenable(S.parse_arm("kc40", allow_legacy=True))
    except S.ArmError:
        pass
    else:
        raise AssertionError("kc40 passed the shipping-search check")


def test_chain_override_is_not_the_shipped_search():
    spec = S.parse_arm("fw_winner", chain=540)
    assert spec["chain"] == 540
    assert spec["theta400_search"] is False
    try:
        S.assert_screenable(spec)
    except S.ArmError:
        pass
    else:
        raise AssertionError("DRCHAIN=540 was treated as the shipped search")


def test_owner_model_matches_committed_fit():
    model = S.load_owner_model()
    p, n = model.fire_probability(5)
    assert abs(p - 0.32051282051282054) < 1e-12 and n == 156
    p, n = model.fire_probability(8)
    assert abs(p - 0.7407407407407407) < 1e-12 and n == 27
    p, _n = model.fire_probability(12)
    assert abs(p - 0.4) < 1e-12
    assert model.n_volleys == 61


def test_banked_gateb_matches_published_rates():
    for arm, rate in S.PUBLISHED_TAPOUT.items():
        rows = S.load_banked(arm)
        summary = S.summarize(rows, n_boot=200)
        assert summary["n"] == 600
        assert abs(summary["tapout"] - rate) < 1e-12
        assert summary["tapout_ci95"][0] < rate < summary["tapout_ci95"][1]
        if summary["n_topout"]:
            assert summary["time_to_topout_s_median"] > 0


def test_clock_size_draw_matches_gate_b():
    assert S._clock_k(0.0) == 2
    assert S._clock_k(0.80) == 3
    assert S._clock_k(0.94) == 4
    assert S._clock_k(0.955) == 2
    assert S._clock_k(0.97) == 8


def test_short_game_records_tapout_fields():
    spec = S.parse_arm("fw_winner")
    scenario = S.load_scenario("owner")

    def choose(env, _col, _vir, _ctx):
        mask = env.action_masks()
        for i, ok in enumerate(mask):
            if ok:
                return int(i)
        return None

    row = S.play_seed(7, spec, scenario, max_pills=4, choose=choose)
    for key in ("topout", "won", "elapsed_s", "how", "garbage", "dies_ahead", "brain"):
        assert key in row
    assert row["brain"] == "theta400"
    assert row["chain"] == 180 and row["strand"] == 20
    assert row["how"] in ("clear", "topout", "stall")


def _arena_row(seed, arm, chain, strand, topout, leaf="winner", label=None):
    row = {
        "seed": seed,
        "arm": arm,
        "chain": chain,
        "strand": strand,
        "leaf": leaf,
        "topout": topout,
        "won": 0 if topout else 1,
        "stall": 0,
        "dies_ahead": 0,
        "elapsed_s": 12.0 if topout else 30.0,
        "pills": 8 if topout else 20,
    }
    if label is not None:
        row["label"] = label
    return row


def test_summary_does_not_merge_chain_doses():
    """`run --arm fw_winner --chain 540` writes arm=fw_winner. Grouping by arm
    name alone merged those rows with the chain-180 fw_winner rows."""
    chain_180 = [_arena_row(1, "fw_winner", 180, 20, 1),
                 _arena_row(2, "fw_winner", 180, 20, 1)]
    chain_540 = [_arena_row(1, "fw_winner", 540, 20, 0),
                 _arena_row(2, "fw_winner", 540, 20, 0)]
    text = S.render_summary(chain_180 + chain_540, n_boot=20)
    assert "n=4" not in text
    assert "fw_winner chain=180 strand=20 leaf=winner: n=2" in text
    assert "fw_winner chain=540 strand=20 leaf=winner: n=2" in text
    assert "100.00%" in text and "0.00%" in text
    pair_lines = [ln for ln in text.splitlines() if "paired n=" in ln]
    assert pair_lines == [
        ln for ln in pair_lines
        if "chain=540" in ln and "chain=180" in ln and "paired n=2" in ln and "-100.00pp" in ln
    ]
    assert len(pair_lines) == 1

    # Same arm and dose, different explicit labels, stay apart.
    labeled = [
        _arena_row(1, "fw_winner", 540, 20, 1, label="screen-a"),
        _arena_row(1, "fw_winner", 540, 20, 0, label="screen-b"),
    ]
    groups = S.group_rows_by_config(labeled)
    assert len(groups) == 2
    assert {len(rows) for _k, _n, rows in groups} == {1}

    # Older jsonl has no chain/strand/leaf. Those still summarise under the arm name.
    legacy = [
        {"arm": "fw_winner", "seed": 1, "topout": 0, "won": 1,
         "elapsed_s": 1.0, "pills": 3},
        {"arm": "fw_winner", "seed": 2, "topout": 1, "won": 0,
         "elapsed_s": 4.0, "pills": 8},
    ]
    legacy_groups = S.group_rows_by_config(legacy)
    assert len(legacy_groups) == 1
    assert legacy_groups[0][1] == "fw_winner"

    # Three configs: pair only the arms that share chain and strand.
    # A chain-540 seed must not enter the chain-180 comparison.
    mixed = [
        _arena_row(1, "fw_winner", 180, 20, 1),
        _arena_row(2, "fw_winner", 180, 20, 1),
        _arena_row(1, "fw_winner", 540, 20, 0),
        _arena_row(2, "fw_winner", 540, 20, 0),
        _arena_row(1, "fw_holes80", 180, 20, 0, leaf="winholes80"),
        _arena_row(2, "fw_holes80", 180, 20, 1, leaf="winholes80"),
    ]
    mixed_text = S.render_summary(mixed, n_boot=20)
    mixed_pairs = [ln for ln in mixed_text.splitlines() if "paired n=" in ln]
    assert len(mixed_pairs) == 1
    assert "chain=540" not in mixed_pairs[0]
    assert "chain=180" in mixed_pairs[0]
    assert "fw_holes80" in mixed_pairs[0] and "fw_winner" in mixed_pairs[0]
    assert "paired n=2" in mixed_pairs[0]
    assert "-50.00pp" in mixed_pairs[0]
    assert "fw_winner chain=540 strand=20 leaf=winner: n=2" in mixed_text


def test_resolve_matches_flat_board():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experiments", "cvx"))
    import repo_paths
    repo_paths.install()
    from fw_brain import resolve_selfcheck
    bad, checked = resolve_selfcheck(n=25, seed=11)
    assert checked == 25
    assert bad == 0, f"{bad} resolve mismatches"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        print(fn.__name__, flush=True)
        fn()
    print(f"{len(fns)} passed")
