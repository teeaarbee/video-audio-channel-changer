from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag, QMouseEvent, QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
    QSizePolicy,
)

from ..probe import Stream, language_badge


MIME_TRACK = "application/x-vac-track"


class TrackCard(QFrame):
    """A draggable card representing an audio track.

    Emits previewRequested(original_position) when user clicks the speaker.
    Emits defaultRequested(original_position) to mark as default.
    """
    previewRequested = Signal(int)
    defaultRequested = Signal(int)

    def __init__(self, stream: Stream, original_position: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("trackCard")
        self.setProperty("selected", False)
        self.setProperty("ghost", False)
        self.stream = stream
        self.original_position = original_position  # 0-based audio index in source
        self.is_default = False
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(72)

        self._drag_start: Optional[tuple[int, int]] = None

        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(14)

        # Drag handle + big position number
        handle_col = QVBoxLayout()
        handle_col.setSpacing(0)
        self.num_label = QLabel()
        self.num_label.setAlignment(Qt.AlignCenter)
        self.num_label.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #b7bdff;"
            "min-width: 40px;"
        )
        handle_col.addWidget(self.num_label)
        handle = QLabel("⋮⋮")
        handle.setAlignment(Qt.AlignCenter)
        handle.setStyleSheet("color: #5c6573; font-size: 12px;")
        handle.setToolTip("Drag to reorder")
        handle_col.addWidget(handle)
        root.addLayout(handle_col)

        # Main info
        info = QVBoxLayout()
        info.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        title_row.addWidget(self.title_label)

        self.default_badge = QLabel("DEFAULT")
        self.default_badge.setObjectName("badgeAccent")
        self.default_badge.hide()
        title_row.addWidget(self.default_badge)

        title_row.addStretch(1)
        info.addLayout(title_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        self.codec_badge = QLabel()
        self.codec_badge.setObjectName("badge")
        self.lang_badge = QLabel()
        self.lang_badge.setObjectName("badge")
        self.ch_badge = QLabel()
        self.ch_badge.setObjectName("badge")
        for w in (self.codec_badge, self.lang_badge, self.ch_badge):
            meta_row.addWidget(w)
        meta_row.addStretch(1)
        info.addLayout(meta_row)
        root.addLayout(info, 1)

        # Controls
        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("icon")
        self.play_btn.setToolTip("Preview this track for ~6s")
        self.play_btn.setFixedWidth(40)
        self.play_btn.clicked.connect(lambda: self.previewRequested.emit(self.original_position))
        btns.addWidget(self.play_btn)

        self.default_btn = QPushButton("★")
        self.default_btn.setObjectName("icon")
        self.default_btn.setToolTip("Make this the default track in output")
        self.default_btn.setFixedWidth(40)
        self.default_btn.clicked.connect(lambda: self.defaultRequested.emit(self.original_position))
        btns.addWidget(self.default_btn)

        root.addLayout(btns)

        self._refresh_text()

    def set_new_position(self, new_pos_0based: int):
        self.num_label.setText(str(new_pos_0based + 1))
        moved = new_pos_0based != self.original_position
        self.num_label.setStyleSheet(
            "font-size: 26px; font-weight: 800; min-width: 40px; "
            + ("color: #a78bfa;" if moved else "color: #6366f1;")
        )

    def set_default(self, is_default: bool):
        self.is_default = is_default
        self.default_badge.setVisible(is_default)

    def _refresh_text(self):
        s = self.stream
        original_label = f"Track {self.original_position + 1}"
        title_text = s.title.strip() if s.title and "Handler" not in s.title else ""
        display = f"{original_label}" + (f" — {title_text}" if title_text else "")
        self.title_label.setText(display)
        self.codec_badge.setText((s.codec_name or "audio").upper())
        self.lang_badge.setText(language_badge(s.language))
        ch = s.pretty_channels or "?"
        extras = []
        if s.sample_rate:
            try:
                extras.append(f"{int(s.sample_rate) // 1000} kHz")
            except ValueError:
                pass
        if s.bit_rate:
            try:
                extras.append(f"{int(s.bit_rate) // 1000} kbps")
            except ValueError:
                pass
        self.ch_badge.setText(" · ".join([ch] + extras) if extras else ch)

    # --- Drag source ---
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._drag_start = (e.position().x(), e.position().y())
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent):
        if not (e.buttons() & Qt.LeftButton) or self._drag_start is None:
            return
        dx = e.position().x() - self._drag_start[0]
        dy = e.position().y() - self._drag_start[1]
        if (dx * dx + dy * dy) < 36:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_TRACK, str(self.original_position).encode())
        drag.setMimeData(mime)

        # Pretty pixmap
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.92)
        self.render(painter)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(e.position().toPoint())
        drag.exec(Qt.MoveAction)
        self._drag_start = None
