param(
  [string]$Version = 'dev'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$distRoot = Join-Path $repoRoot 'release\dist'
$artifactRoot = Join-Path $repoRoot 'release\artifacts'
$pyiRoot = Join-Path $distRoot 'pyinstaller'
$portableRoot = Join-Path $distRoot 'windows-portable'
$launcherName = 'PokemonChampionsAssistantLauncher'
$archiveName = "pokemon-champions-assistant-portable-$Version-win64.zip"
$archivePath = Join-Path $artifactRoot $archiveName

New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
New-Item -ItemType Directory -Force -Path $artifactRoot | Out-Null

if (-not (Test-Path (Join-Path $repoRoot 'frontend\out\index.html'))) {
  throw '缺少 frontend/out/index.html，请先运行 build_frontend_static.ps1'
}

python -m pip install -e './backend'
python -m pip install pyinstaller imageio-ffmpeg

if (Test-Path $pyiRoot) { Remove-Item -Recurse -Force $pyiRoot }
if (Test-Path $portableRoot) { Remove-Item -Recurse -Force $portableRoot }
if (Test-Path $archivePath) { Remove-Item -Force $archivePath }

Push-Location $repoRoot
try {
  pyinstaller --noconfirm --clean --onedir --name $launcherName `
    --paths $repoRoot `
    --paths (Join-Path $repoRoot 'backend') `
    --hidden-import app.main `
    --hidden-import pygrabber.dshow_graph `
    --collect-all imageio_ffmpeg `
    --collect-submodules pygrabber `
    --add-data "backend;backend" `
    --add-data "data;data" `
    --add-data "frontend/out;frontend/out" `
    release/launcher/app.py
}
finally {
  Pop-Location
}

Move-Item -Force (Join-Path $repoRoot "dist\$launcherName") $portableRoot
if (Test-Path (Join-Path $repoRoot 'build')) { Remove-Item -Recurse -Force (Join-Path $repoRoot 'build') }
if (Test-Path (Join-Path $repoRoot 'dist')) { Remove-Item -Recurse -Force (Join-Path $repoRoot 'dist') }
if (Test-Path (Join-Path $repoRoot "$launcherName.spec")) { Remove-Item -Force (Join-Path $repoRoot "$launcherName.spec") }

Compress-Archive -Path (Join-Path $portableRoot '*') -DestinationPath $archivePath
Write-Host "Created portable artifact: $archivePath"
