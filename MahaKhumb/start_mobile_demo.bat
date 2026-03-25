@echo off
setlocal

set PYTHON=.\kumbh_env\Scripts\python.exe
if not exist "%PYTHON%" (
  echo Virtual environment interpreter not found at %PYTHON%
  exit /b 1
)

if not exist "graph_data.pkl" (
  echo Missing graph_data.pkl. Run run_all.bat or run_all.ps1 first.
  exit /b 1
)

if not exist "cluster_data.pkl" (
  echo Missing cluster_data.pkl. Run run_all.bat or run_all.ps1 first.
  exit /b 1
)

if not exist "simulation_state.json" (
  echo Missing simulation_state.json. Run run_all.bat or run_all.ps1 first.
  exit /b 1
)

"%PYTHON%" mobile_guide_server.py --port 8088
