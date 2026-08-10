import marimo

__generated_with = "0.23.16"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        # Dr. Mario — player stats, one master table

        Every measured number we hold on every named player, in a single table, with the
        **confidence tier as a first-class column** rather than a footnote.

        Sources are read live off disk at run time (stdlib `json` only — no numpy, no
        pandas, no plotting library), so the notebook opens anywhere `marimo` is
        installed and does not depend on the project's pinned venv.

        | # | source | what it supplies |
        |---|---|---|
        | 1 | `player_styles/*.md` | identity, scene role, record vs the AI, one-line style |
        | 2 | `results/dr_lulu_20260808_fit.json` | dr. lulu's fitted pressure model (pooled) |
        | 3 | `results/struktured_20260804_pooled_fit.json` | struktured's pooled fit, regenerated from `bursty_model.fit_struktured_20260804()` |
        | 4 | `results/style_ensemble_v1/*_sending_fit.json` | per-player SENDING profiles (struktured, Bidwell, Jarsdad, Rob Burrito, davesmithsays) |
        | 5 | `STYLE_ENSEMBLE_V1.md` §5–7 | the confidence-tier rule and the published cross-check values |
        | 6 | `FILM_REVIEW_20260804_SCORECARD.md` | struktured's metric battery (declined clears, corrections, latency) |
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Read this before reading the table: pooled ≠ per-player

        Two different fit scopes appear below and **they are not interchangeable.**

        - **SENDING** — only the volleys a player's own clears actually sent onto the
          opponent's board. This is the honest per-player profile.
        - **POOLED** — both sides' events summed together. `STYLE_ENSEMBLE_V1.md` §6a
          established that a pooled fit is *contaminated*: 33 of struktured's 61 pooled
          volleys turned out to be the AI coprocessor's own sending events, and the AI's
          cadence is a near-deterministic ROM rule, not human style.

        dr. lulu's fit is **pooled** — `refit_dr_lulu.py` is symmetric across both sides
        by construction ("the fit itself is symmetric/pooled across both sides
        regardless", its own module docstring), deliberately matching the struktured
        precedent so the two stay apples-to-apples. No separated sending fit exists for
        her yet. So her headline **40.8%** must be compared to struktured's **pooled
        32.1%**, never to his separated 28.2%. The like-for-like table further down does
        exactly that comparison; the master table labels every row's scope.
        """
    )
    return


@app.cell(hide_code=True)
def _():
    import json
    import os

    QA_WT = "/home/struktured/projects/dr-mario-qa-wt"
    EVAL47 = os.path.join(QA_WT, "experiments", "eval47")
    RESULTS = os.path.join(EVAL47, "results")
    ENSEMBLE = os.path.join(RESULTS, "style_ensemble_v1")
    STYLES = os.path.join(QA_WT, "player_styles")

    def load_json(*parts):
        path = os.path.join(*parts)
        with open(path) as fh:
            return json.load(fh), path

    return ENSEMBLE, EVAL47, RESULTS, STYLES, load_json, os


@app.cell(hide_code=True)
def _(ENSEMBLE, RESULTS, load_json):
    fit_lulu, path_lulu = load_json(RESULTS, "dr_lulu_20260808_fit.json")
    fit_strukt_pooled, path_strukt_pooled = load_json(
        RESULTS, "struktured_20260804_pooled_fit.json"
    )
    fit_strukt_send, path_strukt_send = load_json(
        ENSEMBLE, "struktured_20260804_P1_sending_fit.json"
    )
    fit_bidwell, path_bidwell = load_json(ENSEMBLE, "white_top_Bidwell_sending_fit.json")
    fit_jarsdad, path_jarsdad = load_json(ENSEMBLE, "white_bottom_Jarsdad_sending_fit.json")
    fit_roburrito, path_roburrito = load_json(ENSEMBLE, "red_bracket_RobBurrito_sending_fit.json")
    fit_dss, path_dss = load_json(ENSEMBLE, "green_bottom_davesmithsays_sending_fit.json")
    # The AI's own SENDING profile from the same session -- scope-matched to struktured's.
    fit_ai_send, path_ai_send = load_json(
        ENSEMBLE, "struktured_20260804_P2_sending_fit.json"
    )
    return (
        fit_ai_send,
        fit_bidwell,
        fit_dss,
        fit_jarsdad,
        fit_lulu,
        fit_roburrito,
        fit_strukt_pooled,
        fit_strukt_send,
        path_ai_send,
        path_bidwell,
        path_dss,
        path_jarsdad,
        path_lulu,
        path_roburrito,
        path_strukt_pooled,
        path_strukt_send,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## The confidence rule, as code

        Straight from `STYLE_ENSEMBLE_V1.md` §7. `NO DATA` is this notebook's name for
        the n=0 case that §7 writes as "UNINFORMATIVE (zero)" — it is broken out because
        it triggers a *different* action: not "caveat the number" but "there is no number
        to print." The suppression is applied by `tier_suppresses_numbers()` below, so no
        pressure figure for a zero-volley player can reach the table by hand-typing.
        """
    )
    return


@app.cell
def _():
    def confidence_tier(n_volleys):
        """n>=20 FITTED · 10<=n<20 LOW-CONF · 0<n<10 UNINFORMATIVE · n==0 NO DATA."""
        match n_volleys:
            case 0:
                return "NO DATA"
            case n if n >= 20:
                return "FITTED"
            case n if n >= 10:
                return "LOW-CONF"
            case _:
                return "UNINFORMATIVE"

    def tier_suppresses_numbers(tier):
        """NO DATA means no pressure-conditional figure is publishable. Team rule."""
        return tier == "NO DATA"

    TIER_ORDER = ["FITTED", "LOW-CONF", "UNINFORMATIVE", "NO DATA"]
    return TIER_ORDER, confidence_tier, tier_suppresses_numbers


@app.cell(hide_code=True)
def _():
    def mean(xs):
        return sum(xs) / len(xs) if xs else None

    def pk(fit, bin_label):
        """p_within_k lives under two different key names across the fit files."""
        block = fit.get("p_within_k") or fit.get("p_volley_within_k_by_clear_size") or {}
        return block.get(bin_label) or {}

    def pct(entry):
        p = entry.get("p")
        match p is None or p != p:  # NaN is the only value unequal to itself
            case True:
                return None
            case False:
                return 100.0 * p

    def fmt_pct(entry):
        value = pct(entry)
        match value is None:
            case True:
                return "&mdash;"
            case False:
                return f"{value:.1f}% <span class='n'>(n={entry.get('n', 0)})</span>"

    def fmt_num(x, digits=2, suffix=""):
        return "&mdash;" if x is None else f"{x:.{digits}f}{suffix}"

    return fmt_num, fmt_pct, mean, pct, pk


@app.cell(hide_code=True)
def _(
    confidence_tier,
    fit_ai_send,
    fit_bidwell,
    fit_dss,
    fit_jarsdad,
    fit_lulu,
    fit_roburrito,
    fit_strukt_send,
    mean,
    pk,
):
    def profile(fit, scope):
        n_volleys = fit["n_volleys"]
        return {
            "scope": scope,
            "n_volleys": n_volleys,
            "n_clears": fit["n_clears"],
            "tier": confidence_tier(n_volleys),
            "volley_size_mean": mean(fit.get("volley_sizes", [])),
            "gap_s": mean(fit.get("gap_samples", [])),
            "p46": pk(fit, "4-6"),
            "p710": pk(fit, "7-10"),
        }

    PROFILES = {
        "Combo Stomper (AI)": profile(fit_ai_send, "SENDING"),
        "dr. lulu": profile(fit_lulu, "POOLED"),
        "struktured": profile(fit_strukt_send, "SENDING"),
        "bidwell": profile(fit_bidwell, "SENDING"),
        "jarsdad": profile(fit_jarsdad, "SENDING"),
        "roburrito": profile(fit_roburrito, "SENDING"),
        "davesmithsays": profile(fit_dss, "SENDING"),
    }
    return (PROFILES,)


@app.cell(hide_code=True)
def _():
    # Dossier-derived facts. Prose fields only -- every number in the master table is
    # computed from a fit file, except the battery block, which is quoted from the
    # film-review scorecard and carries its source line.
    ROSTER = {
        "Combo Stomper (AI)": {
            "role": "The AI. FPGA coprocessor champion, strand180_20 (core a0d5190f) on Pocket/MiSTer",
            "record": (
                "vs struktured 3-2 in sets, but ACROSS BUILDS (v3, v4, strand20); "
                "vs dr. lulu 0 sets won, lifetime. On strand20 alone: 1-1 vs struktured, 0-1 vs dr. lulu"
            ),
            "battery": {
                # Not "not run": these have different answers for a machine.
                "declined_clear": "<span class='n'>pending</span>",
                "corrections_per_100": "<span class='n'>n/a &mdash; deterministic nav</span>",
                "median_latency": "<span class='n'>see speed column</span>",
                "src": "declined-clear decomposition doc is not in this worktree",
            },
            "style": (
                "Risk-neutral racer: wins by out-racing, never out-building; dies while ahead "
                "under timed pressure (the 82x edge case); no attack timing."
            ),
            "src": "player_styles/struktured.md + dr_lulu.md record tables",
        },
        "dr. lulu": {
            "role": "Household champion; first human ever to KO the Combo Stomper",
            "record": "UNDEFEATED in sets vs every Stomper build; 3–0 vs strand180_20 (2026-08-08)",
            "battery": None,
            "style": (
                "Low, flat fortress (stack ≤~4 rows) with timed small-ball drip pressure; "
                "wins by harvesting the AI's edge cases, not by out-racing the search."
            ),
            "src": "player_styles/dr_lulu.md",
        },
        "struktured": {
            "role": "Household co-pilot on this project; the AI's primary test opponent",
            "record": "2–3 in recorded sets vs Stomper builds (2026-08-02..08-04); holds the first human set win and the first full-clear win",
            "battery": {
                "declined_clear": "47.9%",
                "corrections_per_100": "7.25",
                "median_latency": "250 ms",
                "src": "FILM_REVIEW_20260804_SCORECARD.md (n=331 pills, 60 fps)",
            },
            "style": (
                "Quick, deliberate, clean builder whose signature is over-setup — declines "
                "47.9% of available immediate clears; wins by out-lasting, loses on last-2-virus closing lines."
            ),
            "src": "player_styles/struktured.md",
        },
        "bidwell": {
            "role": "TooManyGames DrMC event organizer; expert-tier community player",
            "record": "never played the AI",
            "battery": None,
            "style": (
                "A lead, not a finding: the highest fast counter-fire rate in the whole ensemble, "
                "reading as an aggressive fast-follow-through attacker — pending more footage."
            ),
            "src": "player_styles/bidwell.md",
        },
        "jarsdad": {
            "role": "DrMC Championship 2024 competitor (seed 35, White Bracket)",
            "record": "never played the AI",
            "battery": None,
            "style": (
                "Reads as an aggressive, fast-cadence presser: the fastest inter-volley gap in the "
                "per-player table, paired with high follow-through."
            ),
            "src": "player_styles/jarsdad.md",
        },
        "roburrito": {
            "role": "DrMC scene regular (Championship 2024 Red Bracket, seed 17); DRMC Philadelphia 2026 attendee",
            "record": "never played the AI",
            "battery": None,
            "style": (
                "Moderate-tempo, struktured-like attacker — the closest profile in the ensemble to "
                "struktured's own numbers. One physical tell: index+middle pre-staged over A and B."
            ),
            "src": "player_styles/roburrito.md",
        },
        "davesmithsays": {
            "role": "DrMC Championship 2024 competitor (seed 44, Green Bracket); DRMC Philadelphia 2026 attendee",
            "record": "never played the AI",
            "battery": None,
            "style": (
                "Identity confirmed, style unknown. 51 of his own clears produced zero attributed "
                "volleys in the one usable VS window — the dossier's standing instruction is to cite NO pressure numbers."
            ),
            "src": "player_styles/davesmithsays.md",
        },
    }
    return (ROSTER,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Champion dies-ahead under each player's own pressure

        The payoff column. Each fitted pressure model was replayed against the shipped
        champion (ws=20) for n=120 paired games; **dies-ahead** counts games the AI topped
        out while still holding a virus lead (`viruses_remaining <= 12` at death) — the
        champion's known 82x pressured failure mode, and the thing a human actually
        exploits.

        Counts are recomputed here from the per-seed rows of each rig JSON, not read off a
        summary line. Only two players have a fitted model at usable confidence, so only two
        rows carry a number.
        """
    )
    return


@app.cell(hide_code=True)
def _(RESULTS, load_json):
    fit_rig_lulu, path_rig_lulu = load_json(
        RESULTS, "dr_lulu_20260808_rig_n120_wt0_ws20.json"
    )
    fit_rig_v11, path_rig_v11 = load_json(RESULTS, "bursty_v1_1_n120_wt0_ws20.json")
    fit_rig_v1, path_rig_v1 = load_json(RESULTS, "bursty_n120_wt0_ws20.json")
    return (
        fit_rig_lulu,
        fit_rig_v1,
        fit_rig_v11,
        path_rig_lulu,
        path_rig_v1,
        path_rig_v11,
    )


@app.cell(hide_code=True)
def _(fit_rig_lulu, fit_rig_v1, fit_rig_v11):
    def rig_tally(rows):
        n = len(rows)
        dies = sum(1 for r in rows if r["dies_ahead"])
        topout = sum(1 for r in rows if r["topout"])
        stall = sum(1 for r in rows if r["stall"])
        won = sum(1 for r in rows if r["won"])
        return {
            "n": n,
            "dies_ahead": dies,
            "dies_ahead_pct": 100.0 * dies / n,
            "won": won,
            "clear_pct": 100.0 * won / n,
            "topout": topout,
            "stall": stall,
            "bad_ends": topout + stall,
            "bad_ends_pct": 100.0 * (topout + stall) / n,
        }

    # arm == the shipped champion (ws=20); ctrl == ws=0, kept for the rescue delta.
    RIGS = {
        "lulu_pooled": {
            "arm": rig_tally(fit_rig_lulu["arm"]),
            "ctrl": rig_tally(fit_rig_lulu["ctrl"]),
            "model": "dr. lulu 20260808 fit (POOLED)",
            "file": "dr_lulu_20260808_rig_n120_wt0_ws20.json",
        },
        "strukt_sending": {
            "arm": rig_tally(fit_rig_v11["arm"]),
            "ctrl": rig_tally(fit_rig_v11["ctrl"]),
            "model": "bursty v1.1 = struktured's SEPARATED P1 sending fit",
            "file": "bursty_v1_1_n120_wt0_ws20.json",
        },
        "strukt_pooled": {
            "arm": rig_tally(fit_rig_v1["arm"]),
            "ctrl": rig_tally(fit_rig_v1["ctrl"]),
            "model": "bursty v1 = struktured's POOLED fit (contaminated)",
            "file": "bursty_n120_wt0_ws20.json",
        },
    }

    # Only players whose own fitted model was actually run against the champion.
    PLAYER_RIG = {"dr. lulu": "lulu_pooled", "struktured": "strukt_sending"}
    return PLAYER_RIG, RIGS


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Decision speed, and the instrument check that gates it

        **Definition (identical for every player, so the numbers are comparable):**
        `latency_frames = first_input_frame - spawn_frame` at 60 fps, from the per-pill
        tracker CSVs; `ms = frames / 60 * 1000`. The **reactive population** is
        `latency_frames > 6`; at or below 6 frames the pill is *pre-planned* (including 0,
        a pill that appears already moving under a held button) and is excluded, as are
        straight drops with no input before lock. This is the film review's own definition,
        reused unchanged.

        **These numbers are gated on a control.** The tracker failed on the P2 side of the
        night-two capture — 19.4% of pills were recorded as locking while still in their
        spawn row, against 0–6% across the reference corpus (task #95). A spawn-row lock is
        a tracking-failure signature: the tracker lost the capsule and finalized it where it
        started. A latency computed from a run like that is noise wearing a number's
        clothes.

        So each side is measured first, and its rate must fall inside the reference band
        before any latency is published. The gate is applied in code below — a side that
        fails cannot print a percentile.
        """
    )
    return


