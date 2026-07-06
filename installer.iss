[Setup]
AppId={{A4C5B8D4-7E5E-4E41-9D1B-1D3F5C1A9A11}
AppName=Enhanced Living Whisperwood
AppVersion=2.0.7
AppPublisher=Enhanced Living Whisperwood
DefaultDirName={autopf}\Enhanced Living Whisperwood
DefaultGroupName=Enhanced Living Whisperwood
OutputDir=dist_installer
OutputBaseFilename=WhisperwoodVillaSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\enhanced_living_whisperwood_icon.ico
UninstallDisplayIcon={app}\WhisperwoodVilla.exe

[Files]
Source: "dist\WhisperwoodVilla\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
Type: files; Name: "{autodesktop}\Whisperwood Villa.lnk"
Type: files; Name: "{commondesktop}\Whisperwood Villa.lnk"
Type: filesandordirs; Name: "{commonprograms}\Whisperwood Villa"
Type: filesandordirs; Name: "{userprograms}\Whisperwood Villa"

[Icons]
Name: "{group}\Enhanced Living Whisperwood"; Filename: "{app}\WhisperwoodVilla.exe"; IconFilename: "{app}\WhisperwoodVilla.exe"
Name: "{autodesktop}\Enhanced Living Whisperwood"; Filename: "{app}\WhisperwoodVilla.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\WhisperwoodVilla.exe"; Description: "Launch Enhanced Living Whisperwood"; Flags: nowait postinstall skipifsilent
