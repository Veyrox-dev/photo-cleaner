param(
    [string]$Version,
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$distExe = Join-Path $root "dist\PhotoCleaner\PhotoCleaner.exe"
$wxsPath = Join-Path $root "installer\PhotoCleaner.wxs"
$outDir = Join-Path $root "releases\msi"

if (-not (Test-Path $distExe)) {
    throw "Build artifact missing: $distExe`nRun build.bat first."
}

if (-not (Test-Path $wxsPath)) {
    throw "WiX source file missing: $wxsPath"
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
    throw "Invalid version '$Version'. Expected semantic version format like 0.8.3"
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