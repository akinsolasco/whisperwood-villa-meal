@echo off
setlocal

set "APP_NAME=Enhanced Living Whisperwood"
set "APP_EXE=WhisperwoodVilla.exe"
set "TARGET=%LOCALAPPDATA%\Programs\%APP_NAME%\%APP_EXE%"

rem Let the installer release files, then start exactly one per-user app copy.
timeout /t 2 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$target = Join-Path $env:LOCALAPPDATA 'Programs\Enhanced Living Whisperwood\WhisperwoodVilla.exe'; $work = Split-Path -Parent $target; try { $shell = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'; $taskbar = Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'; $bases = @($desktop, $startMenu, $taskbar); foreach ($base in $bases) { if (Test-Path $base) { Get-ChildItem -LiteralPath $base -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object { $s = $shell.CreateShortcut($_.FullName); $old = [string]$s.TargetPath; $name = $_.Name; $match = (($name -match 'Whisperwood|Enhanced Living') -or ($old -match 'Whisperwood|Enhanced Living')) -and ($name -notmatch 'Demo') -and ($old -notmatch 'Demo'); if ($match) { $s.TargetPath = $target; $s.WorkingDirectory = $work; $s.IconLocation = $target + ',0'; $s.Save() } } } } } catch {}; Get-Process WhisperwoodVilla -ErrorAction SilentlyContinue | Where-Object { $_.Path -and ($_.Path -ne $target) } | Stop-Process -Force -ErrorAction SilentlyContinue; $running = Get-Process WhisperwoodVilla -ErrorAction SilentlyContinue | Where-Object { $_.Path -and ($_.Path -eq $target) } | Select-Object -First 1; if ((-not $running) -and (Test-Path $target)) { Start-Process $target }"

endlocal
