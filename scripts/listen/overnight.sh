#!/bin/bash
# Keep tuning his mouth by ear-model, stage after stage, cycle after cycle (each stage resumes from the best).
cd "$(dirname "$0")/../.."
PY=/tmp/claude-0/-home-user-VoiceClone/7e3261ab-22a0-5713-8c0c-f1044b891953/scratchpad/sparc_env/venv/bin/python
cycle=0
while [ ! -f out/listen/STOP ]; do
  cycle=$((cycle+1)); echo "=== cycle $cycle $(date +%H:%M)" >> out/listen/tune_log.txt
  for stage in ${STAGES:-throat nasal r voicebox cons vowels}; do
    [ -f out/listen/STOP ] && break
    $PY scripts/listen/tune.py $stage ${EVALS:-200} > out/listen/tune_$stage.out 2>&1 || echo "stage $stage failed" >> out/listen/tune_log.txt
  done
done