@app.cell(hide_code=True)
def _(RESULTS, os):
    import csv
    import re
    import statistics as stats

    LATENCY_DIR = os.path.join(RESULTS, "latency_events")
    SPAWN_LOCK_BAND = (0.0, 6.0)  # reference-corpus range, task #95
    PREPLAN_THRESH = 6            # frames; <=6 is pre-planned, not a reaction

    def read_rows(path):
        match os.path.exists(path):
            case False:
                return None
            case True:
                with open(path) as fh:
                    return list(csv.DictReader(fh))

    def pctl(vals, p):
        """Linear-interpolation percentile - the film review's own `pctl`."""
        vals = sorted(vals)
        k = (len(vals) - 1) * p
        f = int(k)
        c = min(f + 1, len(vals) - 1)
        return vals[f] if f == c else vals[f] + (vals[c] - vals[f]) * (k - f)

    def spawn_lock_rate(rows):
        """Share of pills the tracker finalized still occupying spawn row 0."""
        hits = sum(
            1 for r in rows
            if any(int(m) == 0 for m in re.findall(r"\((\d+),\d+\)", r["final_cells"]))
        )
        return len(rows), hits, (100.0 * hits / len(rows) if rows else 0.0)

    def latency_profile(csv_paths):
        """Control first; percentiles only if it passes. Always returns a status."""
        loaded = [(p, read_rows(p)) for p in csv_paths]
        missing = [p for p, r in loaded if r is None]
        match missing:
            case []:
                pass
            case _:
                return {"status": "SOURCE MISSING", "missing": missing}

        rows = [r for _p, rs in loaded for r in rs]
        n_pills, lock_hits, lock_pct = spawn_lock_rate(rows)
        lo, hi = SPAWN_LOCK_BAND
        passed = lo <= lock_pct <= hi
        out = {
            "n_pills": n_pills,
            "spawn_locks": lock_hits,
            "spawn_lock_pct": lock_pct,
            "control_passed": passed,
        }
        match passed:
            case False:
                out["status"] = "CONTROL FAILED"
                return out
            case True:
                lat, preplan, straight = [], 0, 0
                for r in rows:
                    fi = r["first_input_frame"]
                    match fi:
                        case "":
                            straight += 1
                        case _:
                            delta = int(fi) - int(r["spawn_frame"])
                            match delta <= PREPLAN_THRESH:
                                case True:
                                    preplan += 1
                                case False:
                                    lat.append(delta)

                def f2ms(frames):
                    return frames / 60 * 1000

                out.update(
                    status="OK",
                    n_reactive=len(lat),
                    preplanned_pct=100.0 * preplan / n_pills,
                    straight_pct=100.0 * straight / n_pills,
                    p50_ms=f2ms(stats.median(lat)),
                    p75_ms=f2ms(pctl(lat, 0.75)),
                    p90_ms=f2ms(pctl(lat, 0.90)),
                    sd_ms=f2ms(stats.stdev(lat)),
                    max_ms=f2ms(max(lat)),
                )
                return out

    LATENCY = {
        "struktured": {
            "profile": latency_profile([
                os.path.join(LATENCY_DIR, "film_20260804", f"{m}.csv")
                for m in ("m1", "m2", "m3", "m4")
            ]),
            "source": "20260804 capture, P1 (human) side, matches m1-m4",
        },
        "dr. lulu": {
            "profile": latency_profile(
                [os.path.join(LATENCY_DIR, "film_20260808", "p1_m3.csv")]
            ),
            "source": "20260808 capture, P1 (human) side, m3 window 555-739 s",
        },
    }
    return LATENCY, SPAWN_LOCK_BAND


@app.cell(hide_code=True)
def _(RESULTS, load_json):
    # Shadow-latency pilot (task #92). Cached by eval47/cache_shadowlat.py, which imports
    # the gated analyzer and refuses to write unless its killed-mutant selftest passes.
    SHADOWLAT, path_shadowlat = load_json(RESULTS, "shadowlat_pilot_summary.json")
    return SHADOWLAT, path_shadowlat


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## The master table""")
    return


@app.cell(hide_code=True)
def _():
    # Ordinal blue ramp, one hue, monotone lightness -- confidence is an ORDERED tier,
    # not an identity. Both mode ramps pass all four ordinal checks of the dataviz
    # validator (light end 2.06:1 on the light surface, 2.15:1 on the dark).
    VIZ_CSS = """
    <style>
    .pstat {
      color-scheme: light;
      --surface-1: #fcfcfb; --surface-2: #f4f3f0;
      --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #6f6e69;
      --rule: #dedcd6;
      --tier-fitted: #184f95; --tier-low: #3987e5; --tier-uninf: #86b6ef;
      --tier-nodata: #a3a29b;
      font-size: 13px; color: var(--text-primary);
    }
    @media (prefers-color-scheme: dark) {
      :root:where(:not([data-theme="light"])) .pstat {
        color-scheme: dark;
        --surface-1: #1a1a19; --surface-2: #242422;
        --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #94938a;
        --rule: #3a3a36;
        --tier-fitted: #cde2fb; --tier-low: #3987e5; --tier-uninf: #184f95;
        --tier-nodata: #55544e;
      }
    }
    :root[data-theme="dark"] .pstat {
      color-scheme: dark;
      --surface-1: #1a1a19; --surface-2: #242422;
      --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #94938a;
      --rule: #3a3a36;
      --tier-fitted: #cde2fb; --tier-low: #3987e5; --tier-uninf: #184f95;
      --tier-nodata: #55544e;
    }
    .pstat .scroll { overflow-x: auto; max-width: 100%; }
    .pstat table { border-collapse: separate; border-spacing: 0; width: 100%; min-width: 1180px; }
    .pstat th, .pstat td {
      padding: 9px 11px; text-align: left; vertical-align: top;
      border-bottom: 1px solid var(--rule); white-space: nowrap;
    }
    .pstat th {
      font-size: 11px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
      color: var(--text-secondary); border-bottom: 2px solid var(--rule);
      background: var(--surface-2); position: sticky; top: 0;
    }
    .pstat td.wrap, .pstat th.wrap { white-space: normal; min-width: 230px; }
    /* 14 columns cannot fit any sane viewport, so the table scrolls -- pin the
       identity column so a row stays identifiable at any scroll offset. */
    .pstat td.handle, .pstat th.handle {
      font-weight: 650; white-space: nowrap;
      position: sticky; left: 0; z-index: 1; background: var(--surface-1);
      box-shadow: 1px 0 0 var(--rule);
    }
    .pstat th.handle { background: var(--surface-2); z-index: 3; }
    .pstat tr.suppressed td.handle { background: var(--surface-2); }
    .pstat .n { color: var(--text-muted); font-size: 11px; }
    .pstat .sub { color: var(--text-secondary); font-size: 11px; display: block; }
    .pstat .num { font-variant-numeric: tabular-nums; }
    .pstat .chip {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-size: 10.5px; font-weight: 700; letter-spacing: .03em; white-space: nowrap;
    }
    .pstat .chip-FITTED { background: var(--tier-fitted); color: var(--surface-1); }
    .pstat .chip-LOW-CONF { background: var(--tier-low); color: #ffffff; }
    .pstat .chip-UNINFORMATIVE { background: var(--tier-uninf); color: #0b0b0b; }
    .pstat .chip-NODATA {
      background: transparent; color: var(--text-secondary);
      box-shadow: inset 0 0 0 1.5px var(--tier-nodata);
    }
    .pstat .scope {
      font-size: 10.5px; font-weight: 700; letter-spacing: .04em; color: var(--text-secondary);
    }
    .pstat tr.suppressed td { background: var(--surface-2); }
    .pstat td.blocked { box-shadow: inset 3px 0 0 var(--tier-nodata); }
    .pstat caption {
      caption-side: bottom; text-align: left; padding-top: 10px;
      color: var(--text-secondary); font-size: 11.5px; line-height: 1.55; white-space: normal;
    }
    </style>
    """
    return (VIZ_CSS,)


