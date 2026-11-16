param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$Python = $env:DSH_PYTHON
if (-not $Python -or -not (Test-Path $Python)) {
    $Candidates = @(
        (Join-Path $env:USERPROFILE ".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"),
        "python"
    )
    foreach ($candidate in $Candidates) {
        if ($candidate -eq "python" -or (Test-Path $candidate)) {
            $Python = $candidate
            break
        }
    }
}
if (-not $Python) {
    throw "Python not found. Set DSH_PYTHON or install Python."
}

$env:PYTHONIOENCODING = "utf-8"
& $Python (Join-Path $Root "scripts\run_weekly.py") @Rest
exit $LASTEXITCODE
