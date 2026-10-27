# Chess: RealAI vs Stockfish, and learning from the games

## Watch a match
```
C:\venvs\realai-train\Scripts\python.exe C:\temp\chess-match\chess_vs_stockfish.py
```
(or `scripts/chess_vs_stockfish.py` from a checkout). Opens a live board at http://127.0.0.1:8765.
The model (default `realai-sft-1.5b` on :8081) gets FEN + move history only -- no engine help.
Useful flags: `--games 2`, `--sf-skill 0,3,6` / `--sf-elo 1320,1500`, `--delay 2`, `--on-fail resign`,
`--remember` (write a match summary + biggest mistakes into RealAI memory via `abilities/memory_learning`).

Results go to `C:\temp\chess-match\results\`: `match-*.pgn`, `match-*.json` (W/L/D per level, illegal rate,
avg centipawn loss, rough Elo, common mistakes) and **`experience\match-*.jsonl`**: one line per model attempt with
FEN, model move, legal?, Stockfish best move + PV + eval (depth 12) and centipawn loss.

## How it learns
The model does not learn while it plays. The experience logs become training data:

1. The dataset builder source `chess_selfplay_experience` (on by default in `config/dataset_builder.pc.json`)
   reads `C:/temp/chess-match/results/experience/*.jsonl` (and `{realai}/datasets/_sources/chess_experience/*.jsonl`).
   If no files exist it simply contributes 0 rows.
2. Each unique position (deduped by FEN, move counters ignored) becomes one SFT row in the exact match prompt format.
   **The target is always Stockfish's best move + main line -- never the model's own move**, so its mistakes and
   illegal attempts turn into corrections. Rows are tagged `own-data`.
3. The next `python -m realai.training.dataset_builder build ...` + `train_sft train` run picks them up automatically.
   Play more matches -> more corrected positions -> each retrain plays a bit better. Re-run the match afterwards
   to compare illegal-move rate, cp loss and Elo with the previous model.

Options on the source: `only_mistakes` (default false: correct moves are kept as reinforcement), `min_cp_loss`, `limit` (5000).
