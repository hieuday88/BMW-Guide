# Creates "BMW Guide" shortcuts on the Desktop and Start Menu (hotkey Ctrl+Alt+B) that launch the overlay.
$app = Join-Path $PSScriptRoot 'bmw_guide.pyw'
$icon = Join-Path $PSScriptRoot 'assets\BMW.ico'
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($py) { $pythonw = Join-Path (Split-Path $py) 'pythonw.exe' }
}
if (-not $pythonw -or -not (Test-Path $pythonw)) {
    Write-Error 'Python 3 (pythonw.exe) not found. Install Python from https://www.python.org/downloads/ first.'
    exit 1
}
$shell = New-Object -ComObject WScript.Shell
$targets = @(
    (Join-Path ([Environment]::GetFolderPath('Desktop')) 'BMW Guide.lnk'),
    (Join-Path ([Environment]::GetFolderPath('Programs')) 'BMW Guide.lnk')
)
foreach ($path in $targets) {
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath = $pythonw
    $lnk.Arguments = "`"$app`""
    $lnk.WorkingDirectory = $PSScriptRoot
    $lnk.IconLocation = $icon
    $lnk.Description = 'Black Myth: Wukong checklist overlay'
    if ($path -like '*Programs*') { $lnk.Hotkey = 'Ctrl+Alt+B' }
    $lnk.Save()
    Write-Output "Created $path"
}
