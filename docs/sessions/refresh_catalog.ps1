$ErrorActionPreference = "Stop"
$outDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$catalogPath = Join-Path $outDir "catalog.json"
$roots = @(
  @{ key="realai"; cwd="C:\realai"; path="C:\Users\tsmit\.grok\sessions\C%3A%5Crealai"; lane="realai-core" },
  @{ key="RealAI-clean"; cwd="C:\RealAI-clean"; path="C:\Users\tsmit\.grok\sessions\C%3A%5CRealAI-clean"; lane="realai-core" },
  @{ key="voice"; cwd="C:\RealAI-clean\realai\voice"; path="C:\Users\tsmit\.grok\sessions\C%3A%5CRealAI-clean%5Crealai%5Cvoice"; lane="realai-voice" },
  @{ key="grok-bin"; cwd="C:\Users\tsmit\.grok\bin"; path="C:\Users\tsmit\.grok\sessions\C%3A%5CUsers%5Ctsmit%5C.grok%5Cbin"; lane="realai-tooling" },
  @{ key="atomic-fizz"; cwd="C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS"; path="C:\Users\tsmit\.grok\sessions\C%3A%5CUsers%5Ctsmit%5CATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS"; lane="adjacent-other-repo" },
  @{ key="rack-em-up"; cwd="C:\Users\tsmit\Rack_em_up"; path="C:\Users\tsmit\.grok\sessions\C%3A%5CUsers%5Ctsmit%5CRack_em_up"; lane="unrelated" }
)
$rows = New-Object System.Collections.Generic.List[object]
foreach ($r in $roots) {
  if (-not (Test-Path $r.path)) { continue }
  Get-ChildItem $r.path -Directory | ForEach-Object {
    $sumPath = Join-Path $_.FullName "summary.json"
    if (-not (Test-Path $sumPath)) { return }
    $j = Get-Content $sumPath -Raw | ConvertFrom-Json
    $title = [string]$j.generated_title
    if ([string]::IsNullOrWhiteSpace($title)) { $title = [string]$j.session_summary }
    $rows.Add([pscustomobject]@{
      lane = $r.lane
      root_key = $r.key
      cwd = $r.cwd
      session_id = [string]$j.info.id
      session_dir = $_.FullName
      title = $title
      session_summary = [string]$j.session_summary
      last_turn_summary = [string]$j.last_turn_summary
      last_recap = [string]$j.last_recap
      created_at = [string]$j.created_at
      updated_at = [string]$j.updated_at
      last_active_at = [string]$j.last_active_at
      num_messages = [int]$j.num_messages
      num_chat_messages = [int]$j.num_chat_messages
      model = [string]$j.current_model_id
      agent_name = [string]$j.agent_name
      head_branch = [string]$j.head_branch
      git_root_dir = [string]$j.git_root_dir
      refreshed_at = (Get-Date).ToUniversalTime().ToString("o")
    }) | Out-Null
  }
}
$sorted = $rows | Sort-Object { [datetime]$_.created_at }
($sorted | ConvertTo-Json -Depth 6) | Set-Content $catalogPath -Encoding UTF8
Write-Host "Wrote $($sorted.Count) sessions -> $catalogPath"
$sorted | Group-Object lane | ForEach-Object { Write-Host ("  {0}={1}" -f $_.Name, $_.Count) }
