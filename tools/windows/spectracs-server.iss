; Spectracs SERVER installer — docs/SPEC_windows_build.md §5b (W2.1), the same way as the app (Edwin, 2026-10-18).
;   ISCC.exe /DLabel=<label> /DSourceDir=<dist\server\SpectracsServer> /DOutputDir=<dir> /DIconFile=<ico> spectracs-server.iss
; The local server is for development and demos; it listens on 127.0.0.1:8091 only ⇒ no firewall question.

#ifndef Label
  #define Label "dev"
#endif
#ifndef SourceDir
  #error "SourceDir must point at dist\server\SpectracsServer"
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

[Setup]
; ⛔ NEVER CHANGE the AppId (§5b.2).
AppId={{EFF8CDB8-6F33-48ED-B824-B9D9FD0FAEB5}
AppName=Spectracs Server
AppVersion={#Label}
AppVerName=Spectracs Server {#Label}
AppPublisher=Edwin Roth
VersionInfoVersion=1.0.0.0
VersionInfoTextVersion={#Label}
PrivilegesRequired=lowest
DefaultDirName={autopf}\Spectracs Server
DisableDirPage=yes
DefaultGroupName=Spectracs
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=Spectracs-Server-Setup-{#Label}
#ifdef IconFile
SetupIconFile={#IconFile}
#endif
UninstallDisplayIcon={app}\SpectracsServer.exe
UninstallDisplayName=Spectracs Server
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
; SignTool=spectracs $f
; SignedUninstaller=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
en.ServerShortcut=Spectracs Server (local)
de.ServerShortcut=Spectracs Server (lokal)
en.ReadMe=Spectracs Server - read me
de.ReadMe=Spectracs Server - Lies mich
en.DataKept=The server's database was NOT removed.%n%nIt stays in %1\spectracsPy-server\.%nDelete that folder yourself if you want it gone.
de.DataKept=Die Datenbank des Servers wurde NICHT entfernt.%n%nSie bleibt in %1\spectracsPy-server\.%nLöschen Sie diesen Ordner selbst, wenn Sie ihn nicht mehr brauchen.
en.StartServer=Start the server now
de.StartServer=Server jetzt starten

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{cm:ServerShortcut}"; Filename: "{app}\SpectracsServer.exe"
Name: "{group}\{cm:ReadMe}"; Filename: "{app}\START_HERE.txt"

[Run]
Filename: "{app}\SpectracsServer.exe"; Description: "{cm:StartServer}"; Flags: nowait postinstall skipifsilent unchecked

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssInstall) and FileExists(ExpandConstant('{app}\SpectracsServer.exe')) then
    DelTree(ExpandConstant('{app}\*'), False, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent() then
    MsgBox(FmtMessage(CustomMessage('DataKept'), [GetEnv('USERPROFILE')]), mbInformation, MB_OK);
end;
