"""
Shopo Robo — Gunicorn Production Configuration
===============================================
Production-grade WSGI configuration for Shopo Robo Flask application.
Optimized for multi-tenant retail workloads with SQLite WAL mode.
"""

import os
import multiprocessing

# Network Binding
# Uses PORT environment variable provided by hosting environments (Render, Railway, etc.)
port = os.environ.get("PORT", os.environ.get("SHOPO_PORT", "5000"))
host = os.environ.get("SHOPO_HOST", "0.0.0.0")
bind = f"{host}:{port}"

# Worker Processes
# SQLite WAL mode handles concurrent readers smoothly; keep worker count balanced (2-4)
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
worker_class = "sync"
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# Process Lifecycle & Memory Guard
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 30

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(D)s µs)'

# Process Naming
proc_name = "shopo_robo_wsgi"
