from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSplitter, QVBoxLayout, QWidget,
    QSizePolicy,
)

from ..probe import ProbeResult, ensure_tools, probe, default_output_path
from ..remap import RemapPlan, pretty_order
from ..worker import BatchWorker, Job, ProbeWorker
from .style import QSS
from .track_panel import TrackPanel


SUPPORTED_EXTS = {".mp4", ".mkv", ".mov", ".m4v", ".avi", ".webm", ".ts", ".mts", ".m2ts"}


@dataclass
class FileEntry:
    path: Path
    probe: Optional[ProbeResult] = None
    error: str = ""
    audio_order: list[int] = field(default_factory=list)
    default_original: int = 0
    status: str = "pending"  # pending | running | done | error | cancelled
    progress: float = 0.0
    output_path: Optional[Path] = None
    message: str = ""


class FileListWidget(QListWidget):
    """List of video files. Accepts drops of files/folders."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SingleSelection)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        paths: list[Path] = []
        for url in e.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                for child in p.rglob("*"):
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTS:
                        paths.append(child)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                paths.append(p)
        if paths:
            parent = self.parent()
            while parent and not hasattr(parent, "add_paths"):
                parent = parent.parent()
            if parent:
                parent.add_paths(paths)
        e.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Track Swapper")
        self.resize(1200, 780)
        self.setMinimumSize(960, 620)

        # check ffmpeg on startup (soft check)
        self._tools_ok = True
        try:
            ensure_tools()
        except Exception as e:  # noqa: BLE001
            self._tools_ok = False
            QTimer.singleShot(200, lambda: QMessageBox.warning(self, "ffmpeg not found", str(e)))

        self.entries: list[FileEntry] = []
        self._probe_thread: Optional[QThread] = None
        self._probe_worker: Optional[ProbeWorker] = None
        self._batch_thread: Optional[QThread] = None
        self._batch_worker: Optional[BatchWorker] = None
        self._preview_proc: Optional[subprocess.Popen] = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._stop_preview)

        self._build_ui()

    # ------------- UI -------------
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Audio Track Swapper")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addSpacing(10)
        sub = QLabel("Swap audio tracks in videos — lossless, batch, cross-platform")
        sub.setObjectName("dim")
        header.addWidget(sub)
        header.addStretch(1)

        self.add_files_btn = QPushButton("＋ Add files")
        self.add_files_btn.clicked.connect(self._add_files_dialog)
        header.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("＋ Add folder")
        self.add_folder_btn.clicked.connect(self._add_folder_dialog)
        header.addWidget(self.add_folder_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("ghost")
        self.clear_btn.clicked.connect(self._clear_files)
        header.addWidget(self.clear_btn)
        outer.addLayout(header)

        # Body splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(12)
        outer.addWidget(splitter, 1)

        # Left: file list card
        left = QFrame()
        left.setObjectName("card")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(14, 14, 14, 14)
        left_l.setSpacing(10)
        lhead = QHBoxLayout()
        h2 = QLabel("Files")
        h2.setObjectName("h2")
        lhead.addWidget(h2)
        lhead.addStretch(1)
        self.files_count = QLabel("0")
        self.files_count.setObjectName("badge")
        lhead.addWidget(self.files_count)
        left_l.addLayout(lhead)

        self.file_list = FileListWidget()
        self.file_list.currentRowChanged.connect(self._on_row_changed)
        left_l.addWidget(self.file_list, 1)

        drop_hint = QLabel("Drop videos or folders here")
        drop_hint.setObjectName("dim")
        drop_hint.setAlignment(Qt.AlignCenter)
        left_l.addWidget(drop_hint)

        splitter.addWidget(left)

        # Right: details + actions
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(12)

        self.file_header = QFrame()
        self.file_header.setObjectName("card")
        fh = QVBoxLayout(self.file_header)
        fh.setContentsMargins(14, 12, 14, 12)
        fh.setSpacing(4)
        self.fh_name = QLabel("No file selected")
        self.fh_name.setObjectName("h2")
        self.fh_meta = QLabel("")
        self.fh_meta.setObjectName("dim")
        fh.addWidget(self.fh_name)
        fh.addWidget(self.fh_meta)
        right_l.addWidget(self.file_header)

        # Quick actions bar
        qa = QFrame()
        qa.setObjectName("card")
        qa_l = QHBoxLayout(qa)
        qa_l.setContentsMargins(12, 10, 12, 10)
        qa_l.setSpacing(8)

        qa_l.addWidget(QLabel("Quick:"))
        self.swap_combo_a = QComboBox()
        self.swap_combo_b = QComboBox()
        for c in (self.swap_combo_a, self.swap_combo_b):
            c.setMinimumWidth(90)
        qa_l.addWidget(self.swap_combo_a)
        arrow = QLabel("⇄")
        arrow.setStyleSheet("color:#8b5cf6; font-size: 18px; font-weight: 700;")
        qa_l.addWidget(arrow)
        qa_l.addWidget(self.swap_combo_b)
        self.swap_btn = QPushButton("Swap")
        self.swap_btn.clicked.connect(self._quick_swap)
        qa_l.addWidget(self.swap_btn)

        self.reset_btn = QPushButton("Reset order")
        self.reset_btn.setObjectName("ghost")
        self.reset_btn.clicked.connect(self._reset_order)
        qa_l.addWidget(self.reset_btn)

        qa_l.addStretch(1)

        self.apply_all_cb = QCheckBox("Apply to all files")
        self.apply_all_cb.setToolTip(
            "When checked, the order you set here is used for every file in the list.\n"
            "Useful when all files share the same track layout (e.g. a whole season)."
        )
        qa_l.addWidget(self.apply_all_cb)
        right_l.addWidget(qa)

        # Track panel
        self.track_panel = TrackPanel()
        self.track_panel.order_changed.connect(self._on_order_changed)
        self.track_panel.default_changed.connect(self._on_default_changed)
        self.track_panel.preview_requested.connect(self._preview_track)
        right_l.addWidget(self.track_panel, 1)

        # Output settings
        out = QFrame()
        out.setObjectName("card")
        out_l = QHBoxLayout(out)
        out_l.setContentsMargins(12, 10, 12, 10)
        out_l.setSpacing(10)
        out_l.addWidget(QLabel("Output:"))
        self.out_mode = QComboBox()
        self.out_mode.addItems([
            "Same folder, add suffix",
            "Custom folder…",
            "Overwrite original (risky)",
        ])
        self.out_mode.currentIndexChanged.connect(self._on_out_mode_changed)
        out_l.addWidget(self.out_mode)

        self.out_suffix = QComboBox()
        self.out_suffix.setEditable(True)
        self.out_suffix.addItems(["_swapped", "_audio-fixed", "_v2"])
        self.out_suffix.setFixedWidth(160)
        out_l.addWidget(QLabel("Suffix:"))
        out_l.addWidget(self.out_suffix)

        self.out_folder_lbl = QLabel("—")
        self.out_folder_lbl.setObjectName("dim")
        self.out_folder_btn = QPushButton("Choose…")
        self.out_folder_btn.clicked.connect(self._pick_out_folder)
        self.out_folder_btn.hide()
        out_l.addWidget(self.out_folder_btn)
        out_l.addWidget(self.out_folder_lbl)
        out_l.addStretch(1)
        right_l.addWidget(out)

        # Run bar
        run = QFrame()
        run.setObjectName("card")
        run_l = QHBoxLayout(run)
        run_l.setContentsMargins(12, 10, 12, 10)
        self.run_btn = QPushButton("Apply & Process")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self._start_batch)
        run_l.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.clicked.connect(self._cancel_batch)
        self.cancel_btn.setEnabled(False)
        run_l.addWidget(self.cancel_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        run_l.addWidget(self.progress_bar, 1)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("dim")
        run_l.addWidget(self.status_label)

        self.toggle_log_btn = QPushButton("Log")
        self.toggle_log_btn.setObjectName("ghost")
        self.toggle_log_btn.setCheckable(True)
        self.toggle_log_btn.toggled.connect(self._toggle_log)
        run_l.addWidget(self.toggle_log_btn)

        right_l.addWidget(run)

        # Log (hidden by default)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(160)
        self.log_view.hide()
        right_l.addWidget(self.log_view)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([320, 880])

        self._custom_out_folder: Optional[Path] = None
        self._refresh_controls()

    # ------------- File management -------------
    def _add_files_dialog(self):
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTS))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select video files", str(Path.home()),
            f"Videos ({exts});;All files (*)"
        )
        if paths:
            self.add_paths([Path(p) for p in paths])

    def _add_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder", str(Path.home()))
        if folder:
            f = Path(folder)
            paths = [p for p in f.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
            self.add_paths(paths)

    def add_paths(self, paths: list[Path]):
        existing = {e.path.resolve() for e in self.entries}
        new_paths = [p for p in paths if p.resolve() not in existing]
        for p in new_paths:
            entry = FileEntry(path=p)
            self.entries.append(entry)
            item = QListWidgetItem(self._item_text(entry))
            item.setData(Qt.UserRole, len(self.entries) - 1)
            self.file_list.addItem(item)
        self.files_count.setText(str(len(self.entries)))
        if new_paths:
            self._probe_paths(new_paths)
            if self.file_list.currentRow() < 0:
                self.file_list.setCurrentRow(0)

    def _clear_files(self):
        if self._batch_thread and self._batch_thread.isRunning():
            return
        self.entries.clear()
        self.file_list.clear()
        self.files_count.setText("0")
        self.track_panel.set_probe(None)
        self.fh_name.setText("No file selected")
        self.fh_meta.setText("")
        self._refresh_controls()

    def _item_text(self, entry: FileEntry) -> str:
        status_icon = {
            "pending": "●", "running": "…", "done": "✓", "error": "✗", "cancelled": "⦸",
        }.get(entry.status, "●")
        size = _fmt_size(entry.path.stat().st_size) if entry.path.exists() else ""
        probe_info = ""
        if entry.probe:
            n = len(entry.probe.audio_streams)
            probe_info = f"  ·  {n} audio"
        err = f"  ·  ⚠ {entry.error}" if entry.error else ""
        msg = f"  ·  {entry.message}" if entry.message and entry.status in ("done", "error") else ""
        return f"{status_icon}  {entry.path.name}\n    {size}{probe_info}{err}{msg}"

    def _refresh_item(self, idx: int):
        item = self.file_list.item(idx)
        if item:
            item.setText(self._item_text(self.entries[idx]))

    def _current_entry(self) -> Optional[FileEntry]:
        row = self.file_list.currentRow()
        if row < 0 or row >= len(self.entries):
            return None
        return self.entries[row]

    def _on_row_changed(self, row: int):
        self._stop_preview()
        if row < 0 or row >= len(self.entries):
            self.track_panel.set_probe(None)
            self.fh_name.setText("No file selected")
            self.fh_meta.setText("")
            self._refresh_controls()
            return
        entry = self.entries[row]
        self.fh_name.setText(entry.path.name)
        parent = str(entry.path.parent)
        if entry.probe:
            n = len(entry.probe.audio_streams)
            dur = _fmt_duration(entry.probe.duration)
            self.fh_meta.setText(f"{parent}  ·  {n} audio tracks  ·  {dur}")
        else:
            self.fh_meta.setText(parent + ("  ·  probing…" if not entry.error else f"  ·  ⚠ {entry.error}"))
        self.track_panel.set_probe(entry.probe, entry.audio_order or None, entry.default_original)
        self._populate_swap_combos(entry)
        self._refresh_controls()

    def _populate_swap_combos(self, entry: FileEntry):
        self.swap_combo_a.clear()
        self.swap_combo_b.clear()
        if not entry.probe:
            return
        n = len(entry.probe.audio_streams)
        for i in range(n):
            label = f"Track {i + 1}"
            self.swap_combo_a.addItem(label, i)
            self.swap_combo_b.addItem(label, i)
        if n >= 2:
            self.swap_combo_b.setCurrentIndex(1)

    # ------------- Probing -------------
    def _probe_paths(self, paths: list[Path]):
        if self._probe_thread and self._probe_thread.isRunning():
            # Queue by chaining — simplest: wait synchronously for user add rate
            self._probe_thread.wait(50)
        worker = ProbeWorker(paths)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self._on_probe_done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._probe_thread = thread
        self._probe_worker = worker
        thread.start()

    def _on_probe_done(self, payload, err):
        path, result = payload
        for idx, e in enumerate(self.entries):
            if e.path == path:
                if err:
                    e.error = err
                    e.probe = None
                else:
                    e.probe = result
                    e.error = ""
                    e.audio_order = list(range(len(result.audio_streams)))
                    # pick first non-zero-channel track as default
                    e.default_original = 0
                self._refresh_item(idx)
                if self.file_list.currentRow() == idx:
                    self._on_row_changed(idx)
                break
        self._refresh_controls()

    # ------------- Track edits -------------
    def _on_order_changed(self, order: list[int]):
        entry = self._current_entry()
        if not entry:
            return
        entry.audio_order = list(order)

    def _on_default_changed(self, orig_pos: int):
        entry = self._current_entry()
        if not entry:
            return
        entry.default_original = orig_pos

    def _quick_swap(self):
        entry = self._current_entry()
        if not entry or not entry.probe:
            return
        a = self.swap_combo_a.currentData()
        b = self.swap_combo_b.currentData()
        if a is None or b is None or a == b:
            return
        order = list(entry.audio_order)
        # swap by original positions — find their current slots
        ia = order.index(a)
        ib = order.index(b)
        order[ia], order[ib] = order[ib], order[ia]
        entry.audio_order = order
        self.track_panel.set_probe(entry.probe, entry.audio_order, entry.default_original)

    def _reset_order(self):
        entry = self._current_entry()
        if not entry or not entry.probe:
            return
        entry.audio_order = list(range(len(entry.probe.audio_streams)))
        entry.default_original = 0
        self.track_panel.set_probe(entry.probe, entry.audio_order, entry.default_original)

    # ------------- Preview -------------
    def _preview_track(self, orig_pos: int):
        entry = self._current_entry()
        if not entry or not entry.probe:
            return
        self._stop_preview()
        try:
            ffmpeg, _ = ensure_tools()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "ffmpeg missing", str(e))
            return
        ffplay = _which("ffplay")
        if ffplay:
            # ffplay with -map cannot select audio by default, use -ast for audio stream index within file.
            abs_idx = entry.probe.audio_streams[orig_pos].index
            cmd = [ffplay, "-hide_banner", "-nodisp", "-autoexit",
                   "-loglevel", "error", "-t", "6",
                   "-ss", str(max(0, int(entry.probe.duration * 0.1))),
                   "-ast", str(abs_idx), str(entry.path)]
            self._preview_proc = subprocess.Popen(cmd)
            self._preview_timer.start(7000)
            self.status_label.setText(f"Previewing track {orig_pos + 1}")
        else:
            # Fallback: extract a short wav then play with system player
            self.status_label.setText("ffplay not available — install ffmpeg fully to enable preview")

    def _stop_preview(self):
        if self._preview_proc and self._preview_proc.poll() is None:
            try:
                self._preview_proc.terminate()
            except Exception:
                pass
        self._preview_proc = None

    # ------------- Output -------------
    def _on_out_mode_changed(self, idx: int):
        self.out_folder_btn.setVisible(idx == 1)
        if idx == 1:
            self.out_folder_lbl.setText(str(self._custom_out_folder) if self._custom_out_folder else "—")
        elif idx == 2:
            self.out_folder_lbl.setText("overwrite original in place (original is deleted on success)")
        else:
            self.out_folder_lbl.setText("—")

    def _pick_out_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Output folder", str(Path.home()))
        if folder:
            self._custom_out_folder = Path(folder)
            self.out_folder_lbl.setText(folder)

    def _output_for(self, entry: FileEntry) -> Path:
        mode = self.out_mode.currentIndex()
        suffix = self.out_suffix.currentText() or "_swapped"
        if mode == 0:
            return default_output_path(entry.path, suffix)
        if mode == 1:
            folder = self._custom_out_folder or entry.path.parent
            return folder / f"{entry.path.stem}{suffix}{entry.path.suffix}"
        # overwrite -> write to temp then rename over original
        return entry.path.with_name(f"{entry.path.stem}.__swapping__{entry.path.suffix}")

    # ------------- Batch run -------------
    def _ready_jobs(self) -> list[tuple[int, Job]]:
        jobs: list[tuple[int, Job]] = []
        master = None
        if self.apply_all_cb.isChecked():
            entry = self._current_entry()
            if entry and entry.probe:
                master = (list(entry.audio_order), entry.default_original)
        for i, e in enumerate(self.entries):
            if not e.probe or not e.audio_order:
                continue
            order = list(e.audio_order)
            default_orig = e.default_original
            if master:
                order = [o for o in master[0] if o < len(e.probe.audio_streams)]
                if len(order) != len(e.probe.audio_streams):
                    # Skip files whose audio count doesn't match
                    e.status = "error"
                    e.message = "skipped: audio-track count differs"
                    self._refresh_item(i)
                    continue
                default_orig = master[1] if master[1] < len(e.probe.audio_streams) else 0
            if order == list(range(len(e.probe.audio_streams))) and default_orig == 0:
                e.status = "error"
                e.message = "skipped: no change"
                self._refresh_item(i)
                continue
            out_path = self._output_for(e)
            try:
                default_in_new = order.index(default_orig)
            except ValueError:
                default_in_new = 0
            plan = RemapPlan(audio_order=order, output_path=out_path, default_audio=default_in_new)
            jobs.append((i, Job(src=e.path, probe=e.probe, plan=plan)))
        return jobs

    def _start_batch(self):
        if not self._tools_ok:
            QMessageBox.warning(self, "ffmpeg not found", "Install ffmpeg and restart.")
            return
        pairs = self._ready_jobs()
        if not pairs:
            QMessageBox.information(self, "Nothing to do",
                                    "No files have a changed audio order. Rearrange tracks or pick a new default, then try again.")
            return

        # Confirm overwrite mode
        if self.out_mode.currentIndex() == 2:
            r = QMessageBox.question(
                self, "Overwrite originals?",
                f"This will replace {len(pairs)} original file(s) with the swapped version.\n"
                "Continue?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if r != QMessageBox.Yes:
                return

        self._job_index_map = [p[0] for p in pairs]  # batch-index -> entry-index
        jobs = [p[1] for p in pairs]

        for i, e in enumerate(self.entries):
            if i in self._job_index_map:
                e.status = "pending"
                e.progress = 0.0
                e.message = ""
                e.output_path = None
                self._refresh_item(i)

        worker = BatchWorker(jobs)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.job_started.connect(self._on_job_started)
        worker.job_progress.connect(self._on_job_progress)
        worker.job_log.connect(self._on_job_log)
        worker.job_finished.connect(self._on_job_finished)
        worker.all_finished.connect(self._on_batch_finished)
        worker.all_finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._batch_worker = worker
        self._batch_thread = thread

        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.status_label.setText(f"Processing 0 / {len(jobs)}")
        self.progress_bar.setValue(0)
        self._batch_total = len(jobs)
        self._batch_done = 0
        thread.start()

    def _cancel_batch(self):
        if self._batch_worker:
            self._batch_worker.cancel()
            self.status_label.setText("Cancelling…")

    def _on_job_started(self, batch_idx: int, name: str):
        entry_idx = self._job_index_map[batch_idx]
        self.entries[entry_idx].status = "running"
        self._refresh_item(entry_idx)
        self.status_label.setText(f"Processing {self._batch_done + 1} / {self._batch_total}: {name}")

    def _on_job_progress(self, batch_idx: int, frac: float):
        entry_idx = self._job_index_map[batch_idx]
        self.entries[entry_idx].progress = frac
        overall = (self._batch_done + frac) / max(1, self._batch_total)
        self.progress_bar.setValue(int(overall * 1000))

    def _on_job_log(self, batch_idx: int, line: str):
        entry_idx = self._job_index_map[batch_idx]
        self.log_view.appendPlainText(f"[{self.entries[entry_idx].path.name}] {line}")

    def _on_job_finished(self, batch_idx: int, ok: bool, msg: str):
        entry_idx = self._job_index_map[batch_idx]
        entry = self.entries[entry_idx]
        if ok:
            # If overwrite mode, rename the temp output over the original
            if self.out_mode.currentIndex() == 2:
                try:
                    tmp = Path(msg)
                    final = entry.path
                    final.unlink(missing_ok=True)
                    tmp.rename(final)
                    entry.output_path = final
                    entry.message = "overwrote original"
                except Exception as e:
                    entry.status = "error"
                    entry.message = f"rename failed: {e}"
                    self._refresh_item(entry_idx)
                    self._batch_done += 1
                    return
            else:
                entry.output_path = Path(msg)
                entry.message = f"→ {entry.output_path.name}"
            entry.status = "done"
        else:
            entry.status = "cancelled" if msg == "cancelled" else "error"
            entry.message = msg
        self._batch_done += 1
        self._refresh_item(entry_idx)

    def _on_batch_finished(self):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(1000)
        ok = sum(1 for e in self.entries if e.status == "done")
        bad = sum(1 for e in self.entries if e.status in ("error", "cancelled"))
        self.status_label.setText(f"Done — {ok} succeeded, {bad} failed/cancelled")

    # ------------- Misc -------------
    def _refresh_controls(self):
        entry = self._current_entry()
        has = bool(entry and entry.probe and len(entry.probe.audio_streams) >= 2)
        self.swap_combo_a.setEnabled(has)
        self.swap_combo_b.setEnabled(has)
        self.swap_btn.setEnabled(has)
        self.reset_btn.setEnabled(has)
        any_ready = any(e.probe and len(e.probe.audio_streams) >= 2 for e in self.entries)
        self.run_btn.setEnabled(any_ready and self._tools_ok)

    def _toggle_log(self, on: bool):
        self.log_view.setVisible(on)

    def closeEvent(self, e):
        self._stop_preview()
        if self._batch_worker:
            self._batch_worker.cancel()
        if self._batch_thread:
            self._batch_thread.quit()
            self._batch_thread.wait(2000)
        super().closeEvent(e)


def _which(name: str) -> Optional[str]:
    import shutil
    return shutil.which(name)


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"


def _fmt_duration(secs: float) -> str:
    if not secs:
        return "?"
    s = int(secs)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(QSS)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
