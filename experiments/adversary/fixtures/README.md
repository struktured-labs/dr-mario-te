# Adversary fixture library

Minimal, deterministic reproducers for the structural failure modes named in
`../ADVERSARY_FINDINGS.md`. This is the regression suite every future core
(eval change, search change, driver change) should be replayed against
before being called an improvement -- **not** proof any of these happen on
real hardware; read `ADVERSARY_FINDINGS.md` §2 (silicon caveat) first.

## Fixture JSON schema

```jsonc
{
  "id": "unique_slug",
  "family": "buried_virus_stall | garbage_column_targeting | overwhelm_max_pressure",
  "mechanism": "plain-language explanation of WHY this fails",
  "found_by": "which hunt / how it was captured",
  "status": "CANDIDATE | FLUKE | STRUCTURAL | PENDING -- with the supporting detail inline",
  "silicon_status": "always: offline-sim-only caveat text",
  "seed": 12345,
  "schedule": null,                 // or a genome dict for Hunt-B fixtures:
                                     // {"fire": {"4-6": p, "7-10": p, "11-999": p},
                                     //  "size_weights": {"2": w, ..., "6": w},
                                     //  "target_mode": "near_spawn" | "spawn" | ...}
  "budget_halves": 53,              // null for schedule=null (solo-play) fixtures
  "max_pills": 300,
  "expected": {"result": "topout", "dies_ahead": true},   // subset-match against actual
  "fatal_board": { ... },           // OPTIONAL, documentation only -- NOT a runner input
  "provenance": "which script/report produced this fixture"
}
```

**Determinism:** every fixture replays bit-identically from `(seed, schedule,
budget_halves, max_pills, ws)` alone. `fatal_board`/`opening_board`/
`pills_prefix_first20` fields some fixtures carry are captured-at-discovery
documentation for humans reading the JSON -- `runner.py` never reads them.

**`expected` is a subset match**: the runner checks that every key in
`expected` matches the corresponding key in the actual outcome dict
(`result`, `pills`, `viruses_left`, `dies_ahead`, `garbage_injected`) --
extra keys in the actual outcome that aren't in `expected` are ignored, so a
fixture can assert as loosely (just `result`) or as tightly (exact
`viruses_left`) as its author wants.

## Current fixtures

| file | family | seed | schedule | status (see file for full detail) |
|---|---|---|---|---|
| `fx_hunt_a_buried_virus_stall_30999.json` | buried_virus_stall | 30999 | none (solo) | CANDIDATE, n=1, not transfer-filtered |
| `fx_hb_ga_near_spawn_a_seed5000000.json` | garbage_column_targeting | 5000000 | `ga_near_spawn_a` | FLUKE, 1/5 perturbation categories survived |
| `fx_hb_ga_near_spawn_b_seed5000001.json` | garbage_column_targeting | 5000001 | `ga_near_spawn_b` | FLUKE, 2/5 perturbation categories survived |
| `fx_hb_honest_shape_spawn_target_seed5000000.json` | garbage_column_targeting | 5000000 | `honest_shape_spawn_target` | FLUKE, 2/5 perturbation categories survived |
| `fx_hb_always_spawn_max_seed5000001.json` | overwhelm_max_pressure | 5000001 | `always_spawn_max` | **STRUCTURAL, 5/5 -- the one confirmed exploit** |

Run `python runner.py` (no args) to see every fixture's current pass/fail
against the shipped champion (`ws=20`) -- all 5 currently PASS (reproduce
their documented failure) at `ws=20`.

## `runner.py` usage

```
python runner.py                       # every fixture, ws=20 (shipped strand20 champion)
python runner.py --ws 0                # same fixtures, ws=0 (pre-#47 predecessor config)
python runner.py --fixture fx_foo.json --fixture fx_bar.json --ws 20
python runner.py --json                # machine-readable summary to stdout, no pretty printing
```

Exit code 0 iff every replayed fixture's actual outcome matches its
`expected` block; 1 otherwise. CI-usable as-is.

**"ANY candidate config" scope note:** this program's decide path
(`eval47/reach_root.py::choose_base32`) exposes exactly one A/B-able knob,
`ws` (the `g_stranded` root-only dose -- `ws=20` shipped, `ws=0` pre-#47).
`--ws` is that knob. A genuinely different leaf/eval variant (not just a
`ws` dose) is NOT something this runner can replay against without new code
-- see `ADVERSARY_FINDINGS.md` §3 for the proposals that would need that.

### A finding this runner surfaced on its own: `ws=0` vs `ws=20` on 2 of the 5 fixtures

Running `--ws 0` against the same 5 fixtures (a cheap, already-available A/B
this library makes trivial) found that **`fx_hunt_a_buried_virus_stall_30999`
and `fx_hb_honest_shape_spawn_target_seed5000000` both CLEAR under `ws=0`**
where they fail under the shipped `ws=20` champion -- i.e. on these two
specific seeds, the pre-#47 predecessor decide path does NOT hit the failure
the strand20 champion hits. The other three fixtures (`ga_near_spawn_a`,
`ga_near_spawn_b`, `always_spawn_max`) reproduce their failure under BOTH
configs. **This is n=1 per fixture, not a holdout claim** -- but it is
exactly the "long-standing weakness vs. strand20-introduced regression"
question `TRANSFER_FILTER.md` §2.2 planned its own predecessor A/B to
answer, and it points the same way for both of the ws=20-only fixtures:
worth a real paired predecessor A/B (the same seed/schedule pool, both
configs, proper n and CI) before concluding g_stranded at ws=20 is
responsible -- named here as a candidate observation, not asserted as a
finding.
