# Production Notes

## What changed

- All major runtime artifacts can now be redirected with `CONTINUUM_ARTIFACT_DIR`.
- Critical JSON and pickle outputs are written atomically to reduce partial-file corruption.
- The mobile server now exposes `GET /api/ready` in addition to `GET /api/health`.
- The mobile server now enforces request body limits, validates coordinates, and sends basic security headers.
- Dashboard serving falls back from `viz_dashboard.html` to generated dashboard outputs if needed.

## Recommended run order

```powershell
.\kumbh_env\Scripts\python.exe launch_demo.py pipeline
.\kumbh_env\Scripts\python.exe production_check.py
.\kumbh_env\Scripts\python.exe mobile_guide_server.py --host 0.0.0.0 --port 8088
```

## Runtime configuration

Copy `.env.example` into your local environment or export the values directly.

Important variables:

- `CONTINUUM_APP_ENV`
- `CONTINUUM_ARTIFACT_DIR`
- `CONTINUUM_SERVER_ALLOWED_ORIGIN`
- `CONTINUUM_SERVER_MAX_BODY_BYTES`

## Readiness semantics

- `/api/health` means the process is up and the base graph is loaded.
- `/api/ready` means the expected runtime artifacts are available for the full guidance flow.
