[Setup]
AppId={{C4B9F4F2-9F0D-4F86-9E55-DE05B91CF001}
AppName=Whisperwood Villa Demo
AppVersion=2.1.13
AppPublisher=Enhanced Living Whisperwood
DefaultDirName={localappdata}\Programs\Whisperwood Villa Demo
DefaultGroupName=Whisperwood Villa Demo
OutputDir=dist_installer
OutputBaseFilename=WhisperwoodVillaDemoSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UsePreviousAppDir=no
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=assets\enhanced_living_whisperwood_icon.ico
UninstallDisplayIcon={app}\WhisperwoodVillaDemo.exe

[Files]
Source: "dist\WhisperwoodVillaDemo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "scripts\post_update_launcher.bat"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
Type: files; Name: "{autodesktop}\Whisperwood Villa Demo.lnk"
Type: files; Name: "{userdesktop}\Whisperwood Villa Demo.lnk"
Type: filesandordirs; Name: "{userprograms}\Whisperwood Villa Demo"

[Icons]
Name: "{group}\Whisperwood Villa Demo"; Filename: "{app}\WhisperwoodVillaDemo.exe"; IconFilename: "{app}\WhisperwoodVillaDemo.exe"
Name: "{userdesktop}\Whisperwood Villa Demo"; Filename: "{app}\WhisperwoodVillaDemo.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\post_update_launcher.bat"; Flags: runhidden nowait; Check: IsSilentInstall
Filename: "{app}\WhisperwoodVillaDemo.exe"; Description: "Launch Whisperwood Villa Demo"; Flags: nowait postinstall skipifsilent

[Code]
function IsSilentInstall: Boolean;
begin
  Result := WizardSilent();
end;