@app.cell(hide_code=True)
def _(
    LATENCY,
    PLAYER_RIG,
    PROFILES,
    RIGS,
    ROSTER,
    SHADOWLAT,
    VIZ_CSS,
    fmt_num,
    fmt_pct,
    mo,
    tier_suppresses_numbers,
):
    def chip(tier):
        cls = "NODATA" if tier == "NO DATA" else tier
        return f"<span class='chip chip-{cls}'>{tier}</span>"

    def battery_cells(battery):
        match battery:
            case None:
                blank = "<span class='n'>not run</span>"
                return blank, blank, blank
            case _:
                return (
                    f"<span class='num'>{battery['declined_clear']}</span>",
                    f"<span class='num'>{battery['corrections_per_100']}</span>",
                    f"<span class='num'>{battery['median_latency']}</span>",
                )

    def dies_ahead_cell(handle):
        """One cell carrying the rate, its n, and which fitted model produced it."""
        match handle:
            case "Combo Stomper (AI)":
                # The column asks how the champion fares under a player's pressure; for
                # the champion itself the question is inverted, and the answer is the
                # survival ladder below rather than a single cell.
                return (
                    "<td><span class='n'>n/a &mdash; it IS the champion</span>"
                    "<span class='sub'>see the survival ladder</span></td>"
                )
        key = PLAYER_RIG.get(handle)
        match key:
            case None:
                return (
                    "<td><span class='n'>&mdash;</span>"
                    "<span class='sub'>no fitted model at usable confidence</span></td>"
                )
            case _:
                rig = RIGS[key]
                arm, ctrl = rig["arm"], rig["ctrl"]
                scope = "POOLED" if "POOLED" in rig["model"] else "SENDING"
                title = (
                    f"{handle}: champion ws=20 under {rig['model']} — "
                    f"{arm['dies_ahead']}/{arm['n']} dies-ahead, clear {arm['clear_pct']:.1f}%, "
                    f"topout {arm['topout']} stall {arm['stall']}; "
                    f"ws=0 control {ctrl['dies_ahead']}/{ctrl['n']}"
                )
                return (
                    f"<td title='{title}'>"
                    f"<span class='num'><b>{arm['dies_ahead_pct']:.1f}%</b></span> "
                    f"<span class='n'>({arm['dies_ahead']}/{arm['n']})</span>"
                    f"<span class='sub'>{scope} fit &middot; ws=0 ctrl "
                    f"{ctrl['dies_ahead_pct']:.1f}%</span></td>"
                )

    def latency_cell(handle):
        """p50/p75/p90, or the precise reason there is no number."""
        match handle:
            case "Combo Stomper (AI)":
                # Per-decision SEARCH latency, silicon domain. The sim-lockstep pair and the
                # film-observed placement interval are DIFFERENT quantities; they live in the
                # detail table below rather than being averaged into one number.
                sil, sim = SHADOWLAT["silicon"], SHADOWLAT["sim_lockstep"]
                title = (
                    f"Per-decision search latency, champion {SHADOWLAT['arm']}, "
                    f"n={sil['n_decisions']} decisions over {SHADOWLAT['n_games']} games. "
                    f"SILICON median {sil['median_frames']:.1f} f "
                    f"({sil['median_seconds']:.2f} s), p90 {sil['p90_frames']:.1f} f. "
                    f"SIM-LOCKSTEP median {sim['median_frames']:.1f} f — the domains differ "
                    f"{SHADOWLAT['domain_ratio']:.4f}x. Film-observed placement INTERVAL, a "
                    f"different quantity, is 1.54 to 2.13 s."
                )
                return (
                    f"<td title='{title}'>"
                    f"<span class='num'><b>{sil['median_frames']:.1f}</b> / "
                    f"{sil['p90_frames']:.1f} f</span>"
                    f"<span class='sub'>~{sil['median_seconds']:.2f} s median &middot; "
                    f"<b>SILICON</b> &middot; n={sil['n_decisions']} decisions</span></td>"
                )
        entry = LATENCY.get(handle)
        match entry:
            case None:
                return (
                    "<td><span class='n'>&mdash;</span>"
                    "<span class='sub'>no per-pill tracking exists</span></td>"
                )
        p = entry["profile"]
        match p["status"]:
            case "SOURCE MISSING":
                return (
                    "<td><span class='n'>&mdash;</span>"
                    "<span class='sub'>source CSV not found</span></td>"
                )
            case "CONTROL FAILED":
                return (
                    "<td class='blocked'><span class='n'>instrument blocked (#95)</span>"
                    f"<span class='sub'>{p['spawn_lock_pct']:.1f}% spawn-row locks "
                    f"({p['spawn_locks']}/{p['n_pills']}), band 0&ndash;6%</span></td>"
                )
            case _:
                title = (
                    f"{handle}: reactive latency, {entry['source']}. "
                    f"n={p['n_reactive']} reactive of {p['n_pills']} pills "
                    f"({p['preplanned_pct']:.1f}% pre-planned, {p['straight_pct']:.1f}% straight drops); "
                    f"sd {p['sd_ms']:.0f} ms, max {p['max_ms']:.0f} ms. "
                    f"Control: {p['spawn_lock_pct']:.1f}% spawn-row locks, inside the 0-6% band."
                )
                return (
                    f"<td title='{title}'>"
                    f"<span class='num'><b>{p['p50_ms']:.0f}</b> / {p['p75_ms']:.0f} / "
                    f"{p['p90_ms']:.0f} ms</span>"
                    f"<span class='sub'>sd {p['sd_ms']:.0f} ms &middot; n={p['n_reactive']} reactive</span></td>"
                )

    def master_row(handle):
        prof, meta = PROFILES[handle], ROSTER[handle]
        suppressed = tier_suppresses_numbers(prof["tier"])
        dash = "<span class='n'>&mdash; suppressed</span>"
        match suppressed:
            case True:
                size = gap = p46 = p710 = dash
            case False:
                size = f"<span class='num'>{fmt_num(prof['volley_size_mean'])}</span>"
                gap = f"<span class='num'>{fmt_num(prof['gap_s'], 1, ' s')}</span>"
                p46 = f"<span class='num'>{fmt_pct(prof['p46'])}</span>"
                p710 = f"<span class='num'>{fmt_pct(prof['p710'])}</span>"
        declined, corrections, latency = battery_cells(meta["battery"])
        cells = [
            f"<td class='handle'>{handle}<span class='sub'>{meta['src'].split('/')[-1]}</span></td>",
            f"<td class='wrap'>{meta['role']}</td>",
            f"<td class='wrap'>{meta['record']}</td>",
            f"<td><span class='scope'>{prof['scope']}</span></td>",
            f"<td class='num'>{prof['n_volleys']}<span class='sub'>{prof['n_clears']} clears</span></td>",
            f"<td>{chip(prof['tier'])}</td>",
            f"<td>{size}</td>",
            f"<td>{gap}</td>",
            f"<td>{p46}</td>",
            f"<td>{p710}</td>",
            dies_ahead_cell(handle),
            latency_cell(handle),
            f"<td>{declined}</td>",
            f"<td>{corrections}</td>",
            f"<td>{latency}</td>",
            f"<td class='wrap'>{meta['style']}</td>",
        ]
        klass = " class='suppressed'" if suppressed else ""
        return f"<tr{klass}>" + "".join(cells) + "</tr>"

    MASTER_ORDER = [
        "Combo Stomper (AI)",
        "dr. lulu", "struktured", "bidwell", "jarsdad", "roburrito", "davesmithsays",
    ]

    HEADERS = [
        ("player", " class='handle'"), ("scene role", " class='wrap'"), ("record vs the AI", " class='wrap'"),
        ("fit scope", ""), ("n volleys", ""), ("confidence", ""),
        ("volley size", ""), ("inter-volley gap", ""),
        ("P(volley | 4-6 clear)", ""), ("P(volley | 7-10 clear)", ""),
        ("champion dies-ahead under THEIR pressure", ""),
        ("decision latency p50 / p75 / p90", ""),
        ("declined clears", ""), ("corrections /100 pills", ""),
        ("median latency (dossier)", ""),
        ("style, one line", " class='wrap'"),
    ]

    master_table = mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table>"
        + "<thead><tr>"
        + "".join(f"<th{attr}>{name}</th>" for name, attr in HEADERS)
        + "</tr></thead><tbody>"
        + "".join(master_row(h) for h in MASTER_ORDER)
        + "</tbody><caption>"
        + "Pressure columns come from the fit JSONs named in the player cell; battery columns "
        + "from FILM_REVIEW_20260804_SCORECARD.md; the dies-ahead column is recomputed from the "
        + "per-seed rows of each n=120 rig JSON (champion ws=20, hover a cell for its full "
        + "provenance). <b>Fit scope</b> distinguishes a POOLED fit (both sides' events, "
        + "contaminated per STYLE_ENSEMBLE_V1.md &sect;6a) from a per-player SENDING fit &mdash; "
        + "and it applies to the dies-ahead column too, so those two numbers are NOT "
        + "scope-matched (see below). davesmithsays' pressure cells are suppressed "
        + "programmatically by the NO DATA tier, not omitted by hand."
        + "</caption></table></div></div>"
    )
    master_table
    return (MASTER_ORDER,)


