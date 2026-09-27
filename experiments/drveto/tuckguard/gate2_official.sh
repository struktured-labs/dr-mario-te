#!/bin/bash
# Gate 2 via the TESTED official runner. probe6 runs at ~12 fps (its own deadline formula is
# maxf/12+300), so 18k frames is ~25 min per arm -- four arms ~100 min. Background job.
set -u
R=/home/struktured/projects/dr-mario-tempo-wt/tools/gate/run_probe6_cart.sh
D=/home/struktured/projects/dr-mario-tempo-wt/tmp/tuckguard
run(){ echo "=== $1 ==="; P6_SEED=114 bash "$R" "$D/$1.nes" "$2" 18000 2>&1 | tail -4; }
run cvc_ctrl_L20         6e657dc812842c2cc7edb05be0bfa5cf
run cvc_tg1_L20          08211ef4394b0c70ddf4e3f68575e056
run cvc_mut_approach_L20 cb6f061086b803282c86e8eec9d4805c
run cvc_mut_nomargin_L20 1ac576b0d59e09ce3b7212cd292c12a9
