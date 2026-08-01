# Historical manifests — VALID records, superseded recipes

These manifests document carts that **genuinely shipped**. They are kept, not deleted.

They do **not** rebuild from HEAD's emitter, and that is correct, not a defect: the emitter
has legitimately moved on since they were recorded. Each one still reproduces **byte-exact
from the emitter commit it records** — verified 2026-08-01, all four:

| manifest | md5 | reproduces from `patch_cartridge_copro.py` at |
|---|---|---|
| `latch-control.json`    | `21349cb1455eda2a2b95a9f3297d0d03` | `155579bd` |
| `latch-converged.json`  | `e8578322447f3803f46077f95942def6` | `155579bd` |
| `human-latchfix.json`   | `3558d6801b55e87f444febb01c8bc42e` | `155579bd` |
| `_dwell_on.json`        | `8b1aaf0cc4faa87355c91d47aec6e8f2` | `45f5cfb8` |

(`_dwell_on` was verified against `362e5b66`; that commit and the `45f5cfb8` the manifest
records carry the **same** emitter blob `447404b2`, so either works. The table names the
recorded one, which is also what `romgen list` prints.)

To rebuild one:

    git show <commit>:patch_cartridge_copro.py > patch_cartridge_copro.py   # in a scratch tree!
    python3 tools/romgen.py rebuild roms/manifests/historical/<tag>.json

★ Do that in a worktree or restore the file afterwards. Overwriting the live emitter (or the
base ROM) in place and forgetting to put it back has already cost one multi-day search — see
the `dr-mario-base-rom-collision` note. Any sweep script must restore in a `finally`.

## Why they were moved here

`tools/romgen.py rebuild` reported MISMATCH for these against HEAD, which reads as "we lost
the ability to build a shipped ROM" — a false alarm that costs someone an investigation every
time they run the full sweep. Deleting them would have been worse: it erases the record of
what actually shipped. Archiving with the reproducing commit named is the honest option, and
`romgen list` now shows them under a `historical/` heading so they are visible but not
mistaken for live recipes.

## Live successors

The current equivalents of these recipes, which **do** rebuild from HEAD:

- `latch-control` → `latch-control-v2`
- `latch-converged` → `latch-converged-v2`
- `human-latchfix` → `pocket-human-latchfix`
- `_dwell_on` → superseded by the DRNAVDWELL title-hang fix; `_dwell_off` still reproduces

Deliberately **no hashes here**: the live ones move whenever the shared path legitimately
changes — the published-column hardening at `9643b8b` moved all nine at once — and a hash
copied into prose goes stale silently. `tools/romgen.py list` is the live answer.
