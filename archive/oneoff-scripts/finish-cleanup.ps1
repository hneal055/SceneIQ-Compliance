# ========================================
# Finish Nested Folder Cleanup
# Removes remaining locked files after they're closed
# ========================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Finish Cleanup - Nested Folders" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

$nestedPath = "Tax_Incentive_Compliance_Platform"

if (-not (Test-Path $nestedPath)) {
    Write-Host "✅ No nested folder found - already clean!`n" -ForegroundColor Green
    exit 0
}

# Count remaining files
$remainingFiles = Get-ChildItem $nestedPath -Recurse -File -ErrorAction SilentlyContinue
$fileCount = $remainingFiles.Count

Write-Host "Found $fileCount file(s) remaining in nested folder.`n" -ForegroundColor Yellow

if ($fileCount -gt 0) {
    Write-Host "Files that may be open in VS Code:" -ForegroundColor Cyan
    $remainingFiles | Select-Object -First 5 | ForEach-Object {
        Write-Host "  📄 $($_.Name)" -ForegroundColor Gray
    }
    if ($fileCount -gt 5) {
        Write-Host "  ... and $($fileCount - 5) more`n" -ForegroundColor DarkGray
    } else {
        Write-Host ""
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Options:" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "1. Close VS Code tabs from nested folders (recommended)" -ForegroundColor Yellow
Write-Host "   - Close any open tabs from nested folders"
Write-Host "   - Then run this script again`n" -ForegroundColor Gray

Write-Host "2. Force cleanup (may fail if files still locked)" -ForegroundColor Yellow
Write-Host "   - Will attempt to remove all files"
Write-Host "   - Some may fail if still in use`n" -ForegroundColor Gray

$response = Read-Host "Choose option [1=Close tabs first, 2=Force now, Q=Quit]"

if ($response -eq "2") {
    Write-Host "`nAttempting force cleanup...`n" -ForegroundColor Cyan
    
    # Try multiple times with delay
    for ($i = 1; $i -le 3; $i++) {
        Write-Host "  Attempt $i/3..." -NoNewline
        
        try {
            Get-ChildItem $nestedPath -Recurse -Force | Remove-Item -Force -Recurse -Confirm:$false -ErrorAction Stop
            Remove-Item $nestedPath -Force -Recurse -Confirm:$false -ErrorAction Stop
            
            if (-not (Test-Path $nestedPath)) {
                Write-Host " ✅" -ForegroundColor Green
                Write-Host "`n✅ SUCCESS! Nested folder removed.`n" -ForegroundColor Green
                exit 0
            } else {
                Write-Host " ⚠️ Partial" -ForegroundColor Yellow
            }
        } catch {
            Write-Host " ❌ Locked" -ForegroundColor Red
        }
        
        if ($i -lt 3) {
            Start-Sleep -Seconds 2
        }
    }
    
    Write-Host "`n⚠️ Some files still locked. Close VS Code tabs and try again.`n" -ForegroundColor Yellow
    
} elseif ($response -eq "1") {
    Write-Host "`n📋 Instructions:" -ForegroundColor Cyan
    Write-Host "  1. In VS Code, close all tabs from:" -ForegroundColor White
    Write-Host "     Tax_Incentive_Compliance_Platform/Tax_Incentive_Compliance_Platform/" -ForegroundColor Gray
    Write-Host "  2. Run this script again: .\finish-cleanup.ps1`n" -ForegroundColor White
} else {
    Write-Host "`nCleanup cancelled.`n" -ForegroundColor Yellow
}
