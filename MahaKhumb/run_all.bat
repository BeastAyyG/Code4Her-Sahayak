@echo off
setlocal

set PYTHON=.\kumbh_env\Scripts\python.exe
if not exist "%PYTHON%" (
  echo Virtual environment interpreter not found at %PYTHON%
  exit /b 1
)

powershell -ExecutionPolicy Bypass -File ".\start_local_kafka.ps1"
if errorlevel 1 exit /b 1

for %%S in (
  layer1_map.py
  layer2_clustering.py
  layer3_qaoa.py
  comparison.py
  validate_results.py
  stream_simulator.py
  build_dashboard.py
  build_dashboard_demo3.py
) do (
  echo [demo] running %%S
  "%PYTHON%" "%%S"
  if errorlevel 1 exit /b 1
)

echo [demo] dashboard ready: %CD%\demo_dashboard.html
echo [demo] demo3 ready: %CD%\demo_dashboard_3.html
echo [demo] phase2 mobile UI: run start_mobile_demo.bat
