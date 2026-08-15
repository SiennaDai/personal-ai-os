[CmdletBinding()]
param(
    [string]$RuntimePath
)

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$sourcePath = Join-Path $repositoryRoot 'agents\learning-agent\AGENT.md'

if (-not $RuntimePath) {
    $userProfilePath = [Environment]::GetFolderPath('UserProfile')
    $RuntimePath = Join-Path $userProfilePath '.codex\agents\learning-agent.toml'
}

$source = Get-Content -Raw -LiteralPath $sourcePath
$instructions = [regex]::Replace($source, '\A---\r?\n.*?\r?\n---\r?\n', '', [Text.RegularExpressions.RegexOptions]::Singleline).Trim()

if ($instructions.Contains("'''")) {
    throw "AGENT.md contains a triple single quote, which cannot be embedded safely in the generated TOML literal string."
}

$runtimeToml = @"
# Generated from agents/learning-agent/AGENT.md by sync-runtime.ps1.
# Do not edit this runtime projection directly.
name = "learning_agent"
description = "User-facing STEM learning agent for course materials, lecture review, exam preparation, technical concepts, and problem-solving practice."
developer_instructions = '''
$instructions
'''
"@

$runtimeDirectory = Split-Path -Parent $RuntimePath
[IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
$utf8WithoutBom = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($RuntimePath, $runtimeToml, $utf8WithoutBom)

Write-Output $RuntimePath
