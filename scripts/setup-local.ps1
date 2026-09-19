<#
.SYNOPSIS
One-time setup of CampusMate on this machine's PostgreSQL: the low-privilege role and the two
databases, the schema, the dataset, and queued ingestion of the 12 PDFs. Safe to run again.

.EXAMPLE
.\scripts\setup-local.ps1
.\scripts\setup-local.ps1 -AdminEmail admin@campusmate-demo.example   # also create the first admin
.\scripts\setup-local.ps1 -DemoAccounts   # also the demo logins admin/admin@123 and student/student@123

The postgres superuser's password is asked for once (or taken from $env:PGPASSWORD) and used
only for step 1. Everything else connects as the application role from .env.
#>
param(
    [int]$Port = 5432,
    [string]$DbHost = "localhost",
    [string]$SuperUser = "postgres",
    [string]$AdminEmail = "",
    [switch]$DemoAccounts
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Runs a native tool (psql, python). Only its exit code decides success: these tools log normal
# progress to stderr, which Windows PowerShell would otherwise treat as a fatal error.
function Invoke-Native([string]$what, [scriptblock]$command) {
    $ErrorActionPreference = "Continue"
    & $command
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)." }
}
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

# psql: on PATH, or in the standard install folder (newest PostgreSQL first).
$psql = (Get-Command psql -ErrorAction SilentlyContinue).Source
if (-not $psql) {
    $psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
        Sort-Object { [int]$_.Directory.Parent.Name } -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $psql) { throw "psql not found: install PostgreSQL, or add its bin folder to PATH." }
if (-not (Test-Path $python)) { throw "backend\.venv not found: create it first (README, Setup)." }

# The application role's password comes from .env, so the role and the app always agree.
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) { throw ".env not found: copy .env.example to .env and set DB_PASSWORD." }
$line = Select-String -Path $envFile -Pattern '^DB_PASSWORD=' | Select-Object -First 1
if (-not $line) { throw "DB_PASSWORD is not set in .env." }
$appPassword = ($line.Line -split '=', 2)[1]

# 1. Role and databases: the only step that needs the superuser.
$hadPassword = [bool]$env:PGPASSWORD
if (-not $hadPassword) {
    $secure = Read-Host "Password of the PostgreSQL superuser '$SuperUser'" -AsSecureString
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}
try {
    $exists = Invoke-Native "Connecting as $SuperUser (wrong password, or PostgreSQL not running on port ${Port}?)" {
        & $psql -h $DbHost -p $Port -U $SuperUser -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = 'campusmate_app'"
    }
    if ("$exists".Trim() -eq "1") {
        Write-Host "Role campusmate_app already exists: step 1 skipped."
    } else {
        Invoke-Native "Creating the role and the databases" {
            & $psql -h $DbHost -p $Port -U $SuperUser -d postgres -q -v app_password="$appPassword" `
                -f (Join-Path $backend "scripts\create_local_db.sql")
        }
        Write-Host "Created role campusmate_app and databases campusmate, campusmate_test."
    }
} finally {
    if (-not $hadPassword) { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
}

# 2-4. As the application role: schema, dataset, ingestion queue (and optionally an admin).
$env:DB_HOST = $DbHost
$env:DB_PORT = "$Port"
Push-Location $backend
try {
    Invoke-Native "Migrating the schema" { & $python -m alembic upgrade head }
    Invoke-Native "Loading the dataset" { & $python -m app.seed }
    Invoke-Native "Queueing the PDFs for ingestion" { & $python -m app.ingestion queue-missing }
    if ($AdminEmail) {
        Invoke-Native "Creating the admin account" {
            & $python -m app.accounts create --email $AdminEmail --role admin --name "Administrator"
        }
    }
    if ($DemoAccounts) {
        # Public passwords, for a local demo only: refused when APP_ENV=production, and such
        # accounts cannot log in there.
        Invoke-Native "Creating the demo accounts" { & $python -m app.accounts demo }
    }
} finally {
    Pop-Location
    Remove-Item Env:DB_HOST, Env:DB_PORT -ErrorAction SilentlyContinue
}
Write-Host "Done. Start CampusMate with .\scripts\start-local.ps1 (the API ingests the queued PDFs by itself)."
