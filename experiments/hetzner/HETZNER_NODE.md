# Is the Hetzner box worth keeping?

**Short answer: the capability is worth keeping; the always-on billing is not.
Keep the box only if you commit to keeping it loaded 24/7. Otherwise destroy it
and rebuild it per job from `PROVISIONING.md` — you keep 100% of the capability
and pay for hours instead of months.**

That is a real recommendation, not a hedge: the box demonstrably works and
demonstrably earned its keep tonight. But its value comes entirely from being
*busy*, and it has been idle for 110 days.

---

## What it actually is (measured, not from the spec sheet)

The plan says "4 dedicated vCPU". `lscpu` says **2 physical cores + SMT**, and
the throughput curve agrees:

| workers | games/sec | scaling |
|---------|-----------|---------|
| 1 | 0.257 | — |
| 2 | 0.507 | 1.97x — near-linear, two real cores |
| 4 | 0.583 | 1.15x — SMT, not more cores |

So you are buying roughly **2.3 cores of useful throughput**, not 4. Anyone
sizing a job off "4 cores" will be ~40% optimistic. Use `--workers 4` anyway
(0.583 > 0.507), but plan with 0.583 g/s.

**Sustained rate: 0.583 games/sec** = 2,099/hour = ~50,000/day = **~1.5M
champion games per month**. Concretely: a full 65,536-seed census of the entire
16-bit seed space takes ~31 hours. The 32,768-seed half it is grinding now
takes ~15.6 h.

## Does it compute the right answers?

**Yes — proven, not assumed.** `exactness_gate.py` hashes the *complete*
per-seed record (result, pills, viruses_left, every action of the move trace,
and the fatal board) and both nodes produce identical digests:

| gate | digest | local | remote |
|------|--------|-------|--------|
| 20 seeds, clear path | `13eec4a4…` | ✔ | ✔ |
| failure path (a topout + a stall) | `219e2e15…` | ✔ | ✔ |
| code manifest (10 source files) | `833ca707…` | ✔ | ✔ |

Intel i9-12900K and AMD EPYC-Milan agree bit-for-bit. Separately, 200 seeds
were computed twice by two concurrent processes under full CPU contention and
all 200 rows were byte-identical.

## Its role: pure fast-sim, which is what makes rebuild-per-job realistic

Most of this project's compute does not need cycle-accurate simulation. Seed
censuses, dose sweeps, adversarial search and large-n replications all run in
the numba fast sim; only a handful of final survivors need the Verilator co-sim,
and that stays local. So this node needs **no Verilator, no Quartus, no RTL
toolchain** — `apt install python3-venv`, a pinned venv, one rsync, and the
gate. That is what turns "rebuild per job" from a theoretical policy into a
few-minute scripted one (`PROVISIONING.md`).

(A portable co-sim binary *does* run here — cosim-farm built `farm_vsim` with
`-O2` and deliberately without `-march=native`, and it ran unmodified on a box
with no Verilator installed. Worth knowing; it doesn't change the node's role.)

## What it delivered in its first few hours

1. **The definitive clean-stream census** — now the FULL 16-bit space (all
   65,536 seeds), after the local clean census was retired in favour of this
   node. Resumable, checkpointed, auto-restarting, provenance-stamped, keeping
   the fatal board and full replay trace for every failure.
2. **A finding that corrects a project constant.** Pooling this node's census
   rows with the local agent's gives **~1,474 clean games with ZERO failures**
   → clean-stream failure rate **< 0.20%** (rule of three, 95%). The harness
   calibrates against `REACH_ROOT_CLEAN.md`'s "1/120 bad-ends" ≈ 0.8%, which
   would have predicted ~12 failures; P(zero) at that rate ≈ 7e-6. **The
   champion is far more reliable on the clean stream than the number we plan
   with.** That reframes the whole adversary program: clean-stream failure
   hunting is a rare-event search, not a fixture farm.
3. **The failures it did find share a signature.** Both (seeds 33269, 33754)
   reach **exactly 1 virus remaining** and then top out or stall at 300 pills.
   The champion's residual failure mode is the *last virus*, not the opening or
   midgame.
4. **It caught a real bug — code skew.** The gate flagged one seed whose hash
   differed across nodes while `result`, `pills`, `viruses_left` and `n_moves`
   all matched. Cause: the local agent improved `adversary_harness.py` 12
   minutes after the tree was synced, so the two nodes ran different code. The
   move traces were always identical — the champion never disagreed with
   itself — but a summary-statistics gate would have reported perfect
   agreement. The gate now hashes the source files too.

That fourth item is a **separate argument for keeping the box, independent of
games/hour**, and it deserves to be weighed on its own. The node is an
INDEPENDENT SECOND IMPLEMENTATION PATH. Different CPU vendor, different Python
build, a physically separate copy of the tree — and running the same work twice
across that boundary surfaced, within hours, a defect that a single-machine
setup would have carried silently and indefinitely: one field, one rare seed,
every summary statistic in agreement. Nothing about throughput would have found
it. The same class of drift affects any long experiment against an
actively-edited tree, including purely local ones, which is why the detector
(`code_manifest.py`) is now a standalone utility rather than a gate-only trick.

