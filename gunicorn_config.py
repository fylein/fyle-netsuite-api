import os
from psycogreen.gevent import patch_psycopg

# https://docs.gunicorn.org/en/stable/settings.html

port_number = 8001
bind = '0.0.0.0:{0}'.format(port_number)
proc_name = 'fyle_netsuite_api'

# The maximum number of pending connections.
backlog = int(os.environ.get('GUNICORN_BACKLOG', 2048))

# The number of worker processes for handling requests.
workers = int(os.environ.get('GUNICORN_NUMBER_WORKERS', 4))

# Workers silent for more than this many seconds are killed and restarted.
timeout = int(os.environ.get('GUNICORN_WORKER_TIMEOUT', 60))

# The number of seconds to wait for requests on a Keep-Alive connection.
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', 2))

# The maximum number of simultaneous clients.
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', 1000))

# The granularity of Error log outputs.
loglevel = os.environ.get('GUNICORN_LOG _LEVEL', 'debug')

# The type of workers to use.
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gevent')

# The number of worker threads for handling requests.
threads = int(os.environ.get('GUNICORN_NUMBER_WORKER_THREADS', 1))

# The maximum number of requests a worker will process before restarting.
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 20))

# The jitter causes the restart per worker to be randomized by randint(0, max_requests_jitter).
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 20))

# Timeout for graceful workers restart.
graceful_timeout = int(os.environ.get('GUNICORN_WORKER_GRACEFUL_TIMEOUT', 5))

# Restart workers when code changes.
reload = True

# The maximum size of HTTP request line in bytes.
limit_request_line = 0

# Install a trace function that spews every line executed by the server.
spew = False

# Detaches the server from the controlling terminal and enters the background.
daemon = False

pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

errorlog = '-'
accesslog = '-'
access_log_format = '%({X-Real-IP}i)s - - - %(t)s "%(r)s" "%(f)s" "%(a)s" %({X-Request-Id}i)s %(L)s %(b)s %(s)s'


def post_fork(server, worker):
    patch_psycopg()
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def pre_fork(server, worker):  # noqa
    pass


def pre_exec(server):
    server.log.info("Forked child, re-executing.")


def when_ready(server):
    server.log.info("Server is ready. Spawning workers")


def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

    # get traceback info
    import threading
    import sys
    import traceback
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for thread_id, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(thread_id, ""),
                                            thread_id))
        for filename, line_no, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename,
                                                        line_no, name))
            if line:
                code.append("  %s" % (line.strip()))
    worker.log.debug("\n".join(code))


def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")


def child_exit(server, worker):
    server.log.info("server: child_exit is called")
    worker.log.info("worker: child_exit is called")


def worker_exit(server, worker):
    server.log.info("server: worker_exit is called")
    worker.log.info("worker: worker_exit is called")


def nworkers_changed(server, new_value, old_value):
    server.log.info("server: nworkers_changed is called with new_value: %s old_value: %s", new_value, old_value)


def on_exit(server):
    server.log.info("server: on_exit is called")