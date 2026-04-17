Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$frontendDir = Join-Path $repoRoot 'frontend'

Push-Location $frontendDir
try {
  if (Test-Path 'out') {
    Remove-Item -Recurse -Force 'out'
  }

  npm ci --include=dev
  npm run build

  if (-not (Test-Path 'out\index.html')) {
    throw 'frontend static export 未生成 out\index.html'
  }
}
finally {
  Pop-Location
}