@app.cell(hide_code=True)
def _(
    LATENCY,
    MASTER_ORDER,
    PLAYER_RIG,
    PROFILES,
    RIGS,
    ROSTER,
    mo,
    pct,
    tier_suppresses_numbers,
):
    def rounded(x, digits):
        return None if x is None else round(x, digits)

    def sortable_record(handle):
        prof, meta = PROFILES[handle], ROSTER[handle]
        suppressed = tier_suppresses_numbers(prof["tier"])
        rig = RIGS.get(PLAYER_RIG.get(handle) or "", None)
        lat = (LATENCY.get(handle) or {}).get("profile") or {}
        ok = lat.get("status") == "OK"
        return {
            "player": handle,
            "confidence": prof["tier"],
            "fit_scope": prof["scope"],
            "n_volleys": prof["n_volleys"],
            "n_clears": prof["n_clears"],
            "volley_size_mean": None if suppressed else rounded(prof["volley_size_mean"], 2),
            "inter_volley_gap_s": None if suppressed else rounded(prof["gap_s"], 1),
            "p_volley_4_6_pct": None if suppressed else rounded(pct(prof["p46"]), 1),
            "p_volley_7_10_pct": None if suppressed else rounded(pct(prof["p710"]), 1),
            "champ_dies_ahead_pct": rounded(rig["arm"]["dies_ahead_pct"], 1) if rig else None,
            "champ_dies_ahead_n": rig["arm"]["n"] if rig else None,
            "rig_model": rig["model"] if rig else None,
            "latency_p50_ms": rounded(lat.get("p50_ms"), 0) if ok else None,
            "latency_p75_ms": rounded(lat.get("p75_ms"), 0) if ok else None,
            "latency_p90_ms": rounded(lat.get("p90_ms"), 0) if ok else None,
            "latency_sd_ms": rounded(lat.get("sd_ms"), 0) if ok else None,
            "latency_n_reactive": lat.get("n_reactive") if ok else None,
            "tracker_control": lat.get("status"),
            "declined_clear": (meta["battery"] or {}).get("declined_clear"),
            "corrections_per_100": (meta["battery"] or {}).get("corrections_per_100"),
            "median_latency": (meta["battery"] or {}).get("median_latency"),
            "played_the_AI": meta["record"] != "never played the AI",
        }

    mo.vstack(
        [
            mo.md(
                "### Same rows, sortable\n"
                "The machine-readable view of the table above, for filtering and sorting. "
                "`None` in a pressure column means the value is suppressed or undefined, never zero."
            ),
            mo.ui.table(
                [sortable_record(h) for h in MASTER_ORDER],
                selection=None,
                pagination=False,
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## P(volley | 4-6-cell clear), by player

        The bread-and-butter conversion rate: how often a mid-size clear turns into
        pressure on the opponent within 5 s. Bars are ordered by rate and stepped by
        confidence on a single-hue ordinal ramp: **shade encodes how much evidence stands
        behind a bar, never the rate** — the best-evidenced tier is the step that contrasts
        most with the page, so it is the darkest in light mode and the lightest in dark
        mode. Every bar is direct-labeled with its tier, so the ranking never depends on
        reading a color at all.

        The chart is the reason the confidence column exists. Bidwell tops it on n=8
        volleys, which is below every band we accept; his bar is drawn in the palest
        step and should be read as a lead worth more footage, not as a finding.
        """
    )
    return


@app.cell(hide_code=True)
def _(MASTER_ORDER, PROFILES, VIZ_CSS, mo, pct, tier_suppresses_numbers):
    CHART_CSS = """
    <style>
    /* Three columns: name | plotting area | label. Giving labels their own column
       makes value/tier text collision-proof at any bar length. */
    .pstat .chart { max-width: 860px; padding: 4px 0 2px; }
    .pstat .chart .row, .pstat .chart .axis {
      display: grid; grid-template-columns: 108px minmax(0, 1fr) 232px; gap: 12px;
      align-items: center;
    }
    .pstat .chart .row { margin-bottom: 9px; }
    .pstat .chart .who { text-align: right; font-weight: 600; font-size: 12px; }
    .pstat .chart .track { height: 22px; background: var(--surface-2); border-radius: 4px; }
    .pstat .chart .fill { height: 100%; border-radius: 0 4px 4px 0;
                          box-shadow: 0 0 0 2px var(--surface-1); }
    .pstat .chart .fill.f-FITTED { background: var(--tier-fitted); }
    .pstat .chart .fill.f-LOW-CONF { background: var(--tier-low); }
    .pstat .chart .fill.f-UNINFORMATIVE { background: var(--tier-uninf); }
    .pstat .chart .lab { font-size: 11.5px; color: var(--text-secondary);
                         font-variant-numeric: tabular-nums; white-space: nowrap; }
    .pstat .chart .val { color: var(--text-primary); font-weight: 650; }
    .pstat .chart .none { height: 22px; line-height: 22px; font-size: 11.5px;
                          color: var(--text-secondary); padding-left: 9px;
                          border-left: 2px dashed var(--tier-nodata); white-space: nowrap; }
    .pstat .legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 12px 0 4px 120px;
                     font-size: 11px; color: var(--text-secondary); }
    .pstat .legend span.k { display: inline-block; width: 11px; height: 11px;
                            border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
    .pstat .chart .axis { font-size: 10.5px; color: var(--text-muted); }
    .pstat .chart .axis .ticks { display: flex; justify-content: space-between;
                                 border-top: 1px solid var(--rule); padding-top: 3px; }
    </style>
    """

    def chart_rows():
        rows = []
        for handle in MASTER_ORDER:
            prof = PROFILES[handle]
            value = None if tier_suppresses_numbers(prof["tier"]) else pct(prof["p46"])
            rows.append((handle, value, prof["tier"], prof["p46"].get("n", 0)))
        # Ranked; the suppressed player sorts last and is shown, not dropped.
        return sorted(rows, key=lambda r: (r[1] is not None, r[1] or 0), reverse=True)

    def bar(handle, value, tier, n_clears):
        match value is None:
            case True:
                body = (
                    "<div class='none'>0 attributed volleys from 51 own clears</div>"
                    "<div class='lab'>NO DATA &mdash; no rate is publishable</div>"
                )
            case False:
                width = 100.0 * value / 60.0  # axis runs 0-60%
                title = f"{handle}: {value:.1f}% of {n_clears} clears (4-6 cells) drew a volley within 5 s [{tier}]"
                body = (
                    f"<div class='track' title='{title}'>"
                    f"<div class='fill f-{tier}' style='width:{width:.1f}%'></div></div>"
                    f"<div class='lab'><span class='val'>{value:.1f}%</span> "
                    f"&middot; {tier} &middot; n={n_clears}</div>"
                )
        return f"<div class='row'><div class='who'>{handle}</div>{body}</div>"

    legend = (
        "<div class='legend'>"
        "<span><span class='k' style='background:var(--tier-fitted)'></span>FITTED (n&ge;20)</span>"
        "<span><span class='k' style='background:var(--tier-low)'></span>LOW-CONF (10&ndash;19)</span>"
        "<span><span class='k' style='background:var(--tier-uninf)'></span>UNINFORMATIVE (&lt;10)</span>"
        "<span><span class='k' style='background:transparent;box-shadow:inset 0 0 0 1.5px var(--tier-nodata)'></span>NO DATA (n=0)</span>"
        "</div>"
    )

    mo.Html(
        VIZ_CSS
        + CHART_CSS
        + "<div class='pstat'><div class='chart'>"
        + "".join(bar(*r) for r in chart_rows())
        + "<div class='axis'><span></span>"
        + "<span class='ticks'><span>0%</span><span>30%</span><span>60%</span></span>"
        + "<span></span></div>"
        + legend
        + "</div></div>"
    )
    return


@app.cell(hide_code=True)
def _(LATENCY, SPAWN_LOCK_BAND, VIZ_CSS, mo):
    def control_row(handle):
        entry = LATENCY[handle]
        p = entry["profile"]
        match p["status"]:
            case "SOURCE MISSING":
                verdict, colour, detail = "NO SOURCE", "var(--text-secondary)", "&mdash;"
            case "CONTROL FAILED":
                verdict, colour = "FAIL", "#d03b3b"
                detail = (f"{p['spawn_lock_pct']:.1f}% "
                          f"({p['spawn_locks']}/{p['n_pills']})")
            case _:
                verdict, colour = "PASS", "var(--tier-fitted)"
                detail = (f"{p['spawn_lock_pct']:.1f}% "
                          f"({p['spawn_locks']}/{p['n_pills']})")
        published = (
            f"{p['p50_ms']:.0f} / {p['p75_ms']:.0f} / {p['p90_ms']:.0f} ms"
            if p["status"] == "OK" else "<span class='n'>none &mdash; withheld</span>"
        )
        return (
            f"<tr><td class='handle'>{handle}</td>"
            f"<td class='n'>{entry['source']}</td>"
            f"<td class='num'>{detail}</td>"
            f"<td style='color:{colour};font-weight:700'>{verdict}</td>"
            f"<td class='num'>{published}</td></tr>"
        )

    lo, hi = SPAWN_LOCK_BAND
    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:760px'><thead><tr>"
        + "<th>player</th><th>footage measured</th><th>spawn-row lock rate</th>"
        + f"<th>control ({lo:.0f}&ndash;{hi:.0f}%)</th><th>latency published</th>"
        + "</tr></thead><tbody>"
        + "".join(control_row(h) for h in ("struktured", "dr. lulu"))
        + "</tbody><caption>"
        + "The control is run on the same tracker output the latency would come from, so a "
        + "pass certifies the exact numbers published. For reference the tracker scores "
        + "1.2% (4/331) across the whole 20260804 corpus and <b>19.4% (18/93) on the P2 "
        + "side of the night-two capture</b> &mdash; the failure recorded as task #95, "
        + "reproduced here as the check's negative control."
        + "</caption></table></div></div>"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## The AI's decision speed, in both clock domains

        The human latency column and this one measure different things and must not be
        read across: a human's number is *reaction* time from spawn to first input; the
        AI's is *search* time for one `decide()` call. And the AI's own number exists in
        two clocks — the verilated sim ticks the coprocessor in lockstep at 48 master
        clocks per CPU cycle, while real silicon runs it on a 54.669 MHz async tap. They
        differ by a factor the analyzer computes rather than assumes, and quoting one
        without saying which is how that factor travels into a wrong conclusion.

        Two budgets, also not interchangeable. **Fall** asks whether the answer arrived
        after the capsule had already fallen past its target, which makes the placement
        unreachable. **Window** asks whether the answer would have landed before the
        capsule even spawned — the DRPRESTART question — and uses the tallest *hit*
        column against the 264 − 16·h garbage window.
        """
    )
    return


@app.cell(hide_code=True)
def _(SHADOWLAT, VIZ_CSS, mo):
    def dom_row(label, key, emphasis):
        s = SHADOWLAT[key]
        w = SHADOWLAT["window_miss_h13plus_" + ("silicon" if key == "silicon" else "sim")]

        def em(text):
            return f"<b>{text}</b>" if emphasis else text

        med = em(f"{s['median_frames']:.1f}")
        late = em(f"{s['late_pct']:.1f}%")
        return (
            f"<tr><td>{em(label)}</td>"
            f"<td class='num'>{med} f</td>"
            f"<td class='num'>{s['p90_frames']:.1f} f</td>"
            f"<td class='num'>{late}</td>"
            f"<td class='num'>{s['band_9_12_late_pct']:.1f}%</td>"
            f"<td class='num'>{w['miss_pct']:.1f}% "
            f"<span class='n'>({w['miss']}/{w['n']})</span></td></tr>"
        )

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:860px'><thead><tr>"
        + "<th>clock domain</th><th>median search</th><th>p90</th>"
        + "<th>LATE vs fall budget</th><th>LATE at height 9-12</th>"
        + "<th>misses garbage window, h&ge;13</th></tr></thead><tbody>"
        + dom_row("silicon (54.669 MHz async tap) &mdash; the real one", "silicon", True)
        + dom_row("sim-lockstep (48x per CPU cycle)", "sim_lockstep", False)
        + "</tbody><caption>"
        + f"n={SHADOWLAT['silicon']['n_decisions']} decisions over "
        + f"{SHADOWLAT['n_games']} games, champion {SHADOWLAT['arm']}. Domain ratio "
        + f"<b>{SHADOWLAT['domain_ratio']:.4f}x</b>, computed by the analyzer from its own "
        + "clock constants. <b>The domain choice changes the verdict, not just the digits:</b> "
        + "on silicon the champion is late on 14.1% of decisions at board height 9-12 &mdash; "
        + "exactly the crowded boards where a late answer costs a game &mdash; but the same "
        + "runs read 2.8% in sim-lockstep. A sim-domain reader would conclude the search is "
        + "comfortably fast. It is not, on the hardware it ships on."
        + "<br>&#9888; <b>The h&ge;13 window miss is a LIMIT, not a prize.</b> At a tall "
        + "board the 264&minus;16&middot;h window has shrunk to almost nothing, so the "
        + "search cannot finish inside it however early it starts &mdash; that is where "
        + "DRPRESTART is <i>weakest</i>, not where it pays. Reading this row as the case "
        + "for prestart inverts the mechanism; the instrument's value sits at h&le;12, "
        + "where the window is long enough to absorb a whole search."
        + "</caption></table></div></div>"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Owner's four-metric battery — what each instrument can actually answer

        Two of the four are cleanly computable from the per-pill tracker CSVs, one is
        computable only in a weaker form than the question implies, and one has no
        instrument that passes a control today. They are reported that way.

        **1. Horizontal vs vertical clears — WEAK form only.** The CSVs record the
        orientation of the *pill*, so what is computable is how the clearing placement was
        lying. The likely intent — whether the cleared *line* ran along a row or a column —
        needs the board state either side of the clear, which these files do not carry. A
        second limit: a clear is detected by the virus count dropping, so pill-only clears
        are invisible and these are virus-clearing placements specifically.

        **2. Drop speed min/max — answered.** Spawn to lock in 60 fps frames. Spawn-row
        locks are excluded; they contribute near-zero lifetimes, and the minimum is exactly
        the statistic such an artifact would capture.

        **3. A vs B — answered as rotation DIRECTION.** The tracker sees orientation
        transitions, never buttons. Monocolor pills are reported separately as `tog`: with
        both halves identical the direction is genuinely unknowable, and folding them into
        either side would invent a preference.

        **4. Cascade vs instant — NOT computable.** Separating a settle-clear from a direct
        placement clear needs per-clear board state; the CSVs carry only a virus count per
        pill, which cannot tell a cascade from a multi-line direct clear.
        """
    )
    return


@app.cell(hide_code=True)
def _(VIZ_CSS, mo, os):
    import collections as _coll
    import csv as _csv
    import re as _re
    import statistics as _st

    _LE = ("/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/results/"
           "latency_events")
    B4_SRC = {
        "struktured": [f"{_LE}/film_20260804/{m}.csv" for m in ("m1", "m2", "m3", "m4")],
        "dr. lulu": [f"{_LE}/film_20260808/p1_m3.csv"],
    }
    B4_HORIZ = {"H", "HF"}

    def b4_profile(paths):
        mats = []
        for p in paths:
            if not os.path.exists(p):
                return None
            with open(p) as fh:
                mats.append(list(_csv.DictReader(fh)))

        clearing = []
        for rows in mats:
            vl = [int(r["viruses_left_p1"]) for r in rows]
            clearing += [r for i, r in enumerate(rows[:-1]) if vl[i + 1] < vl[i]]
        h = sum(1 for r in clearing if r["final_orient"] in B4_HORIZ)

        def spawn_row_lock(r):
            return any(int(m) == 0
                       for m in _re.findall(r"\((\d+),\d+\)", r["final_cells"]))

        life, excl = [], 0
        for rows in mats:
            for r in rows:
                if spawn_row_lock(r):
                    excl += 1
                else:
                    life.append(int(r["lock_frame"]) - int(r["spawn_frame"]))

        rot = _coll.Counter()
        for rows in mats:
            for r in rows:
                for tok in filter(None, r["rotation_seq"].split(",")):
                    rot[tok.split("@")[0]] += 1
        directional = rot["cw"] + rot["ccw"]

        return {
            "clear_n": len(clearing), "horiz": h,
            "horiz_pct": 100.0 * h / len(clearing) if clearing else None,
            "life_n": len(life), "life_excl": excl,
            "min_f": min(life), "max_f": max(life), "med_f": _st.median(life),
            "cw": rot["cw"], "ccw": rot["ccw"], "tog": rot["tog"],
            "cw_pct": 100.0 * rot["cw"] / directional if directional else None,
            "directional": directional,
        }

    B4 = {k: b4_profile(v) for k, v in B4_SRC.items()}

    def b4_row(name):
        p = B4[name]
        if p is None:
            return (f"<tr><td class='handle'>{name}</td>"
                    "<td colspan='4' class='n'>source missing</td></tr>")
        return (
            f"<tr><td class='handle'>{name}</td>"
            f"<td class='num'>{p['horiz_pct']:.1f}% H / {100 - p['horiz_pct']:.1f}% V"
            f"<span class='sub'>n={p['clear_n']} virus-clearing pills</span></td>"
            f"<td class='num'>{p['min_f']} &ndash; {p['max_f']} f"
            f"<span class='sub'>{p['min_f']/60:.2f}&ndash;{p['max_f']/60:.2f} s &middot; "
            f"median {p['med_f']:.0f} f &middot; n={p['life_n']} "
            f"({p['life_excl']} excl)</span></td>"
            f"<td class='num'>{p['cw_pct']:.0f}% CW / {100 - p['cw_pct']:.0f}% CCW"
            f"<span class='sub'>n={p['directional']} directional &middot; "
            f"{p['tog']} monocolor unknowable</span></td>"
            f"<td class='n'>&mdash; no instrument</td></tr>"
        )

    def b4_absent(name, reason):
        return (f"<tr><td class='handle'>{name}</td>"
                f"<td colspan='4' class='n'>&mdash; {reason}</td></tr>")

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:960px'><thead><tr>"
        + "<th>player</th><th>clearing-pill orientation</th>"
        + "<th>drop speed min &ndash; max</th><th>rotation direction</th>"
        + "<th>cascade vs instant</th></tr></thead><tbody>"
        + b4_absent("Combo Stomper (AI)",
                    "needs a replay pass (jointdig p0_corpus / Mesen census); not run this pass")
        + b4_row("dr. lulu")
        + b4_row("struktured")
        + b4_absent("bidwell, jarsdad, roburrito, davesmithsays",
                    "no per-pill tracking exists for any of them")
        + "</tbody><caption>"
        + "<b>The rotation column is the answer to &quot;A vs B&quot; this data can support, "
        + "and it is a striking one:</b> dr. lulu rotated the same way on every single "
        + "directional rotation in her window, while struktured splits 77/23 &mdash; a "
        + "one-button player beside a two-button one, consistent with his dossier's "
        + "&quot;two-button retrain baseline&quot;."
        + "<br>&#9888; <b>Button mapping, corrected:</b> the ROM at $8E2B does "
        + "<code>AND #$80 &rarr; DEC $A5</code> and <code>AND #$40 &rarr; INC $A5</code>, so "
        + "<b>A rotates CCW and B rotates CW</b> &mdash; the opposite of the A=CW/B=CCW "
        + "mapping this task was specified with, and <code>tuck_enum.py</code> flags the same "
        + "inversion sitting in a comment at <code>drmario/controller.py:103</code>. The "
        + "column still says CW/CCW: naming a button also needs the tracker's orientation "
        + "ring to run the same direction as the ROM's <code>$A5</code>, which matches on "
        + "parity but is unverified on direction, so the observable stays on the label."
        + "</caption></table></div></div>"
    )
    return


@app.cell(hide_code=True)
def _(VIZ_CSS, mo, os):
    import collections as _c2
    import csv as _csv2

    _LE2 = ("/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/results/"
            "latency_events")
    RING = ["H", "V", "HF", "VF"]          # spawn is always H, so delta = index(final)
    ROT_SRC = {
        "struktured": [f"{_LE2}/film_20260804/{m}.csv" for m in ("m1", "m2", "m3", "m4")],
        "dr. lulu": [f"{_LE2}/film_20260808/p1_m3.csv"],
    }

    def rot_profile(paths):
        rows = []
        for p in paths:
            if not os.path.exists(p):
                return None
            with open(p) as fh:
                rows += list(_csv2.DictReader(fh))
        a = _c2.Counter()
        waste = waste_pills = mixed = bad = 0
        for r in rows:
            toks = [t.split("@")[0] for t in r["rotation_seq"].split(",") if t]
            if "tog" in toks or r["final_orient"] not in RING:
                a["mono"] += 1
                continue
            cw, ccw = toks.count("cw"), toks.count("ccw")
            d = RING.index(r["final_orient"])
            if (cw - ccw) % 4 != d:        # control: ring/spawn/labels mutually consistent
                bad += 1
            a["pills"] += 1
            a["cw"] += cw
            a["ccw"] += ccw
            a[f"d{d}"] += 1
            minimal = min(d, 4 - d)
            a["ideal"] += minimal
            match (cw > 0 and ccw > 0):
                case True:
                    mixed += 1
                case False:
                    if (cw + ccw) - minimal > 0:
                        waste += (cw + ccw) - minimal
                        waste_pills += 1
        n1, n2, n3 = a["d1"], a["d2"], a["d3"]
        direc = a["cw"] + a["ccw"]
        return {
            "n_rows": len(rows), "pills": a["pills"], "mono": a["mono"], "control_bad": bad,
            "d0": a["d0"], "d1": n1, "d2": n2, "d3": n3,
            "dump_cw": 100.0 * (n1 + 2 * n2) / (n1 + 2 * n2 + n3),
            "split_cw": 100.0 * (n1 + n2) / (n1 + n3 + 2 * n2),
            "actual_cw": 100.0 * a["cw"] / direc, "cw": a["cw"], "ccw": a["ccw"],
            "presses": direc, "ideal": a["ideal"],
            "waste": waste, "waste_pills": waste_pills, "mixed": mixed,
            "waste_per100": 100.0 * waste / len(rows),
        }

    ROT = {k: rot_profile(v) for k, v in ROT_SRC.items()}

    def rot_row(name):
        p = ROT[name]
        inside = p["split_cw"] <= p["actual_cw"] <= p["dump_cw"]
        verdict = ("<b style='color:var(--tier-fitted)'>inside the optimal band</b>"
                   if inside else "<b style='color:#d03b3b'>outside the band</b>")
        return (
            f"<tr><td class='handle'>{name}</td>"
            f"<td class='num'>{p['d1']} CW-eff / {p['d3']} CCW-eff / {p['d2']} free"
            f"<span class='sub'>{p['d0']} needed no rotation &middot; "
            f"{p['mono']} monocolor excluded</span></td>"
            f"<td class='num'>{p['split_cw']:.1f}% &ndash; {p['dump_cw']:.1f}%"
            f"<span class='sub'>split-free &hellip; dump-free-into-CW</span></td>"
            f"<td class='num'><b>{p['actual_cw']:.1f}%</b>"
            f"<span class='sub'>{p['cw']} cw / {p['ccw']} ccw &middot; {verdict}</span></td>"
            f"<td class='num'><b>{p['waste_per100']:.1f}</b> / 100 pills"
            f"<span class='sub'>{p['waste']} presses over {p['waste_pills']} pills &middot; "
            f"{p['mixed']} mixed-direction (corrections, not direction error)</span></td></tr>"
        )

    _ctrl = sum(p["control_bad"] for p in ROT.values() if p)
    _tot = sum(p["pills"] for p in ROT.values() if p)
    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:980px'><thead><tr>"
        + "<th>player</th><th>placements needing rotation</th><th>OPTIMAL CW band</th>"
        + "<th>ACTUAL CW share</th><th>direction waste</th></tr></thead><tbody>"
        + rot_row("dr. lulu") + rot_row("struktured")
        + "</tbody><caption>"
        + "A pill spawns at H on the ring [H, V, HF, VF], so the distance to its locked "
        + "orientation is 1 (cheaper CW), 3 (cheaper CCW) or <b>2 &mdash; a 180 flip "
        + "costing two presses either way, i.e. a FREE choice</b>. Because free choices are "
        + "cost-identical, optimal play is not one ratio but a <b>band</b>: anywhere from "
        + "splitting them evenly to dumping them all one way is equally efficient. "
        + f"<b>Control: (cw&minus;ccw) mod 4 == delta on {_tot}/{_tot} non-monocolor pills, "
        + f"{_ctrl} violations</b> &mdash; ring, spawn orientation and direction labels are "
        + "mutually consistent, and this analysis needs none of the ROM button mapping. "
        + "Waste is charged only on pills rotated entirely one way that were cheaper the "
        + "other way; mixed-direction pills are corrections, not direction errors, and free "
        + "choices are unchargeable by construction."
        + "</caption></table></div></div>"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ### What that says about the owner's hypothesis

        **His guess was that his ideal is ~60/40 and that he over-favours CW at 77/23. The
        placements say otherwise, and the free choice is why.** His forced placements are
        almost perfectly symmetric — 28 CW-efficient against 30 CCW-efficient — so the
        forced component alone would call for roughly an even split. But 71 of his 129
        rotating placements are 180 flips, where direction costs nothing. That makes *any*
        CW share between 49.5% and 85.0% exactly as cheap, and his actual 76.9% sits
        **inside** that band. He is not over-favouring CW; he is spending free choices on
        his strong hand, which is free.

        His real direction cost is small and specific: **6.0 wasted presses per 100 pills**,
        from 8 pills taken the long way round.

        **dr. lulu's one-buttoning is the expensive one.** Her band is 47.8%–82.6% and she
        plays 100% CW, outside it — a delta-3 placement, cheap at one CCW press, costs her
        three CW presses instead. That is **32.4 wasted presses per 100 pills, 5.4x his
        rate**, and it is the clearest mechanical inefficiency the film has produced for
        either player.

        **The link to her slower minimum drop does not hold.** His fastest pill used *zero*
        rotations (a pure soft-drop, 10 f); hers used one. The two minima are over different
        kinds of pill — an extreme-value statistic with one player on each side — so nothing
        supports connecting her 0.32 s to her press waste. The mechanism fails before the
        sample size does.
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## The AI's survival ladder — its signature stat

        No human row has this: the same champion, the same build, measured across three
        pressure regimes. It is the clearest single statement of what the AI is.

        **One metric, held constant.** The ladder is quoted in *dies-ahead* — topping out
        while still holding a virus lead. Mixing a solo *failure* rate with a pressured
        *dies-ahead* rate would compare two different events and manufacture a slope, so
        both are shown per row and the ladder is read down the dies-ahead column.
        """
    )
    return


@app.cell(hide_code=True)
def _(RIGS, VIZ_CSS, mo, os):
    import json as _json

    CENSUS = (
        "/home/struktured/projects/dr-mario-qa-wt/experiments/adversary/"
        "census/census_results.jsonl"
    )

    def census_tally():
        match os.path.exists(CENSUS):
            case False:
                return None
            case True:
                rows = [_json.loads(l) for l in open(CENSUS) if l.strip()]
                bad = [r for r in rows if r.get("result") != "clear"]
                dies = [r for r in bad if r.get("dies_ahead")]
                return {
                    "n": len(rows),
                    "bad": len(bad),
                    "bad_pct": 100.0 * len(bad) / len(rows),
                    "dies": len(dies),
                    "dies_pct": 100.0 * len(dies) / len(rows),
                    "detail": ", ".join(
                        f"seed {r['seed']} {r['result']} at {r.get('viruses_left')} virus"
                        for r in bad
                    ),
                }

    CEN = census_tally()

    def ladder_row(regime, dies_pct, dies_n, n, bad_pct, source, note):
        return (
            f"<tr><td>{regime}</td>"
            f"<td class='num'><b>{dies_pct}</b> <span class='n'>({dies_n}/{n})</span></td>"
            f"<td class='num'>{bad_pct}</td>"
            f"<td class='n'>{source}</td><td class='n'>{note}</td></tr>"
        )

    solo = (
        ladder_row(
            "Solo, clean stream (no pressure)",
            f"{CEN['dies_pct']:.2f}%", CEN["dies"], CEN["n"], f"{CEN['bad_pct']:.3f}%",
            "adversary/census/census_results.jsonl",
            f"partial census, {100*CEN['n']/65536:.1f}% of seed values. Only failure: {CEN['detail']}",
        )
        if CEN else
        "<tr><td>Solo, clean stream</td><td colspan='4' class='n'>census file not found</td></tr>"
    )

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:900px'><thead><tr>"
        + "<th>pressure regime</th><th>dies-ahead</th><th>all bad ends</th>"
        + "<th>source</th><th>caveat</th></tr></thead><tbody>"
        + solo
        + ladder_row(
            "Under struktured's fitted pressure",
            f"{RIGS['strukt_sending']['arm']['dies_ahead_pct']:.1f}%",
            RIGS["strukt_sending"]["arm"]["dies_ahead"], 120,
            f"{RIGS['strukt_sending']['arm']['bad_ends_pct']:.1f}%",
            "bursty_v1_1_n120_wt0_ws20.json",
            "SENDING-scope fit (bursty v1.1)",
        )
        + ladder_row(
            "Under dr. lulu's fitted pressure",
            f"{RIGS['lulu_pooled']['arm']['dies_ahead_pct']:.1f}%",
            RIGS["lulu_pooled"]["arm"]["dies_ahead"], 120,
            f"{RIGS['lulu_pooled']['arm']['bad_ends_pct']:.1f}%",
            "dr_lulu_20260808_rig_n120_wt0_ws20.json",
            "POOLED-scope fit &mdash; not scope-matched to the row above",
        )
        + "</tbody><caption>"
        + "<b>Every number here is recomputed from a result file.</b> The ladder is the "
        + "82x story made concrete: the champion is near-flawless with nobody shooting at "
        + "it and fails an order of magnitude more often once a human is applying timed "
        + "pressure. Note the solo failure is a <i>stall at one virus</i> and is NOT "
        + "dies-ahead &mdash; solo dies-ahead is genuinely zero in this sample, so the "
        + "failure mode does not merely intensify under pressure, it <i>changes kind</i>. "
        + "<br>&#9888; The often-quoted full-space figure <b>0.0809% (53/65,536)</b> could "
        + "NOT be verified here: it was produced on the Hetzner node and "
        + "<code>experiments/hetzner/results/</code> is gitignored, so no result file backs "
        + "it in this worktree. It is also denominated in seed <i>values</i>, and seeds 2k "
        + "and 2k+1 are the same game (HETZNER_NODE.md &sect;4) &mdash; so a per-distinct-"
        + "stream rate has roughly half the denominator. Treat it as a task record, not a "
        + "measurement, until the file is recovered."
        + "</caption></table></div></div>"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## The dies-ahead numbers are NOT scope-matched either

        The same pooled-vs-sending trap reaches the payoff column, and here it changes the
        headline. dr. lulu's rig run used her **pooled** fit; struktured's row uses bursty
        **v1.1**, fit from his separated P1 sending stream. Read straight across, her
        pressure looks far more lethal than his. Most of that gap is scope.

        Run scope-matched — both pooled — the two are nearly the same, and the honest
        statement is that her fitted pressure is *slightly* harder on the champion than his,
        not dramatically so. The scope-matched pair is the row to quote in any comparison;
        the per-player rows are the ones to quote about a single player.
        """
    )
    return


@app.cell(hide_code=True)
def _(RIGS, VIZ_CSS, mo):
    def da_row(label, key, note):
        rig = RIGS[key]
        arm, ctrl = rig["arm"], rig["ctrl"]
        return (
            f"<tr><td>{label}</td>"
            f"<td class='num'><b>{arm['dies_ahead_pct']:.1f}%</b> "
            f"<span class='n'>({arm['dies_ahead']}/{arm['n']})</span></td>"
            f"<td class='num'>{ctrl['dies_ahead_pct']:.1f}% "
            f"<span class='n'>({ctrl['dies_ahead']}/{ctrl['n']})</span></td>"
            f"<td class='num'>{arm['clear_pct']:.1f}%</td>"
            f"<td class='num'>{arm['bad_ends_pct']:.1f}% "
            f"<span class='n'>({arm['topout']}t/{arm['stall']}s)</span></td>"
            f"<td class='n'>{note}</td></tr>"
        )

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:820px'><thead><tr>"
        + "<th>pressure model driving the rig</th><th>dies-ahead, champion ws=20</th>"
        + "<th>dies-ahead, ws=0 control</th><th>clear rate</th><th>bad ends</th>"
        + "<th>source</th></tr></thead><tbody>"
        + da_row("dr. lulu 20260808 &mdash; POOLED", "lulu_pooled",
                 RIGS["lulu_pooled"]["file"])
        + da_row("struktured bursty v1 &mdash; POOLED", "strukt_pooled",
                 RIGS["strukt_pooled"]["file"])
        + "<tr><td colspan='6' style='border-bottom:2px solid var(--rule)'></td></tr>"
        + da_row("struktured bursty v1.1 &mdash; SENDING", "strukt_sending",
                 RIGS["strukt_sending"]["file"])
        + "</tbody><caption>"
        + "<b>Scope-matched (top two rows): 14.2% vs 13.3%</b> &mdash; her fitted pressure kills "
        + "the champion-while-ahead marginally more often than his, on 120 paired games each. "
        + "The 14.2% vs 7.5% reading across the master table is inflated by comparing her pooled "
        + "model to his separated one. v1.1 remains the right number to cite for struktured "
        + "alone, and for &quot;how often does the shipped build die ahead under honest human "
        + "cadence&quot; &mdash; 7.5%, not 13.3% (STYLE_ENSEMBLE_V1.md &sect;6a). Every count here "
        + "is recomputed from per-seed rows."
        + "</caption></table></div></div>"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## The one like-for-like comparison: dr. lulu vs struktured, both pooled

        This is the only cross-player comparison in the notebook that is scope-clean.
        Both sides are pooled fits produced by the same code path, which is exactly why
        `refit_dr_lulu.py` was written to stay symmetric.
        """
    )
    return


