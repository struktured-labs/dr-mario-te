# hetzfarm-143 — c5 precision extension on the rented Hetzner node (INTERIM)

Ledger note: run started 2026-08-21 11:16 UTC on the rented CCX23 node
(grandfathered flat rate, $0 marginal). Purpose: standing PRECISION run of the
c5 home-regime cell (L20 + honest bursty v1.1) — n=500 (stretch 1000) to
narrow the 28% [16.2, 42.5] stage-1 failure-rate anchor for all future
survival-experiment power math.

## Registration

PREREG_C5_PRECISION_EXT.md committed at e60aad1 BEFORE any row; branch
`hetzfarm-143` off regime-141 d55c3d9. Even seed block 34000-35998 (fresh);
arm `c5ext_L20_bursty`; reading rule exact CP + game-clustered bootstrap;
pooling with local c5 rows gated on the cross-host bit-exactness gate
(seeds 33000/33002, canonical rows minus {wall_secs, host}).

## Instrument

* farm_vsim `3e6569f1b7cd254bac9029ea9c9d8d0f` — SAME BYTES as the local
  binary, shipped (portable: -O2, no -march=native), md5-verified on remote.
* firmware s20b `e970e9ab0208cdbce1d39ed33e2f51ee`, md5-verified on remote,
  confirmed per row by RTL handshake.
* remote venv pinned: numpy 2.4.6, numba 0.66.0, llvmlite 0.48.0, scipy
  1.18.0, + pillow 12.3.0 (bursty-fit footage reader; pinned to local).
* absolute source paths mirrored on the remote (PROVISIONING.md pattern);
  bursty v1.1 model refits remotely from the synced footage: n_volleys=28,
  identical to local.

## Gate sheet (remote host)

(to be filled from /root/drm/c5ext/out/unit.log — last line quoted verbatim)

## Launch

systemd unit `drm-c5precision`, 2 workers, per-seed atomic rows at
/root/drm/c5ext/out/farm.jsonl (resumable), chained analysis to
c5ext_summary.{json,txt}. Progress readable over ssh:
`tail /root/drm/c5ext/out/progress.log`.

## Rate / ETA

(to be filled after the first banked rows)
