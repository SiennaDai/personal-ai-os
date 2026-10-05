[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = (Get-Command python.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$zoteroRoot = Join-Path $repositoryRoot 'integrations/zotero'
$obsidianRoot = Join-Path $repositoryRoot 'integrations/obsidian'
$zoteroServer = Join-Path $zoteroRoot 'src/zotero_mcp_server.py'
$obsidianServer = Join-Path $obsidianRoot 'src/obsidian_mcp_server.py'
$exampleConfig = Join-Path $repositoryRoot 'integrations/config.example.toml'

function Fail([string] $Message) { throw "ERROR: $Message" }
function Invoke-Checked([string] $File, [string[]] $Arguments) {
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) { Fail "command failed ($LASTEXITCODE): $File $($Arguments -join ' ')" }
}

foreach ($required in @($zoteroServer, $obsidianServer, $exampleConfig)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { Fail "missing required repository file: $required" }
}

$originalPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONPATH = Join-Path $zoteroRoot 'src'
    Invoke-Checked $python @('-B', '-m', 'unittest', 'discover', '-s', (Join-Path $zoteroRoot 'tests'), '-v')
    Invoke-Checked $python @('-B', $zoteroServer, '--config', $exampleConfig, 'validate-config')
    $zoteroTools = (& $python -B $zoteroServer --config $exampleConfig list-tools | ConvertFrom-Json).tools
    if ($zoteroTools.Count -ne 9 -or @($zoteroTools | Where-Object { -not $_.annotations.readOnlyHint }).Count -ne 0) { Fail 'unexpected Zotero default tool inventory' }

    $env:PYTHONPATH = Join-Path $obsidianRoot 'src'
    $obsidianTools = (& $python -B $obsidianServer --config $exampleConfig list-tools | ConvertFrom-Json).tools
    if ($obsidianTools.Count -ne 5 -or @($obsidianTools | Where-Object { -not $_.annotations.readOnlyHint }).Count -ne 0) { Fail 'unexpected Obsidian default tool inventory' }
} finally {
    $env:PYTHONPATH = $originalPythonPath
    Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
}

Write-Output 'Validated Zotero Integration: 55 tests, 9 default read tools.'
Write-Output 'Validated Obsidian Integration: configuration and 5 default read tools.'
