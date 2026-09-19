param(
    [string]$Config = "config/universal.json",
    [string]$Blender = $env:BLENDER_PATH,
    [switch]$PreviewOnly,
    [switch]$PrepareLibrary
)
$ErrorActionPreference = 'Stop'
if (-not $Blender) {
    $installed = Get-ChildItem 'C:\Program Files\Blender Foundation\Blender*\blender.exe' -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if ($installed) { $Blender = $installed.FullName }
    else { $Blender = (Get-Command blender -ErrorAction Stop).Source }
}
Push-Location $PSScriptRoot
try {
    $settings = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
    if ($settings.prepare_script -and ($PrepareLibrary -or -not (Test-Path -LiteralPath $settings.asset))) {
        & $Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python $settings.prepare_script
        if ($LASTEXITCODE -ne 0) { throw "Character preparation failed with exit code $LASTEXITCODE" }
    }
    $renderScript = if ($settings.render_script) { Join-Path $PSScriptRoot $settings.render_script } else { "$PSScriptRoot/scripts/render_sprites.py" }
    if ($PreviewOnly -and $settings.render_script) { throw 'PreviewOnly is not supported by this configured renderer.' }
    $arguments = @('--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', $renderScript, '--', '--config', $Config)
    if ($PreviewOnly) { $arguments += '--preview-only' }
    & $Blender @arguments
    if ($LASTEXITCODE -ne 0) { throw "Blender failed with exit code $LASTEXITCODE" }
} finally { Pop-Location }
