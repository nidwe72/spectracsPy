# Self-verification of the Windows INSTALLERS, in the build VM — docs/SPEC_windows_build.md §5b.5 (W2.1d).
#
# Called by tools/buildWindows.sh after setupInVm.ps1. For each setup in $SetupDir: a silent per-user install into a
# throwaway folder, the INSTALLED program's own self-checks, a second install OVER the first (a planted stale file
# must be gone — §5b.2), a silent uninstall (folder, uninstall entry and Start-menu entries gone) and the data folder
# still there (§5b.1). Ends with "SETUP-VERIFY ok" or exits 1 with "SETUP-VERIFY FAILED".
#
# ⚠ It installs under the real AppId. If the program is ALREADY installed for real in this VM (Edwin's W2.1e), the
# check is skipped and says so — it must never uninstall someone's real install.
param(
    [Parameter(Mandatory = $true)][string]$SetupDir,
    [switch]$App,
    [switch]$Server
)
$ErrorActionPreference = "Stop"
$failures = New-Object System.Collections.Generic.List[string]
function Fail($message) { $failures.Add($message); "  FAIL  $message" }
function Ok($message) { "  ok    $message" }
function Port-Open($port) {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $port); $c.Close(); $true } catch { $false }
}
function Run($exe, $arguments, $timeoutMs) {
    $p = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru -WindowStyle Hidden
    $null = $p.Handle          # PowerShell 5.1 reports the ExitCode only with the handle taken (§11c.3)
    if ($p.WaitForExit($timeoutMs)) { return $p.ExitCode }
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    return "TIMEOUT"
}
$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Spectracs"

function Verify-Setup($what, $appId, $exeName, $shortcuts, $dataDir, $check) {
    $setup = Get-ChildItem $SetupDir -Filter $(if ($what -eq "app") { "Spectracs-Setup-*.exe" } else { "Spectracs-Server-Setup-*.exe" }) |
             Select-Object -First 1
    if ($null -eq $setup) { Fail "${what}: no setup in $SetupDir"; return }
    $uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{$appId}_is1"
    if (Test-Path $uninstallKey) {
        "  skip  ${what} setup: already installed for real in this VM ($((Get-ItemProperty $uninstallKey).DisplayVersion)) - not touching it"
        return
    }
    $dir = "$env:TEMP\spectracs-setup-verify\$what"
    Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
    # /LANG=en: the VM is a German Windows, and the shortcut names checked below are the English ones
    $quiet = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LANG=en", "/DIR=`"$dir`"")

    # install
    $rc = Run $setup.FullName ($quiet + "/LOG=`"$SetupDir\setup-$what-install.log`"") 300000
    if ($rc -ne 0 -or -not (Test-Path "$dir\$exeName")) { Fail "${what} install: exit $rc, $exeName present: $(Test-Path "$dir\$exeName")"; return }
    $missing = @($shortcuts | Where-Object { -not (Test-Path "$startMenu\$_.lnk") })
    if ($missing) { Fail "${what} install: Start-menu entries missing: $($missing -join ', ')" }
    else { Ok "${what} install: $exeName + $($shortcuts.Count) Start-menu entries" }
    if (-not (Test-Path $uninstallKey)) { Fail "${what} install: no uninstall entry" }

    # the INSTALLED program's own checks
    & $check "$dir\$exeName"

    # install over: a stale file of the "old version" must not survive (§5b.2)
    Set-Content "$dir\stale-from-the-old-version.pyd" "stale"
    $rc = Run $setup.FullName ($quiet + "/LOG=`"$SetupDir\setup-$what-over.log`"") 300000
    if ($rc -ne 0 -or -not (Test-Path "$dir\$exeName")) { Fail "${what} install over: exit $rc" }
    elseif (Test-Path "$dir\stale-from-the-old-version.pyd") { Fail "${what} install over: the stale file survived" }
    else { Ok "${what} install over: folder emptied first, stale file gone" }

    # uninstall — unins000.exe re-launches itself from %TEMP% and returns at once, so poll for the result
    $rc = Run "$dir\unins000.exe" @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") 120000
    foreach ($i in 1..60) { if (-not (Test-Path "$dir\$exeName") -and -not (Test-Path $uninstallKey)) { break }; Start-Sleep 1 }
    $leftShortcuts = @($shortcuts | Where-Object { Test-Path "$startMenu\$_.lnk" })
    if (Test-Path "$dir\$exeName") { Fail "${what} uninstall: $exeName still there" }
    elseif (Test-Path $uninstallKey) { Fail "${what} uninstall: uninstall entry still there" }
    elseif ($leftShortcuts) { Fail "${what} uninstall: Start-menu entries left: $($leftShortcuts -join ', ')" }
    else { Ok "${what} uninstall: program, uninstall entry and Start-menu entries gone" }
    if (Test-Path $dataDir) { Ok "${what} uninstall: data kept ($dataDir)" } else { Fail "${what} uninstall: $dataDir is gone" }
}

if ($App) {
    Verify-Setup "app" "570849E7-33A6-4660-BC81-922E66D61950" "Spectracs.exe" `
        @("Spectracs", "Spectracs (demo, empty database)", "Spectracs - read me") "$env:USERPROFILE\spectracsPy-demo" {
        param($exe)
        $log = "$env:USERPROFILE\Spectracs\spectracsPy-demo\spectracs.log"
        foreach ($flag in "--check-db", "--check-camera-imports") {
            $rc = Run $exe @("--fresh", $flag) 120000
            $line = Get-Content $log -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -Last 1
            if ($rc -eq 0) { Ok "installed app ${flag}: $line" } else { Fail "installed app ${flag}: exit $rc, last log line '$line'" }
        }
    }
}
if ($Server) {
    Verify-Setup "server" "EFF8CDB8-6F33-48ED-B824-B9D9FD0FAEB5" "SpectracsServer.exe" `
        @("Spectracs Server (local)", "Spectracs Server - read me") "$env:USERPROFILE\spectracsPy-server" {
        param($exe)
        if (Port-Open 8091) { "  skip  installed server: 8091 already in use"; return }
        $p = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
        $up = $false
        foreach ($i in 1..30) { if (Port-Open 8091) { $up = $true; break }; if ($p.HasExited) { break }; Start-Sleep 1 }
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep 2                               # let Windows release the exe before the next install overwrites it
        if ($up) { Ok "installed server: 127.0.0.1:8091 open" } else { Fail "installed server: 8091 not open after 30 s" }
    }
}

if ($failures.Count -gt 0) { "SETUP-VERIFY FAILED ($($failures.Count)): $($failures -join '; ')"; exit 1 }
"SETUP-VERIFY ok"
