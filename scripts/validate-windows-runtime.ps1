[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$agentRuntimeRoot = Join-Path (Join-Path $HOME '.codex') 'agents'
$skillRuntimeRoot = Join-Path (Join-Path $HOME '.agents') 'skills'
$agentDirectories = @('learning-agent', 'research-agent', 'writing-agent', 'coding-agent', 'modeling-agent', 'experiment-agent')
$skills = @('assessment', 'code-review', 'document-understanding', 'education-learning', 'evidence-synthesis', 'knowledge-extraction', 'knowledge-mapping', 'literature-search', 'model-formulation', 'model-validation', 'software-verification', 'stem-reasoning', 'structured-writing', 'systematic-debugging', 'visualization', 'writing-revision')

function Fail([string] $Message) { throw "ERROR: $Message" }
function Get-FrontmatterValue([string] $Path, [string] $Name) {
    $content = Get-Content -LiteralPath $Path
    for ($index = 1; $index -lt $content.Count; $index++) {
        if ($content[$index] -eq '---') { break }
        if ($content[$index] -match "^$([regex]::Escape($Name)):\s*(.+?)\s*$") { return $Matches[1].Trim('"') }
    }
    Fail "missing frontmatter '$Name': $Path"
}

foreach ($directory in $agentDirectories) {
    $source = Join-Path $repositoryRoot "agents/$directory/AGENT.md"
    $name = Get-FrontmatterValue $source 'name'
    $target = Join-Path $agentRuntimeRoot "$name.toml"
    if (-not (Test-Path -LiteralPath $target)) { Fail "missing Agent runtime: $target" }
    $runtime = Get-Content -LiteralPath $target -Raw
    $expectedNameLine = '^name = "' + [regex]::Escape($name) + '"\r?$'
    if ($runtime -notmatch "(?m)$expectedNameLine") { Fail "invalid Agent name: $target" }
    if ($runtime -notmatch "(?m)^developer_instructions = '''\r?$") { Fail "missing Agent instructions: $target" }
}

foreach ($skill in $skills) {
    $source = Join-Path $repositoryRoot "skills/$skill"
    $target = Join-Path $skillRuntimeRoot $skill
    if (-not (Test-Path -LiteralPath (Join-Path $target 'SKILL.md'))) { Fail "missing Skill runtime: $target" }
    $item = Get-Item -LiteralPath $target -Force
    if ($item.LinkType -notin @('Junction', 'SymbolicLink') -or @($item.Target)[0] -ne $source) { Fail "Skill runtime does not resolve to canonical source: $target" }
}

Write-Output 'Validated Agents: learning_agent research_agent writing_agent coding_agent modeling_agent experiment_agent'
Write-Output "Validated Skills: $($skills -join ' ')"
Write-Output "Canonical: $repositoryRoot"
