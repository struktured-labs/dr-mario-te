#!/usr/bin/env bash
# Multi-pass STT over the three v6c session recordings.
# Pass A: raw audio, no VAD, no prompt   (baseline truth)
# Pass B: normalized audio, no VAD, no prompt
# Pass C: normalized audio, no VAD, domain initial_prompt
set -u
cd /home/struktured/projects/dr-mario-qa-wt/tmp/commentary

SEGS="20260809_202915_struktured_v6c 20260809_203247_struktured_v6c_part2 20260809_203405_struktured_v6c_part2"
PROMPT="Dr. Mario cart testing notes: the STUDY button, the pause screen, the virus count, capsules and pills, the P2 side, the coprocessor, the Analogue Pocket handheld, MiSTer FPGA, the TE romhack, tuck moves, garbage, top out, the level select screen, flickering tiles, a black screen, a freeze."

run() { # $1=outdir $2=wav $3... extra
  local out="$1"; shift
  local wav="$1"; shift
  echo "### $out <- $wav $*"
  uvx --from whisper-ctranslate2 whisper-ctranslate2 \
    --model large-v3 --device cpu --compute_type int8 --threads 16 \
    --language en --task transcribe \
    --output_dir "$out" --output_format all \
    --word_timestamps True --vad_filter False \
    --temperature 0 --beam_size 5 --condition_on_previous_text False \
    "$@" "$wav" 2>&1 | tail -60
}

for s in $SEGS; do run out_A_raw   "${s}.wav"; done
for s in $SEGS; do run out_B_norm  "${s}_norm.wav"; done
for s in $SEGS; do run out_C_prompt "${s}_norm.wav" --initial_prompt "$PROMPT"; done
echo "ALL PASSES DONE"
