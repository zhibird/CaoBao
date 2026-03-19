param(
  [string]$Version = "",

  [string]$CommitMessage = "release: v$Version",

  [string]$Remote = "origin",

  [string]$Branch = "",

  [bool]$SkipRelease = $true,

  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Exec([string]$Cmd) {
  if ($DryRun) {
    Write-Host $Cmd
    return
  }
  & cmd.exe /c $Cmd
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed ($LASTEXITCODE): $Cmd"
  }
}

function ExecCapture([string]$Cmd) {
  $out = & cmd.exe /c $Cmd
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed ($LASTEXITCODE): $Cmd"
  }
  return ($out | Out-String).Trim()
}

function GetLatestChangelogVersion() {
  $items = Get-ChildItem -Path "changelogs" -File -Filter "*.md" -ErrorAction SilentlyContinue |
    Where-Object { $_.BaseName -match '^\d+\.\d+\.\d+$' } |
    Sort-Object { [version]$_.BaseName } -Descending
  if ($null -eq $items -or $items.Count -eq 0) {
    return ""
  }
  return $items[0].BaseName
}

if ([string]::IsNullOrWhiteSpace($Version)) {
  $suggested = GetLatestChangelogVersion
  if (-not [string]::IsNullOrWhiteSpace($suggested)) {
    $inputV = Read-Host "Version (X.Y.Z). Press Enter to use latest changelog '$suggested'"
    if ([string]::IsNullOrWhiteSpace($inputV)) {
      $Version = $suggested
    } else {
      $Version = $inputV.Trim()
    }
  } else {
    $Version = (Read-Host "Version (X.Y.Z)").Trim()
  }
}

if ([string]::IsNullOrWhiteSpace($CommitMessage) -or $CommitMessage -eq "release: v") {
  $CommitMessage = "release: v$Version"
}

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
  throw "Version must match X.Y.Z (e.g. 0.5.1). Got: '$Version'"
}

$tag = "v$Version"
$changelog = Join-Path "changelogs" "$Version.md"

if (-not (Test-Path $changelog)) {
  throw "Changelog file not found: $changelog"
}

$gitTop = ExecCapture "git rev-parse --show-toplevel"
if (-not $gitTop) {
  throw "Not a git repository (git rev-parse failed)."
}

$null = ExecCapture "git --version"

$hasGh = $true
try {
  $null = ExecCapture "gh --version"
} catch {
  $hasGh = $false
}

if (-not $SkipRelease -and -not $DryRun) {
  if (-not $hasGh) {
    throw "GitHub CLI (gh) not found. Install it first: https://cli.github.com/"
  }

  try {
    ExecCapture "gh auth status"
  } catch {
    throw "gh is not authenticated. Run: gh auth login"
  }
}

if ([string]::IsNullOrWhiteSpace($Branch)) {
  $Branch = ExecCapture "git branch --show-current"
}

if ([string]::IsNullOrWhiteSpace($Branch)) {
  throw "Cannot detect current branch. Please pass -Branch explicitly."
}

$existingTag = ""
try {
  $existingTag = ExecCapture "git tag -l $tag"
} catch {
  $existingTag = ""
}

if (-not [string]::IsNullOrWhiteSpace($existingTag)) {
  throw "Tag already exists: $tag"
}

Exec "git status --porcelain"

Exec "git add -A"

$hasChanges = ExecCapture "git status --porcelain"
if (-not [string]::IsNullOrWhiteSpace($hasChanges)) {
  Exec ('git commit -m "{0}"' -f $CommitMessage)
}

Exec ('git tag -a {0} -m "{0}"' -f $tag)

Exec "git push $Remote $Branch"
Exec "git push $Remote $tag"

if (-not $SkipRelease) {
  if (-not $hasGh -and $DryRun) {
    Write-Host "gh not found; DryRun will still print the gh release command below."
  }

  $releaseTitle = $tag
  Exec ('gh release create {0} --title "{0}" --notes-file "{1}"' -f $releaseTitle, $changelog)
}

if ($SkipRelease) {
  Write-Host "Done: pushed $Branch and pushed tag $tag (release skipped)"
} else {
  Write-Host "Done: pushed $Branch and created release $tag"
}
