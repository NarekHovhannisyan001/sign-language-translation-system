import sys
import os
import shutil
import cv2

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QFrame, QSizePolicy, QComboBox, QCheckBox, QMenu
)
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QPoint

QUICK_PHRASES = [
    "Բարև Ձեզ","Ինչպե՞ս եք","Շնորհակալություն",
    "Ես ուզում եմ", "Օգնեք ինձ", "Հասկացա",
    "Ոչ", "Այո", "Ճիշտ է", "Ցտեսություն"
]


# ─────────────────────────────────────────────
# Video Playback Worker
# ─────────────────────────────────────────────
class VideoWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    finished    = pyqtSignal()

    def __init__(self, video_path, size=(600, 400), speed=1.0, loop=False):
        super().__init__()
        self.video_path = video_path
        self.size       = size
        self.speed      = speed   # 0.5 / 1.0 / 1.5 / 2.0
        self.loop       = loop    # if True, seeks back to frame 0 instead of stopping
        self._stop      = False
        self._paused    = False

    def stop(self):   self._stop   = True
    def pause(self):  self._paused = True
    def resume(self): self._paused = False
    def set_speed(self, speed): self.speed = speed

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        while cap.isOpened() and not self._stop:
            if self._paused:
                self.msleep(50)
                continue
            ret, frame = cap.read()
            if not ret:
                if self.loop:
                    # Seek back to beginning — no gap, no new thread
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
                    continue
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, self.size)
            h, w, ch = frame.shape
            img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.frame_ready.emit(img.copy())
            delay = max(1, int(1000 / (fps * self.speed)))
            self.msleep(delay)
        cap.release()
        self.finished.emit()


