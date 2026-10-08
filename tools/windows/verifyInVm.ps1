# Self-verification of a Windows build, IN the build VM — docs/SPEC_windows_build.md §5.1 (W0.7).
#
# Called by tools/buildWindows.sh after buildInVm.ps1, while $BuildDir still holds src\ and dist\. Headless, no
# window to click; every program run has a timeout as the safety net (§5.1.5) and its exit code is read through the
# process handle (§11c.3). Prints one line per check and ends with "VERIFY ok" or exits 1 with "VERIFY FAILED".
#
#   app:    1  Spectracs.exe --fresh --check-db  -> exit 0, "check-db ok", script head == $ExpectedHead, demo dir
#           2  Spectracs.exe --fresh --check-lamp-imports -> exit 0, "lamp imports ok"
#           +  GUI smoke (beyond §5.1): offscreen --fresh start alive after 25 s, no Traceback in the log
#   server: 3  a dummy listener on 8091 -> SpectracsServer.exe refuses with exit 1
#           4  SpectracsServer.exe (no args) opens 8091; login masterUserExakta FROM SOURCE in the VM venv;
#              calibration is information only (a fresh VM server DB has none)
#
# --fresh everywhere on the app side: the VM's build user is not a demo user, %USERPROFILE%\spectracsPy-demo is
# throwaway and wiped first. The server checks use the VM's real server dir, like the Linux verify does.
param(
    [Parameter(Mandatory = $true)][string]$BuildDir,
    [Parameter(Mandatory = $true)][string]$Venv,
    [string]$ExpectedHead = "",
    [switch]$App,
    [switch]$Server
)
$ErrorActionPreference = "Stop"
$failures = New-Object System.Collections.Generic.List[string]
function Fail($message) { $failures.Add($message); "  FAIL  $message" }
function Ok($message) { "  ok    $message" }

function Start-Headless($exe, $arguments, $logBase) {
    $options = @{ FilePath = $exe; PassThru = $true }
    if ($arguments) { $options.ArgumentList = $arguments }
    if ($logBase) { $options.RedirectStandardOutput = "$logBase.out"; $options.RedirectStandardError = "$logBase.err"; $options.WindowStyle = "Hidden" }
    $p = Start-Process @options
    $null = $p.Handle          # without this PowerShell 5.1 never reports the ExitCode (§11c.3)
    return $p
}
function Wait-Exit($p, $timeoutMs) {
    if ($p.WaitForExit($timeoutMs)) { return $p.ExitCode }
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    return "TIMEOUT"
}
function Port-Open($port) {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $port); $c.Close(); $true } catch { $false }
}

# ------------------------------------------------------------------------------------------------ the app
if ($App) {
    $exe = "$BuildDir\dist\app\Spectracs\Spectracs.exe"
    $demoCwd = "$env:USERPROFILE\Spectracs\spectracsPy-demo"
    $demoData = "$env:USERPROFILE\spectracsPy-demo"
    $log = "$demoCwd\spectracs.log"
    Remove-Item -Recurse -Force $demoCwd, $demoData -ErrorAction SilentlyContinue

    # 1 — the DB migrates to head, and lands where D4 says
    $rc = Wait-Exit (Start-Headless $exe @("--fresh", "--check-db")) 120000
    $line = if (Test-Path $log) { Get-Content $log -Encoding UTF8 | Where-Object { $_ -like "check-db *" } | Select-Object -Last 1 } else { $null }
    if ($rc -ne 0) { Fail "check-db: exit $rc ($line)" }
    elseif ($line -notmatch "^check-db ok: app db (\w+) head (\w+) at (.+)$") { Fail "check-db: no 'check-db ok' line in $log" }
    elseif ($ExpectedHead -and $Matches[2] -ne $ExpectedHead) { Fail "check-db: bundled head $($Matches[2]) != -model head $ExpectedHead" }
    elseif ($Matches[3] -notlike "$demoData*") { Fail "check-db: DB at $($Matches[3]), not under $demoData (the hook's chdir)" }
    else { Ok "check-db: app db $($Matches[1]) == head $($Matches[2]) at $($Matches[3])" }

    # 2 — zeroconf's Cython modules are in the bundle
    $rc = Wait-Exit (Start-Headless $exe @("--fresh", "--check-lamp-imports")) 60000
    $line = Get-Content $log -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -Last 1
    if ($rc -eq 0 -and $line -eq "lamp imports ok") { Ok "lamp imports" } else { Fail "lamp imports: exit $rc, last log line '$line'" }

    # + — the window comes up (offscreen) and survives its start
    $before = @(Get-Content $log -Encoding UTF8).Count
    $env:QT_QPA_PLATFORM = "offscreen"
    $p = Start-Headless $exe @("--fresh")
    Remove-Item Env:\QT_QPA_PLATFORM
    $exited = $p.WaitForExit(25000)
    if (-not $exited) { Stop-Process -Id $p.Id -Force; Start-Sleep 1 }
    $runLog = @(Get-Content $log -Encoding UTF8 | Select-Object -Skip $before)
    if ($exited) { Fail "gui smoke: exited after <25 s with code $($p.ExitCode)" }
    elseif ($runLog -match "Traceback") { Fail "gui smoke: Traceback in the log"; $runLog | Select-Object -Last 15 }
    else { Ok "gui smoke: alive after 25 s offscreen, no Traceback ($($runLog.Count) log lines)" }
}

