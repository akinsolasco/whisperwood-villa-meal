[Setup]
AppId={{B74D9E5F-6D74-4F7A-8A2B-5EC6B1C29E44}
AppName=Whisperwood Villa Live Demo
AppVersion=2.0.6.1
AppPublisher=Whisperwood Villa
DefaultDirName={autopf}\Whisperwood Villa Live Demo
DefaultGroupName=Whisperwood Villa Live Demo
OutputDir=dist_installer
OutputBaseFilename=WhisperwoodVillaLiveDemoSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\WhisperwoodVillaLiveDemo.exe

[Files]
Source: "dist\WhisperwoodVillaLiveDemo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Whisperwood Villa Live Demo"; Filename: "{app}\WhisperwoodVillaLiveDemo.exe"; IconFilename: "{app}\WhisperwoodVillaLiveDemo.exe"
Name: "{autodesktop}\Whisperwood Villa Live Demo"; Filename: "{app}\WhisperwoodVillaLiveDemo.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\WhisperwoodVillaLiveDemo.exe"; Description: "Launch Whisperwood Villa Live Demo"; Flags: nowait postinstall skipifsilent