@app.cell(hide_code=True)
def _(VIZ_CSS, fit_lulu, fit_strukt_pooled, mean, mo, pct, pk):
    def like_for_like():
        lulu, strukt = fit_lulu, fit_strukt_pooled
        return [
            ("n_matches", strukt["n_matches"], lulu["n_matches"], "{:.0f}"),
            ("n_volleys", strukt["n_volleys"], lulu["n_volleys"], "{:.0f}"),
            ("n_clears", strukt["n_clears"], lulu["n_clears"], "{:.0f}"),
            (
                "volley size mean",
                strukt["volley_size_mean"],
                mean(lulu["volley_sizes"]),
                "{:.3f}",
            ),
            (
                "inter-volley gap (s)",
                strukt["inter_volley_gap_mean_s"],
                mean(lulu["gap_samples"]),
                "{:.2f}",
            ),
            (
                "P(volley | 4-6 clear)",
                pct(pk(strukt, "4-6")),
                pct(pk(lulu, "4-6")),
                "{:.1f}%",
            ),
            (
                "P(volley | 7-10 clear)",
                pct(pk(strukt, "7-10")),
                pct(pk(lulu, "7-10")),
                "{:.1f}%",
            ),
        ]

    def l4l_row(label, a, b, fmt):
        return (
            f"<tr><td>{label}</td><td class='num'>{fmt.format(a)}</td>"
            f"<td class='num'><b>{fmt.format(b)}</b></td></tr>"
        )

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><table style='min-width:520px'>"
        + "<thead><tr><th>metric (POOLED both sides)</th>"
        + "<th>struktured 20260804</th><th>dr. lulu 20260808</th></tr></thead><tbody>"
        + "".join(l4l_row(*r) for r in like_for_like())
        + "</tbody><caption>"
        + "dr. lulu converts bread-and-butter 4-6-cell clears into pressure markedly more "
        + "often than the model the champion was tuned against, on a slightly tighter cadence "
        + "with smaller volleys — a steady drip rather than spikes. Caveats carried from her "
        + "dossier: 3 matches, no event-CSV lock cross-check (0/59 annotated), single level and "
        + "speed (L11 MED), v4 cart only."
        + "</caption></table></div>"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Self-check: do the derived numbers match the published ones?

        Every pressure figure above is recomputed from the raw `volley_sizes` /
        `gap_samples` / `p_within_k` arrays rather than copied out of a report. That is
        only worth something if it agrees with the published tables, so the notebook
        asserts it. A FAIL here means a fit file changed under a document that still
        quotes the old number — which is the failure this cell exists to catch.
        """
    )
    return


@app.cell(hide_code=True)
def _(LATENCY, PROFILES, RIGS, SHADOWLAT, VIZ_CSS, fit_strukt_pooled, mo, pct, pk):
    # Values as published in STYLE_ENSEMBLE_V1.md 7, dr_lulu_20260808_fit_report.md,
    # BURSTY_V1_RESULTS.md, the refit driver log, and player_styles/*.md.
    # Tolerances are one unit in the last published digit.
    CITED = [
        ("struktured", "volley_size_mean", PROFILES["struktured"]["volley_size_mean"], 2.68, 0.005, "ENSEMBLE 7"),
        ("struktured", "gap_s", PROFILES["struktured"]["gap_s"], 27.4, 0.05, "ENSEMBLE 7"),
        ("struktured", "P(4-6)", pct(PROFILES["struktured"]["p46"]), 28.2, 0.05, "ENSEMBLE 7"),
        ("struktured", "P(7-10)", pct(PROFILES["struktured"]["p710"]), 62.5, 0.05, "ENSEMBLE 7"),
        ("dr. lulu", "volley_size_mean", PROFILES["dr. lulu"]["volley_size_mean"], 2.390, 0.0005, "lulu fit report"),
        ("dr. lulu", "gap_s", PROFILES["dr. lulu"]["gap_s"], 21.85, 0.005, "lulu fit report"),
        ("dr. lulu", "P(4-6)", pct(PROFILES["dr. lulu"]["p46"]), 40.8, 0.05, "lulu fit report + dossier"),
        ("dr. lulu", "P(7-10)", pct(PROFILES["dr. lulu"]["p710"]), 56.2, 0.05, "lulu fit report"),
        ("bidwell", "P(4-6)", pct(PROFILES["bidwell"]["p46"]), 52.0, 0.05, "ENSEMBLE 7"),
        ("jarsdad", "P(4-6)", pct(PROFILES["jarsdad"]["p46"]), 50.0, 0.05, "ENSEMBLE 7"),
        ("jarsdad", "gap_s", PROFILES["jarsdad"]["gap_s"], 18.4, 0.05, "ENSEMBLE 7"),
        ("roburrito", "P(4-6)", pct(PROFILES["roburrito"]["p46"]), 25.6, 0.05, "ENSEMBLE 7"),
        ("roburrito", "volley_size_mean", PROFILES["roburrito"]["volley_size_mean"], 2.67, 0.005, "ENSEMBLE 7"),
        ("struktured (pooled)", "P(4-6)", pct(pk(fit_strukt_pooled, "4-6")), 32.1, 0.05, "lulu fit report"),
        ("struktured (pooled)", "P(7-10)", pct(pk(fit_strukt_pooled, "7-10")), 74.1, 0.05, "lulu fit report"),
        ("struktured (pooled)", "n_volleys", fit_strukt_pooled["n_volleys"], 61, 0, "bursty_model docstring"),
        ("struktured (pooled)", "n_clears", fit_strukt_pooled["n_clears"], 188, 0, "bursty_model docstring"),
        ("dr. lulu rig", "dies-ahead ws=20", RIGS["lulu_pooled"]["arm"]["dies_ahead"], 17, 0, "refit log [4/4]"),
        ("dr. lulu rig", "dies-ahead ws=0", RIGS["lulu_pooled"]["ctrl"]["dies_ahead"], 41, 0, "refit log [4/4]"),
        ("dr. lulu rig", "clear% ws=20", RIGS["lulu_pooled"]["arm"]["clear_pct"], 75.0, 0.05, "refit log [4/4]"),
        ("struktured rig v1.1", "dies-ahead ws=20", RIGS["strukt_sending"]["arm"]["dies_ahead_pct"], 7.5, 0.05, "BURSTY_V1_RESULTS 5"),
        ("struktured rig v1.1", "bad-ends ws=20", RIGS["strukt_sending"]["arm"]["bad_ends_pct"], 16.7, 0.05, "BURSTY_V1_RESULTS 5"),
        ("struktured rig v1.1", "dies-ahead ws=0", RIGS["strukt_sending"]["ctrl"]["dies_ahead_pct"], 27.5, 0.05, "BURSTY_V1_RESULTS 5"),
        ("struktured rig v1", "dies-ahead ws=20", RIGS["strukt_pooled"]["arm"]["dies_ahead_pct"], 13.3, 0.05, "BURSTY_V1_RESULTS 3"),
        ("struktured rig v1", "bad-ends ws=20", RIGS["strukt_pooled"]["arm"]["bad_ends_pct"], 26.7, 0.05, "BURSTY_V1_RESULTS 3"),
        # Latency: the film review's own published reactive population is the control for
        # this recomputation. The dossier's "median 250 ms" must equal the computed p50,
        # which is why both a transcribed and a computed latency column exist.
        ("struktured latency", "n reactive", LATENCY["struktured"]["profile"].get("n_reactive"), 244, 0, "analysis/latency.md"),
        ("struktured latency", "p50 ms", LATENCY["struktured"]["profile"].get("p50_ms"), 250.0, 0.05, "analysis/latency.md + dossier"),
        ("struktured latency", "p75 ms", LATENCY["struktured"]["profile"].get("p75_ms"), 366.7, 0.05, "analysis/latency.md"),
        ("struktured latency", "p90 ms", LATENCY["struktured"]["profile"].get("p90_ms"), 511.7, 0.05, "analysis/latency.md"),
        ("struktured latency", "pre-planned %", LATENCY["struktured"]["profile"].get("preplanned_pct"), 23.6, 0.05, "SCORECARD + dossier"),
        ("struktured latency", "straight-drop %", LATENCY["struktured"]["profile"].get("straight_pct"), 2.7, 0.05, "dossier"),
        ("struktured latency", "control spawn-lock %", LATENCY["struktured"]["profile"].get("spawn_lock_pct"), 1.2, 0.05, "reference corpus, task #95"),
        # Shadow-latency pilot: the cache must agree with the gated analyzer's own tables.
        ("AI shadowlat", "silicon median f", SHADOWLAT["silicon"]["median_frames"], 49.6, 0.05, "shadowlat_analyze table A"),
        ("AI shadowlat", "silicon p90 f", SHADOWLAT["silicon"]["p90_frames"], 63.8, 0.05, "shadowlat_analyze table A"),
        ("AI shadowlat", "silicon late %", SHADOWLAT["silicon"]["late_pct"], 9.5, 0.05, "shadowlat_analyze table A"),
        ("AI shadowlat", "silicon late % h9-12", SHADOWLAT["silicon"]["band_9_12_late_pct"], 14.1, 0.05, "shadowlat_analyze table A"),
        ("AI shadowlat", "sim median f", SHADOWLAT["sim_lockstep"]["median_frames"], 31.6, 0.05, "shadowlat_analyze table A"),
        ("AI shadowlat", "sim late %", SHADOWLAT["sim_lockstep"]["late_pct"], 2.5, 0.05, "shadowlat_analyze table A"),
        ("AI shadowlat", "window miss % h>=13", SHADOWLAT["window_miss_h13plus_silicon"]["miss_pct"], 68.2, 0.05, "shadowlat_analyze table B"),
        ("AI shadowlat", "domain ratio", SHADOWLAT["domain_ratio"], 1.5714, 0.0005, "analyzer clock constants"),
        ("AI shadowlat", "n decisions", SHADOWLAT["silicon"]["n_decisions"], 1500, 0, "pilot jsonl"),
    ]

    def check_row(who, metric, derived, cited, tol, src):
        ok = derived is not None and abs(derived - cited) <= tol
        mark = "PASS" if ok else "FAIL"
        colour = "var(--tier-fitted)" if ok else "#d03b3b"
        shown = "&mdash;" if derived is None else f"{derived:.4g}"
        return (
            f"<tr><td>{who}</td><td>{metric}</td><td class='num'>{shown}</td>"
            f"<td class='num'>{cited:g}</td><td class='n'>{src}</td>"
            f"<td style='color:{colour};font-weight:700'>{mark}</td></tr>"
        ), ok

    CHECK_ROWS = [check_row(*c) for c in CITED]
    N_PASS = sum(1 for _, ok in CHECK_ROWS if ok)

    N_CHECKS = len(CHECK_ROWS)

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:720px'><thead><tr>"
        + "<th>player</th><th>metric</th><th>derived here</th><th>as published</th>"
        + "<th>published in</th><th>&nbsp;</th></tr></thead><tbody>"
        + "".join(html for html, _ in CHECK_ROWS)
        + f"</tbody><caption><b>{N_PASS}/{N_CHECKS} cross-checks pass.</b> "
        + "Derived values are recomputed from the raw arrays and per-seed rows in the JSONs; "
        + "published values are transcribed from the reports named in the last column."
        + "</caption></table></div></div>"
    )
    return N_CHECKS, N_PASS


@app.cell(hide_code=True)
def _(N_CHECKS, N_PASS, mo):
    mo.md(
        f"""
        /// {"tip" if N_PASS == N_CHECKS else "danger"} | Cross-check result

        **{N_PASS}/{N_CHECKS} derived values agree with the published reports.**
        {"Every number in the master table traces to a fit or rig file and matches the document that quotes it."
         if N_PASS == N_CHECKS else
         f"{N_CHECKS - N_PASS} MISMATCH(ES): a file and a report have diverged - reconcile before citing anything above."}
        ///
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Coverage: who has what

        What is missing is as much a result as what is present. Nothing in this notebook
        is estimated, imputed, or carried across from a pooled fit to fill a gap.
        """
    )
    return


@app.cell(hide_code=True)
def _(LATENCY, MASTER_ORDER, PLAYER_RIG, PROFILES, ROSTER, VIZ_CSS, mo):
    def coverage_row(handle):
        prof, meta = PROFILES[handle], ROSTER[handle]
        yes = "<span style='color:var(--tier-fitted);font-weight:700'>yes</span>"
        no = "<span class='n'>no</span>"
        has_pressure = {"FITTED": yes, "LOW-CONF": yes, "UNINFORMATIVE": yes, "NO DATA": no}[prof["tier"]]
        lat_status = ((LATENCY.get(handle) or {}).get("profile") or {}).get("status")
        lat_cell = {
            "OK": f"{yes} <span class='n'>(control passed)</span>",
            "CONTROL FAILED": "<span class='n'>blocked (#95)</span>",
            "SOURCE MISSING": "<span class='n'>no source</span>",
            None: no,
        }[lat_status]
        return (
            f"<tr><td class='handle'>{handle}</td>"
            f"<td>{yes}</td>"
            f"<td>{has_pressure} <span class='n'>({prof['tier']}, {prof['scope']})</span></td>"
            f"<td>{yes if handle in PLAYER_RIG else no}</td>"
            f"<td>{lat_cell}</td>"
            f"<td>{yes if meta['battery'] else no}</td>"
            f"<td>{yes if meta['record'] != 'never played the AI' else no}</td></tr>"
        )

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:820px'><thead><tr>"
        + "<th>player</th><th>dossier</th><th>pressure fit</th><th>rig run vs champion</th>"
        + "<th>decision latency</th><th>metric battery</th><th>played the AI</th>"
        + "</tr></thead><tbody>"
        + "".join(coverage_row(h) for h in MASTER_ORDER)
        + "</tbody><caption>"
        + "The metric battery (declined-clear rate, corrections per 100 pills, decision "
        + "latency, endgame seal counting) has been run for exactly one player. A rig run "
        + "needs a fitted model first, so the four players below the confidence line have "
        + "no dies-ahead number and cannot get one without more footage."
        + "</caption></table></div></div>"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Standing gaps

        - **dr. lulu has no separated SENDING fit.** Her 40.8% is pooled and therefore
          carries some of the AI copro's near-deterministic attack cadence. Re-running her
          capture through the per-player split of `STYLE_ENSEMBLE_V1.md` §5 would make her
          directly comparable to struktured's 28.2% and is the single highest-value fix here.
          It would also make the two dies-ahead numbers directly comparable, which they
          currently are not.
        - **The metric battery is n=1 player.** Everything outside the pressure columns is
          struktured only.
        - **Only two players have a rig run,** because a rig run needs a fitted model. The
          four below the confidence line cannot get a dies-ahead number without more footage —
          this is the column that most rewards extending the corpus.
        - **The two latency samples are not the same size.** struktured's is 244 reactive
          pills over four matches; dr. lulu's is 44 over a single match window. The gap
          between them is large enough to survive that, but her percentiles will move more
          than his as windows are added, and only her m3 window has been tracked at 60 fps.
        - **Task #95 is narrower than it looked.** The P1 side of the night-two capture
          passes the same control the P2 side fails (2.7% vs 19.4%, same footage, same
          tracker, same window). Whatever breaks the tracker is specific to the P2 crop or
          to what the AI's board does, not to the capture — which is a much smaller problem
          than "the tracker does not work on captured footage."
        - **Three of six players sit below the n=20 line** and one is at zero. §8 of the
          ensemble report is blunt that an archetype grid is not possible on this data.
        - **davesmithsays needs a different window,** not a different method: his Speed-bracket
          appearances are a solo race format the volley extractor cannot fit, a documented
          negative rather than an unexplored option.
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## The blunder battery

        Five detectors over the same footage, kept as **separate rows that are never
        pooled**, because they are not equally trustworthy and averaging them would hide
        exactly that. Each one carries its own control, its own killed mutants, and its own
        false-positive estimate; a tier whose gate fails publishes nothing.

        The design constraint throughout is **precision, not recall**. A single
        "blunder rate" from engine disagreement is known-poisoned here — the vocabulary wall
        says the engine is least trustworthy near death, joint-dig closed as REFUTED, and
        struktured's 47.9% clear-decline rate was adjudicated as *style*, not error. So every
        tier is tuned to miss rather than to over-fire, and the direction of each residual
        error is stated rather than assumed.

        | tier | what fires | how it is trusted |
        |---|---|---|
        | **M** mechanical | rotation reversal / overshoot / late flurry | reproduces the film review's **hand-adjudicated** per-match counts exactly |
        | **D** wrong phase | a horizontal capsule locked colour-swapped, where the 180 flip strictly dominates on every contact | engine-free; tempo and seeding gates |
        | **D2** hard burial &mdash; **NOT QUOTABLE** | mismatched material dropped over a virus that can no longer be dug vertically | drop model controlled against the tracker's own landings; forced positions excluded &mdash; **but 77.5% / 92.1% of the flagged burials were dug back out, so the rate is a count of a recoverable state, not a blunder rate.** A matched-reopen gate ported from F2 and a last-straw rule were both tried: they move volume, not precision. dr. lulu full-cleared her m3 (39 of 39 virus sites), so every D2 flag there is false by construction. |
        | **F2** last-access seal | a self-placement takes a virus's **route count** from >0 to 0, with no matched reopen | validated against the m4 seal ledger; volley seals structurally unflaggable |
        | **O** evaporated opportunity | a top-decile clear declined, then destroyed uncashed within 3 pills | reproduces the adjudicated 47.9% decline figure exactly before flagging anything |

        The AI row is the shipped champion (`wt=0, ws=20`) over 250 solo games on a seed
        block disjoint from every earlier probe. **It is not a like-for-like opponent
        comparison**: the humans are playing versus, under incoming volleys, and the AI
        corpus is solo. Read it as a reference scale for each detector, not as a scoreboard.
        """
    )
    return


