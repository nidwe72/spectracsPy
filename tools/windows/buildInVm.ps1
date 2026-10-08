# The Windows half of tools/buildWindows.sh — docs/SPEC_windows_build.md §5 steps 4-5 and 7.
#
# Runs IN the build VM, called over ssh. Expects $BuildDir to hold what the Linux side unpacked there:
#   src\<six repos at the ref>   recipe\<specs, server entry, tools\rthook_win_*.py>   icons\*.ico
# Builds the requested programs with PyInstaller, applies the licence gate to the artefact, records the toolchain
# and packs dist\ into dist.tar for the way back. The last line is "RESULT ok <sha256 of dist.tar>" or the script
# exits non-zero. Build logs stay in $BuildDir (build-app.log, build-server.log).
param(
    [Parameter(Mandatory = $true)][string]$BuildDir,
    [Parameter(Mandatory = $true)][string]$Venv,
    [switch]$App,
    [switch]$Server
)
$ErrorActionPreference = "Stop"
Set-Location $BuildDir

$env:SPECTRACS_SRC_ROOT        = "$BuildDir\src\spectracsPy"
$env:SPECTRACS_ICON_ICO        = "$BuildDir\icons\spectracs.ico"
$env:SPECTRACS_ICON_ICO_SERVER = "$BuildDir\icons\spectracs-server.ico"

function Build($what, $spec) {
    # cmd /c: PyInstaller writes its warnings to stderr, which PowerShell 5.1 turns into terminating errors
    $seconds = [int](Measure-Command {
        cmd /c "`"$Venv\Scripts\pyinstaller.exe`" --noconfirm --clean --log-level WARN --workpath `"$BuildDir\work\$what`" --distpath `"$BuildDir\dist\$what`" `"$BuildDir\recipe\$spec`" > `"$BuildDir\build-$what.log`" 2>&1"
    }).TotalSeconds
    if ($LASTEXITCODE -ne 0) {
        Get-Content "$BuildDir\build-$what.log" -Tail 30
        throw "PyInstaller failed for the $what (exit $LASTEXITCODE), see $BuildDir\build-$what.log"
    }
    "  ${what}: built in $seconds s"
}

if ($Server) { Build "server" "spectracsServerAppImage.spec" }
if ($App) {
    Build "app" "spectracsAppImage.spec"
    # N8 — the licence gate, re-checked on the artefact and not only inside the spec (§8.1.9)
    $leaked = Get-ChildItem "$BuildDir\dist\app" -Recurse | Where-Object { $_.Name -match "Charts|DataVisualization|WebEngine" }
    if ($leaked) { $leaked | Select-Object -First 5 -ExpandProperty FullName; throw "LICENCE GATE FAILED - GPL/unused Qt modules in the bundle" }
    "  app: licence gate ok"
}

$os = Get-CimInstance Win32_OperatingSystem
@(
    "python      $(& "$Venv\Scripts\python.exe" -c "import platform; print(platform.python_version())")"
    "pyinstaller $(& "$Venv\Scripts\pyinstaller.exe" --version)"
    "opencv      $(& "$Venv\Scripts\python.exe" -c "import importlib.metadata as m; print(m.version('opencv-python'))")"
    "windows     $($os.Caption) $($os.Version)"
) | Set-Content -Encoding ASCII "$BuildDir\dist\toolchain.txt"

tar -cf "$BuildDir\dist.tar" -C "$BuildDir\dist" .
if ($LASTEXITCODE -ne 0) { throw "tar of dist failed" }
"RESULT ok $((Get-FileHash "$BuildDir\dist.tar" -Algorithm SHA256).Hash.ToLower())"
