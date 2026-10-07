#!/bin/bash
# census_of.sh NAME BASE [K=V ...]  -> static NMI census of a publog-family flag set (tmp/silfid_census/NAME_*)
cd "$(dirname "$0")/../.."
GPY=/home/struktured/projects/dr-mario-mods/.venv/bin/python
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
name=$1; shift; mkdir -p tmp/silfid_census
FL=$($PY tools/silfid/publog_flags.py "$@")
$PY -c "
import json,sys
s=dict(kv.split('=',1) for kv in sys.argv[2:])
json.dump({'flag_snapshot': s}, open(sys.argv[1],'w'))" tmp/silfid_census/$name.manifest.json $FL
nice -n 19 $GPY tools/nmi126/capture_ir.py tmp/silfid_census/$name.manifest.json tmp/silfid_census/${name}_ir.json > tmp/silfid_census/$name.capture.log 2>&1 || { echo "CAPTURE FAIL $name"; tail -5 tmp/silfid_census/$name.capture.log; exit 1; }
nice -n 19 $GPY tools/nmi126/census.py tmp/silfid_census/${name}_ir.json > tmp/silfid_census/$name.census.log 2>&1; rc=$?
command grep -a -E "WORST ADMISSIBLE|ALL_PATHS +hook|FAIL|UNDECLARED|OVER" tmp/silfid_census/$name.census.log | head -12; exit $rc
