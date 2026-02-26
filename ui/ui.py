import sys
import os
import shutil
import cv2

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QLineEdit, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QThread

qci = []
current_video_path = None

# Always resolve paths relative to THIS script's folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class VideoWorker(QThread):
    frame_ready = pyqtSignal(QPixmap)
    finished = pyqtSignal()

    def __init__(self, video_path, size=(960, 540)):
        super().__init__()
        self.video_path = video_path
        self.size = size
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        while cap.isOpened() and not self._stop:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, self.size)
            # Keep frame in memory until QImage is done (prevents garbage collection bug)
            h, w, ch = frame.shape
            img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
            img = img.copy()  # detach from frame buffer
            pix = QPixmap.fromImage(img)
            self.frame_ready.emit(pix)
            self.msleep(33)
        cap.release()
        self.finished.emit()


class GlowButton(QPushButton):
    def __init__(self, text, color_start="#00c6ff", color_end="#0072ff", glow_color=None, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color_start}, stop:1 {color_end});
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 1px;
                padding: 0 28px;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
            QPushButton:pressed {{
                padding-top: 2px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(glow_color or color_start) if glow_color else QColor(color_start))
        self.setGraphicsEffect(shadow)


class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sign Language Translation System")
        self.setMinimumSize(1060, 700)
        self._idle_worker = None
        self._main_worker = None
        self._setup_ui()
        self._start_idle()

    def _setup_ui(self):
        self.setStyleSheet("QWidget { background-color: #0d0d14; color: #e0e0f0; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── HEADER ──
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("QFrame { background-color: #13131f; border-bottom: 1px solid #1e1e35; }")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(36, 0, 36, 0)

        title = QLabel("Sign Language Translation System")
        title.setFont(QFont("Courier New", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #00c6ff; letter-spacing: 2px;")

        badge = QLabel("● LIVE")
        badge.setFont(QFont("Courier New", 9))
        badge.setStyleSheet("color: #00ffaa; letter-spacing: 2px;")

        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(badge)
        root.addWidget(header)

        # ── BODY ──
        body = QVBoxLayout()
        body.setContentsMargins(40, 32, 40, 32)
        body.setSpacing(20)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Video container
        self.video_container = QFrame()
        self.video_container.setFixedSize(960, 540)
        self.video_container.setStyleSheet("""
            QFrame {
                background-color: #000010;
                border: 1px solid #1a1a40;
                border-radius: 14px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 198, 255, 50))
        self.video_container.setGraphicsEffect(shadow)

        self.video_label = QLabel(self.video_container)
        self.video_label.setGeometry(0, 0, 960, 540)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.placeholder = QLabel("մուտքագրեք բառ կամ արտահայտություն…", self.video_container)
        self.placeholder.setGeometry(0, 0, 960, 540)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setFont(QFont("Courier New", 13))
        self.placeholder.setStyleSheet("color: #2a2a55; background: transparent;")

        body.addWidget(self.video_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(12)

        self.input = QLineEdit()
        self.input.setPlaceholderText("մուտքագրեք տեքստն այստեղ…")
        self.input.setFixedHeight(52)
        self.input.setFont(QFont("Courier New", 13))
        self.input.setStyleSheet("""
            QLineEdit {
                background-color: #13131f;
                color: #e0e0f0;
                border: 1px solid #2a2a50;
                border-radius: 10px;
                padding: 0 18px;
            }
            QLineEdit:focus {
                border: 1px solid #00c6ff;
                background-color: #15152a;
            }
        """)
        self.input.returnPressed.connect(self.handle_submit)

        translate_btn = GlowButton("Թարգմանել", "#00c6ff", "#0072ff")
        translate_btn.setFixedWidth(140)
        translate_btn.clicked.connect(self.handle_submit)

        download_btn = GlowButton("Ներբեռնել", "#9b59b6", "#6c3483")
        download_btn.setFixedWidth(130)
        download_btn.clicked.connect(self.handle_download)

        self.replay_btn = GlowButton("↺  Կրկնել", "#1a6b3a", "#145229")
        self.replay_btn.setFixedWidth(130)
        self.replay_btn.setEnabled(False)
        self.replay_btn.setStyleSheet(self.replay_btn.styleSheet() + "QPushButton:disabled { background: #1a1a2a; color: #333355; }")
        self.replay_btn.clicked.connect(self.handle_replay)

        input_row.addWidget(self.input)
        input_row.addWidget(translate_btn)
        input_row.addWidget(download_btn)
        input_row.addWidget(self.replay_btn)
        body.addLayout(input_row)

        # Status bar
        self.status_label = QLabel("Idle")
        self.status_label.setFont(QFont("Courier New", 9))
        self.status_label.setStyleSheet("color: #444466; letter-spacing: 1px;")
        body.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft)

        body_widget = QWidget()
        body_widget.setLayout(body)
        root.addWidget(body_widget)

        # ── FOOTER ──
        footer = QFrame()
        footer.setFixedHeight(36)
        footer.setStyleSheet("background-color: #0a0a12; border-top: 1px solid #1a1a30;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(32, 0, 32, 0)
        f_lbl = QLabel("Sign Language Translation System  •  Armenian Sign Language  •  MediaPipe Holistic")
        f_lbl.setFont(QFont("Courier New", 8))
        f_lbl.setStyleSheet("color: #2a2a44;")
        f_layout.addWidget(f_lbl)
        root.addWidget(footer)

    def _set_status(self, text, color="#444466"):
        self.status_label.setText(f"● {text}")
        self.status_label.setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-size: 9px; letter-spacing: 1px;")

    def _start_idle(self):
        idle_video = os.path.join(BASE_DIR, "idle.mp4")
        if not os.path.exists(idle_video):
            self._set_status("idle.mp4 not found", "#ff4466")
            return
        self._idle_worker = VideoWorker(idle_video)
        self._idle_worker.frame_ready.connect(self._update_frame)
        self._idle_worker.finished.connect(self._start_idle)
        self._idle_worker.start()
        self._set_status("Idle", "#444466")

    def _stop_idle(self):
        if self._idle_worker:
            self._idle_worker.finished.disconnect()
            self._idle_worker.stop()
            self._idle_worker = None

    def _update_frame(self, pix):
        self.video_label.setPixmap(pix)
        self.placeholder.hide()

    def handle_submit(self):
        prompt = self.input.text().strip()
        if not prompt:
            return
        self.input.clear()

        global current_video_path, qci
        qci = prompt.split()

        video_path = os.path.join(BASE_DIR, "idle.mp4")
        if not os.path.exists(video_path):
            self._set_status("Video not found", "#ff4466")
            return

        current_video_path = video_path
        self._stop_idle()
        self._set_status("Playing…", "#00ffaa")
        self.replay_btn.setEnabled(True)

        self._main_worker = VideoWorker(video_path)
        self._main_worker.frame_ready.connect(self._update_frame)
        self._main_worker.finished.connect(self._on_main_finished)
        self._main_worker.start()

    def _on_main_finished(self):
        self._set_status("Done ✓", "#00ffaa")
        self._start_idle()

    def handle_replay(self):
        if current_video_path is None or not os.path.exists(current_video_path):
            self._set_status("No video to replay", "#ff4466")
            return
        self._stop_idle()
        self._set_status("Replaying…", "#00ffaa")
        self._main_worker = VideoWorker(current_video_path)
        self._main_worker.frame_ready.connect(self._update_frame)
        self._main_worker.finished.connect(self._on_main_finished)
        self._main_worker.start()

    def handle_download(self):
        if current_video_path is None or not os.path.exists(current_video_path):
            self._set_status("No video to download", "#ff4466")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "video.mp4", "Video Files (*.mp4)")
        if save_path:
            try:
                shutil.copy(current_video_path, save_path)
                self._set_status("Saved ✓", "#00ffaa")
            except Exception as e:
                self._set_status("Save failed", "#ff4466")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())