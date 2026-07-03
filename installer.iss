[Setup]
AppId={{C4B9F4F2-9F0D-4F86-9E55-DE05B91CF001}
AppName=Whisperwood Villa Demo
AppVersion=2.0.5.11
AppPublisher=Whisperwood Villa
DefaultDirName={autopf}\Whisperwood Villa Demo
DefaultGroupName=Whisperwood Villa Demo
OutputDir=dist_installer
OutputBaseFilename=WhisperwoodVillaDemoSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\WhisperwoodVillaDemo.exe

[Files]
Source: "dist\WhisperwoodVillaDemo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Whisperwood Villa Demo"; Filename: "{app}\WhisperwoodVillaDemo.exe"; IconFilename: "{app}\WhisperwoodVillaDemo.exe"
Name: "{autodesktop}\Whisperwood Villa Demo"; Filename: "{app}\WhisperwoodVillaDemo.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\WhisperwoodVillaDemo.exe"; Description: "Launch Whisperwood Villa Demo"; Flags: nowait postinstall skipifsilent
