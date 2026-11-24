$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python -m pip install pyinstaller requests
& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name EnhancedLivingCareNotebook `
    --icon (Join-Path $root "assets\enhanced_living_whisperwood_icon.ico") `
    --add-data "$(Join-Path $root 'assets\enhanced_living_whisperwood_icon.ico');assets" `
    (Join-Path $root "tools\care_notebook_client.py")

$artifactDir = Join-Path $root "_build\care_notebook_client"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$exe = Join-Path $root "dist\EnhancedLivingCareNotebook.exe"
Copy-Item $exe (Join-Path $artifactDir "EnhancedLivingCareNotebook.exe") -Force
Copy-Item (Join-Path $root "docs\CARE_NOTEBOOK_CLIENT.md") (Join-Path $artifactDir "README.md") -Force

$zip = Join-Path $artifactDir "EnhancedLivingCareNotebook-demo-v0.1.2.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $artifactDir "EnhancedLivingCareNotebook.exe"), (Join-Path $artifactDir "README.md") -DestinationPath $zip
Write-Host "Built: $exe"
Write-Host "Packaged: $zip"
