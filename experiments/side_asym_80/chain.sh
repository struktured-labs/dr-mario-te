#!/bin/bash
# Sequential FOREGROUND children of one shell. No pgrep, no pidfile, no pattern of
# any kind -- the shell's own exit code does the waiting, which is the one mechanism
# that cannot match the wrong process (harness-pgrep-self-match, "eliminate the
# class, do not harden the predicate").
set -u
cd "$(dirname "$0")"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
W=12

echo "CHAIN START $(date -Is)"

# Arms ordered by INFORMATIVENESS so a truncated window still answers the question
# (measurement-rules rule 23). The mirror arm goes FIRST: it is the one that can
# find a harness-level cause, and it is the one whose null is hardest to fake.
$PY run_side_asym.py --arm mirror --seed0 53000 --n 1500 --workers $W \
    --out out/mirror_n1500.jsonl                                        || exit 1
echo "CHAIN mirror done $(date -Is)"

$PY run_side_asym.py --arm adv --seed0 56000 --n 1500 --workers $W \
    --out out/adv_n1500.jsonl                                           || exit 1
echo "CHAIN adv done $(date -Is)"

# Gates last, on subsets of the SAME seeds so the counts are directly comparable.
$PY run_side_asym.py --arm mirror --seed0 53000 --n 200 --workers $W \
    --mutant swap_scoring --out out/mirror_mut_swap.jsonl               || exit 1
$PY run_side_asym.py --arm adv --seed0 56000 --n 200 --workers $W \
    --mutant swap_scoring --out out/adv_mut_swap.jsonl                  || exit 1
$PY run_side_asym.py --arm mirror --seed0 53000 --n 100 --workers $W \
    --mutant same_board --out out/mirror_mut_sameboard.jsonl            || exit 1

echo "CHAIN ALL DONE $(date -Is)"
