QSS = """
* { font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif; }

QMainWindow, QWidget#root { background: #0f1115; color: #e8ecf1; }

QLabel { color: #e8ecf1; }
QLabel#h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }
QLabel#h2 { font-size: 14px; font-weight: 600; color: #c9d1da; }
QLabel#dim { color: #8a94a4; font-size: 12px; }
QLabel#badge {
    background: #1b2230; color: #9fb0c6; border: 1px solid #2a3446;
    border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 600;
}
QLabel#badgeAccent {
    background: #1e2140; color: #b7bdff; border: 1px solid #3a3f73;
    border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 600;
}

QFrame#card {
    background: #161a22; border: 1px solid #232a36; border-radius: 14px;
}
QFrame#trackCard {
    background: #181c26; border: 1px solid #2a3140; border-radius: 12px;
}
QFrame#trackCard[selected="true"] { border: 1px solid #6366f1; background: #1b1f34; }
QFrame#trackCard[ghost="true"] { border: 1px dashed #6366f1; background: #12141b; }

QPushButton {
    background: #1b2230; color: #e8ecf1; border: 1px solid #2a3446;
    border-radius: 10px; padding: 8px 14px; font-weight: 600;
}
QPushButton:hover { background: #222a3a; border-color: #3a4458; }
QPushButton:pressed { background: #161c28; }
QPushButton:disabled { color: #5c6573; background: #141821; border-color: #1f2532; }

QPushButton#primary {
    background: qlineargradient(x1:0 y1:0 x2:1 y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
    color: white; border: none;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0 y1:0 x2:1 y2:1, stop:0 #7478ff, stop:1 #a07aff);
}
QPushButton#primary:disabled { background: #2b2f46; color: #8c93ae; }

QPushButton#danger { color: #ffb3b3; border-color: #4a2a30; }
QPushButton#danger:hover { background: #2a1a1f; }

QPushButton#ghost { background: transparent; border: 1px solid transparent; color: #9fb0c6; }
QPushButton#ghost:hover { background: #1b2230; color: #e8ecf1; }

QPushButton#icon {
    background: #1b2230; border: 1px solid #2a3446; border-radius: 8px;
    padding: 4px 8px; font-weight: 700;
}
QPushButton#icon:hover { background: #222a3a; }

QListWidget {
    background: #12151c; border: 1px solid #232a36; border-radius: 12px;
    padding: 6px; outline: none;
}
QListWidget::item {
    background: #161a22; border: 1px solid #232a36; border-radius: 10px;
    padding: 10px 12px; margin: 4px 2px; color: #e8ecf1;
}
QListWidget::item:selected { background: #1b1f34; border-color: #6366f1; color: #e8ecf1; }
QListWidget::item:hover { background: #1a1f29; }

QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2a3446; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3a4458; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #2a3446; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QProgressBar {
    background: #12151c; border: 1px solid #232a36; border-radius: 8px;
    text-align: center; color: #c9d1da; height: 16px; font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0 y1:0 x2:1 y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
    border-radius: 7px;
}

QComboBox, QLineEdit {
    background: #161a22; border: 1px solid #2a3446; border-radius: 8px;
    padding: 6px 10px; color: #e8ecf1;
}
QComboBox:hover, QLineEdit:hover { border-color: #3a4458; }
QComboBox QAbstractItemView {
    background: #161a22; color: #e8ecf1; border: 1px solid #2a3446;
    selection-background-color: #1b1f34;
}

QCheckBox { color: #c9d1da; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #3a4458;
    border-radius: 4px; background: #12151c;
}
QCheckBox::indicator:checked { background: #6366f1; border-color: #6366f1; }

QToolTip {
    background: #1b2230; color: #e8ecf1; border: 1px solid #2a3446;
    padding: 4px 8px; border-radius: 6px;
}

QPlainTextEdit {
    background: #0b0d12; color: #9fb0c6; border: 1px solid #232a36;
    border-radius: 10px; font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 11px;
}

QSplitter::handle { background: transparent; }
"""
