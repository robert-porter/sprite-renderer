param([int]$Port = 8767, [string]$Config = 'config/universal.json')
$ErrorActionPreference = 'Stop'
$settings = Get-Content -LiteralPath (Join-Path $PSScriptRoot $Config) -Raw | ConvertFrom-Json
$outputPath = Join-Path $PSScriptRoot $settings.output
if (-not (Test-Path -LiteralPath (Join-Path $outputPath 'preview.html'))) {
    throw 'Render first with .\render.ps1.'
}
$python = Get-ChildItem 'C:\Program Files\Blender Foundation\Blender*\*\python\bin\python.exe' -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
if (-not $python) { throw 'Could not find Blender Python. Open the output preview.html directly in your browser.' }
Write-Host "Preview: http://127.0.0.1:$Port/preview.html (Ctrl+C stops the server)"
& $python.FullName -m http.server $Port --bind 127.0.0.1 --directory $outputPath
