# Promote for real (not more maps)

## One command

```powershell
cd C:\realai
powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1
```

This **starts stack + applies curated allowlist + verifies imports**.  
It does **not** create new `recovered/from_*` dump folders.

## Promote only

```powershell
cd C:\realai
$env:REALAI_SELF_IMPROVE="true"
python scripts\curated_promote.py
# dry-run:
python scripts\curated_promote.py --dry-run
```

## Clean the mess (move dumps out of the repo)

```powershell
python scripts\cold_archive_recovered.py
# preview:
python scripts\cold_archive_recovered.py --dry-run
```

Dumps go to `C:\realai-cold\recovered-archive\<timestamp>\`  
(under WSL: `/mnt/c/realai-cold/recovered-archive/<timestamp>/`).  
Keeps only `recovered/CURATED_PROMOTE_LOG.json` + `recovered/inbox/`.

**Run cold-archive from Windows PowerShell when possible** so paths stay on
`C:\realai-cold` (WSL used to create a bogus `C:` folder inside the repo —
that is fixed in `cold_archive_recovered.py`).

## What “promote” means now

| Old (mess) | New |
|------------|-----|
| Scan → dump 70 folders | Allowlist of ~20 real files |
| Dry-run by default | **Apply by default** |
| Maps only | Copy into `realai/` + import check |

Edit allowlist: `scan_results\curated_promote_allowlist.json`
