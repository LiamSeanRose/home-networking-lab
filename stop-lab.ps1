# Tear down all lab VMs
Write-Host "Destroying lab..." -ForegroundColor Cyan
terraform destroy -auto-approve

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nLab is down. Host resources freed." -ForegroundColor Green
} else {
    Write-Host "`nDestroy failed. Check the output above." -ForegroundColor Red
}