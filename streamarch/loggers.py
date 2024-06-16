import datetime as dt
import json
import logging
import time
import logging.handlers
import threading
from queue import Empty, SimpleQueue



LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}




class SingleThreadQueueListener(logging.handlers.QueueListener):
    """A subclass of QueueListener that uses a single thread for all queues.

    See https://github.com/python/cpython/blob/main/Lib/logging/handlers.py
    for the implementation of QueueListener.
    """
    monitor_thread = None
    listeners = []
    sleep_time = 0.1

    @classmethod
    def _start(cls):
        """Start a single thread, only if none is started."""
        if cls.monitor_thread is None or not cls.monitor_thread.is_alive():
            cls.monitor_thread = t = threading.Thread(
                target=cls._monitor_all, name='logging_monitor')
            t.daemon = True
            t.start()
        return cls.monitor_thread

    @classmethod
    def _join(cls):
        """Waits for the thread to stop.
        Only call this after stopping all listeners.
        """
        if cls.monitor_thread is not None and cls.monitor_thread.is_alive():
            cls.monitor_thread.join()
        cls.monitor_thread = None

    @classmethod
    def _monitor_all(cls):
        """A monitor function for all the registered listeners.
        Does not block when obtaining messages from the queue to give all
        listeners a chance to get an item from the queue. That's why we
        must sleep at every cycle.

        If a sentinel is sent, the listener is unregistered.
        When all listeners are unregistered, the thread stops.
        """
        noop = lambda: None
        while cls.listeners:
            time.sleep(cls.sleep_time)  # does not block all threads
            for listener in cls.listeners:
                try:
                    # Gets all messages in this queue without blocking
                    task_done = getattr(listener.queue, 'task_done', noop)
                    while True:
                        record = listener.dequeue(False)
                        if record is listener._sentinel:
                            cls.listeners.remove(listener)
                        else:
                            listener.handle(record)
                        task_done()
                except Empty:
                    continue

    def start(self):
        """Override default implementation.
        Register this listener and call class' _start() instead.
        """
        SingleThreadQueueListener.listeners.append(self)
        # Start if not already
        SingleThreadQueueListener._start()

    def stop(self):
        """Enqueues the sentinel but does not stop the thread."""
        self.enqueue_sentinel()

# https://medium.com/@augustomen/using-logging-asynchronously-c8e854de874c
class LogContext:

    def __init__(self):
        self.listeners = []

    def iter_loggers(self):
        """Iterates through all registered loggers."""
        for name in logging.root.manager.loggerDict:
            yield logging.getLogger(name)
        yield logging.getLogger()  # don't forget the root logger

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        """Replace all loggers' handlers with a new listener."""
        for logger in self.iter_loggers():
            if handlers := logger.handlers:
                queue = SimpleQueue()
                listener = SingleThreadQueueListener(queue, *handlers)
                logger.handlers = [logging.handlers.QueueHandler(queue)]
                self.listeners.append((listener, logger))
                listener.start()

    def close(self):
        """Stops the listener and restores all original handlers."""
        while self.listeners:
            listener, logger = self.listeners.pop()
            logger.handlers = listener.handlers
            listener.stop()

class MyJSONFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        fmt_keys = None,
    ):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}


    def format(self, record) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record):
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc
            ).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: msg_val
            if (msg_val := always_fields.pop(val, None)) is not None
            else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)

        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                message[key] = val

        return message


class NonErrorFilter(logging.Filter):

    def filter(self, record) :
        return record.levelno <= logging.INFO

# Email handler on: https://gist.github.com/anonymous/1379446    