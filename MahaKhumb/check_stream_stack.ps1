$python = Join-Path $PSScriptRoot "kumbh_env\Scripts\python.exe"
& $python -c "from runtime_services import kafka_is_ready, configure_java_environment; print('JAVA_READY:', configure_java_environment()); print('KAFKA_READY:', kafka_is_ready())"