# --------------------------------------------------------------------------------------------- the server
if ($Server) {
    $exe = "$BuildDir\dist\server\SpectracsServer\SpectracsServer.exe"
    if (Port-Open 8091) {
        "  skip  server: 127.0.0.1:8091 already in use - refusing to test someone else's daemon (§8g.3)"
    } else {
        # 3 — a taken port is refused, not silently shared (D4: SO_REUSEADDR on Windows)
        $listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 8091)
        $listener.Start()
        try { $rc = Wait-Exit (Start-Headless $exe $null "$BuildDir\verify-server-refuse") 15000 } finally { $listener.Stop() }
        if ($rc -eq 1) { Ok "server refuses a taken 8091 (exit 1)" } else { Fail "server with 8091 taken: exit $rc, expected 1" }

        # 4 — the pair proof: the frozen server answers a login from the source client
        $p = Start-Headless $exe $null "$BuildDir\verify-server"
        $up = $false
        foreach ($i in 1..30) { if (Port-Open 8091) { $up = $true; break }; if ($p.HasExited) { break }; Start-Sleep 1 }
        try {
            if (-not $up) { Fail "server: 8091 not open after 30 s (exited: $($p.HasExited))" }
            else {
                $clientCwd = "$BuildDir\spectracsPy-verify-client"      # appdata names the client's data dir after it
                New-Item -ItemType Directory -Force $clientCwd | Out-Null
                Push-Location $clientCwd
                $src = "$BuildDir\src"
                $env:PYTHONPATH = "$src\spectracsPy;$src\spectracsPy-core;$src\spectracsPy-model;$src\spectracsPy-base;$src\spectracsPy-server"
                $ErrorActionPreference = "Continue"     # the client's warnings on stderr must not abort the script
                $out = & "$Venv\Scripts\python.exe" -c @"
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
r = SpectracsPyServerClient().login('masterUserExakta', 'masterUserExakta')
assert r['ok'] and 'MASTER_USER' in r['roles'], r
print('login ok - %s / %s / calibration %s' % (r['roles'][0], r.get('registeredSerial'),
      'present' if r.get('calibration') else 'MISSING (info only)'))
"@ 2>&1
                $loginRc = $LASTEXITCODE
                $ErrorActionPreference = "Stop"
                Remove-Item Env:\PYTHONPATH
                Pop-Location
                if ($loginRc -eq 0) { Ok "server: $($out | Select-Object -Last 1)" } else { Fail "server login: exit $loginRc"; $out | Select-Object -Last 10 }
            }
        } finally {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($failures.Count -gt 0) { "VERIFY FAILED ($($failures.Count)): $($failures -join '; ')"; exit 1 }
"VERIFY ok"
