# gunicorn.conf.py — place in project root alongside manage.py

# One worker is enough for uploads — Render free tier has limited RAM
workers = 1

# CRITICAL: timeout must be long enough to upload 2.4 GB over a typical connection.
# 2.4 GB at ~5 MB/s upload speed = ~480 seconds. Set 1800s (30 min) to be safe.
timeout = 1800

# Keep the connection alive during large uploads
keepalive = 30

# Stream large request bodies to a temp file instead of buffering in RAM
# This is what actually makes multi-GB uploads not OOM-kill the worker
worker_tmp_dir = "/dev/shm"

# Log to stdout so Render captures it
accesslog = "-"
errorlog  = "-"
loglevel  = "info"