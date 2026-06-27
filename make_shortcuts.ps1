# Creates Desktop and Start Menu shortcuts for the PhonePad server.
# Run once:  powershell -ExecutionPolicy Bypass -File make_shortcuts.ps1
# Optional auto-start on login:  add  -AutoStart

param([switch]$AutoStart)

$proj   = $PSScriptRoot
$server = Join-Path $proj 'server.py'
$ico    = Join-Path $proj 'phonepad.ico'

# Prefer pythonw (no console window); fall back to python's folder.
$pw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $pw) {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($py) { $pw = Join-Path (Split-Path $py) 'pythonw.exe' }
}
if (-not $pw -or -not (Test-Path $pw)) {
    Write-Error 'Could not find pythonw.exe. Install Python and add it to PATH.'
    exit 1
}

function New-PhonePadShortcut($dir) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $path = Join-Path $dir 'PhonePad Server.lnk'
    $ws   = New-Object -ComObject WScript.Shell
    $lnk  = $ws.CreateShortcut($path)
    $lnk.TargetPath       = $pw
    $lnk.Arguments        = "`"$server`""
    $lnk.WorkingDirectory = $proj
    if (Test-Path $ico) { $lnk.IconLocation = "$ico,0" }
    $lnk.Description      = 'PhonePad - use your phone as a touchpad'
    $lnk.WindowStyle      = 1
    $lnk.Save()
    Write-Host "Created: $path"
}

New-PhonePadShortcut ([Environment]::GetFolderPath('Desktop'))
New-PhonePadShortcut (Join-Path ([Environment]::GetFolderPath('Programs')) 'PhonePad')

if ($AutoStart) {
    New-PhonePadShortcut ([Environment]::GetFolderPath('Startup'))
    Write-Host 'Auto-start enabled (runs at login). To disable, delete the shortcut from:'
    Write-Host "  $([Environment]::GetFolderPath('Startup'))"
} else {
    Write-Host 'Tip: re-run with  -AutoStart  to also launch PhonePad at login.'
}
