@echo off
setlocal

set "APP_DIR=%~dp0"
set "APP_EXE=WhisperwoodVilla.exe"
set "APP_CHANNEL=main"

if exist "%APP_DIR%WhisperwoodVillaDemo.exe" (
    set "APP_EXE=WhisperwoodVillaDemo.exe"
    set "APP_CHANNEL=demo"
)

set "WW_POST_UPDATE_TARGET=%APP_DIR%%APP_EXE%"
set "WW_POST_UPDATE_CHANNEL=%APP_CHANNEL%"

rem Let the installer release files, then start exactly one per-user app copy.
timeout /t 2 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$target = $env:WW_POST_UPDATE_TARGET; $channel = $env:WW_POST_UPDATE_CHANNEL; $work = Split-Path -Parent $target; $exe = Split-Path -Leaf $target; $proc = [System.IO.Path]::GetFileNameWithoutExtension($exe); try { $shell = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'; $taskbar = Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'; $bases = @($desktop, $startMenu, $taskbar); foreach ($base in $bases) { if (Test-Path $base) { Get-ChildItem -LiteralPath $base -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object { $s = $shell.CreateShortcut($_.FullName); $old = [string]$s.TargetPath; $name = $_.Name; $isDemoShortcut = ($name -match 'Demo') -or ($old -match 'Demo'); $isWhisperwood = ($name -match 'Whisperwood|Enhanced Living') -or ($old -match 'Whisperwood|Enhanced Living'); $match = if ($channel -eq 'demo') { $isDemoShortcut } else { $isWhisperwood -and (-not $isDemoShortcut) }; if ($match) { $s.TargetPath = $target; $s.WorkingDirectory = $work; $s.IconLocation = $target + ',0'; $s.Save() } } } } } catch {}; Get-Process $proc -ErrorAction SilentlyContinue | Where-Object { $_.Path -and ($_.Path -ne $target) } | Stop-Process -Force -ErrorAction SilentlyContinue; $running = Get-Process $proc -ErrorAction SilentlyContinue | Where-Object { $_.Path -and ($_.Path -eq $target) } | Select-Object -First 1; if ((-not $running) -and (Test-Path $target)) { Start-Process $target }"

endlocal
