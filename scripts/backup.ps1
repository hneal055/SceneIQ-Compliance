<#
Simple backup script pattern:
- Dumps database to a timestamped file
- Compresses the dump
- Verifies checksum
- (Optional) Uploads to remote storage (placeholder)

Customize DB dump and upload commands for your environment.
#>
param(
    [string]$OutDir = "./backups",
    [string]$DbDumpCmd = "", # e.g. 'pg_dump --dbname=$env:DATABASE_URL'
    [switch]$Upload = $false
)

Set-StrictMode -Version Latest
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$dumpFile = Join-Path $OutDir "db-$timestamp.sql"
$archiveFile = Join-Path $OutDir "db-$timestamp.zip"

Write-Output "Starting backup: $timestamp"

if ($DbDumpCmd -ne "") {
    Write-Output "Running DB dump command..."
    iex "$DbDumpCmd > '$dumpFile'"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "DB dump command failed with exit code $LASTEXITCODE"
        exit 2
    }
}
else {
    # Placeholder sample content when no DB command supplied
    "-- sample dump --`n" | Out-File -FilePath $dumpFile -Encoding utf8
}

Write-Output "Compressing dump to $archiveFile"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory((Split-Path $dumpFile -Parent), $archiveFile)

# Compute checksum
$sha256 = Get-FileHash -Path $archiveFile -Algorithm SHA256
Write-Output "Checksum: $($sha256.Hash)"

if ($Upload) {
    Write-Output "Upload requested: implement upload step (AzCopy/CLI) here"
    # Example (commented): az storage blob upload --container-name backups --file $archiveFile --name (Split-Path $archiveFile -Leaf)
}

Write-Output "Backup complete: $archiveFile"
Write-Output "Checksum: $($sha256.Hash)"

exit 0