# ─────────────────────────────────────────────
# Reusable Widgets
# ─────────────────────────────────────────────
class ToolBtn(QPushButton):
    def __init__(self, text, accent=False, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        if accent:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00c6ff,stop:1 #0072ff);
                    color: white; border: none; border-radius: 7px;
                    padding: 0 18px; letter-spacing: 1px;
                }
                QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #33d6ff,stop:1 #2299ff); }
                QPushButton:disabled { background: #1a1a2e; color: #333355; }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #8899cc;
                    border: 1px solid #1e1e40; border-radius: 7px;
                    padding: 0 14px; letter-spacing: 1px;
                }
                QPushButton:hover { background: #0e0e28; color: #aabbee; border-color: #3344aa; }
                QPushButton:disabled { color: #252540; border-color: #111128; }
            """)


class PhraseChip(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Courier New", 10))
        self.setStyleSheet("""
            QPushButton { background:#0d0d24; color:#7788bb;
                border:1px solid #1e1e44; border-radius:15px; padding:0 14px; }
            QPushButton:hover { background:#141438; color:#aabbee; border-color:#3344aa; }
            QPushButton:pressed { background:#0a0a1e; }
        """)


# ─────────────────────────────────────────────
# Video Panel
# ─────────────────────────────────────────────
class VideoPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("QFrame { background:#03030f; border:1px solid #0e0e2a; border-radius:10px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_label.setStyleSheet("background:#03030f; border-radius:10px 10px 0 0;")

        self.placeholder = QLabel("[ Sign Preview ]")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setFont(QFont("Courier New", 13))
        self.placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.placeholder.setStyleSheet("color:#111130; background:transparent; letter-spacing:3px;")

        stack = QWidget()
        stack.setStyleSheet("background:transparent;")
        sl = QVBoxLayout(stack)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(self.video_label)
        self.video_label.hide()
        sl.addWidget(self.placeholder)
        layout.addWidget(stack)

        # Controls bar
        ctrl = QFrame()
        ctrl.setFixedHeight(82)
        ctrl.setStyleSheet("QFrame { background:#07071a; border-top:1px solid #0e0e28; border-radius:0 0 10px 10px; }")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(14, 0, 14, 0)
        cl.setSpacing(6)

        pbtn_small = """
            QPushButton { background:transparent; color:#556688; border:none; font-size:22px; padding:0 5px; }
            QPushButton:hover { color:#aabbee; }
            QPushButton:disabled { color:#1e1e3a; }
        """
        pbtn_large = """
            QPushButton { background:#0d0d28; color:#aabbee; border:1px solid #1e1e44;
                border-radius:12px; font-size:30px; padding:0; }
            QPushButton:hover { background:#141440; color:#00c6ff; border-color:#0050cc; }
            QPushButton:pressed { background:#080820; }
            QPushButton:disabled { color:#1e1e3a; border-color:#111128; background:transparent; }
        """

        self.btn_prev   = QPushButton("⏮"); self.btn_prev.setFixedSize(50, 50)
        self.btn_play   = QPushButton("▶"); self.btn_play.setFixedSize(66, 66)
        self.btn_next   = QPushButton("⏭"); self.btn_next.setFixedSize(50, 50)
        self.btn_replay = QPushButton("↺"); self.btn_replay.setFixedSize(50, 50)

        self.btn_prev.setStyleSheet(pbtn_small)
        self.btn_play.setStyleSheet(pbtn_large)
        self.btn_next.setStyleSheet(pbtn_small)
        self.btn_replay.setStyleSheet(pbtn_small)

        for b in [self.btn_prev, self.btn_play, self.btn_next, self.btn_replay]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.loop_check = QCheckBox("Loop")
        self.loop_check.setFont(QFont("Courier New", 9))
        self.loop_check.setStyleSheet("color:#334466; spacing:4px;")

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5×", "1×", "1.5×", "2×"])
        self.speed_combo.setCurrentIndex(1)
        self.speed_combo.setFixedWidth(62)
        self.speed_combo.setFont(QFont("Courier New", 9))
        self.speed_combo.setStyleSheet("""
            QComboBox { background:#0a0a1e; color:#556688; border:1px solid #1a1a35;
                border-radius:4px; padding:2px 6px; }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView { background:#0d0d22; color:#8899cc;
                border:1px solid #1a1a35; selection-background-color:#1a2a5a; }
        """)

        self.status_dot  = QLabel("●")
        self.status_dot.setFont(QFont("Courier New", 8))
        self.status_dot.setStyleSheet("color:#1e1e3a;")
        self.status_text = QLabel("STANDBY")
        self.status_text.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.status_text.setStyleSheet("color:#1e1e3a; letter-spacing:2px;")

        cl.addStretch()
        cl.addWidget(self.btn_prev)
        cl.addWidget(self.btn_play)
        cl.addWidget(self.btn_next)
        cl.addWidget(self.btn_replay)
        cl.addStretch()
        cl.addWidget(self.loop_check)
        cl.addWidget(self.speed_combo)
        cl.addSpacing(8)
        cl.addWidget(self.status_dot)
        cl.addWidget(self.status_text)
        layout.addWidget(ctrl)

    def show_frame(self, img):
        self.placeholder.hide()
        self.video_label.show()
        pix = QPixmap.fromImage(img)
        self.video_label.setPixmap(
            pix.scaled(self.video_label.size(),
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        )

    def set_status(self, text, color="#1e1e3a", playing=False):
        self.status_dot.setStyleSheet(f"color:{color}; font-family:'Courier New';")
        self.status_text.setText(text)
        self.status_text.setStyleSheet(
            f"color:{color}; font-family:'Courier New'; font-size:8px; font-weight:700; letter-spacing:2px;"
        )
        self.btn_play.setText("⏸" if playing else "▶")



# ─────────────────────────────────────────────
# Smart Text Input — Enter triggers translate
# Shift+Enter adds a new line
# ─────────────────────────────────────────────
class ArmenianTextInput(QTextEdit):
    enter_pressed = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)   # Shift+Enter = new line
            else:
                self.enter_pressed.emit()       # Enter = translate
        else:
            super().keyPressEvent(event)

# ─────────────────────────────────────────────
# Main Window — UI only, emits signals to main.py
# ─────────────────────────────────────────────
class MainWindow(QWidget):
    # Signals emitted to main.py — no logic here
    translate_requested = pyqtSignal(str)   # user pressed Translate
    replay_requested    = pyqtSignal()      # user pressed Replay
    prev_requested      = pyqtSignal()      # user pressed ⏮
    next_requested      = pyqtSignal()      # user pressed ⏭
    save_requested      = pyqtSignal()      # user pressed Save

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sign Language Translation System")
        self.setMinimumSize(1100, 720)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("QWidget { background:#06060f; color:#c8d8ff; }")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── TOOLBAR ──────────────────────────
        toolbar = QFrame()
        toolbar.setFixedHeight(54)
        toolbar.setStyleSheet("QFrame { background:#08081a; border-bottom:1px solid #0e0e28; }")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(20, 0, 20, 0)
        tb.setSpacing(8)

        logo = QLabel("SLTS")
        logo.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        logo.setStyleSheet("color:#00c6ff; letter-spacing:6px; margin-right:16px;")

        self.btn_replay_tb = ToolBtn("↺ Replay")
        self.btn_replay_tb.setFixedWidth(100)
        self.btn_replay_tb.setEnabled(False)
        self.btn_replay_tb.clicked.connect(self.replay_requested)

        self.btn_save = ToolBtn("⬇ Save")
        self.btn_save.setFixedWidth(90)
        self.btn_save.clicked.connect(self.save_requested)

        self.btn_export = ToolBtn("Export ▾")
        self.btn_export.setFixedWidth(100)
        self.btn_export.clicked.connect(self._export_menu)

        self.btn_settings = ToolBtn("⚙")
        self.btn_settings.setFixedWidth(40)

        tb.addWidget(logo)
        tb.addWidget(self.btn_replay_tb)
        tb.addWidget(self.btn_save)
        tb.addWidget(self.btn_export)
        tb.addStretch()
        tb.addWidget(self.btn_settings)
        root.addWidget(toolbar)

        # ── TWO PANELS ───────────────────────
        panels = QHBoxLayout()
        panels.setContentsMargins(20, 16, 20, 12)
        panels.setSpacing(16)

        # Left panel
        left_widget = QWidget()
        left_widget.setFixedWidth(360)
        left = QVBoxLayout(left_widget)
        left.setSpacing(10)
        left.setContentsMargins(0, 0, 0, 0)

        lh = QLabel("Armenian Text")
        lh.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        lh.setStyleSheet("color:#334466; letter-spacing:2px;")
        left.addWidget(lh)

        self.text_input = ArmenianTextInput()
        self.text_input.setPlaceholderText("Գրեք հայերեն տեքստ…")
        self.text_input.setFont(QFont("Courier New", 14))
        self.text_input.setMinimumHeight(160)
        self.text_input.setMaximumHeight(220)
        self.text_input.setStyleSheet("""
            QTextEdit { background:#09091e; color:#c8d8ff;
                border:1px solid #1a1a3a; border-radius:10px; padding:14px;
                selection-background-color:#1a3a8a; }
            QTextEdit:focus { border:1px solid #0050cc; }
        """)
        left.addWidget(self.text_input)

        self.btn_translate = QPushButton("▶  TRANSLATE")
        self.btn_translate.setFixedSize(200, 44)
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        self.btn_translate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00c6ff,stop:1 #0072ff);
                color: white; border: none; border-radius: 10px; letter-spacing: 2px;
            }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #33d6ff,stop:1 #2299ff); }
            QPushButton:disabled { background: #1a1a2e; color: #333355; }
        """)
        self.btn_translate.clicked.connect(self._on_translate_clicked)
        self.text_input.enter_pressed.connect(self._on_translate_clicked)
        tr = QHBoxLayout()
        tr.addStretch(); tr.addWidget(self.btn_translate); tr.addStretch()
        left.addLayout(tr)

        tok_hdr = QLabel("Parsed tokens")
        tok_hdr.setFont(QFont("Courier New", 9))
        tok_hdr.setStyleSheet("color:#222244; letter-spacing:2px;")
        left.addWidget(tok_hdr)

        self.parsed_label = QLabel("")
        self.parsed_label.setFont(QFont("Courier New", 10))
        self.parsed_label.setStyleSheet("color:#4455aa; letter-spacing:1px;")
        self.parsed_label.setWordWrap(True)
        left.addWidget(self.parsed_label)

        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Courier New", 9))
        self.info_label.setStyleSheet("color:#ff5252; letter-spacing:1px;")
        self.info_label.setWordWrap(True)
        left.addWidget(self.info_label)
        left.addStretch()

        # Right panel
        right_widget = QWidget()
        right_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right = QVBoxLayout(right_widget)
        right.setSpacing(10)
        right.setContentsMargins(0, 0, 0, 0)

        rh = QLabel("Sign Preview")
        rh.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        rh.setStyleSheet("color:#334466; letter-spacing:2px;")
        right.addWidget(rh)

        self.video_panel = VideoPanel()
        self.video_panel.btn_play.clicked.connect(self._on_play_clicked)
        self.video_panel.btn_replay.clicked.connect(self.replay_requested)
        self.video_panel.btn_prev.clicked.connect(self.prev_requested)
        self.video_panel.btn_next.clicked.connect(self.next_requested)
        right.addWidget(self.video_panel)

        panels.addWidget(left_widget)
        panels.addWidget(right_widget)
        panels_widget = QWidget()
        panels_widget.setLayout(panels)
        root.addWidget(panels_widget)

        # ── PHRASE CHIPS ─────────────────────
        chips_frame = QFrame()
        chips_frame.setFixedHeight(54)
        chips_frame.setStyleSheet("QFrame { background:#07071a; border-top:1px solid #0e0e28; }")
        cl = QHBoxLayout(chips_frame)
        cl.setContentsMargins(20, 0, 20, 0)
        cl.setSpacing(8)
        ql = QLabel("Quick:")
        ql.setFont(QFont("Courier New", 9))
        ql.setStyleSheet("color:#222244; letter-spacing:1px;")
        cl.addWidget(ql)
        for phrase in QUICK_PHRASES:
            chip = PhraseChip(phrase)
            chip.clicked.connect(lambda _, p=phrase: self._insert_phrase(p))
            cl.addWidget(chip)
        cl.addStretch()
        root.addWidget(chips_frame)

    # ── UI-only helpers ───────────────────────
    def _on_translate_clicked(self):
        text = self.text_input.toPlainText().strip()
        if text:
            self.translate_requested.emit(text)

    def _on_play_clicked(self):
        # Emit toggle signal — main.py handles pause/resume state
        self.video_panel.btn_play.setText(
            "▶" if self.video_panel.btn_play.text() == "⏸" else "⏸"
        )

    def _insert_phrase(self, phrase):
        cur = self.text_input.toPlainText().strip()
        self.text_input.setPlainText((cur + " " + phrase).strip())

    def _export_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background:#0d0d22; color:#8899cc; border:1px solid #1e1e40;
                border-radius:6px; padding:4px; }
            QMenu::item { padding:6px 20px; border-radius:4px; }
            QMenu::item:selected { background:#1a2a5a; color:#aabbee; }
        """)
        menu.addAction("Export as MP4")
        menu.addAction("Export as GIF")
        menu.addAction("Export as WebM")
        menu.exec(self.btn_export.mapToGlobal(QPoint(0, self.btn_export.height())))

    # ── Public methods called by main.py ──────
    def set_status(self, text, color="#1e1e3a", playing=False):
        self.video_panel.set_status(text, color, playing)

    def set_parsed(self, text):
        self.parsed_label.setText(text)

    def set_error(self, text):
        self.info_label.setText(f"⚠ {text}" if text else "")

    def set_translate_enabled(self, enabled):
        self.btn_translate.setEnabled(enabled)

    def set_replay_enabled(self, enabled):
        self.btn_replay_tb.setEnabled(enabled)

    def set_nav_enabled(self, prev, nxt):
        self.video_panel.btn_prev.setEnabled(prev)
        self.video_panel.btn_next.setEnabled(nxt)

    def clear_input(self):
        self.text_input.clear()

    def set_input_enabled(self, enabled):
        self.text_input.setEnabled(enabled)
        # Dim the text box visually when disabled
        self.text_input.setStyleSheet("""
            QTextEdit { background:%s; color:%s;
                border:1px solid #1a1a3a; border-radius:10px; padding:14px;
                selection-background-color:#1a3a8a; }
            QTextEdit:focus { border:1px solid #0050cc; }
        """ % (('#06060f' if not enabled else '#09091e'),
               ('#333355' if not enabled else '#c8d8ff')))

    def show_frame(self, img):
        self.video_panel.show_frame(img)