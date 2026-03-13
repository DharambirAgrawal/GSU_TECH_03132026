param(
    [ValidateSet('both', 'server', 'client', 'worker')]
    [string]$Mode = 'both'
)

$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $RootDir 'server'
$ClientDir = Join-Path $RootDir 'client'
$VenvDir = Join-Path $RootDir '.venv'
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
$CeleryExe = Join-Path $VenvDir 'Scripts\celery.exe'

function Ensure-PythonInstalled {
    if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw '[run.ps1] Python not found. Install Python 3 first.'
    }
}

function Ensure-Venv {
    Ensure-PythonInstalled

    if (-not (Test-Path $PythonExe)) {
        Write-Host "[run.ps1] Creating Python virtual environment at $VenvDir ..."
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv $VenvDir
        }
        else {
            & python -m venv $VenvDir
        }
    }
}

function Install-ServerDeps {
    Ensure-Venv
    Write-Host '[run.ps1] Installing server dependencies...'
    & $PythonExe -m pip install -r (Join-Path $ServerDir 'requirements.txt')
}

function Install-ClientDeps {
    Write-Host '[run.ps1] Installing client dependencies...'
    Push-Location $ClientDir
    try {
        & npm.cmd install
    }
    finally {
        Pop-Location
    }
}

function Run-Server {
    Install-ServerDeps
    Write-Host '[run.ps1] Starting Flask app on http://localhost:5000 ...'
    Push-Location $ServerDir
    try {
        & $PythonExe 'run.py'
    }
    finally {
        Pop-Location
    }
}

function Run-Worker {
    Install-ServerDeps
    Write-Host '[run.ps1] Starting Celery worker...'
    Push-Location $ServerDir
    try {
        & $CeleryExe -A celery_worker.celery_app worker --loglevel=info
    }
    finally {
        Pop-Location
    }
}

function Run-Client {
    Install-ClientDeps
    Write-Host '[run.ps1] Starting Vite client on http://localhost:5173 ...'
    Push-Location $ClientDir
    try {
        & npm.cmd run dev -- --host 0.0.0.0 --port 5173
    }
    finally {
        Pop-Location
    }
}

function Run-Both {
    Install-ServerDeps
    Install-ClientDeps

    Write-Host '[run.ps1] Starting Flask app on http://localhost:5000 ...'
    $serverProc = Start-Process -FilePath $PythonExe -ArgumentList 'run.py' -WorkingDirectory $ServerDir -PassThru

    Write-Host '[run.ps1] Starting Vite client on http://localhost:5173 ...'
    $clientProc = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev', '--', '--host', '0.0.0.0', '--port', '5173' -WorkingDirectory $ClientDir -PassThru

    try {
        Wait-Process -Id $serverProc.Id, $clientProc.Id
    }
    finally {
        Write-Host '[run.ps1] Shutting down processes...'
        foreach ($proc in @($serverProc, $clientProc)) {
            if ($null -ne $proc -and -not $proc.HasExited) {
                Stop-Process -Id $proc.Id -Force
            }
        }
    }
}

switch ($Mode) {
    'server' { Run-Server }
    'client' { Run-Client }
    'worker' { Run-Worker }
    'both' { Run-Both }
    default { throw "Usage: ./run.ps1 [server|client|worker|both]" }
}
