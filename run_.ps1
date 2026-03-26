[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendUrl = "http://127.0.0.1:8000"
$StateDir = Join-Path $Root ".venomai-launcher"

function Write-Step {
    param([string]$Message)
    Write-Host $Message
}

function Get-FrontendConfig {
    $frontendDir = Join-Path $Root "frontend"

    if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
        throw "The frontend package.json was not found in frontend\."
    }

    return @{
        Key  = "frontend"
        Dir  = $frontendDir
        Port = 4500
        Url  = "http://localhost:4500"
    }
}

function Get-PythonCommand {
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return @{
            Exe  = $venvPython
            Args = @()
        }
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return @{
            Exe  = $pyCmd.Source
            Args = @("-3")
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return @{
            Exe  = $pythonCmd.Source
            Args = @()
        }
    }

    throw "Python 3 was not found. Install Python 3.12+ or create .venv first."
}

function Get-NpmCommand {
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npmCmd) {
        return $npmCmd.Source
    }

    $npmPlain = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmPlain) {
        return $npmPlain.Source
    }

    throw "npm is not available in PATH. Install Node.js and try again."
}

function Invoke-External {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [switch]$Quiet
    )

    Push-Location $WorkingDirectory
    try {
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        if (-not $Quiet -and $null -ne $output) {
            $output | Out-Host
        }
        return $exitCode
    }
    finally {
        Pop-Location
    }
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return $true
            }
        }
        catch {
        }
        Start-Sleep -Seconds 1
    }

    return $false
}

function Get-CombinedHash {
    param([string[]]$Paths)

    $parts = foreach ($path in $Paths) {
        if (Test-Path $path) {
            "{0}:{1}" -f (Split-Path $path -Leaf), (Get-FileHash -Path $path -Algorithm SHA256).Hash
        }
    }

    return [string]::Join("|", $parts)
}

function Write-Stamp {
    param(
        [string]$StampPath,
        [string]$HashValue
    )

    New-Item -ItemType Directory -Force (Split-Path -Parent $StampPath) | Out-Null
    Set-Content -LiteralPath $StampPath -Value $HashValue -NoNewline
}

function Quote-CmdToken {
    param([string]$Token)

    if ($Token -match '^[A-Za-z0-9_:\.\-\\/]+$') {
        return $Token
    }

    return '"' + ($Token -replace '"', '""') + '"'
}

function Join-CmdTokens {
    param([string[]]$Tokens)

    return ($Tokens | ForEach-Object { Quote-CmdToken $_ }) -join " "
}

function Stop-ExistingVenomAIInstances {
    param([string]$ProjectRoot)

    Write-Step "[1/4] Stopping existing VenomAI instances..."

    & taskkill /FI "WINDOWTITLE eq VenomAI Backend" /T /F *> $null
    & taskkill /FI "WINDOWTITLE eq VenomAI Frontend" /T /F *> $null

    $rootLower = $ProjectRoot.ToLowerInvariant()
    $ports = @(8000, 4500, 3000)

    foreach ($port in $ports) {
        $connections = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
        foreach ($connection in $connections) {
            $processId = $connection.OwningProcess
            if (-not $processId) {
                continue
            }

            $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
            if (-not $process) {
                continue
            }

            $commandLine = [string]$process.CommandLine
            $executablePath = [string]$process.ExecutablePath
            $shouldStop = $false

            if ($commandLine.ToLowerInvariant().Contains($rootLower) -or $executablePath.ToLowerInvariant().Contains($rootLower)) {
                $shouldStop = $true
            }

            if ($port -eq 8000 -and $commandLine -match "uvicorn") {
                $shouldStop = $true
            }

            if (($port -eq 4500 -or $port -eq 3000) -and $commandLine -match "next") {
                $shouldStop = $true
            }

            if ($shouldStop) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        }
    }

    Start-Sleep -Seconds 2
    Write-Host "       Existing launcher-owned processes were stopped."
}

