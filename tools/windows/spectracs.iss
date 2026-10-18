; Spectracs app installer — docs/SPEC_windows_build.md §5b (W2.1). Compiled IN the build VM by setupInVm.ps1:
;   ISCC.exe /DLabel=<label> /DSourceDir=<dist\app\Spectracs> /DOutputDir=<dir> /DIconFile=<spectracs.ico> spectracs.iss
; Per user, no admin (§5b.1). Install over = the program folder is emptied first (§5b.2). The data folders under
; %USERPROFILE% are never touched (§5b.1) — the runtime hook puts them there, not into {app}.

#ifndef Label
  #define Label "dev"
#endif
#ifndef SourceDir
  #error "SourceDir must point at dist\app\Spectracs"
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

[Setup]
; ⛔ NEVER CHANGE the AppId: it is how Windows knows the next Setup is an update of this program (§5b.2).
AppId={{570849E7-33A6-4660-BC81-922E66D61950}
AppName=Spectracs
AppVersion={#Label}
AppVerName=Spectracs {#Label}
AppPublisher=Edwin Roth
VersionInfoVersion=1.0.0.0
VersionInfoTextVersion={#Label}
; per user: {autopf} is %LOCALAPPDATA%\Programs under PrivilegesRequired=lowest
PrivilegesRequired=lowest
DefaultDirName={autopf}\Spectracs
; ⛔ no folder choice: the install-over step empties {app} (§5b.2), so it must be OUR folder, never one a user picked
DisableDirPage=yes
DefaultGroupName=Spectracs
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=Spectracs-Setup-{#Label}
#ifdef IconFile
SetupIconFile={#IconFile}
#endif
UninstallDisplayIcon={app}\Spectracs.exe
UninstallDisplayName=Spectracs
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
; W2.3 (signing) is a switch, not a rewrite — §5b.3:
; SignTool=spectracs $f
; SignedUninstaller=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
en.DemoShortcut=Spectracs (demo, empty database)
de.DemoShortcut=Spectracs (Demo, leere Datenbank)
en.ReadMe=Spectracs - read me
de.ReadMe=Spectracs - Lies mich
en.DataKept=Your measurements were NOT removed.%n%nThey stay in %1\spectracsPy\ (the demo data in %1\spectracsPy-demo\, the log in %1\Spectracs\).%nDelete those folders yourself if you want them gone.
de.DataKept=Ihre Messungen wurden NICHT entfernt.%n%nSie bleiben in %1\spectracsPy\ (die Demo-Daten in %1\spectracsPy-demo\, das Protokoll in %1\Spectracs\).%nLöschen Sie diese Ordner selbst, wenn Sie sie nicht mehr brauchen.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Spectracs"; Filename: "{app}\Spectracs.exe"
Name: "{group}\{cm:DemoShortcut}"; Filename: "{app}\Spectracs.exe"; Parameters: "--fresh"
Name: "{group}\{cm:ReadMe}"; Filename: "{app}\START_HERE.txt"
Name: "{autodesktop}\Spectracs"; Filename: "{app}\Spectracs.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Spectracs.exe"; Description: "{cm:LaunchProgram,Spectracs}"; Flags: nowait postinstall skipifsilent unchecked

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  // §5b.2: a PyInstaller folder changes its file list between versions; a stale .pyd/.dll from the old one could be
  // loaded by the new. Guarded by the exe, so only OUR folder is ever emptied.
  if (CurStep = ssInstall) and FileExists(ExpandConstant('{app}\Spectracs.exe')) then
    DelTree(ExpandConstant('{app}\*'), False, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // §5b.1: a measurement archive is not a cache — say where it stays, never offer to delete it.
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent() then
    MsgBox(FmtMessage(CustomMessage('DataKept'), [GetEnv('USERPROFILE')]), mbInformation, MB_OK);
end;
