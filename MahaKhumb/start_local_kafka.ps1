$python = Join-Path $PSScriptRoot "kumbh_env\Scripts\python.exe"
& $python -c "from runtime_services import ensure_local_kafka; print('Kafka ready:', ensure_local_kafka())"
