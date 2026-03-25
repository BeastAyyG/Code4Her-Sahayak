$ErrorActionPreference = "Stop"

$python = ".\kumbh_env\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment interpreter not found at $python"
}

powershell -ExecutionPolicy Bypass -File .\start_local_kafka.ps1

$steps = @(
    "layer1_map.py",
    "layer2_clustering.py",
    "layer3_qaoa.py",
    "comparison.py",
    "validate_results.py",
    "stream_simulator.py",
    "build_dashboard.py",
    "build_dashboard_demo3.py"
)

foreach ($step in $steps) {
    Write-Host "[demo] running $step"
    & $python $step
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE"
    }
}

Write-Host "[demo] dashboard ready: $PWD\demo_dashboard.html"
Write-Host "[demo] demo3 ready: $PWD\demo_dashboard_3.html"
Write-Host "[demo] phase2 mobile UI: start server via '$python mobile_guide_server.py --port 8088' then open http://localhost:8088"
