# θ400 vs the striker: reconciling co-sim and fast-sim — VERDICT

**Question (task B).** θ400 dominates on co-sim firmware under BLIND bursty
([[dr-mario-theta400-dose-verdict]]: DA 1.5% tied with the champion floor, −11.0 pills,
clear 95.0%, the best dose). Against the timed striker on the fast-sim rig it showed
nothing (gauntlet item 4: θ400 108 v 105 DA, p≥0.18; θ150 looked better). Which is it?

**Decision rule, fixed in advance by the task:** if the fast sim reproduces the co-sim
ORDERING at the blind baseline, the striker null is a real *timed-pressure* limitation of
θ400. If it does not, the discrepancy is an *implementation gap* and the striker result
cannot be read as evidence about θ400.

**No new run was required.** Both gauntlet arms already carry a common `blind_bursty`
condition — same pressure model, same 240 seeds — so the baseline comparison was sitting in
`results/`.

## The blind-bursty baseline, all three arms, same model and seeds (n=240)

| arm | clear | topout | stall | **dies-ahead** | bad-end |
|---|---|---|---|---|---|
| champion_baseline | 185 | 38 | 17 | **32** | 55 |
| tuck_theta150 | 205 | 29 | 6 | **26** | 35 |
| tuck_theta400 | 202 | 30 | 8 | **25** | 38 |

Both tuck arms beat the champion. **θ400 and θ150 are indistinguishable.**

### Paired, per-seed, McNemar — the test that settles it

θ150 vs θ400, blind bursty, the same 240 seeds, dies-ahead:

> θ400-only deaths **22** · θ150-only deaths **23** · discordant **45** · **p = 1.0000**

A textbook null. **The fast sim does not reproduce co-sim's θ400 > θ150 ordering at the
blind baseline — it finds the two doses tied.**

## ⚠ A trap that nearly produced the opposite answer

The report's per-arm **"matched blind"** columns look like a blind baseline and are NOT
comparable across arms: each is volume-matched to *that arm's own* striker schedule.
Measured garbage per game in those controls — champion 43.3-45.1, θ150 31.3-32.0,
**θ400 35.3-39.4**. θ400's control delivers ~20% more garbage than θ150's, so reading those
columns side by side "shows" θ400 worse (41 v 26 dies-ahead summed) purely from volume.
The common `blind_bursty` condition is the only cross-arm-legitimate baseline, and it says
the opposite (tied). This is the matched-index rule biting exactly where it always bites.

## VERDICT: implementation gap — the striker null is NOT a θ400 limitation

By the pre-fixed rule, this is the implementation-gap branch. The fast-sim rig **never
reproduced θ400's advantage in the first place**, with no timing involved. A rig that shows
no effect at baseline has no power to test whether that effect survives timed pressure, so
the striker null is uninformative about θ400 rather than damning.

The gap has documented prior art and a named mechanism: the fast-sim tuck arms consume an
**ENUMERATED** tuck vocabulary ([[dr-mario-tuck-armD-enumerator-not-firmware]] — "a
perfect-vocabulary UPPER BOUND, never a ship signal"), while co-sim θ400 is the **firmware
scanner**, and the two are already known to differ measurably
([[dr-mario-fw-scanner-better-than-proof]], p=0.0002, blocker DOWNSTREAM).

**Consequences, stated plainly:**
1. The striker gauntlet must **not** be cited as evidence against θ400. It is silent on θ400.
2. It is equally **not** evidence *for* θ400. The θ400 case rests entirely on the co-sim /
   firmware measurement, unreplicated by any independent rig.
3. `[[dr-mario-theta400-dose-verdict]]`'s striker caveat should be **re-worded, not
   upgraded**: from "θ400 shows nothing vs the striker" to "the fast-sim rig cannot
   currently test θ400 — it does not reproduce the dose ordering at baseline."

## Does this gate a θ400 MiSTer core build today?

**The striker result does not block it.** But a separate, harder blocker is unchanged and
independent of everything above: **the cart has no tuck executor**
([[dr-mario-cart-no-tuck-executor]] — DRTUCK absent from the probe cart, so tuck descriptors
are INERT on silicon). θ lives in the copro firmware; the executor lives in the driver. A
θ400 core would compute a dose the cart cannot act on.

⇒ **Recommendation: do not trigger a θ400 core build on the strength of this
reconciliation.** It removes an objection; it does not supply a reason. The build becomes
meaningful only once a tuck executor exists on the cart — at which point θ400 should be
re-validated against a rig that can actually see the firmware's behaviour.

## Reproduce

    results/gauntlet/gauntlet_tuck_theta150_n240.jsonl        (condition blind_bursty)
    results/gauntlet_theta400/gauntlet_tuck_theta400_n240*.jsonl
    results/gauntlet/champion_baseline_n240_summary.json      (conditions.blind_bursty)

Paired McNemar over the 240 common seeds on `dies_ahead`, blind_bursty rows only.
