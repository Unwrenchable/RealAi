#!/bin/bash

MEGA="/workspaces/RealAi/.blackbox/prompts/all-phases.prompt"

if [ ! -f "$MEGA" ]; then
    echo "ERROR: Mega prompt file not found:"
    echo "  $MEGA"
    exit 1
fi

echo "=============================================="
echo " RealAI FULL PIPELINE MEGA PROMPT"
echo "=============================================="
echo
cat "$MEGA"
echo
echo "=============================================="
echo " Copy the above MEGA PROMPT into Blackbox."
echo "=============================================="
