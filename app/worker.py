from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from .probe import ProbeResult, probe
from .remap import RemapPlan, run_remap


@dataclass
class Job:
    src: Path
    probe: ProbeResult
    plan: RemapPlan


class ProbeWorker(QObject):
    done = Signal(object, object)  # (path: Path, result: ProbeResult | None), err: str | None
    finished = Signal()

    def __init__(self, paths: list[Path]):
        super().__init__()
        self._paths = paths

    def run(self):
        for p in self._paths:
            try:
                r = probe(p)
                self.done.emit((p, r), None)
            except Exception as e:  # noqa: BLE001
                self.done.emit((p, None), str(e))
        self.finished.emit()


class BatchWorker(QObject):
    job_started = Signal(int, str)           # index, src filename
    job_progress = Signal(int, float)        # index, fraction [0..1]
    job_log = Signal(int, str)               # index, line
    job_finished = Signal(int, bool, str)    # index, success, message
    all_finished = Signal()

    def __init__(self, jobs: list[Job]):
        super().__init__()
        self._jobs = jobs
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        for i, job in enumerate(self._jobs):
            if self._cancel:
                self.job_finished.emit(i, False, "cancelled")
                continue
            self.job_started.emit(i, job.src.name)
            try:
                run_remap(
                    src=job.src,
                    probe=job.probe,
                    plan=job.plan,
                    on_progress=lambda f, idx=i: self.job_progress.emit(idx, f),
                    on_log=lambda s, idx=i: self.job_log.emit(idx, s),
                    cancel_check=lambda: self._cancel,
                )
                if self._cancel:
                    self.job_finished.emit(i, False, "cancelled")
                else:
                    self.job_finished.emit(i, True, str(job.plan.output_path))
            except Exception as e:  # noqa: BLE001
                self.job_finished.emit(i, False, str(e))
        self.all_finished.emit()


def run_in_thread(worker: QObject, start_slot_name: str = "run") -> QThread:
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(getattr(worker, start_slot_name))
    # Caller is responsible for connecting finished signals and calling thread.quit()
    return thread
