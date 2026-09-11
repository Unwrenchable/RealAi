#Requires -Version 5.1
$ErrorActionPreference = "Continue"
$Root = "C:\models\checkpoints_lora"
$Log = @()
function Log($m) { $script:Log += $m; Write-Host $m }
function EnsureDir($p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null } }
function QuickHash([string]$path) {
  $fs = [System.IO.File]::OpenRead($path)
  try {
    $buf = New-Object byte[] (4MB)
    $n = $fs.Read($buf, 0, $buf.Length)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $h1 = [BitConverter]::ToString($sha.ComputeHash($buf, 0, $n)).Replace("-", "").Substring(0, 16)
    if ($fs.Length -gt 8MB) {
      $fs.Seek(-1MB, "End") | Out-Null
      $n2 = $fs.Read($buf, 0, 1MB)
      $h2 = [BitConverter]::ToString($sha.ComputeHash($buf, 0, $n2)).Replace("-", "").Substring(0, 16)
    } else { $h2 = $h1 }
    return "$h1-$h2-$($fs.Length)"
  } finally { $fs.Close() }
}
function Move-Into($src, $destDir) {
  EnsureDir $destDir
  $dest = Join-Path $destDir (Split-Path $src -Leaf)
  if (Test-Path -LiteralPath $dest) {
    if ((Get-Item -LiteralPath $src).PSIsContainer) {
      # merge files
      Get-ChildItem -LiteralPath $src -Force -EA SilentlyContinue | ForEach-Object {
        $d2 = Join-Path $dest $_.Name
        if (-not (Test-Path -LiteralPath $d2)) { Move-Item -LiteralPath $_.FullName -Destination $d2 -Force }
      }
      # remove src if empty-ish
      $left = @(Get-ChildItem -LiteralPath $src -Force -EA SilentlyContinue)
      if ($left.Count -eq 0) { Remove-Item -LiteralPath $src -Force -Recurse -EA SilentlyContinue }
    } else {
      # file exists at dest — leave src for dedupe pass
    }
  } else {
    Move-Item -LiteralPath $src -Destination $dest -Force
  }
  return $dest
}

Log "=== ORGANIZE checkpoints_lora @ $(Get-Date -Format o) ==="
EnsureDir "$Root\agent_lora_runs"
EnsureDir "$Root\datasets"
EnsureDir "$Root\safetensors\adapters"
EnsureDir "$Root\safetensors\hf_shards"
EnsureDir "$Root\_junk_pip"
EnsureDir "$Root\_deleted_gguf_dupes"

# 1) Move agent *-default-run dirs
$movedRuns = 0
Get-ChildItem $Root -Directory -Force | Where-Object { $_.Name -match "-default-run$" } | ForEach-Object {
  Move-Into $_.FullName "$Root\agent_lora_runs" | Out-Null
  $movedRuns++
}
Log "Moved agent_lora_runs: $movedRuns"

# 2) Datasets
foreach ($d in @("normalized_datasets", "realai_training_data")) {
  $p = Join-Path $Root $d
  if (Test-Path $p) {
    $dest = Join-Path "$Root\datasets" $d
    if (-not (Test-Path $dest)) {
      Move-Item $p $dest -Force
      Log "Moved dataset: $d"
    } elseif ((Get-Item $p).FullName -ne (Get-Item $dest).FullName) {
      # already have datasets copy; remove top-level if duplicate name under datasets
      Log "Dataset already under datasets/: $d (left top-level if distinct)"
    }
  }
}
# Also mirror C:\models\normalized_datasets if richer
if ((Test-Path "C:\models\normalized_datasets") -and -not (Test-Path "$Root\datasets\normalized_datasets")) {
  cmd /c "mklink /J `"$Root\datasets\normalized_datasets`" `"C:\models\normalized_datasets`"" | Out-Null
  Log "Junction datasets/normalized_datasets -> C:\models\normalized_datasets"
}

# 3) Pip junk
Get-ChildItem $Root -Force | Where-Object {
  $_.Name -match "^(safetensors|safetensors-.*\.dist-info)$" -or
  $_.Name -match "^_safetensors" -or
  $_.Name -match "^safetensors_" -or
  $_.Name -match "^_consolidate_hf_safetensors"
} | ForEach-Object {
  Move-Into $_.FullName "$Root\_junk_pip" | Out-Null
  Log "Junk pip -> _junk_pip: $($_.Name)"
}

# 4) HF shards + tokenizer/config sitting at root
$shardFiles = @(Get-ChildItem $Root -File -Force | Where-Object {
  $_.Name -match "^model-\d+-of-\d+\.safetensors" -or
  $_.Name -match "^model\.safetensors\.index\.json" -or
  $_.Name -in @("config.json","generation_config.json","tokenizer.json","tokenizer_config.json","merges.txt","vocab.json","LICENSE",".gitattributes") -or
  $_.Name -match "^model-\d+-of-\d+\.safetensors\.metadata$" -or
  $_.Name -eq "model.safetensors.index.json.metadata"
})
if ($shardFiles.Count -gt 0) {
  $hfDest = "$Root\safetensors\hf_shards\qwen3_or_base"
  EnsureDir $hfDest
  foreach ($f in $shardFiles) {
    $dest = Join-Path $hfDest $f.Name
    if (-not (Test-Path $dest)) { Move-Item -LiteralPath $f.FullName -Destination $dest -Force; Log "HF shard -> $hfDest : $($f.Name)" }
  }
}

