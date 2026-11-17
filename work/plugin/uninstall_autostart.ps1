$taskName = "PW3D-Watcher"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$startup = [Environment]::GetFolderPath("Startup")
$link = Join-Path $startup "PW3D-Watcher.lnk"
if (Test-Path $link) {
    Remove-Item -LiteralPath $link -Force
    Write-Output "removed: $link"
} else {
    Write-Output "shortcut not present"
}
Write-Output "unregistered scheduled task: $taskName"
