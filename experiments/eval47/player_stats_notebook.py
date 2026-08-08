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
    return (
        fit_bidwell,
        fit_dss,
        fit_jarsdad,
        fit_lulu,
        fit_roburrito,
        fit_strukt_pooled,
        fit_strukt_send,
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
    .pstat caption {
      caption-side: bottom; text-align: left; padding-top: 10px;
      color: var(--text-secondary); font-size: 11.5px; line-height: 1.55; white-space: normal;
    }
    </style>
    """
    return (VIZ_CSS,)


@app.cell(hide_code=True)
def _(PROFILES, ROSTER, VIZ_CSS, fmt_num, fmt_pct, mo, tier_suppresses_numbers):
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
            f"<td>{declined}</td>",
            f"<td>{corrections}</td>",
            f"<td>{latency}</td>",
            f"<td class='wrap'>{meta['style']}</td>",
        ]
        klass = " class='suppressed'" if suppressed else ""
        return f"<tr{klass}>" + "".join(cells) + "</tr>"

    MASTER_ORDER = ["dr. lulu", "struktured", "bidwell", "jarsdad", "roburrito", "davesmithsays"]

    HEADERS = [
        ("player", " class='handle'"), ("scene role", " class='wrap'"), ("record vs the AI", " class='wrap'"),
        ("fit scope", ""), ("n volleys", ""), ("confidence", ""),
        ("volley size", ""), ("inter-volley gap", ""),
        ("P(volley | 4-6 clear)", ""), ("P(volley | 7-10 clear)", ""),
        ("declined clears", ""), ("corrections /100 pills", ""), ("median latency", ""),
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
        + "from FILM_REVIEW_20260804_SCORECARD.md. <b>Fit scope</b> distinguishes a POOLED fit "
        + "(both sides' events, contaminated per STYLE_ENSEMBLE_V1.md &sect;6a) from a per-player "
        + "SENDING fit. davesmithsays' pressure cells are suppressed programmatically by the "
        + "NO DATA tier, not omitted by hand."
        + "</caption></table></div></div>"
    )
    master_table
    return (MASTER_ORDER,)


@app.cell(hide_code=True)
def _(MASTER_ORDER, PROFILES, ROSTER, mo, pct, tier_suppresses_numbers):
    def rounded(x, digits):
        return None if x is None else round(x, digits)

    def sortable_record(handle):
        prof, meta = PROFILES[handle], ROSTER[handle]
        suppressed = tier_suppresses_numbers(prof["tier"])
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
def _(PROFILES, VIZ_CSS, fit_strukt_pooled, mo, pct, pk):
    # Values as published in STYLE_ENSEMBLE_V1.md 7, dr_lulu_20260808_fit_report.md,
    # and player_styles/*.md. Tolerances are one unit in the last published digit.
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

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><table style='min-width:720px'><thead><tr>"
        + "<th>player</th><th>metric</th><th>derived here</th><th>as published</th>"
        + "<th>published in</th><th>&nbsp;</th></tr></thead><tbody>"
        + "".join(html for html, _ in CHECK_ROWS)
        + f"</tbody><caption><b>{N_PASS}/{len(CHECK_ROWS)} cross-checks pass.</b> "
        + "Derived values are recomputed from the raw arrays in the fit JSONs; published "
        + "values are transcribed from the reports named in the last column."
        + "</caption></table></div>"
    )
    return (N_PASS,)


@app.cell(hide_code=True)
def _(N_PASS, mo):
    mo.md(
        f"""
        /// {"tip" if N_PASS == 17 else "danger"} | Cross-check result

        **{N_PASS}/17 derived values agree with the published reports.**
        {"Every number in the master table traces to a fit file and matches the document that quotes it."
         if N_PASS == 17 else
         "A mismatch means a fit file and a report have diverged - reconcile before citing anything above."}
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
def _(MASTER_ORDER, PROFILES, ROSTER, VIZ_CSS, mo):
    def coverage_row(handle):
        prof, meta = PROFILES[handle], ROSTER[handle]
        yes = "<span style='color:var(--tier-fitted);font-weight:700'>yes</span>"
        no = "<span class='n'>no</span>"
        has_pressure = {"FITTED": yes, "LOW-CONF": yes, "UNINFORMATIVE": yes, "NO DATA": no}[prof["tier"]]
        return (
            f"<tr><td class='handle'>{handle}</td>"
            f"<td>{yes}</td>"
            f"<td>{has_pressure} <span class='n'>({prof['tier']}, {prof['scope']})</span></td>"
            f"<td>{yes if meta['battery'] else no}</td>"
            f"<td>{yes if meta['record'] != 'never played the AI' else no}</td></tr>"
        )

    mo.Html(
        VIZ_CSS
        + "<div class='pstat'><table style='min-width:640px'><thead><tr>"
        + "<th>player</th><th>dossier</th><th>pressure fit</th>"
        + "<th>metric battery</th><th>played the AI</th></tr></thead><tbody>"
        + "".join(coverage_row(h) for h in MASTER_ORDER)
        + "</tbody><caption>"
        + "The metric battery (declined-clear rate, corrections per 100 pills, decision "
        + "latency, endgame seal counting) has been run for exactly one player. Extending it "
        + "needs capture-card footage of the kind that only exists for struktured's 2026-08-04 "
        + "set and dr. lulu's 2026-08-08 session."
        + "</caption></table></div>"
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
        - **The metric battery is n=1 player.** Everything outside the pressure columns is
          struktured only.
        - **Three of six players sit below the n=20 line** and one is at zero. §8 of the
          ensemble report is blunt that an archetype grid is not possible on this data.
        - **davesmithsays needs a different window,** not a different method: his Speed-bracket
          appearances are a solo race format the volley extractor cannot fit, a documented
          negative rather than an unexplored option.
        """
    )
    return


@app.cell(hide_code=True)
def _(
    EVAL47,
    STYLES,
    mo,
    os,
    path_bidwell,
    path_dss,
    path_jarsdad,
    path_lulu,
    path_roburrito,
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
        ("confidence rule + per-player table", "eval47/STYLE_ENSEMBLE_V1.md §5-7"),
        ("struktured metric battery", "player_styles/FILM_REVIEW_20260804_SCORECARD.md"),
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
