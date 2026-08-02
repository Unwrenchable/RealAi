param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$llamaCli = $env:REALAI_LLAMA_CLI_PATH
if (-not $llamaCli) {
    $llamaCli = Get-Command llama-cli -ErrorAction SilentlyContinue
    if ($llamaCli) {
        $llamaCli = $llamaCli.Source
    }
}

if (-not $llamaCli) {
    throw "No llama-cli executable found. Set REALAI_LLAMA_CLI_PATH."
}

$modelPath = $env:REALAI_MODEL_PATH
if (-not $modelPath) {
    $modelPath = Join-Path $PSScriptRoot '..' 'models'
}

& $llamaCli -m $modelPath @Args
