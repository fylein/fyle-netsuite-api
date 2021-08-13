import sys
import time
import os
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class LoggingEventHandler(FileSystemEventHandler):
    """Logs all the events captured."""

    def __init__(self, logger=None):
        super().__init__()
        self.counter = 0
        self.proc = None
        self.logger = logger or logging.root

    def on_modified(self, event):
        super().on_modified(event)

        if 'tasks.py' in event.src_path:
            if self.counter != 0 and self.counter % 2 == 1:
                print('Restarting . . .')
                os.system('docker-compose restart qcluster')
                print('Modified {}'.format(event.src_path))
            self.counter = self.counter + 1

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    event_handler = LoggingEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
