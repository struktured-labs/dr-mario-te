# Hetzner experiment node — provisioning notes

> ⚠ The node's IP and SSH key filename are redacted here (`<NODE_IP>`,
> `<KEYFILE>`). This repo is public and the box accepts root SSH; a rebuilt
> node gets a new IP anyway, so the concrete values add nothing to the
> rebuild procedure this file exists to document.

Everything needed to rebuild this box from a bare Ubuntu image. Written so the
node is disposable: if it is ever cancelled and later re-created, this file is
the only thing required to bring it back.

**Box**: Hetzner CCX23, `<NODE_IP>`, Ubuntu 24.04, 4 vCPU (**2 physical
cores + SMT**, AMD EPYC-Milan), 16 GB RAM, ~86 GB free.
**Access**: `ssh -i ~/.ssh/<KEYFILE> root@<NODE_IP>`
**Hands off**: `/root/rbm-mccfr` and `/root/rbm_mccfr` are an unrelated older
project. Leave them alone.

## 1. System packages

```bash
apt-get update
apt-get install -y python3-venv python3-pip rsync
```

## 2. Python environment — versions are PINNED ON PURPOSE

A node that computes *slightly* different answers is worse than no node, and
numba/llvmlite are the realistic divergence risk. Match local exactly:

```bash
python3 -m venv /root/drm/venv
/root/drm/venv/bin/pip install --upgrade pip setuptools wheel
/root/drm/venv/bin/pip install "numpy==2.4.6" "numba==0.66.0" "llvmlite==0.48.0" scipy
```

Resulting versions (verified identical to the local project interpreter at
`/home/struktured/projects/dr_mario_rl/tmp/venv`):

| package  | local    | remote   |
|----------|----------|----------|
| python   | 3.12.11  | 3.12.3   |
| numpy    | 2.4.6    | 2.4.6    |
| numba    | 0.66.0   | 0.66.0   |
| llvmlite | 0.48.0   | 0.48.0   |
| scipy    | 1.18.0   | 1.18.0   |

The Python patch level differs (3.12.11 vs 3.12.3, whatever Ubuntu ships) and
does **not** affect results — the hot path is numba-compiled and the gate below
proves bit-equality empirically rather than by argument.

## 3. Source tree — mirror the ABSOLUTE paths

The experiment scripts hardcode absolute paths (`ROOT = "/home/struktured/
projects/dr_mario_rl"` etc.). Rather than patch them — which would fork the
code and invite drift — replicate the same paths on the remote. The import
manifest is the `sys.path` header of `experiments/tuck_v3/union_mirror.py`.

```bash
ssh … 'mkdir -p /home/struktured/projects/dr_mario_rl/tmp \
                /home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim \
                /home/struktured/projects/dr-mario-qa-wt/fpga/copro'

EX="--exclude=__pycache__/ --exclude=*.pyc --exclude=.git/ --exclude=setenv.sh \
    --exclude=*.mp4 --exclude=*.png --exclude=*.jpg --exclude=id_* --exclude=*.pem"

for d in combo_term endgame tuck pillrng; do
  rsync -a $EX  /home/struktured/projects/dr_mario_rl/tmp/$d/ \
    root@HOST:/home/struktured/projects/dr_mario_rl/tmp/$d/
done
rsync -a $EX /home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src/ \
  root@HOST:/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src/
rsync -a $EX /home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation/ \
  root@HOST:/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation/
rsync -a $EX --exclude=eval47/tmp/ --exclude=pocket_shots/ \
  /home/struktured/projects/dr-mario-qa-wt/experiments/ \
  root@HOST:/home/struktured/projects/dr-mario-qa-wt/experiments/
```

`eval47/tmp/` is excluded — it is 3.6 GB of local run output and nothing
imports it. Total transferred: ~103 MB. `setenv.sh` and key material are
excluded by pattern; **no secrets go to this box** (the SSH key is sufficient,
the Hetzner API token is not needed and must never be copied here).

The census path's actual third-party dependency set is small — `numpy`,
`numba`, `llvmlite`, `scipy` — confirmed by tracing `sys.modules` after
importing the real chain, not by reading requirements files.

## 4. Validation gate — RUN THIS BEFORE TRUSTING ANY OUTPUT

```bash
# remote
/root/drm/venv/bin/python …/hetzner/exactness_gate.py --out …/gate_remote.json
# local
…/tmp/venv/bin/python …/hetzner/exactness_gate.py --out …/gate_local.json
# then compare the `digest` fields — one string comparison
```

