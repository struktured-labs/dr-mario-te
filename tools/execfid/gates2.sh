#!/usr/bin/env bash
# execfid gates, second pass: the gravity-fidelity new arms at 6000 frames x 3 seeds, and the LGPRESTART defect gate with
# counts summed over 4 seeds (the per-seed counts on D are too small to judge alone).
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
echo; echo "## tests/test_gravity_fidelity.py, the new arms (+ D_abort control), seeds 5/11/23, 6000 frames"
for s in 5 11 23; do echo "seed $s"
  nice -n 19 $GPY tests/test_gravity_fidelity.py --frames 6000 --seed $s --arm couch_fair_D_abort --arm couch_fair_D_lgp \
     --arm couch_fair_A_lgp --arm couch_fair_A_row --arm couch_fair_D_lgp_row --arm couch_fair_A_lgp_row 2>&1 | tail -7 | cut -c1-230
done
echo; echo "## tests/test_lgprestart.py (defect gate), counts summed over seeds 5/11/23/77, 6000 frames each"
nice -n 19 $GPY tests/test_lgprestart.py --frames 6000 --seeds 5,11,23,77 2>&1 | tail -7 | cut -c1-330