@app.cell(hide_code=True)
def _(RESULTS, VIZ_CSS, load_json, mo):
    BATTERY, path_battery = load_json(RESULTS, "blunder_battery.json")

    B_TIERS = (
        ("tier_M", "M mechanical", "per 100 pills"),
        ("tier_D", "D wrong phase", "per 100 dual-colour H locks"),
        ("tier_D2", "D2 hard burial", "per 100 placements &mdash; NOT QUOTABLE"),
        ("tier_F2", "F2 last-access seal", "per 100 endgame placements"),
        ("tier_O", "O evaporated", "per 100 placements"),
    )
    B_EVIDENCE = {
        "adjudicated": ("adjudicated", "var(--tier-fitted)"),
        "controlled": ("controlled", "var(--tier-low)"),
        "bracketed": ("bracketed", "var(--tier-uninf)"),
        "not quotable": ("count only, not a rate", "#d03b3b"),
    }

    def b_cell(d):
        if not d or d.get("per100") is None:
            return "<td class='n'>&mdash;</td>"
        label, colour = B_EVIDENCE[d["evidence"]]
        fp = d.get("fp_estimate")
        extra = f"<br><span class='n'>FP est {fp:.0f}%</span>" if fp is not None else ""
        # A tier the cache marks unquotable carries the marker HERE, next to its own
        # figure -- struck through so the number cannot be lifted out of the table.
        unq = d.get("quotable") is False
        val = (f"<b style='opacity:.55;text-decoration:line-through'>{d['per100']:.2f}</b>"
               if unq else f"<b>{d['per100']:.2f}</b>")
        warn = ("<br><span style='color:#d03b3b;font-weight:700'>NOT QUOTABLE</span>"
                if unq else "")
        return (f"<td class='num'>{val}<br>"
                f"<span class='n'>{d.get('flagged', d.get('any', 0))} of {d['n']}</span>"
                f"{extra}{warn}<br><span style='color:{colour}'>{label}</span></td>")

    def b_ai_cell(key):
        ai = BATTERY.get("ai")
        if not ai:
            return "<td class='n'>&mdash;</td>"
        n = ai["corpus"]["n_placements"]
        match key:
            case "tier_D2":
                return "<td class='n'>not run<br>(human-corpus tier)</td>"
            case "tier_F2":
                r = ai["row3_selfseal"]["route_gated"]
                games = ai["corpus"]["n_games"]
                return (f"<td class='num'><b>{r['seals'] / games:.2f}</b>/game<br>"
                        f"<span class='n'>{r['seals']} seals, {games} games<br>"
                        f"reopened {100 * r['reopens'] / r['seals']:.0f}%</span><br>"
                        f"<span style='color:var(--tier-low)'>controlled</span></td>")
            case "tier_O":
                t = ai["row4_tier_o"]["topdecile"]
                return (f"<td class='num'><b>{t['per_100_placements']:.2f}</b><br>"
                        f"<span class='n'>{t['n_evaporated']} of {n}</span><br>"
                        f"<span style='color:var(--tier-low)'>controlled</span></td>")
            case _:
                return ("<td class='n'>not computable<br>"
                        "(no rotation sequence<br>on the AI side)</td>")

    b_rows = []
    for player in ("struktured", "dr. lulu"):
        d = BATTERY["players"][player]
        b_rows.append(f"<tr><td class='handle'>{player}</td>"
                    + "".join(b_cell(d.get(k)) for k, _t, _u in B_TIERS) + "</tr>")
    b_rows.append("<tr><td class='handle'>AI champion<br><span class='n'>solo, n=250</span></td>"
                + "".join(b_ai_cell(k) for k, _t, _u in B_TIERS) + "</tr>")

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><div class='scroll'><table style='min-width:1000px'><thead><tr>"
        + "<th>player</th>"
        + "".join(f"<th>{t}<br><span class='n'>{u}</span></th>" for _k, t, u in B_TIERS)
        + "</tr></thead><tbody>" + "".join(b_rows) + "</tbody><caption>"
        + "Every cell carries its own n, because the denominators are deliberately "
        + "different: tier D only sees dual-colour horizontal locks, tier F2 only the "
        + "endgame (virus count &le; 6, the same threshold the AI-side seal probe uses). "
        + "<b>FP est</b> is the tier's own false-positive estimate &mdash; the share of "
        + "flagged burials whose virus was later dug back out, i.e. survivable after all. "
        + "<b style='color:#d03b3b'>Tier D2 is NOT QUOTABLE as a blunder rate</b>: at an FP "
        + "estimate of 77.5% (struktured) and 92.1% (dr. lulu) it counts a state players "
        + "routinely recover from. A matched-reopen gate ported from F2 and a last-straw "
        + "rule were both measured and neither improves precision &mdash; see "
        + "<code>blunder_tier_d2.py</code>'s TIGHTENING ATTEMPTED block. Quote F2 for "
        + "sealing. The AI row is solo play and does not face volleys; the human rows do."
        + "</caption></table></div></div>"
    )
    return (BATTERY, path_battery)


