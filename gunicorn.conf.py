"""Gunicorn configuration file for FuelLens application."""

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 4  # Number of worker processes
worker_class = "sync"  # Worker type (sync, gevent, eventlet, etc.)
worker_connections = 1000  # Max simultaneous connections per worker
max_requests = 1000  # Restart workers after this many requests
max_requests_jitter = 100  # Randomize max_requests by this amount
timeout = 120  # Request timeout in seconds
keepalive = 5  # Number of seconds to keep connections alive

# Security
limit_request_line = 4094  # Maximum size of HTTP request line
limit_request_fields = 100  # Maximum number of HTTP headers
limit_request_field_size = 8190  # Maximum size of HTTP headers

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "fuellens"

# Server mechanics
preload_app = True  # Preload application code before forking workers
daemon = False  # Don't run as daemon
pidfile = "/tmp/fuellens.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Additional settings
worker_tmp_dir = "/dev/shm"  # Use tmpfs for worker temporary files