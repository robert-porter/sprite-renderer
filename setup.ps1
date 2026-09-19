$ErrorActionPreference = 'Stop'
$packs = @(
    @{ Name = 'universal-base-characters'; Upload = '15861669'; Hash = 'FDBF1804C90DFC1EA03E992BFF7DA2DFD1A79318E13270A660180F9308455F40'; Folder = 'Universal Base Characters[Standard]' },
    @{ Name = 'universal-animation-library'; Upload = '17958403'; Hash = 'CC73FC4E495B82958207316596317A3F40B9FA38065BDE1027937452DA537724'; Folder = 'Universal Animation Library[Standard]' }
)
$directory = Join-Path $PSScriptRoot 'assets/quaternius/universal'
New-Item -ItemType Directory -Force $directory | Out-Null
foreach ($pack in $packs) {
    $archive = Join-Path $directory "$($pack.Name).zip"
    if (-not (Test-Path -LiteralPath $archive)) {
        $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
        $url = "https://quaternius.itch.io/$($pack.Name)"
        $page = (Invoke-WebRequest -Uri $url -WebSession $session -UseBasicParsing).Content
        $token = [regex]::Match($page, 'name="csrf_token" value="([^"]+)"').Groups[1].Value
        if (-not $token) { throw 'Could not read the itch.io free download form.' }
        $download = Invoke-RestMethod -Method Post -Uri "$url/file/$($pack.Upload)" -WebSession $session -Body @{ csrf_token = $token }
        if (-not $download.url) { throw 'No free download URL returned; check the official pack page.' }
        $temporary = "$archive.download"
        Invoke-WebRequest -Uri $download.url -OutFile $temporary
        if ((Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash -ne $pack.Hash) {
            throw "The published pack changed. Inspect $temporary before updating its expected hash."
        }
        Move-Item -LiteralPath $temporary -Destination $archive
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $pack.Hash) {
        throw "Existing archive differs from the verified download and was preserved: $archive"
    }
    $destination = Join-Path $directory $pack.Name
    if (-not (Test-Path -LiteralPath (Join-Path $destination $pack.Folder))) {
        Expand-Archive -LiteralPath $archive -DestinationPath $destination
    }
}
Write-Host 'Universal Base Characters and Universal Animation Library are installed. Run .\render.ps1 next.'
