$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop "LetsGoSurf.lnk"
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath = 'C:\Repos\LetsGoSurf\launch.bat'
$lnk.WorkingDirectory = 'C:\Repos\LetsGoSurf'
$lnk.IconLocation = 'C:\Repos\LetsGoSurf\letsgosurf.ico'
$lnk.Description = 'LetsGoSurf - Find waves near you'
$lnk.Save()
Write-Output "Shortcut created at: $lnkPath"
