# ========================================
# Repository Cleanup Script
# SceneIQ - Tax Incentive Compliance Platform
# ========================================

param(
    [switch]$DryRun,
    [switch]$Force
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Repository Cleanup Script" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No files will be deleted`n" -ForegroundColor Yellow
}

$rootPath = $PSScriptRoot
$issues = @()
$actions = @()

# ========================================
# 1. CHECK FOR NESTED FOLDERS
# ========================================
Write-Host "[1/5] Checking for nested folders..." -ForegroundColor Yellow

$nestedFolder = Join-Path $rootPath "Tax_Incentive_Compliance_Platform"
if (Test-Path $nestedFolder) {
    $size = (Get-ChildItem $nestedFolder -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    $issues += "🔴 CRITICAL: Nested folder found ($([math]::Round($size, 2)) MB)"
    $actions += @{
        Type = "Delete"
        Path = $nestedFolder
        Priority = "HIGH"
        Reason = "Nested duplicate folder"
    }
    Write-Host "  ❌ Found: Tax_Incentive_Compliance_Platform/ ($([math]::Round($size, 2)) MB)" -ForegroundColor Red
} else {
    Write-Host "  ✅ No nested folders found" -ForegroundColor Green
}

# ========================================
# 2. CHECK FOR BACKUP FOLDERS
# ========================================
Write-Host "`n[2/5] Checking for backup folders..." -ForegroundColor Yellow

$backupFolders = Get-ChildItem -Path $rootPath -Directory -Filter "backup_*"
if ($backupFolders.Count -gt 0) {
    foreach ($folder in $backupFolders) {
        $size = (Get-ChildItem $folder.FullName -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        $issues += "⚠️  Backup folder: $($folder.Name) ($([math]::Round($size, 2)) MB)"
        $actions += @{
            Type = "Delete"
            Path = $folder.FullName
            Priority = "MEDIUM"
            Reason = "Backup folder (should not be in git)"
        }
        Write-Host "  ⚠️  Found: $($folder.Name) ($([math]::Round($size, 2)) MB)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✅ No backup folders found" -ForegroundColor Green
}

# ========================================
# 3. CHECK FOR LEGACY FILES
# ========================================
Write-Host "`n[3/5] Checking for legacy files..." -ForegroundColor Yellow

$legacyPatterns = @("legacy_*", "*.backup", "*.bak", "*_old.*")
$legacyFiles = @()

foreach ($pattern in $legacyPatterns) {
    $found = Get-ChildItem -Path $rootPath -File -Filter $pattern -ErrorAction SilentlyContinue
    $legacyFiles += $found
}

if ($legacyFiles.Count -gt 0) {
    foreach ($file in $legacyFiles) {
        $issues += "⚠️  Legacy file: $($file.Name)"
        $actions += @{
            Type = "Archive"
            Path = $file.FullName
            Priority = "MEDIUM"
            Reason = "Legacy/backup file"
        }
        Write-Host "  ⚠️  Found: $($file.Name)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✅ No legacy files found" -ForegroundColor Green
}

# ========================================
# 4. CHECK FOR DUPLICATE ENV FILES
# ========================================
Write-Host "`n[4/5] Checking environment files..." -ForegroundColor Yellow

$envFiles = Get-ChildItem -Path $rootPath -File -Filter ".env*"
$problematicEnvFiles = $envFiles | Where-Object { $_.Name -eq ".env.txt" }

if ($problematicEnvFiles) {
    foreach ($file in $problematicEnvFiles) {
        $issues += "⚠️  Duplicate env file: $($file.Name)"
        $actions += @{
            Type = "Delete"
            Path = $file.FullName
            Priority = "LOW"
            Reason = "Duplicate/redundant env file"
        }
        Write-Host "  ⚠️  Found: $($file.Name)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✅ Environment files look good" -ForegroundColor Green
}

# ========================================
# 5. CHECK .GITIGNORE
# ========================================
Write-Host "`n[5/5] Checking .gitignore..." -ForegroundColor Yellow

$gitignorePath = Join-Path $rootPath ".gitignore"
$gitignoreNeeds = @()

if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw
    
    if ($gitignoreContent -notmatch "backup_\*") {
        $gitignoreNeeds += "backup_*/"
    }
    if ($gitignoreContent -notmatch "\*\.backup") {
        $gitignoreNeeds += "*.backup"
    }
    if ($gitignoreContent -notmatch "\*\.bak") {
        $gitignoreNeeds += "*.bak"
    }
    
    if ($gitignoreNeeds.Count -gt 0) {
        Write-Host "  ⚠️  Missing entries: $($gitignoreNeeds -join ', ')" -ForegroundColor Yellow
        $issues += "⚠️  .gitignore missing backup exclusions"
    } else {
        Write-Host "  ✅ .gitignore looks good" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠️  .gitignore not found" -ForegroundColor Yellow
    $issues += "⚠️  .gitignore file missing"
}

# ========================================
# SUMMARY
# ========================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

if ($issues.Count -eq 0) {
    Write-Host "✅ Repository is clean! No issues found.`n" -ForegroundColor Green
    exit 0
}

Write-Host "Found $($issues.Count) issue(s):`n" -ForegroundColor Yellow
foreach ($issue in $issues) {
    Write-Host "  $issue"
}

Write-Host "`nProposed actions: $($actions.Count)`n" -ForegroundColor Cyan

# Group by priority
$highPriority = $actions | Where-Object { $_.Priority -eq "HIGH" }
$mediumPriority = $actions | Where-Object { $_.Priority -eq "MEDIUM" }
$lowPriority = $actions | Where-Object { $_.Priority -eq "LOW" }

if ($highPriority) {
    Write-Host "🔴 HIGH PRIORITY ($($highPriority.Count)):" -ForegroundColor Red
    foreach ($action in $highPriority) {
        Write-Host "  • [$($action.Type)] $($action.Path)" -ForegroundColor Gray
        Write-Host "    Reason: $($action.Reason)`n" -ForegroundColor DarkGray
    }
}

if ($mediumPriority) {
    Write-Host "⚠️  MEDIUM PRIORITY ($($mediumPriority.Count)):" -ForegroundColor Yellow
    foreach ($action in $mediumPriority) {
        Write-Host "  • [$($action.Type)] $(Split-Path $action.Path -Leaf)" -ForegroundColor Gray
    }
    Write-Host ""
}

if ($lowPriority) {
    Write-Host "💡 LOW PRIORITY ($($lowPriority.Count)):" -ForegroundColor Cyan
    foreach ($action in $lowPriority) {
        Write-Host "  • [$($action.Type)] $(Split-Path $action.Path -Leaf)" -ForegroundColor Gray
    }
    Write-Host ""
}

# ========================================
# EXECUTE CLEANUP
# ========================================
if ($DryRun) {
    Write-Host "DRY RUN complete. Run without -DryRun to execute cleanup.`n" -ForegroundColor Yellow
    exit 0
}

if (-not $Force) {
    Write-Host "========================================" -ForegroundColor Cyan
    $response = Read-Host "`nProceed with cleanup? This will delete/archive files (Y/N)"
    if ($response -ne 'Y' -and $response -ne 'y') {
        Write-Host "Cleanup cancelled.`n" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "EXECUTING CLEANUP" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

# Create archive folder for files to preserve
$archivePath = Join-Path $rootPath "archive_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

foreach ($action in $actions) {
    $itemName = Split-Path $action.Path -Leaf
    
    try {
        if ($action.Type -eq "Delete") {
            Write-Host "  Deleting: $itemName..." -NoNewline
            Remove-Item -Path $action.Path -Recurse -Force
            Write-Host " ✅" -ForegroundColor Green
        }
        elseif ($action.Type -eq "Archive") {
            if (-not (Test-Path $archivePath)) {
                New-Item -Type Directory -Path $archivePath -Force | Out-Null
            }
            Write-Host "  Archiving: $itemName..." -NoNewline
            Move-Item -Path $action.Path -Destination $archivePath -Force
            Write-Host " ✅" -ForegroundColor Green
        }
    }
    catch {
        Write-Host " ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Update .gitignore if needed
if ($gitignoreNeeds.Count -gt 0) {
    Write-Host "`n  Updating .gitignore..." -NoNewline
    try {
        $gitignoreContent = Get-Content $gitignorePath -Raw
        $gitignoreContent += "`n# Cleanup script additions`n"
        foreach ($entry in $gitignoreNeeds) {
            $gitignoreContent += "$entry`n"
        }
        Set-Content -Path $gitignorePath -Value $gitignoreContent
        Write-Host " ✅" -ForegroundColor Green
    }
    catch {
        Write-Host " ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

if (Test-Path $archivePath) {
    Write-Host "📁 Archived files saved to: $archivePath`n" -ForegroundColor Cyan
}

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review the changes" -ForegroundColor White
Write-Host "  2. Run: git status" -ForegroundColor White
Write-Host "  3. Test the application: .\start.ps1" -ForegroundColor White
Write-Host "  4. Commit the cleanup: git commit -am 'Clean up repository structure'`n" -ForegroundColor White
