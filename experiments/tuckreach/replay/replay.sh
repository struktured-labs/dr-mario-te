#!/bin/bash
# Mesen replay of one co-sim publish timeline on one couch cart (the late-flip lane's probe, copied here):
#   replay.sh <tag> <pubtrace.jsonl> <cart.nes> [maxframes]
# -> tmp/replay/<tag>/lateflip_<tag>.log  (score with experiments/tuckreach/replay_eval.py)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
D="$(cd "$HERE/../../.." && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
tag="${1:?tag}"; pt="$(realpath "${2:?pubtrace}")"; cart="$(realpath "${3:?cart}")"; maxf="${4:-20000}"
mkdir -p "$D/tmp/replay"
lua="$D/tmp/replay/cases_${tag}.lua"; srt="$D/tmp/replay/pubtrace_${tag}.jsonl"
"$PY" -c "import json,sys; R=[json.loads(l) for l in open(sys.argv[1])]; R.sort(key=lambda r: r['p']); open(sys.argv[2],'w').write(''.join(json.dumps(r)+chr(10) for r in R))" "$pt" "$srt"
"$PY" "$HERE/gen_cases_lua.py" "$srt" "$lua"
bash "$HERE/run_lateflip.sh" "$tag" "$cart" "$lua" "$maxf" 0
