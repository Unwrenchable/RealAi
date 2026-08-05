#!/bin/bash

PROMPT_DIR="/workspaces/RealAi/.blackbox/prompts"

echo "=============================================="
echo " RealAI Full Unification Pipeline Runner"
echo "=============================================="
echo

for PHASE in {0..8}
do
    PHASE_FILE="$PROMPT_DIR/phase${PHASE}.prompt"

    echo "----------------------------------------------"
    echo " Running Phase ${PHASE}"
    echo "----------------------------------------------"

    if [ ! -f "$PHASE_FILE" ]; then
        echo "ERROR: Missing prompt file:"
        echo "  $PHASE_FILE"
        exit 1
    fi

    echo
    echo "========== Phase ${PHASE} Prompt =========="
    echo
    cat "$PHASE_FILE"
    echo
    echo "=============================================="
    echo " Copy the above Phase ${PHASE} prompt into Blackbox."
    echo " Press ENTER when you're ready for the next phase."
    echo "=============================================="
    read -p ""
done

echo
echo "=============================================="
echo " All phases complete."
echo " RealAI unification pipeline fully executed."
echo "=============================================="