# 5) Loose adapter_model*.safetensors — keep unique by hash
$adapters = @(Get-ChildItem $Root -File -Filter "adapter_model*.safetensors" -Force -EA SilentlyContinue)
$seen = @{}
$kept = 0; $deletedAdapters = 0
foreach ($a in ($adapters | Sort-Object { if ($_.Name -eq "adapter_model.safetensors") { 0 } else { 1 } }, Name)) {
  $h = QuickHash $a.FullName
  if ($seen.ContainsKey($h)) {
    Remove-Item -LiteralPath $a.FullName -Force
    $deletedAdapters++
    Log "Deleted dupe adapter: $($a.Name) (= $($seen[$h]))"
  } else {
    $seen[$h] = $a.Name
    $destName = if ($a.Name -eq "adapter_model.safetensors") { "adapter_model.safetensors" } else { "adapter_model_$($kept).safetensors" }
    $dest = Join-Path "$Root\safetensors\adapters" $destName
    if ($a.FullName -ne $dest) {
      if (-not (Test-Path $dest)) { Move-Item -LiteralPath $a.FullName -Destination $dest -Force }
      else { Remove-Item -LiteralPath $a.FullName -Force; $deletedAdapters++ }
    }
    $kept++
  }
}
Log "Adapters kept=$kept deleted_dupes=$deletedAdapters"

# 6) GGUF dedupe
# 6a) Delete .bak ggufs
Get-ChildItem $Root -Recurse -Filter "*.gguf" -File -EA SilentlyContinue | Where-Object { $_.Name -match "\.bak_" -or $_.Name -match "\.bak\.gguf$" } | ForEach-Object {
  $tomb = Join-Path "$Root\_deleted_gguf_dupes" ($_.Name + ".DELETED.txt")
  Set-Content $tomb "Deleted duplicate/bak: $($_.FullName) size=$($_.Length) at $(Get-Date -Format o)"
  Remove-Item -LiteralPath $_.FullName -Force
  Log "Deleted bak GGUF: $($_.FullName)"
}

# 6b) Llama identical trio — keep Llama-3.2-1B-Instruct-Q4_K_M.gguf, hardlink aliases
$llamaCanon = Join-Path $Root "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
$llamaAliases = @("llama-3.2-1b.gguf", "llama-local-1b-Q4_K_M.gguf")
if (Test-Path $llamaCanon) {
  $canonHash = QuickHash $llamaCanon
  foreach ($alias in $llamaAliases) {
    $ap = Join-Path $Root $alias
    if (Test-Path $ap) {
      $ah = QuickHash $ap
      if ($ah -eq $canonHash) {
        Remove-Item -LiteralPath $ap -Force
        cmd /c "mklink /H `"$ap`" `"$llamaCanon`"" | Out-Null
        Log "Hardlinked alias $alias -> Llama-3.2-1B-Instruct-Q4_K_M.gguf"
      }
    }
  }
}

# 6c) Misnamed flat realai-1.0-instruct-Q4_K_M.gguf that is actually Llama — replace with real 718MB weight
$flatRealai = Join-Path $Root "realai-1.0-instruct-Q4_K_M.gguf"
$realWeight = Join-Path $Root "realai-1.0-instruct\weights\realai-1.0-instruct-Q4_K_M.gguf"
if (-not (Test-Path $realWeight)) { $realWeight = Join-Path $Root "realai-1.0\weights\realai-1.0-instruct-Q4_K_M.gguf" }
if ((Test-Path $flatRealai) -and (Test-Path $llamaCanon) -and (Test-Path $realWeight)) {
  if ((QuickHash $flatRealai) -eq (QuickHash $llamaCanon)) {
    Remove-Item -LiteralPath $flatRealai -Force
    Copy-Item -LiteralPath $realWeight -Destination $flatRealai -Force
    Log "Replaced misnamed flat realai-1.0-instruct-Q4_K_M.gguf (was Llama copy) with real 718MB weight"
  }
}

# 6d) Nested duplicate realai ggufs identical to flat — delete nested copies that match flat
if (Test-Path $flatRealai) {
  $fh = QuickHash $flatRealai
  Get-ChildItem $Root -Recurse -Filter "realai-1.0-instruct-Q4_K_M.gguf" -File -EA SilentlyContinue |
    Where-Object { $_.FullName -ne $flatRealai } | ForEach-Object {
      if ((QuickHash $_.FullName) -eq $fh) {
        Remove-Item -LiteralPath $_.FullName -Force
        Log "Deleted nested identical realai GGUF: $($_.FullName)"
      }
    }
}

