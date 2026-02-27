# Windows default profile path bridge.
# Delegate to the XDG config profile so one profile definition works everywhere.
$configRoot = if ($env:XDG_CONFIG_HOME) {
    $env:XDG_CONFIG_HOME
} else {
    Join-Path $HOME ".config"
}

$xdgProfile = Join-Path (Join-Path $configRoot "powershell") "Microsoft.PowerShell_profile.ps1"
if (Test-Path $xdgProfile -PathType Leaf) {
    . $xdgProfile
}

Remove-Variable configRoot, xdgProfile -ErrorAction SilentlyContinue
