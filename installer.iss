[Setup]
AppId={{A4C5B8D4-7E5E-4E41-9D1B-1D3F5C1A9A11}
AppName=Whisperwood Villa
AppVersion=1.0.3
AppPublisher=Whisperwood Villa
DefaultDirName={autopf}\Whisperwood Villa
DefaultGroupName=Whisperwood Villa
OutputDir=dist_installer
OutputBaseFilename=WhisperwoodVillaSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\WhisperwoodVilla.exe

[Files]
Source: "dist\WhisperwoodVilla\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Whisperwood Villa"; Filename: "{app}\WhisperwoodVilla.exe"; IconFilename: "{app}\WhisperwoodVilla.exe"
Name: "{autodesktop}\Whisperwood Villa"; Filename: "{app}\WhisperwoodVilla.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\WhisperwoodVilla.exe"; Description: "Launch Whisperwood Villa"; Flags: nowait postinstall skipifsilent