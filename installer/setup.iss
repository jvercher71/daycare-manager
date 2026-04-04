; ─────────────────────────────────────────────────────────────────────────────
; setup.iss — Inno Setup script for Daycare Manager v2
;
; Pre-requisites:
;   1. Build the PyInstaller bundle first (run build_windows.bat)
;   2. Install Inno Setup 6: https://jrsoftware.org/isinfo.php
;   3. Compile: ISCC.exe installer\setup.iss
; ─────────────────────────────────────────────────────────────────────────────

[Setup]
AppId={{A3F8C2D1-7E4B-4A1F-9C3D-2B5E8F7A6D0C}}
AppName=Daycare Manager v2
AppVersion=2.0.0
AppPublisher=Daycare Manager
AppPublisherURL=https://github.com/jvercher71/daycare-manager
DefaultDirName={autopf}\DaycareManagerV2
DefaultGroupName=Daycare Manager v2
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=DaycareManagerV2_Setup
SetupIconFile=installer\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; All compiled PyInstaller output
Source: "dist\DaycareManagerV2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Daycare Manager v2";        Dest: "{app}\DaycareManagerV2.exe"; IconFilename: "{app}\installer\icon.ico"
Name: "{group}\Uninstall Daycare Manager"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Daycare Manager v2"; Dest: "{app}\DaycareManagerV2.exe"; IconFilename: "{app}\installer\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\DaycareManagerV2.exe"; Description: "{cm:LaunchProgram,Daycare Manager v2}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
