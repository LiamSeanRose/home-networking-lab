# Spin up the lab VMs defined in main.tf
Write-Host "Starting lab..." -ForegroundColor Cyan
terraform apply -auto-approve

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nLab is up." -ForegroundColor Green
    Write-Host "VM IPs:" -ForegroundColor Yellow
    terraform output vm_ips
} else {
    Write-Host "`nSomething went wrong. Check the output above." -ForegroundColor Red
}