# ========================================
# Tax-Incentive Compliance Platform
# Self-Healing Startup Script
# ========================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tax-Incentive Compliance Platform" -ForegroundColor White
Write-Host "Startup Script" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan

# ========================================
# 1. CHECK PYTHON 3.12
# ========================================
Write-Host "`n[1/6] Checking Python 3.12..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.12\. (\d+)") {
        Write-Host "✓ Python 3.12 found:  $pythonVersion" -ForegroundColor Green
        $pythonCmd = "python"
    } else {
        # Try python3.12 explicitly
        $pythonVersion = python3.12 --version 2>&1
        if ($pythonVersion -match "Python 3\.12\.(\d+)") {
            Write-Host "✓ Python 3.12 found: $pythonVersion" -ForegroundColor Green
            $pythonCmd = "python3.12"
        } else {
            Write-Host "❌ Python 3.12 NOT found!" -ForegroundColor Red
            Write-Host "   Current: $pythonVersion" -ForegroundColor Yellow
            Write-Host "   Please install Python 3.12 from:  https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
    }
} catch {
    Write-Host "❌ Python not found in PATH!" -ForegroundColor Red
    exit 1
}

# ========================================
# 2. CHECK/CREATE CORRECT VENV
# ========================================
Write-Host "`n[2/6] Checking virtual environment..." -ForegroundColor Yellow

$venvPath = ".venv"
$needsRecreate = $false

# Check if venv exists
if (-not (Test-Path $venvPath)) {
    Write-Host "⚠ Virtual environment not found" -ForegroundColor Yellow
    $needsRecreate = $true
} else {
    # Check if venv is using Python 3.12
    $venvPython = & "$venvPath\Scripts\python. exe" --version 2>&1
    if ($venvPython -match "Python 3\.12\. (\d+)") {
        Write-Host "✓ Virtual environment is Python 3.12" -ForegroundColor Green
    } else {
        Write-Host "⚠ Virtual environment is wrong version:  $venvPython" -ForegroundColor Yellow
        Write-Host "  Expected: Python 3.12.x" -ForegroundColor Yellow
        $needsRecreate = $true
    }
}

# Recreate venv if needed
if ($needsRecreate) {
    Write-Host "`n  Recreating virtual environment with Python 3.12..." -ForegroundColor Cyan
    
    # Remove old venv if it exists
    if (Test-Path $venvPath) {
        Write-Host "  Removing old venv..." -ForegroundColor Gray
        Remove-Item -Path $venvPath -Recurse -Force
    }
    
    # Create new venv
    Write-Host "  Creating new venv..." -ForegroundColor Gray
    & $pythonCmd -m venv $venvPath
    
    if (Test-Path "$venvPath\Scripts\python. exe") {
        $newVersion = & "$venvPath\Scripts\python.exe" --version
        Write-Host "✓ Virtual environment created:  $newVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }
}

# ========================================
# 3. ACTIVATE VENV
# ========================================
Write-Host "`n[3/6] Activating virtual environment..." -ForegroundColor Yellow

try {
    & "$venvPath\Scripts\Activate.ps1"
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to activate virtual environment!" -ForegroundColor Red
    Write-Host "   Try running: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    exit 1
}

# ========================================
# 4. INSTALL/UPDATE DEPENDENCIES
# ========================================
Write-Host "`n[4/6] Checking dependencies..." -ForegroundColor Yellow

if (Test-Path "requirements.txt") {
    # Quick check if packages are installed
    $pipList = pip list 2>&1
    if ($pipList -notmatch "fastapi") {
        Write-Host "  Installing dependencies (first time)..." -ForegroundColor Cyan
        pip install -r requirements.txt --quiet
        Write-Host "✓ Dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "✓ Dependencies already installed" -ForegroundColor Green
        Write-Host "  (Run 'pip install -r requirements.txt' manually to update)" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ requirements.txt not found" -ForegroundColor Yellow
}

# Generate Prisma client if needed
if (Test-Path "prisma") {
    Write-Host "  Generating Prisma client..." -ForegroundColor Gray
    python -m prisma generate 2>&1 | Out-Null
    Write-Host "✓ Prisma client ready" -ForegroundColor Green
}

# ========================================
# 5. START DOCKER & POSTGRESQL
# ========================================
Write-Host "`n[5/6] Starting Docker services..." -ForegroundColor Yellow

# Check Docker is running
try {
    docker version 2>$null 1>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Desktop is not running!" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop and run this script again" -ForegroundColor Yellow
    exit 1
}

# Start PostgreSQL container
$containerRunning = docker ps --filter "name=tax-incentive-db" --format "{{.Names}}" 2>$null

if ($containerRunning -eq "tax-incentive-db") {
    Write-Host "✓ PostgreSQL container already running" -ForegroundColor Green
} else {
    # Try to start existing container
    docker start tax-incentive-db 2>$null | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        # Container doesn't exist, create it
        Write-Host "  Creating PostgreSQL container..." -ForegroundColor Cyan
        docker-compose up -d
    } else {
        Write-Host "✓ PostgreSQL container started" -ForegroundColor Green
    }
    
    # Wait for PostgreSQL to be ready
    Write-Host "  Waiting for PostgreSQL..." -ForegroundColor Gray
    $maxAttempts = 20
    $attempt = 0
    
    do {
        $attempt++
        Start-Sleep -Seconds 2
        $isReady = docker exec tax-incentive-db pg_isready -U postgres 2>$null
        if ($isReady -match "accepting connections") {
            Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green
            break
        }
        Write-Host "." -NoNewline
    } while ($attempt -lt $maxAttempts)
    
    if ($attempt -ge $maxAttempts) {
        Write-Host "`n❌ PostgreSQL failed to start" -ForegroundColor Red
        Write-Host "   Check logs: docker logs tax-incentive-db" -ForegroundColor Yellow
        exit 1
    }
}

# ========================================
# 6. CREATE . ENV IF MISSING
# ========================================
Write-Host "`n[6/6] Checking configuration..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    if (Test-Path ". env.example") {
        Write-Host "  Creating .env from .env.example..." -ForegroundColor Cyan
        Copy-Item .env.example .env
        Write-Host "✓ .env file created" -ForegroundColor Green
    } else {
        Write-Host "⚠ No .env or .env.example found" -ForegroundColor Yellow
    }
} else {
    Write-Host "✓ .env file exists" -ForegroundColor Green
}

# ========================================
# START APPLICATION
# ========================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✓ All Systems Ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nStarting FastAPI server..." -ForegroundColor Yellow
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Health:    http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host "========================================`n" -ForegroundColor Cyan

# Start the server
python -m uvicorn src.main:app --reload