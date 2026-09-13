# Final Gold Archaeology — 2026-09-13

Static unique-hash pass of D: archives vs live `C:\RealAI-clean`.
NO deletes. Shelf only. Promote later after review.

## Counts

- Live files hashed: **3506** (1875 unique hashes)
- Archive files scanned (interesting): **111786**
- Dup of live (skipped): **76511**
- Unique candidate hashes: **6623** (4,934,864,496 bytes)
- dest_empty_unique: **1781** (505,605,975 bytes)
- unique_orphan: **4842**
- Copied to gold shelf: **5249** files, **570,731,925** bytes
- Orphan .py copied under gold/orphans: **3489**
- Errors/inaccessible: **0**

## By extension (unique candidates)

- `.py`: 3842
- `.json`: 917
- `.md`: 589
- `.ts`: 553
- `.js`: 501
- `.yaml`: 54
- `.bat`: 33
- `.tsx`: 31
- `.ps1`: 26
- `.toml`: 22
- `.html`: 18
- `.cmd`: 10
- `.mjs`: 10
- `.cjs`: 7
- `.yml`: 6
- `.css`: 4

## How to use the shelf

1. Review `dest_empty_promotable.jsonl` — each row has `inferred_live_rel`.
2. After review, copy from `C:\RealAI-gold\<rel>` → `C:\RealAI-clean\<rel>` only if still dest-empty.
3. Orphans under `C:\RealAI-gold\orphans\` need manual placement.
4. Do NOT wholesale-promote nested Recovery/grok_export trees.

## Top interesting unique paths

1. `dest_empty_unique` .py 2541B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\organs\hive.py` → `realai\modules\organs\hive.py`
2. `dest_empty_unique` .py 1224B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\organs\base.py` → `realai\modules\organs\base.py`
3. `dest_empty_unique` .py 289B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\organs\__init__.py` → `realai\modules\organs\__init__.py`
4. `dest_empty_unique` .py 13565B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\self_improvement\self_builder.py` → `realai\modules\self_improvement\self_builder.py`
5. `dest_empty_unique` .py 15708B — `D:\RealAI-archive\recovered\delta_candidates\agents\realai\modules\agents_advanced\code_engineer_agent.py` → `agents\realai\modules\agents_advanced\code_engineer_agent.py`
6. `dest_empty_unique` .py 68B — `D:\RealAI-archive\recovered\delta_candidates\agents\realai\modules\agents_advanced\__init__.py` → `agents\realai\modules\agents_advanced\__init__.py`
7. `dest_empty_unique` .py 4946B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\desktop_unique\examples.py` → `realai\modules\desktop_unique\examples.py`
8. `dest_empty_unique` .py 8838B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\desktop_unique\examples_local_ai.py` → `realai\modules\desktop_unique\examples_local_ai.py`
9. `dest_empty_unique` .py 5522B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\desktop_unique\examples_ultimate.py` → `realai\modules\desktop_unique\examples_ultimate.py`
10. `dest_empty_unique` .py 3379B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\desktop_unique\lambda_advanced.py` → `realai\modules\desktop_unique\lambda_advanced.py`
11. `dest_empty_unique` .py 242B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\desktop_unique\standalone_ai.py` → `realai\modules\desktop_unique\standalone_ai.py`
12. `dest_empty_unique` .py 71B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\desktop_unique\__init__.py` → `realai\modules\desktop_unique\__init__.py`
13. `dest_empty_unique` .py 6784B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\self_improvement\closed_loop.py` → `realai\modules\self_improvement\closed_loop.py`
14. `dest_empty_unique` .py 1275B — `D:\RealAI-archive\recovered\delta_candidates\agents\realai\modules\agents_skills\coding_agent.py` → `agents\realai\modules\agents_skills\coding_agent.py`
15. `dest_empty_unique` .py 7907B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\organs\request_path.py` → `realai\modules\organs\request_path.py`
16. `dest_empty_unique` .py 116B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules\self_improvement\__init__.py` → `realai\modules\self_improvement\__init__.py`
17. `dest_empty_unique` .py 600B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules_unify_20260830\torch_qat_stubs\conv.py` → `realai\modules_unify_20260830\torch_qat_stubs\conv.py`
18. `dest_empty_unique` .py 596B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules_unify_20260830\torch_qat_stubs\fused.py` → `realai\modules_unify_20260830\torch_qat_stubs\fused.py`
19. `dest_empty_unique` .py 548B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules_unify_20260830\torch_qat_stubs\activation.py` → `realai\modules_unify_20260830\torch_qat_stubs\activation.py`
20. `dest_empty_unique` .py 118B — `D:\RealAI-archive\recovered\delta_candidates\unknown\realai\modules_unify_20260830\torch_qat_stubs\bn_relu.py` → `realai\modules_unify_20260830\torch_qat_stubs\bn_relu.py`

## Outputs

- `live_hashes.jsonl`
- `unique_candidates.jsonl`
- `dest_empty_promotable.jsonl`
- `skipped_heavy.txt`
- `scan_log.txt`
- Shelf: `C:\RealAI-gold\`
