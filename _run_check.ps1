$ErrorActionPreference = "Stop"
$exe = "C:\console-control-main\dist\ConsoleControl.exe"
$out = "$env:TEMP\cc_stdout.log"
$err = "$env:TEMP\cc_stderr.log"
Remove-Item $out, $err -ErrorAction SilentlyContinue

$env:PYTHONUNBUFFERED = "1"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.RedirectStandardInput = $true
$psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1"

$proc = [System.Diagnostics.Process]::Start($psi)
Start-Sleep -Seconds 6

if (-not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "--- STDOUT ---"
Write-Host $proc.StandardOutput.ReadToEnd()
Write-Host "--- STDERR ---"
Write-Host $proc.StandardError.ReadToEnd()