@app.cell(hide_code=True)
def _(BATTERY, mo):
    def m4_pct(d, k):
        return "&mdash;" if d.get(k) is None else f"{d[k]:.1f}%"

    b_m4 = {p: BATTERY["players"][p]["metric4"] for p in BATTERY["players"]}
    b_ai = BATTERY.get("ai", {}).get("row2_cascade")
    b_lines = [
        f"| {p} | {d['frame_cascade']} of {d['frame_events']} = "
        f"**{m4_pct(d, 'frame_cascade_pct')}** | {d['engine_cascade']} of {d['engine_clears']} = "
        f"**{m4_pct(d, 'engine_cascade_pct')}** |"
        for p, d in b_m4.items()
    ]
    if b_ai:
        b_lines.append(f"| AI champion (solo) | &mdash; | {b_ai['n_cascade']} of "
                     f"{b_ai['n_clear_events']} = **{b_ai['cascade_pct']:.1f}%** |")

    mo.md(
        "### Metric 4 — cascade share of clear events\n\n"
        "The fourth metric of the owner's battery, and the one place two instruments "
        "**disagree and neither is promoted to the answer**. The frame instrument watches "
        "occupied-cell count in the quiet window between a lock and the next spawn and calls "
        "a clear a cascade when a second drop follows within 96 frames (6 rows at the "
        "measured 16 frames/row settle gravity). The engine instrument asks whether the "
        "cascade fixpoint removes more cells than the first step.\n\n"
        "| player | frame instrument | engine instrument |\n|---|---|---|\n"
        + "\n".join(b_lines)
        + "\n\nThe frame number is a **lower bound** — it cannot separate two removals "
        "landing within a few frames of each other under blink noise. The engine number is "
        "biased the other way: `cascade_x`'s own docstring says its pass-2+ compact gravity "
        "over-estimates chaining, because a linked half whose partner is supported falls "
        "there and does not fall in the real game. Adjudicating between them needs a "
        "frame-accurate ROM-side trace of `comboCounter`, not a vision read of a capture. "
        "Until then the honest statement is the bracket, not a point."
    )
    return


