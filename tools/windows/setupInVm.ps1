# The installers, in the build VM — docs/SPEC_windows_build.md §5b.5 (W2.1c). Called by tools/buildWindows.sh after
# the zips, while $BuildDir still holds dist\. Expects the text files made on Linux in $BuildDir\texts\<app|server>\
# (START_HERE.txt for the INSTALLED copy, RELEASE_MANIFEST.txt); copies them into the dist folder, compiles the
# setup with Inno Setup into $BuildDir\setup\ and prints one "SETUP ok <file> <sha256>" line per setup.
param(
    [Parameter(Mandatory = $true)][string]$BuildDir,
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][string]$Iscc,
    [switch]$App,
    [switch]$Server
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Iscc)) { throw "Inno Setup not found at $Iscc (W2.1a: install it once in the VM)" }
$out = "$BuildDir\setup"
New-Item -ItemType Directory -Force $out | Out-Null

function Build-Setup($what, $source, $iss, $icon) {
    Copy-Item "$BuildDir\texts\$what\*" $source -Force
    $seconds = [int](Measure-Command {
        & $Iscc /Q "/DLabel=$Label" "/DSourceDir=$source" "/DOutputDir=$out" "/DIconFile=$icon" "$BuildDir\recipe\tools\$iss" `
            > "$BuildDir\setup-$what.log" 2>&1
    }).TotalSeconds
    if ($LASTEXITCODE -ne 0) { Get-Content "$BuildDir\setup-$what.log" -Tail 20; throw "ISCC failed for the $what (exit $LASTEXITCODE)" }
    $file = Get-ChildItem $out -Filter $(if ($what -eq "app") { "Spectracs-Setup-*.exe" } else { "Spectracs-Server-Setup-*.exe" }) |
            Select-Object -First 1
    "  ${what} setup: built in $seconds s"
    "SETUP ok $($file.Name) $((Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower())"
}
if ($App) { Build-Setup "app" "$BuildDir\dist\app\Spectracs" "spectracs.iss" "$BuildDir\icons\spectracs.ico" }
if ($Server) {
    Build-Setup "server" "$BuildDir\dist\server\SpectracsServer" "spectracs-server.iss" "$BuildDir\icons\spectracs-server.ico"
}
