# gunicorn.conf.py
bind = "0.0.0.0:8080"
workers = 2
timeout = 120
loglevel = "debug"
capture_output = True
enable_stdio_inheritance = True
forwarded_allow_ips = "*"
accesslog = "-"
errorlog = "-"