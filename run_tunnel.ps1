# Public hostname for the voice platform: https://kohler-care-demo.loca.lt -> localhost:8010
# Runs localtunnel in a loop so a dropped connection re-claims the same subdomain automatically.
Set-Location $PSScriptRoot
while ($true) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content logs\localtunnel.log "$ts starting localtunnel"
    npx --yes localtunnel --port 8010 --subdomain kohler-care-demo 2>&1 | ForEach-Object { Add-Content logs\localtunnel.log $_ }
    Add-Content logs\localtunnel.log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') localtunnel exited; restarting in 5 s"
    Start-Sleep 5
}