The habit generalises. The same "prove it on whole trajectories, not summary
statistics" discipline was then applied to a proposed faster champion kernel:
it passed on all 8 whole games (790 moves, byte-identical) but delivered only
**1.09x**, because the cost lives in the inner depth search, not the root loop
that was fused. That saved another agent from re-planning a program around a
speedup that isn't there. Cheap to check, expensive to assume.

## The honest case against

- **Only ~2.3 useful cores.** For a project whose bottleneck is games/sec, this
  is a small increment.
- **0.583 g/s is modest.** Experiments that need to resolve a few-percent
  effect want thousands of games per arm; a 4-arm paired sweep at n=400 is
  ~1.9 h here, and n=4,000 would be most of a day.
- **The local box has 24 threads.** On raw capability the Hetzner box is a
  rounding error next to it.
- **It does not absorb concurrent tenants.** Measured: with a census (4
  workers), a dose sweep (2) and a co-sim process sharing 2 physical cores, the
  sweep crawled at **0.04 games/sec**. Deprioritising the census with `nice 10`
  took the sweep to **0.143 g/s (3.5x)** without stalling the census — but the
  lesson is that the total is fixed and small. **Schedule jobs onto this box
  serially; do not treat it as a shared pool.** Three agents wanted it
  simultaneously on night one, which is a demand signal but also a warning.

## The rebuttal, which is the actual point

The local box is **saturated**, not idle. Measured during this work: load
average **78** on 24 threads, ~3x oversubscribed by the agent fleet plus a live
silicon A/B. A `nice -19` worker there got **0.038 games/sec** — **15x slower
than a single Hetzner worker**, and with unpredictable latency.

So the comparison is not "4 cores vs 24 cores". It is **"0.583 g/s you can
count on, overnight, unattended" vs "a queue"**. Long unattended grinds — a
15.6 h census — are exactly what the local box cannot hold and what this box
does well.

## Recommendation

**Do not keep paying a monthly idle fee for it.** At the stated $100+/month,
the box spent 110 days idle. Its entire value is in utilisation.

Two defensible options:

1. **Keep it, and keep it loaded.** Only justified if there is a standing queue
   of overnight jobs. There currently is (the full-space census, dose sweeps,
   and large-n replications of the project's chronic n=60 results). At ~1.5M
   games/month it would deliver roughly **23 full 65,536-seed censuses per
   month**, or a 4-arm paired experiment at n=10,000 every ~2.4 days. Three
   agents wanted it simultaneously tonight. If that demand is real and
   recurring, this is fine value.
2. **Better: destroy it and rebuild per job.** Hetzner bills hourly. A ~31 h
   full-space census costs a couple of dollars of compute rather than a month
   of rent, and because the node needs **no RTL toolchain** — just python,
   numpy, numba and one rsync — `PROVISIONING.md` rebuilds it from a bare image
   in minutes. This keeps every capability demonstrated here, including the
   independent-second-path property, and removes the idle cost, which is the
   only thing actually wrong with the box.

**I recommend option 2**, with option 1 as the fallback if per-job setup
friction proves annoying in practice. The deciding fact is that this node's
value is bursty and scheduled, and the cost model should match.

Note the two arguments are independent and both survive under option 2: the
throughput argument (uncontended overnight games/hour) and the
**independent-second-implementation-path** argument (a physically separate copy
of the tree on a different CPU vendor, which is what caught the code-skew
defect). A rebuilt-per-job node retains both. An idle always-on node delivers
neither.

⚠ Verify the actual line item against the invoice before acting — the "$100+"
figure is as stated, and a CCX23 lists well below that, so there may be extra
volumes, backups, or a second resource on the account. I did not touch the
Hetzner API token and did not need it; the SSH key was sufficient.

## If you keep it, do these

- Re-run `exactness_gate.py` **after every sync** and treat a code-manifest
  mismatch as invalidating results produced since the last match.
- Launch long jobs with `systemd-run --unit=…`, never `nohup`/`setsid` over SSH
  (see `PROVISIONING.md` §5 — the failure mode is a job that looks dead and
  isn't).
- Keep single-writer discipline on any appended results file (`census.py` takes
  an exclusive `flock`).
- Have every long job **stamp its own provenance at start**:
  `code_manifest.stamp(out_dir + "/manifest.json")`. A 31 h census outlives
  several edits to the tree it started from; without the stamp its rows cannot
  be tied to the code that produced them. This applies to LOCAL jobs too — two
  agents importing a module at different times have the same exposure.
- When sharing the box, agree a worker budget explicitly. It is 2 physical
  cores; three concurrent tenants at "4 workers" each is 3x oversubscription and
  everyone's numbers get slower, not just the newcomer's.
