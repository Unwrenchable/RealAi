# docs/spine (One-Spine Phase 1a)

Inventory artifacts for `docs/ONE_SPINE_PLAN.md` (PR #217). Docs and tests only: nothing here moves, edits or archives code.

- `orchestrators.csv`: every git-tracked `.py` whose filename contains `orchestrat` (70 on main @ 0b8ae22). Columns: path, sha256, size, imported_by count + up to 3 examples, top-level import style (`import *`, `path-based` = sys.path / spec_from_file_location / runpy / `__import__`, or `normal`), **proposed** fate (core / plugin / shim / archive) and `duplicate_of` for byte-identical copies. Fates are heuristic proposals for travis to review; nothing is archived without a GO per batch (D2).
- `build_orchestrators_csv.py`: regenerates the CSV with `python docs/spine/build_orchestrators_csv.py` (ast only, imports nothing).
- `tests/spine/test_import_graph.py`: the Phase 1b critical-path skeleton. Statically parses every tracked `.py` and asserts each repo-local import resolves to a file or package. Imports already broken on main are frozen in `tests/spine/import_graph_baseline.txt`; the test fails only on new breaks. It must stay green before ANY archive batch.

Note: imported_by counts only static `import`/`from` statements. Path-based loads are flagged in import_style but not counted, so review those rows by hand.
