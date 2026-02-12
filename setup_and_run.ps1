# Setup y ejecución de isoReport (Streamlit)
# Instala Python si no está y luego arranca la app.

$ErrorActionPreference = "Stop"
$pythonUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
$installerPath = "$env:TEMP\python-3.12.10-amd64.exe"
$pythonPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:ProgramFiles\Python312\python.exe",
    "$env:ProgramFiles(x86)\Python312\python.exe"
)

function Find-Python {
    # PATH actual
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    foreach ($p in $pythonPaths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$pythonExe = Find-Python

if (-not $pythonExe) {
    Write-Host "Python no encontrado. Descargando e instalando Python 3.12..." -ForegroundColor Yellow
    if (-not (Test-Path $installerPath)) {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
    }
    Write-Host "Ejecutando instalador (puede aparecer UAC - acepta una vez)..." -ForegroundColor Yellow
    Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1" -Wait -Verb RunAs
    # Refrescar PATH para esta sesión
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $pythonExe = Find-Python
    if (-not $pythonExe) {
        Write-Host "ERROR: Tras instalar, Python no se encontró. Cierra esta terminal, abre una nueva y ejecuta:" -ForegroundColor Red
        Write-Host "  cd `"$PSScriptRoot`"" -ForegroundColor Cyan
        Write-Host "  python -m pip install -r requirements.txt" -ForegroundColor Cyan
        Write-Host "  python -m streamlit run app.py" -ForegroundColor Cyan
        exit 1
    }
}

Write-Host "Python: $pythonExe" -ForegroundColor Green
& $pythonExe --version

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Instalando dependencias..." -ForegroundColor Yellow
& $pythonExe -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error instalando dependencias." -ForegroundColor Red
    exit 1
}

Write-Host "Iniciando Streamlit..." -ForegroundColor Green
& $pythonExe -m streamlit run app.py
