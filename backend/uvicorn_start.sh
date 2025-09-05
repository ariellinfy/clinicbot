
#!/usr/bin/env bash
set -e
exec uvicorn app.api:app --host 0.0.0.0 --port 8080 --reload
