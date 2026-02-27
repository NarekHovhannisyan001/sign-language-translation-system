import sys
import os
import shutil
import cv2
import json

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QFrame, QGraphicsDropShadowEffect, QSizePolicy,
    QScrollArea, QComboBox, QCheckBox, QMenu
)
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QPen, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QPoint

qci = []
current_video_path = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(os.path.dirname(BASE_DIR), "assets", "signlang_kp")

QUICK_PHRASES = [
    "Բարև", "Շնորհակալություն", "Ինչպե՞ս եք",
    "Ես ուզում եմ", "Օգնեք ինձ", "Հասկացա",
    "Ոչ", "Այո", "Ճիշտ է", "Ցտեսություն"
]


# ─────────────────────────────────────────────
#  Worker Thread
# ─────────────────────────────────────────────
class VideoWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    finished = pyqtSignal()

    def __init__(self, video_path, size=(600, 400)):
        super().__init__()
        self.video_path = video_path
        self.size = size
        self._stop = False
        self._paused = False

    def stop(self):   self._stop = True
    def pause(self):  self._paused = True
    def resume(self): self._paused = False

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        delay = max(1, int(1000 / fps))
        while cap.isOpened() and not self._stop:
            if self._paused:
                self.msleep(50)
                continue
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, self.size)
            h, w, ch = frame.shape
            img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
            img = img.copy()
            self.frame_ready.emit(img)
            self.msleep(delay)
        cap.release()
        self.finished.emit()


# ─────────────────────────────────────────────
#  Reusable Widgets
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


