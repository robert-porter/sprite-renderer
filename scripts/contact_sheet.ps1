param([string]$Output = 'output/universal')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$project = Split-Path $PSScriptRoot -Parent
$directory = Join-Path $project $Output
$manifest = Get-Content -LiteralPath (Join-Path $directory 'sprites.json') -Raw | ConvertFrom-Json
$clips = @($manifest.animations.PSObject.Properties)
$columns = 7
$cellWidth = 240
$cellHeight = 270
$bitmap = New-Object System.Drawing.Bitmap ($columns * $cellWidth), ([int][Math]::Ceiling($clips.Count / $columns) * $cellHeight)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$font = New-Object System.Drawing.Font 'Segoe UI', 10
$brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(225,235,245))
try {
    $graphics.Clear([System.Drawing.Color]::FromArgb(32,42,56))
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    for ($i = 0; $i -lt $clips.Count; $i++) {
        $name = $clips[$i].Name
        $clip = $clips[$i].Value
        $frame = [int][Math]::Floor($clip.frameCount / 2)
        $path = Join-Path $directory ("$name/{0:D4}.png" -f $frame)
        $source = [System.Drawing.Image]::FromFile($path)
        $x = ($i % $columns) * $cellWidth
        $y = [int][Math]::Floor($i / $columns) * $cellHeight
        try { $graphics.DrawImage($source, $x, $y, 240, 240) }
        finally { $source.Dispose() }
        $caption = $clip.label
        if ($clip.variantOf) { $caption = ($caption -split ' · ')[0] + ' · edited' }
        $graphics.DrawString($caption, $font, $brush, $x + 8, $y + 244)
    }
    $bitmap.Save((Join-Path $directory 'contact-sheet.png'), [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $brush.Dispose()
    $font.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}
