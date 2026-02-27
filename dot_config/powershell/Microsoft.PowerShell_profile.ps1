# Load generated PowerShell shell functions and modules.
$configRoot = if ($env:XDG_CONFIG_HOME) {
    $env:XDG_CONFIG_HOME
} else {
    Join-Path $HOME ".config"
}

$pwshConfigDir = Join-Path $configRoot "powershell"
$functionsDir = Join-Path $pwshConfigDir "functions"
$modulesDir = Join-Path $pwshConfigDir "conf.d"

if (Test-Path $functionsDir -PathType Container) {
    Get-ChildItem -Path $functionsDir -Filter "*.ps1" -File |
        Sort-Object Name |
        ForEach-Object { . $_.FullName }
}

if (Test-Path $modulesDir -PathType Container) {
    Get-ChildItem -Path $modulesDir -Filter "*.ps1" -File |
        Sort-Object Name |
        ForEach-Object { . $_.FullName }
}

# Local overrides (not managed by chezmoi).
$localProfile = Join-Path $pwshConfigDir "profile.local.ps1"
if (Test-Path $localProfile -PathType Leaf) {
    . $localProfile
}

Remove-Variable configRoot, pwshConfigDir, functionsDir, modulesDir, localProfile -ErrorAction SilentlyContinue
