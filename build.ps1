$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --onefile --windowed --name NightCityScorpion --icon assets/app.ico --add-data 'assets;assets' --exclude-module numpy --exclude-module PIL --exclude-module cv2 main.py
if ($LASTEXITCODE -ne 0) { throw 'Game build failed.' }
& '.\.venv\Scripts\python.exe' tools\copy_licenses.py
Copy-Item -LiteralPath 'README.md' -Destination 'dist\README.md' -Force
Copy-Item -LiteralPath 'TEST_REPORT.md' -Destination 'dist\TEST_REPORT.md' -Force
Compress-Archive -LiteralPath 'dist\NightCityScorpion.exe','dist\README.md','dist\TEST_REPORT.md','dist\THIRD_PARTY_LICENSES' -DestinationPath 'dist\NightCityScorpion-Windows.zip' -Force
