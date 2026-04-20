from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget, QLabel, QHBoxLayout

from ..probe import ProbeResult
from .track_card import TrackCard, MIME_TRACK


class TrackPanel(QFrame):
    """Holds a vertical stack of TrackCards and supports drag-to-reorder.

    order_changed(list[int]) — emits new audio_order (original positions) on drop.
    default_changed(int)     — emits original_position chosen as default.
    preview_requested(int)   — emits original_position to preview.
    """
    order_changed = Signal(list)
    default_changed = Signal(int)
    preview_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setAcceptDrops(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Audio tracks")
        title.setObjectName("h2")
        header.addWidget(title)
        header.addStretch(1)
        self.hint = QLabel("Drag cards to reorder · ▶ preview · ★ set default")
        self.hint.setObjectName("dim")
        header.addWidget(self.hint)
        outer.addLayout(header)

        self._stack = QVBoxLayout()
        self._stack.setSpacing(8)
        self._stack.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(self._stack)
        outer.addStretch(1)

        self._cards: list[TrackCard] = []
        self._probe: Optional[ProbeResult] = None
        self._default_original = 0

        # Empty state
        self._empty = QLabel("Select a file to view its audio tracks")
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setObjectName("dim")
        self._empty.setStyleSheet("padding: 40px; font-size: 13px;")
        outer.insertWidget(1, self._empty)

    # --- public API ---
    def set_probe(self, probe: Optional[ProbeResult], audio_order: Optional[list[int]] = None,
                  default_original: int = 0):
        self._clear_cards()
        self._probe = probe
        if probe is None or not probe.audio_streams:
            self._empty.setText("No audio tracks found" if probe else "Select a file to view its audio tracks")
            self._empty.show()
            return
        self._empty.hide()
        self._default_original = default_original
        order = audio_order if audio_order is not None else list(range(len(probe.audio_streams)))
        for new_pos, orig in enumerate(order):
            stream = probe.audio_streams[orig]
            card = TrackCard(stream, orig, self)
            card.set_new_position(new_pos)
            card.set_default(orig == default_original)
            card.previewRequested.connect(self.preview_requested.emit)
            card.defaultRequested.connect(self._on_default_clicked)
            self._stack.addWidget(card)
            self._cards.append(card)

    def current_order(self) -> list[int]:
        return [c.original_position for c in self._cards]

    # --- internals ---
    def _clear_cards(self):
        for c in self._cards:
            c.setParent(None)
            c.deleteLater()
        self._cards.clear()

    def _on_default_clicked(self, orig_pos: int):
        self._default_original = orig_pos
        for c in self._cards:
            c.set_default(c.original_position == orig_pos)
        self.default_changed.emit(orig_pos)

    # --- drag & drop ---
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasFormat(MIME_TRACK):
            e.acceptProposedAction()

    def dragMoveEvent(self, e: QDragMoveEvent):
        if not e.mimeData().hasFormat(MIME_TRACK):
            return
        e.acceptProposedAction()
        # highlight the card the cursor is over
        y = e.position().y()
        for c in self._cards:
            top = c.y()
            inside = top <= y <= top + c.height()
            c.setProperty("ghost", inside)
            c.style().unpolish(c)
            c.style().polish(c)

    def dropEvent(self, e: QDropEvent):
        src_original = int(bytes(e.mimeData().data(MIME_TRACK)).decode())
        y = e.position().y()
        target_idx = len(self._cards) - 1
        for i, c in enumerate(self._cards):
            if y < c.y() + c.height() / 2:
                target_idx = i
                break

        # Find source index in current list
        src_idx = next(
            (i for i, c in enumerate(self._cards) if c.original_position == src_original), None
        )
        if src_idx is None or src_idx == target_idx:
            self._clear_ghosts()
            e.acceptProposedAction()
            return

        # Reorder
        card = self._cards.pop(src_idx)
        # Adjust target after pop
        if target_idx > src_idx:
            target_idx -= 1
        self._cards.insert(target_idx, card)

        # Rebuild layout
        while self._stack.count():
            self._stack.takeAt(0)
        for i, c in enumerate(self._cards):
            self._stack.addWidget(c)
            c.set_new_position(i)

        self._clear_ghosts()
        e.acceptProposedAction()
        self.order_changed.emit(self.current_order())

    def _clear_ghosts(self):
        for c in self._cards:
            c.setProperty("ghost", False)
            c.style().unpolish(c)
            c.style().polish(c)