`exactness_gate.py` hashes the **complete** per-seed record (result, pills,
viruses_left, and the entire move trace, plus the fatal board when there is
one). A gate that compared only clear-rate or pill counts could pass while the
two nodes made different moves.

**Result 2026-08-06: PASS.** Both nodes produced
`13eec4a42bd0656ffd04c7d9767da65b715e6a9f6db6d5018e4819f16a77aa27`
over 20 seeds spanning both halves of the seed space.

Known gap: all 20 gate seeds cleared, so the *failure* path is unexercised by
the gate itself. It is closed separately by re-running census-discovered
failure seeds on the local box and comparing.

## 5. Running long jobs — use systemd, NOT nohup

⚠ **`nohup setsid … & disown` over SSH is not reliable here**, and it fails in
the worst way: it *looks* dead. When an SSH session was torn down, `pgrep -c`
reported 0 matching processes and the output file did not exist — but the
process tree was alive and orphaned to init. Relaunching on that false reading
put two censuses on one output file: 400 rows covering 200 seeds, every seed
duplicated, with both processes reporting healthy progress.

Use a transient systemd unit, which is inspectable and genuinely
session-independent:

```bash
systemd-run --unit=drm-census --description="…" \
  --property=Restart=on-failure --property=RestartSec=20 \
  /bin/bash …/hetzner/run_census.sh

systemctl is-active drm-census      # status
systemctl stop drm-census           # stop
journalctl -u drm-census            # unit-level log
```

Two independent lessons, both learned the hard way:
- **Verify with `ps`, not `pgrep -c`** — `pgrep -c` returned 0 for a process
  tree that `ps -eo pid,ppid,cmd` clearly showed running.
- **A resumable appender must be single-writer.** `census.py` now takes an
  exclusive `flock` on its output directory and exits rather than share it.
  Verified by attempting a real second writer (it exited 1; the first was
  unaffected) — the defect was simulated, not just the guard asserted.

## 6. Files

| file | purpose |
|------|---------|
| `exactness_gate.py` | bit-exactness gate; run on both nodes, compare `digest` AND `code` |
| `code_manifest.py` | standalone skew detector (importable + CLI); `from_imports()` catches wrong-worktree resolution |
| `census.py` | seed census; resumable, flock-guarded, fsync per chunk, stamps a manifest |
| `run_census.sh` | keepalive wrapper (census.py is resumable, so retry == recovery) |
| `dedupe_census.py` | repairs a double-written JSONL; refuses to collapse disagreeing rows |
| `verify_fixture.py` | proves stored fatal boards reload and replay — backs the "fixture" claim |
| `bench_workers.py` | measures the worker-count knee instead of assuming it |
| `kernel_gate.py` | whole-game gate for any proposed faster champion (traces, not positions) |
| `fit_bursty_v11.py` | fits bursty v1.1 where the footage lives; pickles it for compute nodes |
| `ws_dose_bursty.py` | failure-rate-vs-`ws` curve under bursty v1.1, driving `pressure_rig.run_arm` |
| `analyze_ws.py`, `ws_sweep.py` | drip-era dose sweep, superseded by the bursty rig; kept as a contrast arm |
| `HETZNER_NODE.md` | the keep-or-cancel verdict |

### systemd units

| unit | job |
|------|-----|
| `drm-census` | full-space census (`run_census.sh`) |
| `drm-wsbursty` | ws dose curve under bursty v1.1 |

`systemctl is-active|stop <unit>`, `journalctl -u <unit>`. Job logs in `logs/`,
results in `results/` (both gitignored).

### Bursty pressure model — do NOT try to fit it here

The fit reads 1fps JPEG frames plus a `vision.py` calibrated against them, none
of which is synced (nor should be). Run `fit_bursty_v11.py` **locally**; it
writes `bursty_v1_1.pkl`, which `ws_dose_bursty.py` prefers over re-fitting.
It refuses to ship a model whose summary looks like the contaminated v1 pool
(61 volleys / 188 clears) instead of v1.1 (28 / 89). Verified identical on both
nodes: 28 volleys, 89 clears, gap 27.42 s, 28.2% / 62.5% — the published values.

## 7. Measured throughput

| workers | games/sec | note |
|---------|-----------|------|
| 1 | 0.257 | |
| 2 | 0.507 | ~linear — 2 real cores |
| 4 | 0.583 | +15% only — SMT, not more cores |

Use `--workers 4`; ~0.583 g/s ⇒ a full 65,536-seed census ≈ 31 h uncontended.
**Budget workers explicitly when sharing** — this is 2 physical cores, so three
tenants at "4 workers" each is 3x oversubscription and slows everyone.
