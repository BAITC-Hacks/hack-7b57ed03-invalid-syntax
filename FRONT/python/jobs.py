"""Run blocking API calls off the Qt UI thread."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    finished = Signal()


class Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = Signals()

    @Slot()
    def run(self):
        try:
            self.signals.done.emit(self.fn())
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class Jobs(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(4)
        self.active = set()

    def submit(self, fn, done, failed, finished=lambda: None):
        job = Job(fn)
        self.active.add(job)
        job.signals.done.connect(done)
        job.signals.failed.connect(failed)
        job.signals.finished.connect(finished)
        job.signals.finished.connect(lambda: self.active.discard(job))
        self.pool.start(job)