@app.cell(hide_code=True)
def _(
    EVAL47,
    STYLES,
    mo,
    os,
    path_battery,
    path_bidwell,
    path_dss,
    path_jarsdad,
    path_lulu,
    path_rig_lulu,
    path_rig_v1,
    path_rig_v11,
    path_roburrito,
    path_shadowlat,
    path_strukt_pooled,
    path_strukt_send,
):
    def rel(path):
        return os.path.relpath(path, os.path.dirname(EVAL47))

    PROVENANCE = [
        ("dr. lulu pressure fit", rel(path_lulu)),
        ("struktured pooled fit", rel(path_strukt_pooled)),
        ("struktured sending fit", rel(path_strukt_send)),
        ("bidwell sending fit", rel(path_bidwell)),
        ("jarsdad sending fit", rel(path_jarsdad)),
        ("roburrito sending fit", rel(path_roburrito)),
        ("davesmithsays sending fit", rel(path_dss)),
        ("dies-ahead: dr. lulu rig (POOLED)", rel(path_rig_lulu)),
        ("dies-ahead: struktured bursty v1.1 (SENDING)", rel(path_rig_v11)),
        ("dies-ahead: struktured bursty v1 (POOLED)", rel(path_rig_v1)),
        ("rig driver log (dr. lulu, step 4/4)", "eval47/tmp/dr_lulu_20260808_refit.log"),
        ("AI search latency (cached pilot summary)", rel(path_shadowlat)),
        ("AI search latency: gated analyzer", "dr-mario-prestart-wt/experiments/prestart/shadowlat_analyze.py"),
        ("AI search latency: cache generator", "eval47/cache_shadowlat.py"),
        ("latency: struktured per-pill events", "eval47/results/latency_events/film_20260804/m{1,2,3,4}.csv"),
        ("latency: dr. lulu per-pill events", "eval47/results/latency_events/film_20260808/p1_m3.csv"),
        ("P1 tracker (produced p1_m3.csv)", "eval47/film_20260808/tracker_p1.py"),
        ("P1 crop-geometry check", "eval47/film_20260808/verify_p1_crop.py"),
        ("confidence rule + per-player table", "eval47/STYLE_ENSEMBLE_V1.md §5-7"),
        ("struktured metric battery", "player_styles/FILM_REVIEW_20260804_SCORECARD.md"),
        ("blunder battery cache", rel(path_battery)),
        ("blunder battery: exporter (runs every tier gate)", "eval47/blunder_battery_export.py"),
        ("blunder tier M: rotation corrections", "eval47/blunder_tiers.py"),
        ("blunder tier D: wrong colour phase", "eval47/blunder_tier_d.py"),
        ("blunder tier D2: hard burial", "eval47/blunder_tier_d2.py"),
        ("blunder tier F2: last-access seal", "eval47/blunder_tier_f2.py"),
        ("blunder tier O: evaporated opportunity", "eval47/blunder_tier_o.py"),
        ("blunder metric 4: cascade share", "eval47/battery4_metric4.py"),
        ("blunder shared board + virus map", "eval47/blunder_boards.py"),
        ("blunder AI rows (champion, n=250 solo)", "eval47/blunder_ai_rows.py"),
        ("dossiers", f"{os.path.relpath(STYLES, os.path.dirname(os.path.dirname(EVAL47)))}/*.md"),
    ]

    mo.md(
        "## Provenance\n\n"
        "| artifact | path |\n|---|---|\n"
        + "\n".join(f"| {label} | `{path}` |" for label, path in PROVENANCE)
        + "\n\n"
        "`struktured_20260804_pooled_fit.json` is the cached output of "
        "`bursty_model.fit_struktured_20260804()`. That call decodes 1,497 film-review "
        "frames, so it is run once out-of-band by `eval47/repro_struktured_fit.py` against "
        "the project's pinned venv rather than inside a notebook cell — this box carries live "
        "jobs and the notebook is deliberately I/O-light. To regenerate:\n\n"
        "```\n"
        "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python \\\n"
        "    experiments/eval47/repro_struktured_fit.py\n"
        "```\n\n"
        "The run that produced the cached file reproduced the published pooled fit exactly: "
        "n_volleys=61, n_clears=188, volley_size_mean=2.541, gap=22.70 s, P(4-6)=32.1%, "
        "P(7-10)=74.1%."
    )
    return


if __name__ == "__main__":
    app.run()