function Assert-PortClear {
    param([int]$Port)

    $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($connection) {
        throw "Port $Port is still busy after cleanup. Close the conflicting process, then run this launcher again."
    }
}

function Test-PortListening {
    param([int]$Port)

    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Get-BackendStartMode {
    if (-not (Test-PortListening -Port 8000)) {
        return "start"
    }

    if (Wait-HttpReady -Url "$BackendUrl/api/health" -TimeoutSeconds 3) {
        Write-Host "[warn] Port 8000 is still serving VenomAI after cleanup, so the backend will be reused."
        return "reuse"
    }

    throw "Port 8000 is still busy after cleanup. Close the conflicting process, then run this launcher again."
}

function Get-FrontendStartMode {
    param([hashtable]$FrontendConfig)

    if (-not (Test-PortListening -Port $FrontendConfig.Port)) {
        return "start"
    }

    if (Wait-HttpReady -Url $FrontendConfig.Url -TimeoutSeconds 3) {
        Write-Host ("[warn] Port {0} is still serving the frontend after cleanup, so it will be reused." -f $FrontendConfig.Port)
        return "reuse"
    }

    throw "Port $($FrontendConfig.Port) is still busy after cleanup. Close the conflicting process, then run this launcher again."
}

function Sync-BackendDependencies {
    param(
        [hashtable]$Python,
        [string]$StampPath
    )

    Write-Step "[2/4] Syncing backend dependencies..."

    $backendDir = Join-Path $Root "backend"
    $manifestPaths = @(Join-Path $backendDir "pyproject.toml")
    $currentHash = Get-CombinedHash $manifestPaths

    $stampMatches = (Test-Path $StampPath) -and ((Get-Content -LiteralPath $StampPath -Raw) -eq $currentHash)
    $reason = $null

    if (-not $stampMatches) {
        $reason = "backend manifest changed"
    }

    $importExit = Invoke-External -FilePath $Python.Exe -Arguments ($Python.Args + @("-c", "import fastapi, uvicorn, sqlalchemy, aiosqlite")) -WorkingDirectory $backendDir -Quiet
    if ($importExit -ne 0) {
        $reason = "backend packages missing or broken"
    }

    if ($reason) {
        Write-Host "       $reason, running pip install -e ."
        $installExit = Invoke-External -FilePath $Python.Exe -Arguments ($Python.Args + @("-m", "pip", "install", "-e", ".")) -WorkingDirectory $backendDir
        if ($installExit -ne 0) {
            throw "Backend dependency installation failed."
        }
        Write-Stamp -StampPath $StampPath -HashValue $currentHash
    }
    else {
        Write-Host "       Backend dependencies already current."
    }
}

function Sync-FrontendDependencies {
    param(
        [string]$NpmExe,
        [hashtable]$FrontendConfig,
        [string]$StampPath
    )

    Write-Step "[3/4] Syncing frontend dependencies..."

    $manifestPaths = @(
        (Join-Path $FrontendConfig.Dir "package.json"),
        (Join-Path $FrontendConfig.Dir "package-lock.json")
    )
    $currentHash = Get-CombinedHash $manifestPaths

    $reason = $null
    if (-not (Test-Path (Join-Path $FrontendConfig.Dir "node_modules"))) {
        $reason = "node_modules is missing"
    }

    $stampMatches = (Test-Path $StampPath) -and ((Get-Content -LiteralPath $StampPath -Raw) -eq $currentHash)
    if (-not $stampMatches) {
        $reason = "frontend manifest changed"
    }

    if (-not $reason) {
        $npmLsExit = Invoke-External -FilePath $NpmExe -Arguments @("ls", "--depth=0") -WorkingDirectory $FrontendConfig.Dir -Quiet
        if ($npmLsExit -ne 0) {
            $reason = "frontend packages missing or broken"
        }
    }

    if ($reason) {
        Write-Host "       $reason, running npm install."
        $installExit = Invoke-External -FilePath $NpmExe -Arguments @("install") -WorkingDirectory $FrontendConfig.Dir
        if ($installExit -ne 0) {
            throw "Frontend dependency installation failed."
        }
        Write-Stamp -StampPath $StampPath -HashValue $currentHash
    }
    else {
        Write-Host "       Frontend dependencies already current."
    }
}

function Start-BackendWindow {
    param([hashtable]$Python)

    $backendDir = Join-Path $Root "backend"
    $tokens = @($Python.Exe) + $Python.Args + @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000")
    $command = 'title VenomAI Backend && cd /d {0} && {1}' -f (Quote-CmdToken $backendDir), (Join-CmdTokens $tokens)
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $command | Out-Null
}

function Start-FrontendWindow {
    param(
        [string]$NpmExe,
        [hashtable]$FrontendConfig
    )

    $tokens = @($NpmExe, "run", "dev")
    $command = 'title VenomAI Frontend && cd /d {0} && {1}' -f (Quote-CmdToken $FrontendConfig.Dir), (Join-CmdTokens $tokens)
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $command | Out-Null
}

try {
    $frontendConfig = Get-FrontendConfig
    $python = Get-PythonCommand
    $npmExe = Get-NpmCommand

    New-Item -ItemType Directory -Force $StateDir | Out-Null
    $backendStamp = Join-Path $StateDir "backend-deps.hash"
    $frontendStamp = Join-Path $StateDir ("frontend-{0}-deps.hash" -f $frontendConfig.Key)

    Write-Host "=========================================="
    Write-Host "  VenomAI Launcher"
    Write-Host "=========================================="
    Write-Host ("  Root:      {0}" -f $Root)
    Write-Host ("  Frontend:  {0}" -f $frontendConfig.Dir.Substring($Root.Length + 1))
    Write-Host ("  URL:       {0}" -f $frontendConfig.Url)
    Write-Host ""

    Stop-ExistingVenomAIInstances -ProjectRoot $Root
    $backendStartMode = Get-BackendStartMode
    $frontendStartMode = Get-FrontendStartMode -FrontendConfig $frontendConfig

    Sync-BackendDependencies -Python $python -StampPath $backendStamp
    Sync-FrontendDependencies -NpmExe $npmExe -FrontendConfig $frontendConfig -StampPath $frontendStamp

    if (-not (Test-Path (Join-Path $Root "backend\.env"))) {
        Write-Host "[note] backend\.env was not found."
        Write-Host "       The app can still start, but chat features may need ANTHROPIC_API_KEY."
        Write-Host ""
    }

    Write-Step "[4/4] Starting backend..."
    if ($backendStartMode -eq "start") {
        Start-BackendWindow -Python $python
    }
    else {
        Write-Host "Backend is already healthy and will be reused."
    }

    Write-Host "Waiting for backend health check..."
    if (Wait-HttpReady -Url "$BackendUrl/api/health" -TimeoutSeconds 30) {
        Write-Host "Backend is ready."
    }
    else {
        Write-Host "Backend did not answer within 30 seconds. Starting the frontend anyway."
    }

    Write-Host "Starting frontend..."
    if ($frontendStartMode -eq "start") {
        Start-FrontendWindow -NpmExe $npmExe -FrontendConfig $frontendConfig
    }
    else {
        Write-Host "Frontend is already healthy and will be reused."
    }

    Write-Host "Waiting for frontend..."
    if (Wait-HttpReady -Url $frontendConfig.Url -TimeoutSeconds 30) {
        Write-Host "Frontend is ready."
    }
    else {
        Write-Host "Frontend is still booting. The browser will open anyway."
    }

    Start-Sleep -Seconds 2
    Start-Process $frontendConfig.Url | Out-Null

    Write-Host ""
    Write-Host "=========================================="
    Write-Host "  VenomAI is starting"
    Write-Host "=========================================="
    Write-Host ("  Backend:  {0}" -f $BackendUrl)
    Write-Host ("  Frontend: {0}" -f $frontendConfig.Url)
    Write-Host ""
    Write-Host "  Re-run run_venomai.cmd any time to force-restart the stack."
    Write-Host "=========================================="
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
