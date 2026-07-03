[Setup]
AppId={{B74D9E5F-6D74-4F7A-8A2B-5EC6B1C29E44}
AppName=Enhanced Living Whisperwood Live Demo
AppVersion=2.0.6.2
AppPublisher=Enhanced Living Whisperwood
DefaultDirName={autopf}\Enhanced Living Whisperwood Live Demo
DefaultGroupName=Enhanced Living Whisperwood Live Demo
OutputDir=dist_installer
OutputBaseFilename=EnhancedLivingWhisperwoodLiveDemoSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\enhanced_living_whisperwood_icon.ico
UninstallDisplayIcon={app}\EnhancedLivingWhisperwoodLiveDemo.exe

[Files]
Source: "dist\EnhancedLivingWhisperwoodLiveDemo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Enhanced Living Whisperwood Live Demo"; Filename: "{app}\EnhancedLivingWhisperwoodLiveDemo.exe"; IconFilename: "{app}\EnhancedLivingWhisperwoodLiveDemo.exe"
Name: "{autodesktop}\Enhanced Living Whisperwood Live Demo"; Filename: "{app}\EnhancedLivingWhisperwoodLiveDemo.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\EnhancedLivingWhisperwoodLiveDemo.exe"; Description: "Launch Enhanced Living Whisperwood Live Demo"; Flags: nowait postinstall skipifsilent