class WordBadge(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, word, found=True, parent=None):
        super().__init__(parent)
        self.word = word
        self.found = found
        self.setText(f" {word} {'✓' if found else '✗'} ")
        self.setFont(QFont("Courier New", 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor if found else Qt.CursorShape.ArrowCursor)
        if found:
            self.setStyleSheet("""
                QLabel { color:#00e676; background:rgba(0,230,118,12);
                    border:1px solid rgba(0,230,118,40); border-radius:6px; padding:3px 6px; }
                QLabel:hover { background:rgba(0,230,118,22); }
            """)
        else:
            self.setStyleSheet("""
                QLabel { color:#ff5252; background:rgba(255,82,82,12);
                    border:1px solid rgba(255,82,82,40); border-radius:6px; padding:3px 6px; }
            """)

    def mousePressEvent(self, e):
        if self.found:
            self.clicked.emit(self.word)


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
#  Video Panel (right side)
# ─────────────────────────────────────────────
class VideoPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("QFrame { background:#03030f; border:1px solid #0e0e2a; border-radius:10px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video area
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_label.setStyleSheet("background:#03030f; border-radius:10px 10px 0 0;")

        self.placeholder = QLabel("[ Sign Preview ]")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setFont(QFont("Courier New", 13))
        self.placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.placeholder.setStyleSheet("color:#111130; background:transparent; letter-spacing:3px;")

        # Stack
        self.stack = QWidget()
        self.stack.setStyleSheet("background:transparent;")
        sl = QVBoxLayout(self.stack)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(self.video_label)
        self.video_label.hide()
        sl.addWidget(self.placeholder)
        layout.addWidget(self.stack)

        # Controls bar
        ctrl = QFrame()
        ctrl.setFixedHeight(72)
        ctrl.setStyleSheet("QFrame { background:#07071a; border-top:1px solid #0e0e28; border-radius:0 0 10px 10px; }")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(14, 0, 14, 0)
        cl.setSpacing(6)

        pbtn_small = """
            QPushButton { background:transparent; color:#556688; border:none; font-size:20px; padding:0 5px; }
            QPushButton:hover { color:#aabbee; }
            QPushButton:disabled { color:#1e1e3a; }
        """
        pbtn_large = """
            QPushButton { background:#0d0d28; color:#aabbee; border:1px solid #1e1e44;
                border-radius:10px; font-size:26px; padding:0; }
            QPushButton:hover { background:#141440; color:#00c6ff; border-color:#0050cc; }
            QPushButton:pressed { background:#080820; }
            QPushButton:disabled { color:#1e1e3a; border-color:#111128; background:transparent; }
        """
        self.btn_prev   = QPushButton("⏮"); self.btn_prev.setFixedSize(42, 42)
        self.btn_play   = QPushButton("▶"); self.btn_play.setFixedSize(56, 56)
        self.btn_next   = QPushButton("⏭"); self.btn_next.setFixedSize(42, 42)
        self.btn_replay = QPushButton("↺"); self.btn_replay.setFixedSize(42, 42)
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

        cl.addWidget(self.btn_prev)
        cl.addWidget(self.btn_play)
        cl.addWidget(self.btn_next)
        cl.addWidget(self.btn_replay)
        cl.addSpacing(8)
        cl.addWidget(self.loop_check)
        cl.addWidget(self.speed_combo)
        cl.addStretch()
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
#  Main Window
# ─────────────────────────────────────────────
class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sign Language Translation System")
        self.setMinimumSize(1100, 720)
        self._idle_worker = None
        self._main_worker = None
        self._is_paused   = False
        self._loop        = False
        self._setup_ui()
        self._start_idle()

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

        self.btn_replay_tb = ToolBtn("↺  Replay")
        self.btn_replay_tb.setFixedWidth(100)
        self.btn_replay_tb.setEnabled(False)
        self.btn_replay_tb.clicked.connect(self.handle_replay)

        self.btn_save = ToolBtn("⬇  Save")
        self.btn_save.setFixedWidth(90)
        self.btn_save.clicked.connect(self.handle_download)

        self.btn_export = ToolBtn("Export ▾")
        self.btn_export.setFixedWidth(100)
        self.btn_export.clicked.connect(self._show_export_menu)

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

        self.text_input = QTextEdit()
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

        # Centered Translate button below text input
        self.btn_translate = QPushButton("▶  TRANSLATE")
        self.btn_translate.setFixedSize(200, 44)
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        self.btn_translate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00c6ff,stop:1 #0072ff);
                color: white; border: none; border-radius: 10px;
                letter-spacing: 2px;
            }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #33d6ff,stop:1 #2299ff); }
            QPushButton:pressed { opacity: 0.8; }
            QPushButton:disabled { background: #1a1a2e; color: #333355; }
        """)
        self.btn_translate.clicked.connect(self.handle_submit)
        translate_row = QHBoxLayout()
        translate_row.addStretch()
        translate_row.addWidget(self.btn_translate)
        translate_row.addStretch()
        left.addLayout(translate_row)

        tok_hdr = QLabel("Word recognition")
        tok_hdr.setFont(QFont("Courier New", 9))
        tok_hdr.setStyleSheet("color:#222244; letter-spacing:2px;")
        left.addWidget(tok_hdr)

        tok_scroll = QScrollArea()
        tok_scroll.setFixedHeight(48)
        tok_scroll.setWidgetResizable(True)
        tok_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tok_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tok_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.token_widget = QWidget()
        self.token_widget.setStyleSheet("background:transparent;")
        self.token_layout = QHBoxLayout(self.token_widget)
        self.token_layout.setContentsMargins(0, 4, 0, 4)
        self.token_layout.setSpacing(6)
        self.token_layout.addStretch()
        tok_scroll.setWidget(self.token_widget)
        left.addWidget(tok_scroll)

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
        self.video_panel.btn_play.clicked.connect(self._toggle_pause)
        self.video_panel.btn_replay.clicked.connect(self.handle_replay)
        self.video_panel.loop_check.stateChanged.connect(
            lambda s: setattr(self, '_loop', s == Qt.CheckState.Checked.value)
        )
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

    # ── Helpers ──────────────────────────────
    def _insert_phrase(self, phrase):
        cur = self.text_input.toPlainText().strip()
        self.text_input.setPlainText((cur + " " + phrase).strip())

    def _show_export_menu(self):
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

    def _toggle_pause(self):
        if self._main_worker and self._main_worker.isRunning():
            if self._is_paused:
                self._main_worker.resume()
                self._is_paused = False
                self.video_panel.set_status("PLAYING", "#00ffaa", playing=True)
            else:
                self._main_worker.pause()
                self._is_paused = True
                self.video_panel.set_status("PAUSED", "#ffaa00", playing=False)

    def _update_tokens(self, text):
        for i in reversed(range(self.token_layout.count())):
            w = self.token_layout.itemAt(i).widget()
            if w: w.deleteLater()

        missing = []
        for word in text.strip().split():
            found = os.path.isfile(os.path.join(JSON_DIR, f"{word}.json"))
            badge = WordBadge(word, found)
            self.token_layout.insertWidget(self.token_layout.count() - 1, badge)
            if not found:
                missing.append(word)

        self.info_label.setText(
            f"⚠ Missing keypoints: {', '.join(missing)}" if missing else ""
        )

    # ── Playback ─────────────────────────────
    def _start_idle(self):
        idle = os.path.join(BASE_DIR, "idle.mp4")
        if not os.path.exists(idle):
            self.video_panel.set_status("IDLE.MP4 NOT FOUND", "#ff4466")
            return
        self._idle_worker = VideoWorker(idle)
        self._idle_worker.frame_ready.connect(self.video_panel.show_frame)
        self._idle_worker.finished.connect(self._start_idle)
        self._idle_worker.start()
        self.video_panel.set_status("STANDBY", "#1e2e5a")

    def _stop_idle(self):
        if self._idle_worker:
            self._idle_worker.finished.disconnect()
            self._idle_worker.stop()
            self._idle_worker = None

    def handle_submit(self):
        prompt = self.text_input.toPlainText().strip()
        if not prompt:
            return

        global current_video_path, qci
        qci = prompt.split()
        self._update_tokens(prompt)

        video_path = os.path.join(BASE_DIR, "idle.mp4")
        if not os.path.exists(video_path):
            self.video_panel.set_status("VIDEO NOT FOUND", "#ff4466")
            return

        current_video_path = video_path
        self._stop_idle()
        self._is_paused = False
        self.btn_translate.setEnabled(False)
        self.btn_replay_tb.setEnabled(False)
        self.video_panel.set_status("TRANSLATING", "#00ffaa", playing=True)

        self._main_worker = VideoWorker(video_path)
        self._main_worker.frame_ready.connect(self.video_panel.show_frame)
        self._main_worker.finished.connect(self._on_main_finished)
        self._main_worker.start()

    def _on_main_finished(self):
        self.btn_translate.setEnabled(True)
        self.btn_replay_tb.setEnabled(True)
        self.video_panel.set_status("DONE  ✓", "#00e676")
        if self._loop and current_video_path:
            self.handle_replay()
        else:
            self._start_idle()

    def handle_replay(self):
        if not current_video_path or not os.path.exists(current_video_path):
            self.video_panel.set_status("NOTHING TO REPLAY", "#ff4466")
            return
        self._stop_idle()
        self._is_paused = False
        self.btn_replay_tb.setEnabled(False)
        self.video_panel.set_status("REPLAYING", "#00c6ff", playing=True)
        self._main_worker = VideoWorker(current_video_path)
        self._main_worker.frame_ready.connect(self.video_panel.show_frame)
        self._main_worker.finished.connect(self._on_main_finished)
        self._main_worker.start()

    def handle_download(self):
        if not current_video_path or not os.path.exists(current_video_path):
            self.video_panel.set_status("NO VIDEO LOADED", "#ff4466")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save", "translation.mp4", "Video (*.mp4)")
        if path:
            try:
                shutil.copy(current_video_path, path)
                self.video_panel.set_status("SAVED  ✓", "#00e676")
            except Exception:
                self.video_panel.set_status("SAVE FAILED", "#ff4466")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())