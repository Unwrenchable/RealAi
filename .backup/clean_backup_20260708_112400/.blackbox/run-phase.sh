#!/bin/bash

PROMPT_DIR="/workspaces/RealAi/.blackbox/prompts"

if [ -z "$1" ]; then
    echo "Usage: bash run-phase.sh <phase-number>"
    echo "Example: bash run-phase.sh 0"
    exit 1
fi

PHASE_FILE="$PROMPT_DIR/phase$1.prompt"

if [ ! -f "$PHASE_FILE" ]; then
    echo "Error: Phase prompt file not found:"
    echo "  $PHASE_FILE"
    exit 1
fi

echo "=============================================="
echo " RealAI Phase $1 Prompt"
echo "=============================================="
echo
cat "$PHASE_FILE"
echo
echo "=============================================="
echo " Copy the above prompt into Blackbox."
echo "=============================================="