# 6e) Quarantine/backup GGUF identical to checkpoints — delete from quarantine+backup to free space
foreach ($qroot in @("C:\RealAI-clean\_quarantine\models", "C:\RealAI-clean-backup\models")) {
  if (-not (Test-Path $qroot)) { continue }
  Get-ChildItem $qroot -Recurse -Filter "*.gguf" -File -EA SilentlyContinue | ForEach-Object {
    $name = $_.Name
    $live = Join-Path $Root $name
    # also search recursively in Root for same name
    if (-not (Test-Path $live)) {
      $hit = Get-ChildItem $Root -Recurse -Filter $name -File -EA SilentlyContinue | Select-Object -First 1
      if ($hit) { $live = $hit.FullName }
    }
    if ((Test-Path $live) -and ((QuickHash $_.FullName) -eq (QuickHash $live))) {
      Remove-Item -LiteralPath $_.FullName -Force
      Log "Deleted quarantine/backup dupe GGUF: $($_.FullName)"
    } elseif (-not (Test-Path $live)) {
      # unique weight not in checkpoints — MOVE into Root
      $dest = Join-Path $Root $name
      Move-Item -LiteralPath $_.FullName -Destination $dest -Force
      Log "Moved unique GGUF into checkpoints_lora: $name"
    } else {
      # different content same name — keep as .quarantine-variant
      $dest = Join-Path $Root ($_.BaseName + ".quarantine-variant.gguf")
      if (-not (Test-Path $dest)) {
        Move-Item -LiteralPath $_.FullName -Destination $dest -Force
        Log "Kept differing quarantine GGUF as: $(Split-Path $dest -Leaf)"
      } else {
        Remove-Item -LiteralPath $_.FullName -Force
        Log "Dropped extra quarantine variant (already kept one): $($_.Name)"
      }
    }
  }
}

# 7) Copy non-weight model metadata from quarantine into repo models/
$repoModels = "C:\RealAI-clean\models"
EnsureDir $repoModels
Copy-Item "C:\RealAI-clean\_quarantine\models\CANONICAL_MODELS_ROOT.txt" "$repoModels\CANONICAL_MODELS_ROOT.txt" -Force -EA SilentlyContinue
foreach ($meta in @("registry.json","registry.json.example","metadata.json","__init__.py","index.ts","types.ts")) {
  $src = "C:\RealAI-clean\_quarantine\models\$meta"
  if ((Test-Path $src) -and -not (Test-Path "$repoModels\$meta")) {
    Copy-Item $src "$repoModels\$meta" -Force
    Log "Repo models meta: $meta"
  }
}
# package manifests for realai-* model cards
foreach ($card in @("realai-1.0","realai-1.0-instruct","realai-hive","realai-overseer","realai-vision","realai-embed")) {
  $src = "C:\RealAI-clean\_quarantine\models\$card"
  $dst = Join-Path $repoModels $card
  if (Test-Path $src) {
    EnsureDir $dst
    Get-ChildItem $src -Recurse -File -EA SilentlyContinue | Where-Object {
      $_.Extension -match '\.(json|md|txt|ts|py)$' -or $_.Name -eq "ACTIVE_GGUF.txt"
    } | ForEach-Object {
      $rel = $_.FullName.Substring($src.Length).TrimStart("\")
      $d = Join-Path $dst $rel
      EnsureDir (Split-Path $d -Parent)
      if (-not (Test-Path $d)) { Copy-Item $_.FullName $d -Force; Log "Model card: $card/$rel" }
    }
  }
}

# 8) Write layout README
$readme = @"
# RealAI model root (canonical)

**Path:** ``C:\models\checkpoints_lora``

## Layout
- ``*.gguf`` at this root — chat/inference weights referenced by ``config/realai_models.json``
- ``qwen*/llama*/realai-*/`` — LoRA adapter / export folders
- ``agent_lora_runs/`` — per-agent LoRA training runs (``*-default-run``)
- ``datasets/`` — ``normalized_datasets``, ``realai_training_data``
- ``safetensors/adapters/`` — deduped loose adapter weights
- ``safetensors/hf_shards/`` — multi-shard HF base weights + tokenizer
- ``_junk_pip/`` — accidental pip package debris (safe to delete)
- ``_deleted_gguf_dupes/`` — tombstones for removed GGUF backups/dupes

## Env
``````
REALAI_MODELS_DIR=C:\models\checkpoints_lora
REALAI_LORA_ROOT=C:\models\checkpoints_lora
``````

Repo ``C:\RealAI-clean\models`` holds manifests/cards only — not primary weights.
"@
Set-Content "$Root\README.md" $readme -Encoding UTF8
Set-Content "$repoModels\CANONICAL_MODELS_ROOT.txt" @"
Canonical RealAI weights + LoRA adapters live at:

  C:\models\checkpoints_lora

Set in repo .env:
  REALAI_MODELS_DIR=C:\models\checkpoints_lora
  REALAI_LORA_ROOT=C:\models\checkpoints_lora

This folder (C:\RealAI-clean\models) is manifests / model cards only.
Do not train/load from here as the primary root.
"@ -Encoding UTF8

# Persist log
$logPath = "C:\RealAI-clean\scan_results\organize_checkpoints_lora_log.txt"
($Log -join "`n") | Set-Content $logPath -Encoding UTF8
Log "Log written: $logPath"
Log "DONE"
