param(
    [string]$Version,
    [switch]$Clean,
    [switch]$SkipAppRebuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$distExe = Join-Path $root "dist\PhotoCleaner\PhotoCleaner.exe"
$wxsPath = Join-Path $root "installer\PhotoCleaner.wxs"
$outDir = Join-Path $root "releases\msi"
$buildBat = Join-Path $root "build.bat"

if (-not (Test-Path $wxsPath)) {
    throw "WiX source file missing: $wxsPath"
}

if (-not (Test-Path $buildBat) -and -not $SkipAppRebuild) {
    throw "build.bat not found at $buildBat. Cannot rebuild app automatically."
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $runUiPath = Join-Path $root "run_ui.py"
    if (-not (Test-Path $runUiPath)) {
        throw "Could not infer version because run_ui.py was not found."
    }

    $content = Get-Content -Path $runUiPath -Raw
    $match = [regex]::Match($content, 'VERSION\s*=\s*"(?<v>[0-9]+\.[0-9]+\.[0-9]+)"')
    if (-not $match.Success) {
        throw "Could not infer version from run_ui.py. Pass -Version <major.minor.patch>."
    }

    $Version = $match.Groups["v"].Value
}

if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$') {
    throw "Invalid version '$Version'. Expected semantic version format like 0.8.4"
}

function Get-NewestSourceTimestamp {
    param([string]$WorkspaceRoot)

    $sourceCandidates = @(
        (Join-Path $WorkspaceRoot "run_ui.py"),
        (Join-Path $WorkspaceRoot "PhotoCleaner.spec"),
        (Join-Path $WorkspaceRoot "src"),
        (Join-Path $WorkspaceRoot "build_hooks")
    )

    $timestamps = @()
    foreach ($candidate in $sourceCandidates) {
        if (-not (Test-Path $candidate)) {
            continue
        }
        $item = Get-Item $candidate
        if ($item.PSIsContainer) {
            $timestamps += Get-ChildItem $candidate -Recurse -File | Select-Object -ExpandProperty LastWriteTimeUtc
        } else {
            $timestamps += $item.LastWriteTimeUtc
        }
    }

    if (-not $timestamps -or $timestamps.Count -eq 0) {
        return [datetime]::MinValue
    }

    return ($timestamps | Sort-Object -Descending | Select-Object -First 1)
}

function Invoke-AppBuild {
    param(
        [string]$WorkspaceRoot,
        [switch]$CleanBuild
    )

    Push-Location $WorkspaceRoot
    try {
        $arguments = @("/c", "build.bat")
        if ($CleanBuild) {
            $arguments += "clean"
        }

        Write-Host "Building app artifact before MSI packaging..."
        & cmd.exe @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "build.bat failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

$needsRebuild = -not (Test-Path $distExe)
if (-not $needsRebuild) {
    $exeTime = (Get-Item $distExe).LastWriteTimeUtc
    $srcTime = Get-NewestSourceTimestamp -WorkspaceRoot $root
    if ($exeTime -lt $srcTime) {
        $needsRebuild = $true
        Write-Host "App build artifact is stale (dist older than sources)."
    }
}

if ($needsRebuild -and -not $SkipAppRebuild) {
    Invoke-AppBuild -WorkspaceRoot $root -CleanBuild:$Clean
}

if (-not (Test-Path $distExe)) {
    throw "Build artifact missing after rebuild attempt: $distExe"
}

$wix = Get-Command wix -ErrorAction SilentlyContinue
$wixExe = if ($wix) { $wix.Source } else { $null }

if (-not $wixExe) {
    $candidatePaths = @(
        "C:\Program Files\WiX Toolset\bin\wix.exe",
        "C:\Program Files\WiX Toolset v6.0\bin\wix.exe",
        "C:\Program Files\WiX Toolset v6\bin\wix.exe",
        "C:\Program Files\WiX Toolset v4\bin\wix.exe"
    )

    foreach ($candidate in $candidatePaths) {
        if (Test-Path $candidate) {
            $wixExe = $candidate
            break
        }
    }
}

if (-not $wixExe) {
    throw "WiX CLI not found. Install it via: winget install --id WiXToolset.WiXCLI"
}

if ($Clean -and (Test-Path $outDir)) {
    Remove-Item -Path $outDir -Recurse -Force
}

New-Item -Path $outDir -ItemType Directory -Force | Out-Null

$outputPath = Join-Path $outDir ("PhotoCleaner-{0}-x64.msi" -f $Version)

Write-Host "Building MSI with WiX..."
Write-Host "Version: $Version"
Write-Host "Input:   $wxsPath"
Write-Host "Output:  $outputPath"

& $wixExe build $wxsPath -d ProductVersion=$Version -arch x64 -out $outputPath

if (-not (Test-Path $outputPath)) {
    throw "MSI build reported success, but output was not found: $outputPath"
}

$msi = Get-Item $outputPath
Write-Host "MSI build complete: $($msi.FullName)"
Write-Host "Size (MB): $([Math]::Round($msi.Length / 1MB, 2))"