[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string] $ObsidianVaultPath
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = (Get-Command python.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$codex = (Get-Command codex.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$zoteroServer = Join-Path $repositoryRoot 'integrations/zotero/src/zotero_mcp_server.py'
$obsidianServer = Join-Path $repositoryRoot 'integrations/obsidian/src/obsidian_mcp_server.py'
$exampleConfig = Join-Path $repositoryRoot 'integrations/config.example.toml'
$configRoot = Join-Path (Join-Path $HOME '.config') 'personal-ai-os'
$runtimeConfig = Join-Path $configRoot 'integrations.toml'
$env:CODEX_HOME = Join-Path $HOME '.codex'

function Fail([string] $Message) { throw "ERROR: $Message" }
function Invoke-Checked([string] $File, [string[]] $Arguments) {
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) { Fail "command failed ($LASTEXITCODE): $File $($Arguments -join ' ')" }
}
function Get-McpRegistration([string] $Name) {
    try { $result = & $codex mcp get $Name --json 2>$null } catch { return $null }
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($result | ConvertFrom-Json)
}
function Assert-OwnedRegistration([string] $Name, [string] $Server) {
    $registration = Get-McpRegistration $Name
    if ($null -eq $registration) {
        Invoke-Checked $codex @('mcp', 'add', $Name, '--', $python, $Server, '--config', $runtimeConfig, 'serve')
        $registration = Get-McpRegistration $Name
    }
    $arguments = @($registration.transport.args)
    if ($registration.transport.command -ne $python -or $arguments.Count -ne 4 -or $arguments[0] -ne $Server -or $arguments[1] -ne '--config' -or $arguments[2] -ne $runtimeConfig -or $arguments[3] -ne 'serve') {
        Fail "refusing to replace unexpected MCP registration: $Name"
    }
}

foreach ($required in @($zoteroServer, $obsidianServer, $exampleConfig)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { Fail "missing required repository file: $required" }
}

& (Join-Path $PSScriptRoot 'validate-windows-integrations.ps1')
New-Item -ItemType Directory -Force -Path $configRoot | Out-Null
if (-not (Test-Path -LiteralPath $runtimeConfig)) {
    $lineNumber = (Select-String -LiteralPath $exampleConfig -Pattern '^\[obsidian\]$').LineNumber
    $beforeObsidian = Get-Content -LiteralPath $exampleConfig | Select-Object -First ($lineNumber - 1)
    [System.IO.File]::WriteAllLines($runtimeConfig, $beforeObsidian, [System.Text.UTF8Encoding]::new($false))
}

Invoke-Checked $python @('-B', $zoteroServer, '--config', $runtimeConfig, 'validate-config')
& $python -B $obsidianServer --config $runtimeConfig validate-runtime-config *> $null
if ($LASTEXITCODE -ne 0) {
    Invoke-Checked $python @('-B', $obsidianServer, '--config', $runtimeConfig, 'bootstrap-config', '--vault-path', (Resolve-Path -LiteralPath $ObsidianVaultPath).Path)
}
Invoke-Checked $python @('-B', $obsidianServer, '--config', $runtimeConfig, 'validate-runtime-config')

Assert-OwnedRegistration 'zotero' $zoteroServer
Assert-OwnedRegistration 'obsidian' $obsidianServer

Write-Output "Preserved validated Integration configuration: $runtimeConfig"
Write-Output 'Registered Windows Codex MCP servers: zotero, obsidian'
Write-Output 'Canonical bootstrap exposure is read-only: Zotero 9 tools; Obsidian 5 tools.'
