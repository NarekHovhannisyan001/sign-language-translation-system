from __future__ import annotations

import cv2

from PyQt6.QtCore import (
    Qt, QSize, QTimer, QRectF, QPointF, pyqtSignal, QThread, QPoint,
)
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QFont,
    QIcon, QPixmap, QImage,
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QPlainTextEdit, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QButtonGroup, QMenu, QCheckBox,
)

# ── Design tokens ──────────────────────────────────────────────────────────────
C_CANVAS    = "#F7F5F1"
C_SURFACE   = "#FFFFFF"
C_SAGE      = "#ECEBE6"
C_BORDER    = "#E3E1DB"
C_MUTED     = "#6E6B63"
C_INK       = "#1A1A1F"
C_TEAL      = "#2B7A78"
C_TEAL_DEEP = "#1F5D5B"
C_TEAL_SOFT = "#D8E4E0"
C_CORAL     = "#E07856"
C_AMBER     = "#C68A3C"
C_MINT      = "#E6EFEB"

UI_FONT   = "Inter"
MONO_FONT = "JetBrains Mono"

QUICK_PHRASES = [
    "Բարև Ձեզ", "Ինչպե՞ս եք", "Շնորհակալություն",
    "Ես ուզում եմ", "Օգնեք ինձ", "Հասկացա",
    "Ոչ", "Այո", "Ճիշտ է", "Ցտեսություն",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _font(family: str, size: int, weight: int = QFont.Weight.Normal,
          letter_spacing: float = 0.0) -> QFont:
    f = QFont(family)
    f.setFamilies([family, "Helvetica Neue", "Arial", "Sans Serif"])
    f.setPixelSize(size)
    f.setWeight(weight)
    if letter_spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
    return f


def _apply_shadow(widget: QWidget, blur: int = 24, y: int = 8,
                  alpha: int = 18) -> None:
    e = QGraphicsDropShadowEffect(widget)
    e.setBlurRadius(blur)
    e.setOffset(0, y)
    e.setColor(QColor(26, 26, 31, alpha))
    widget.setGraphicsEffect(e)


# ── Icon factory ───────────────────────────────────────────────────────────────

class Icon:
    @staticmethod
    def _base(size: int = 20, color: str = C_INK,
              stroke: float = 1.8) -> tuple[QPixmap, QPainter, QPen]:
        pm = QPixmap(QSize(size, size) * 2)
        pm.setDevicePixelRatio(2.0)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(2, 2)
        pen = QPen(QColor(color))
        pen.setWidthF(stroke)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        return pm, p, pen

    @classmethod
    def play(cls, size=20, color=C_INK):
        pm, p, _ = cls._base(size, color)
        path = QPainterPath()
        path.moveTo(7, 5); path.lineTo(7, size - 5)
        path.lineTo(size - 5, size / 2); path.closeSubpath()
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path); p.end()
        return QIcon(pm)

    @classmethod
    def pause(cls, size=20, color=C_INK):
        pm, p, _ = cls._base(size, color)
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(6, 5, 3.2, size - 10), 1, 1)
        p.drawRoundedRect(QRectF(size - 9.2, 5, 3.2, size - 10), 1, 1)
        p.end()
        return QIcon(pm)

    @classmethod
    def prev(cls, size=20, color=C_INK):
        pm, p, _ = cls._base(size, color)
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
        path = QPainterPath()
        path.moveTo(size - 6, 5); path.lineTo(size - 6, size - 5)
        path.lineTo(8, size / 2); path.closeSubpath()
        p.drawPath(path)
        p.drawRoundedRect(QRectF(5, 5, 2.2, size - 10), 1, 1)
        p.end()
        return QIcon(pm)

    @classmethod
    def next(cls, size=20, color=C_INK):
        pm, p, _ = cls._base(size, color)
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
        path = QPainterPath()
        path.moveTo(6, 5); path.lineTo(6, size - 5)
        path.lineTo(size - 8, size / 2); path.closeSubpath()
        p.drawPath(path)
        p.drawRoundedRect(QRectF(size - 7.2, 5, 2.2, size - 10), 1, 1)
        p.end()
        return QIcon(pm)

    @classmethod
    def replay(cls, size=20, color=C_INK):
        pm, p, _ = cls._base(size, color, stroke=1.9)
        r = QRectF(4, 4, size - 8, size - 8)
        p.drawArc(r, 45 * 16, 270 * 16)
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
        ah = QPainterPath()
        ah.moveTo(size - 4.5, 7.5); ah.lineTo(size - 8.5, 5.5)
        ah.lineTo(size - 7.0, 9.5); ah.closeSubpath()
        p.drawPath(ah); p.end()
        return QIcon(pm)

    @classmethod
    def mic(cls, size=20, color=C_INK):
        pm, p, pen = cls._base(size, color, stroke=1.8)
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(size / 2 - 3, 3, 6, 10), 3, 3)
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(pen)
        p.drawArc(QRectF(size / 2 - 5.5, 7, 11, 8), 200 * 16, 140 * 16)
        p.drawLine(QPointF(size / 2, 15), QPointF(size / 2, size - 3))
        p.drawLine(QPointF(size / 2 - 3, size - 3), QPointF(size / 2 + 3, size - 3))
        p.end()
        return QIcon(pm)

    @classmethod
    def stop_square(cls, size=20, color="#FFFFFF"):
        pm, p, _ = cls._base(size, color)
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(5, 5, size - 10, size - 10), 2, 2)
        p.end()
        return QIcon(pm)

    @classmethod
    def download(cls, size=20, color=C_INK):
        pm, p, _ = cls._base(size, color)
        mid = size / 2
        p.drawLine(QPointF(mid, 4), QPointF(mid, size - 7))
        arrow = QPainterPath()
        arrow.moveTo(mid - 3.5, size - 10); arrow.lineTo(mid, size - 6.5)
        arrow.lineTo(mid + 3.5, size - 10)
        p.drawPath(arrow)
        p.drawLine(QPointF(4, size - 4), QPointF(size - 4, size - 4))
        p.end()
        return QIcon(pm)

    @classmethod
    def share(cls, size=20, color=C_INK):
        pm, p, _ = cls._base(size, color)
        mid = size / 2
        p.drawLine(QPointF(mid, size - 5), QPointF(mid, 5))
        arrow = QPainterPath()
        arrow.moveTo(mid - 3.5, 8.5); arrow.lineTo(mid, 5)
        arrow.lineTo(mid + 3.5, 8.5)
        p.drawPath(arrow)
        p.drawLine(QPointF(4, 11), QPointF(4, size - 4))
        p.drawLine(QPointF(4, size - 4), QPointF(size - 4, size - 4))
        p.drawLine(QPointF(size - 4, size - 4), QPointF(size - 4, 11))
        p.end()
        return QIcon(pm)

    @classmethod
    def translate_arrow(cls, size=20, color="#FFFFFF"):
        pm, p, _ = cls._base(size, color, stroke=2.0)
        p.drawLine(QPointF(4, size / 2), QPointF(size - 6, size / 2))
        arrow = QPainterPath()
        arrow.moveTo(size - 9, size / 2 - 4)
        arrow.lineTo(size - 5, size / 2)
        arrow.lineTo(size - 9, size / 2 + 4)
        p.drawPath(arrow); p.end()
        return QIcon(pm)


# ── Status Pill ────────────────────────────────────────────────────────────────

class StatusPill(QFrame):
    STATES = {
        "STANDBY":   (C_MUTED,  "Ready"),
        "RECORDING": (C_CORAL,  "Recording"),
        "PLAYING":   (C_TEAL,   "Playing"),
        "DONE":      (C_TEAL,   "Complete"),
        "ERROR":     (C_AMBER,  "Error"),
        "WORKING":   (C_TEAL,   "Working"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self._state = "STANDBY"
        self._pulse = 0.0

        self.setFixedHeight(36)
        self.setMinimumWidth(180)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 16, 0)
        lay.setSpacing(10)

        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        self._label = QLabel("STANDBY  ·  Ready")
        self._label.setFont(_font(MONO_FONT, 12, QFont.Weight.Medium, 1.2))

        lay.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._label, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._repaint_style()

    def setState(self, state: str, custom_text: str = "") -> None:
        state = state.upper()
        if state not in self.STATES:
            state = "STANDBY"
        self._state = state
        _, human = self.STATES[state]
        display = custom_text if custom_text else human
        self._label.setText(f"{state}  ·  {display}")
        self._label.setStyleSheet(f"color: {C_INK};")
        if state in ("RECORDING", "PLAYING", "WORKING"):
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self._pulse = 0.0
        self._repaint_style()
        self.update()

    def _tick(self):
        self._pulse = (self._pulse + 0.08) % 1.0
        self.update()

    def _repaint_style(self):
        bg = {
            "STANDBY":   C_SAGE,
            "RECORDING": "#F9E5DE",
            "PLAYING":   C_TEAL_SOFT,
            "DONE":      C_MINT,
            "ERROR":     "#F4E6CE",
            "WORKING":   C_TEAL_SOFT,
        }[self._state]
        self.setStyleSheet(f"""
            #StatusPill {{
                background: {bg};
                border-radius: 18px;
                border: 1px solid {C_BORDER};
            }}
        """)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        color, _ = self.STATES[self._state]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dot_x, dot_y = 18, self.height() / 2
        if self._timer.isActive():
            halo = abs((self._pulse * 2) - 1)
            ring = QColor(color)
            ring.setAlphaF(0.25 * (1 - halo))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ring)
            p.drawEllipse(QPointF(dot_x, dot_y), 6 + halo * 7, 6 + halo * 7)
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(dot_x, dot_y), 5, 5)
        p.end()


# ── Video Stage ────────────────────────────────────────────────────────────────

class VideoStage(QFrame):
    """Simple dark-card video display using a QLabel — no custom painting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoStage")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("""
            #VideoStage { background: #111216; border-radius: 18px; }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._video_label = QLabel()
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._video_label.setStyleSheet("background: transparent;")

        self._placeholder = QLabel("[ Sign Preview ]")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setFont(_font(MONO_FONT, 13))
        self._placeholder.setStyleSheet("color: #2a2a3a; background: transparent; letter-spacing: 3px;")
        self._placeholder.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        lay.addWidget(self._video_label)
        lay.addWidget(self._placeholder)
        self._video_label.hide()

    def setFrame(self, frame) -> None:
        if isinstance(frame, QImage):
            pix = QPixmap.fromImage(frame)
        elif isinstance(frame, QPixmap):
            pix = frame
        else:
            pix = None

        if pix and not pix.isNull():
            self._placeholder.hide()
            self._video_label.show()
            self._video_label.setPixmap(
                pix.scaled(
                    self._video_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self._video_label.hide()
            self._placeholder.show()

    def clear(self):
        self._video_label.hide()
        self._placeholder.show()


# ── Segmented Speed Control ────────────────────────────────────────────────────

class SegmentedControl(QFrame):
    """Pill-shaped segmented control. Exposes currentText() and
    currentIndexChanged for compatibility with main.py."""

    changed             = pyqtSignal(float)
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, options: list[tuple[str, float]], default_index: int = 1,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("Segmented")
        self._options  = options
        self._values   = [v for _, v in options]
        self._cur      = default_index
        self._buttons: list[QPushButton] = []
        self._group    = QButtonGroup(self)
        self._group.setExclusive(True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(0)

        for i, (label, _) in enumerate(options):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            b.setFont(_font(MONO_FONT, 12, QFont.Weight.Medium))
            b.setFixedHeight(32)
            b.setMinimumWidth(46)
            self._buttons.append(b)
            self._group.addButton(b, i)
            lay.addWidget(b)
            b.clicked.connect(lambda _=False, idx=i: self._select(idx))

        self._select(default_index, emit=False)
        self.setStyleSheet(f"""
            #Segmented {{
                background: {C_SAGE};
                border: 1px solid {C_BORDER};
                border-radius: 20px;
            }}
            QPushButton {{
                background: transparent; color: {C_MUTED};
                border: none; border-radius: 16px; padding: 0 12px;
            }}
            QPushButton:checked {{ background: {C_SURFACE}; color: {C_INK}; }}
            QPushButton:hover:!checked {{ color: {C_INK}; }}
            QPushButton:focus {{ outline: none; }}
        """)

    def _select(self, idx: int, emit: bool = True) -> None:
        self._cur = idx
        for i, b in enumerate(self._buttons):
            b.setChecked(i == idx)
        if emit:
            self.changed.emit(self._values[idx])
            self.currentIndexChanged.emit(idx)

    def currentText(self) -> str:
        return self._options[self._cur][0]


# ── Icon Button ────────────────────────────────────────────────────────────────

class IconButton(QPushButton):
    def __init__(self, icon: QIcon, tooltip: str, size: int = 44,
                 primary: bool = False, parent=None):
        super().__init__(parent)
        self.setIcon(icon)
        self.setIconSize(QSize(20, 20))
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._primary = primary
        self._apply_style()

    def _apply_style(self):
        r = self.width() // 2
        if self._primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C_INK}; border: none; border-radius: {r}px;
                }}
                QPushButton:hover    {{ background: {C_TEAL_DEEP}; }}
                QPushButton:pressed  {{ background: {C_TEAL}; }}
                QPushButton:disabled {{ background: {C_BORDER}; }}
                QPushButton:focus    {{ border: 2px solid {C_TEAL}; }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C_SURFACE};
                    border: 1px solid {C_BORDER};
                    border-radius: {r}px;
                }}
                QPushButton:hover    {{ background: {C_TEAL_SOFT}; border-color: {C_TEAL}; }}
                QPushButton:pressed  {{ background: {C_MINT}; }}
                QPushButton:disabled {{ background: {C_SAGE}; border-color: {C_BORDER}; }}
                QPushButton:focus    {{ border: 2px solid {C_TEAL}; }}
            """)


# ── Phrase Chip ────────────────────────────────────────────────────────────────

class PhraseChip(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(_font(UI_FONT, 13, QFont.Weight.Medium))
        self.setFixedHeight(34)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {C_SURFACE}; color: {C_INK};
                border: 1px solid {C_BORDER}; border-radius: 17px; padding: 0 14px;
            }}
            QPushButton:hover   {{ background: {C_TEAL_SOFT}; border-color: {C_TEAL}; color: {C_TEAL_DEEP}; }}
            QPushButton:pressed {{ background: {C_MINT}; }}
            QPushButton:focus   {{ border: 2px solid {C_TEAL}; padding: 0 13px; }}
        """)


# ── Armenian Text Input ────────────────────────────────────────────────────────

class ArmenianTextInput(QPlainTextEdit):
    """Enter = translate, Shift+Enter = new line (existing behaviour preserved)."""

    enter_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ArmInput")
        self.setPlaceholderText("Գրեք հայերեն տեքստ…")
        self.setTabChangesFocus(True)
        self.setFont(_font(UI_FONT, 16))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumHeight(160)
        self.setMaximumHeight(240)
        self.setStyleSheet(f"""
            #ArmInput {{
                background: {C_SURFACE}; color: {C_INK};
                border: 1.5px solid {C_BORDER};
                border-radius: 16px; padding: 16px 18px;
                selection-background-color: {C_TEAL_SOFT};
                selection-color: {C_INK};
            }}
            #ArmInput:focus {{ border: 1.5px solid {C_TEAL}; }}
        """)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.enter_pressed.emit()
        else:
            super().keyPressEvent(event)


# ── Video Worker ───────────────────────────────────────────────────────────────
# Kept unchanged from original ui.py — cv2-based, reads video files.

class VideoWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    finished    = pyqtSignal()

    def __init__(self, video_path, size=(600, 400), speed=1.0, loop=False):
        super().__init__()
        self.video_path = video_path
        self.size       = size
        self.speed      = speed
        self.loop       = loop
        self._stop      = False
        self._paused    = False

    def stop(self):              self._stop   = True
    def pause(self):             self._paused = True
    def resume(self):            self._paused = False
    def set_speed(self, speed):  self.speed   = speed

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
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
                    continue
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, self.size)
            h, w, ch = frame.shape
            img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.frame_ready.emit(img.copy())
            self.msleep(max(1, int(1000 / (fps * self.speed))))
        cap.release()
        self.finished.emit()


# ── Fullscreen Viewer ─────────────────────────────────────────────────────────

class FullScreenViewer(QWidget):
    """Borderless fullscreen window that mirrors the video.
    Close with the on-screen button or the Esc key."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("SLTS — Fullscreen")
        self.setStyleSheet("background: #0a0a0a;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Top bar: exit button anchored to the right
        bar = QWidget()
        bar.setFixedHeight(54)
        bar.setStyleSheet("background: transparent;")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(20, 9, 20, 9)
        bar_lay.addStretch(1)

        btn_exit = QPushButton("✕   Exit Fullscreen")
        btn_exit.setToolTip("Exit fullscreen  (Esc)")
        btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exit.setFixedHeight(36)
        f = QFont()
        f.setPixelSize(13)
        btn_exit.setFont(f)
        btn_exit.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.10);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 10px;
                padding: 0 18px;
            }
            QPushButton:hover   { background: rgba(255,255,255,0.22); }
            QPushButton:pressed { background: rgba(255,255,255,0.06); }
        """)
        btn_exit.clicked.connect(self.close)
        bar_lay.addWidget(btn_exit)

        # Video label — fills remaining space
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label.setStyleSheet("background: transparent;")

        # Bottom controls bar
        ctrl_bar = QWidget()
        ctrl_bar.setFixedHeight(72)
        ctrl_bar.setStyleSheet("background: rgba(0,0,0,0.55);")
        ctrl_lay = QHBoxLayout(ctrl_bar)
        ctrl_lay.setContentsMargins(0, 0, 0, 0)
        ctrl_lay.setSpacing(16)
        ctrl_lay.addStretch(1)

        self.btn_prev   = self._fsbtn("⏮", "Previous translation",   44)
        self.btn_play   = self._fsbtn("▶", "Play / Pause",            52, primary=True)
        self.btn_next   = self._fsbtn("⏭", "Next translation",        44)
        self.btn_replay = self._fsbtn("↺", "Replay from beginning",   44)

        ctrl_lay.addWidget(self.btn_prev)
        ctrl_lay.addWidget(self.btn_play)
        ctrl_lay.addWidget(self.btn_next)
        ctrl_lay.addSpacing(8)
        ctrl_lay.addWidget(self.btn_replay)
        ctrl_lay.addStretch(1)

        outer.addWidget(bar)
        outer.addWidget(self._label, 1)
        outer.addWidget(ctrl_bar)

    @staticmethod
    def _fsbtn(symbol: str, tooltip: str, size: int = 44, primary: bool = False) -> QPushButton:
        b = QPushButton(symbol)
        b.setToolTip(tooltip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedSize(size, size)
        b.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        f = QFont()
        f.setPixelSize(size // 3)
        b.setFont(f)
        r = size // 2
        if primary:
            b.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.90); color: #0a0a0a;
                    border: none; border-radius: {r}px;
                }}
                QPushButton:hover    {{ background: #FFFFFF; }}
                QPushButton:pressed  {{ background: rgba(255,255,255,0.70); }}
                QPushButton:disabled {{ background: rgba(255,255,255,0.25); color: rgba(255,255,255,0.40); }}
            """)
        else:
            b.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.12); color: #FFFFFF;
                    border: 1px solid rgba(255,255,255,0.25); border-radius: {r}px;
                }}
                QPushButton:hover    {{ background: rgba(255,255,255,0.25); border-color: rgba(255,255,255,0.50); }}
                QPushButton:pressed  {{ background: rgba(255,255,255,0.08); }}
                QPushButton:disabled {{ background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.25); border-color: rgba(255,255,255,0.10); }}
            """)
        return b

    def show_frame(self, img) -> None:
        if isinstance(img, QImage):
            pix = QPixmap.fromImage(img)
        elif isinstance(img, QPixmap):
            pix = img
        else:
            return
        if not pix.isNull():
            self._label.setPixmap(
                pix.scaled(
                    self._label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


# ── Video Panel ────────────────────────────────────────────────────────────────
# Redesigned look; btn_play / loop_check / speed_combo names kept for main.py.

class VideoPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fs_viewer: FullScreenViewer | None = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"QFrame {{ background: {C_CANVAS}; border: none; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Video display
        self._stage = VideoStage()
        _apply_shadow(self._stage, blur=34, y=14, alpha=28)
        layout.addWidget(self._stage, 1)

        # Playback bar
        bar = QFrame()
        bar.setObjectName("PlaybackBar")
        bar.setFixedHeight(76)
        bar.setStyleSheet(f"""
            #PlaybackBar {{
                background: {C_SURFACE};
                border: 1px solid {C_BORDER};
                border-radius: 18px;
            }}
        """)
        _apply_shadow(bar, blur=24, y=8, alpha=12)

        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(12)

        # Transport buttons — small symbol + tooltip on hover
        self.btn_prev   = self._tbtn("⏮", "Previous translation",   44)
        self.btn_play   = self._tbtn("▶", "Play / Pause",            52, primary=True)
        self.btn_next   = self._tbtn("⏭", "Next translation",        44)
        self.btn_replay = self._tbtn("↺", "Replay from beginning",   44)

        bl.addWidget(self.btn_prev)
        bl.addWidget(self.btn_play)
        bl.addWidget(self.btn_next)
        bl.addSpacing(4)
        bl.addWidget(self.btn_replay)
        bl.addStretch(1)

        sp_lbl = QLabel("SPEED")
        sp_lbl.setFont(_font(MONO_FONT, 10, QFont.Weight.Medium, 1.8))
        sp_lbl.setStyleSheet(f"color: {C_MUTED};")
        bl.addWidget(sp_lbl)

        # SegmentedControl styled as test.py; exposes currentText() and
        # currentIndexChanged so main.py's AppController works unchanged.
        self.speed_combo = SegmentedControl(
            [("0.5×", 0.5), ("1×", 1.0), ("1.5×", 1.5), ("2×", 2.0)],
            default_index=1,
        )
        bl.addWidget(self.speed_combo)
        bl.addSpacing(8)

        # QCheckBox kept — main.py connects stateChanged
        self.loop_check = QCheckBox("Loop")
        self.loop_check.setFont(_font(UI_FONT, 13, QFont.Weight.Medium))
        self.loop_check.setStyleSheet(f"""
            QCheckBox {{ color: {C_INK}; spacing: 6px; }}
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                border: 1.5px solid {C_BORDER}; border-radius: 5px;
                background: {C_SURFACE};
            }}
            QCheckBox::indicator:checked {{
                background: {C_TEAL}; border-color: {C_TEAL};
            }}
            QCheckBox::indicator:hover {{ border-color: {C_TEAL}; }}
        """)
        bl.addWidget(self.loop_check)
        bl.addSpacing(8)

        self.btn_fs = self._tbtn("⛶", "Toggle fullscreen", 40)
        self.btn_fs.clicked.connect(self._toggle_fullscreen)
        bl.addWidget(self.btn_fs)

        layout.addWidget(bar)

    @staticmethod
    def _tbtn(symbol: str, tooltip: str, size: int = 44, primary: bool = False) -> QPushButton:
        b = QPushButton(symbol)
        b.setToolTip(tooltip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedSize(size, size)
        b.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        f = QFont()
        f.setPixelSize(size // 3)
        b.setFont(f)
        r = size // 2
        if primary:
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {C_INK}; color: #FFFFFF;
                    border: none; border-radius: {r}px;
                }}
                QPushButton:hover    {{ background: {C_TEAL_DEEP}; }}
                QPushButton:pressed  {{ background: {C_TEAL}; }}
                QPushButton:disabled {{ background: {C_BORDER}; color: {C_MUTED}; }}
            """)
        else:
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {C_SURFACE}; color: {C_INK};
                    border: 1px solid {C_BORDER}; border-radius: {r}px;
                }}
                QPushButton:hover    {{ background: {C_TEAL_SOFT}; border-color: {C_TEAL}; }}
                QPushButton:pressed  {{ background: {C_MINT}; }}
                QPushButton:disabled {{ background: {C_SAGE}; color: {C_MUTED}; border-color: {C_BORDER}; }}
            """)
        return b

    def _toggle_fullscreen(self) -> None:
        if self._fs_viewer is not None and self._fs_viewer.isVisible():
            self._fs_viewer.close()
        else:
            self._fs_viewer = FullScreenViewer()
            # Wire FS buttons → main panel buttons so all AppController signals stay intact
            self._fs_viewer.btn_prev.clicked.connect(self.btn_prev.click)
            self._fs_viewer.btn_play.clicked.connect(self.btn_play.click)
            self._fs_viewer.btn_next.clicked.connect(self.btn_next.click)
            self._fs_viewer.btn_replay.clicked.connect(self.btn_replay.click)
            # Sync current enabled / text state into the new viewer
            self._fs_viewer.btn_prev.setEnabled(self.btn_prev.isEnabled())
            self._fs_viewer.btn_next.setEnabled(self.btn_next.isEnabled())
            self._fs_viewer.btn_replay.setEnabled(self.btn_replay.isEnabled())
            self._fs_viewer.btn_play.setText(self.btn_play.text())
            self._fs_viewer.showFullScreen()

    def show_frame(self, img) -> None:
        self._stage.setFrame(img)
        if self._fs_viewer is not None and self._fs_viewer.isVisible():
            self._fs_viewer.show_frame(img)

    def set_status(self, *_, playing=False):
        text = "⏸" if playing else "▶"
        self.btn_play.setText(text)
        if self._fs_viewer is not None and self._fs_viewer.isVisible():
            self._fs_viewer.btn_play.setText(text)


# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    translate_requested = pyqtSignal(str)
    replay_requested    = pyqtSignal()
    prev_requested      = pyqtSignal()
    next_requested      = pyqtSignal()
    save_requested      = pyqtSignal()
    voice_requested     = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._phrase_chips: list[PhraseChip] = []
        self.setWindowTitle("Sign Language Translation System")
        self.setMinimumSize(1100, 720)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: {C_CANVAS}; }}
            QToolTip {{
                background: {C_INK}; color: #FFFFFF;
                border: none; padding: 6px 10px; border-radius: 6px;
                font-family: "{UI_FONT}";
            }}
        """)
        root = QWidget(self)
        self.setCentralWidget(root)

        rlay = QVBoxLayout(root)
        rlay.setContentsMargins(28, 22, 28, 22)
        rlay.setSpacing(18)

        rlay.addWidget(self._build_header())
        rlay.addWidget(self._build_body(), 1)
        rlay.addWidget(self._build_footer())

    # ── Header ─────────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        # Logo mark — painted inline
        mark = QLabel()
        mark.setFixedSize(40, 40)
        pm = QPixmap(80, 80)
        pm.setDevicePixelRatio(2.0)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(2, 2)
        p.setBrush(QColor(C_INK)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, 40, 40), 10, 10)
        pen = QPen(QColor("#FFFFFF")); pen.setWidthF(2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(10, 10, 20, 20), 30 * 16, 210 * 16)
        p.drawLine(QPointF(12, 28), QPointF(28, 28))
        p.setBrush(QColor(C_TEAL)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(30, 12), 3, 3)
        p.end()
        mark.setPixmap(pm)

        titles = QWidget()
        tlay = QVBoxLayout(titles)
        tlay.setContentsMargins(0, 0, 0, 0); tlay.setSpacing(0)
        top = QLabel("SLTS")
        top.setFont(_font(MONO_FONT, 11, QFont.Weight.Medium, 2.2))
        top.setStyleSheet(f"color: {C_MUTED};")
        ttl = QLabel("Armenian Sign Language Translation")
        ttl.setFont(_font(UI_FONT, 20, QFont.Weight.DemiBold))
        ttl.setStyleSheet(f"color: {C_INK};")
        tlay.addWidget(top); tlay.addWidget(ttl)

        lay.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(6)
        lay.addWidget(titles, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addStretch(1)

        self.status_pill = StatusPill()

        self.btn_save = QPushButton("  Save video")
        self.btn_save.setIcon(Icon.download(20, C_INK))
        self.btn_save.setIconSize(QSize(18, 18))
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFont(_font(UI_FONT, 13, QFont.Weight.Medium))
        self.btn_save.setFixedHeight(36)
        self.btn_save.setStyleSheet(self._ghost_btn_css())
        self.btn_save.clicked.connect(self.save_requested)

        self.btn_export = QPushButton("  Export")
        self.btn_export.setIcon(Icon.share(20, C_INK))
        self.btn_export.setIconSize(QSize(18, 18))
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setFont(_font(UI_FONT, 13, QFont.Weight.Medium))
        self.btn_export.setFixedHeight(36)
        self.btn_export.setStyleSheet(self._ghost_btn_css())
        self.btn_export.clicked.connect(self._export_menu)

        lay.addWidget(self.status_pill)
        lay.addSpacing(8)
        lay.addWidget(self.btn_save)
        lay.addWidget(self.btn_export)
        return w

    def _ghost_btn_css(self) -> str:
        return f"""
            QPushButton {{
                background: {C_SURFACE}; color: {C_INK};
                border: 1px solid {C_BORDER}; border-radius: 10px; padding: 0 14px;
            }}
            QPushButton:hover   {{ background: {C_TEAL_SOFT}; border-color: {C_TEAL}; color: {C_TEAL_DEEP}; }}
            QPushButton:pressed {{ background: {C_MINT}; }}
            QPushButton:disabled {{ color: {C_MUTED}; background: {C_SAGE}; }}
            QPushButton:focus   {{ border: 2px solid {C_TEAL}; padding: 0 13px; }}
        """

    # ── Body ───────────────────────────────────────────────────────────────────

    def _build_body(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)
        lay.addWidget(self._build_input_column(), 0)
        lay.addWidget(self._build_stage_column(), 1)
        return w

    def _build_input_column(self) -> QWidget:
        col = QFrame()
        col.setObjectName("InputCol")
        col.setFixedWidth(400)
        col.setStyleSheet(f"""
            #InputCol {{
                background: {C_SURFACE};
                border: 1px solid {C_BORDER};
                border-radius: 20px;
            }}
        """)
        _apply_shadow(col, blur=30, y=10, alpha=14)

        lay = QVBoxLayout(col)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(14)

        # Column label row
        lbl_row = QHBoxLayout(); lbl_row.setSpacing(8)
        kicker = QLabel("INPUT")
        kicker.setFont(_font(MONO_FONT, 10, QFont.Weight.Medium, 1.8))
        kicker.setStyleSheet(f"color: {C_MUTED};")
        lang = QLabel("Armenian  ·  Հայերեն")
        lang.setFont(_font(MONO_FONT, 10, QFont.Weight.Medium, 1.2))
        lang.setStyleSheet(f"color: {C_TEAL_DEEP};")
        lbl_row.addWidget(kicker); lbl_row.addStretch(1); lbl_row.addWidget(lang)
        lay.addLayout(lbl_row)

        # Text area
        self.text_input = ArmenianTextInput()
        self.text_input.enter_pressed.connect(self._on_translate_clicked)
        lay.addWidget(self.text_input)

        # Error banner (hidden until set_error is called)
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setFont(_font(UI_FONT, 12, QFont.Weight.Medium))
        self.info_label.setStyleSheet(f"""
            background: #F4E6CE; color: #6A4A14;
            border: 1px solid #E6CE9E; border-radius: 10px; padding: 10px 12px;
        """)
        self.info_label.hide()
        lay.addWidget(self.info_label)

        # Mic + Translate action row
        action_row = QHBoxLayout(); action_row.setSpacing(10)

        self.btn_mic = QPushButton("  Voice")
        self.btn_mic.setIcon(Icon.mic(20, C_INK))
        self.btn_mic.setIconSize(QSize(18, 18))
        self.btn_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mic.setFont(_font(UI_FONT, 14, QFont.Weight.Medium))
        self.btn_mic.setFixedHeight(48)
        self.btn_mic.setMinimumWidth(120)
        self.btn_mic.setToolTip("Record voice")
        self._style_mic_idle()
        self.btn_mic.clicked.connect(self.voice_requested)

        self.btn_translate = QPushButton("Translate to Sign")
        self.btn_translate.setIconSize(QSize(18, 18))
        self.btn_translate.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.setFont(_font(UI_FONT, 14, QFont.Weight.DemiBold))
        self.btn_translate.setFixedHeight(48)
        self.btn_translate.setStyleSheet(f"""
            QPushButton {{
                background: {C_INK}; color: #FFFFFF;
                border: none; border-radius: 14px; padding: 0 18px;
            }}
            QPushButton:hover   {{ background: {C_TEAL_DEEP}; }}
            QPushButton:pressed {{ background: {C_TEAL}; }}
            QPushButton:disabled {{ background: {C_BORDER}; color: {C_MUTED}; }}
            QPushButton:focus   {{ border: 2px solid {C_TEAL}; padding: 0 17px; }}
        """)
        self.btn_translate.clicked.connect(self._on_translate_clicked)

        action_row.addWidget(self.btn_mic)
        action_row.addWidget(self.btn_translate, 1)
        lay.addLayout(action_row)

        lay.addStretch(1)

        foot = QLabel("Enter to translate  ·  Shift+Enter for new line")
        foot.setFont(_font(MONO_FONT, 10))
        foot.setStyleSheet(f"color: {C_MUTED};")
        foot.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay.addWidget(foot)
        return col

    def _build_stage_column(self) -> QWidget:
        self.video_panel = VideoPanel()
        # Disable replay until a translation has been generated
        self.video_panel.btn_replay.setEnabled(False)
        # Wire nav signals; btn_play is wired by main.py's AppController
        self.video_panel.btn_prev.clicked.connect(self.prev_requested)
        self.video_panel.btn_next.clicked.connect(self.next_requested)
        self.video_panel.btn_replay.clicked.connect(self.replay_requested)
        return self.video_panel

    # ── Footer ─────────────────────────────────────────────────────────────────

    def _build_footer(self) -> QWidget:
        w = QFrame()
        w.setObjectName("Footer")
        w.setStyleSheet(f"""
            #Footer {{
                background: {C_SAGE};
                border-radius: 16px;
                border: 1px solid {C_BORDER};
            }}
        """)
        _apply_shadow(w, blur=16, y=4, alpha=10)

        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(8)

        lbl = QLabel("Phrases:")
        lbl.setFont(_font(MONO_FONT, 10, QFont.Weight.Medium, 1.2))
        lbl.setStyleSheet(f"color: {C_MUTED};")
        lay.addWidget(lbl)

        for phrase in QUICK_PHRASES:
            chip = PhraseChip(phrase)
            chip.clicked.connect(lambda _, p=phrase: self._insert_phrase(p))
            lay.addWidget(chip)
            self._phrase_chips.append(chip)

        lay.addStretch(1)
        return w

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _on_translate_clicked(self):
        text = self.text_input.toPlainText().strip()
        if text:
            self.translate_requested.emit(text)

    def _insert_phrase(self, phrase):
        cursor = self.text_input.textCursor()
        current = self.text_input.toPlainText().strip()
        if current:
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(" " + phrase)
        else:
            cursor.insertText(phrase)
        self.text_input.setTextCursor(cursor)
        self.text_input.setFocus()

    def _export_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {C_SURFACE}; color: {C_INK};
                border: 1px solid {C_BORDER}; border-radius: 8px; padding: 4px;
            }}
            QMenu::item {{ padding: 8px 20px; border-radius: 5px; }}
            QMenu::item:selected {{ background: {C_TEAL_SOFT}; color: {C_TEAL_DEEP}; }}
        """)
        menu.addAction("Export as MP4")
        menu.addAction("Export as GIF")
        menu.addAction("Export as WebM")
        menu.exec(self.btn_export.mapToGlobal(QPoint(0, self.btn_export.height())))

    def _style_mic_idle(self) -> None:
        self.btn_mic.setIcon(Icon.mic(20, C_INK))
        self.btn_mic.setText("  Voice")
        self.btn_mic.setStyleSheet(f"""
            QPushButton {{
                background: {C_SURFACE}; color: {C_INK};
                border: 1.5px solid {C_BORDER}; border-radius: 14px;
                padding: 0 14px; text-align: left;
            }}
            QPushButton:hover   {{ background: {C_TEAL_SOFT}; border-color: {C_TEAL}; color: {C_TEAL_DEEP}; }}
            QPushButton:pressed {{ background: {C_MINT}; }}
            QPushButton:focus   {{ border: 2px solid {C_TEAL}; padding: 0 13px; }}
        """)

    def _style_mic_recording(self) -> None:
        self.btn_mic.setIcon(Icon.stop_square(20, "#FFFFFF"))
        self.btn_mic.setText("  Stop")
        self.btn_mic.setStyleSheet(f"""
            QPushButton {{
                background: {C_CORAL}; color: #FFFFFF;
                border: 1.5px solid {C_CORAL}; border-radius: 14px;
                padding: 0 14px; text-align: left;
            }}
            QPushButton:hover   {{ background: #D66B4A; border-color: #D66B4A; }}
            QPushButton:pressed {{ background: #C45F40; }}
            QPushButton:focus   {{ border: 2px solid {C_TEAL}; padding: 0 13px; }}
        """)

    def _status_to_pill_state(self, text: str) -> tuple[str, str]:
        t = text.upper()
        if any(k in t for k in ("RECORD", "MIC", "🎤")):
            return "RECORDING", text
        if "PLAY" in t and "DISPLAY" not in t:
            return "PLAYING", text
        if any(k in t for k in ("PARS", "GENERAT", "TRANSCRIB", "WORKING", "PREPARING")):
            return "WORKING", text
        if any(k in t for k in ("✓", "DONE", "SAVED", "COMPLETE")):
            return "DONE", text
        if any(k in t for k in ("ERROR", "FAILED", "NOT FOUND")):
            return "ERROR", text
        return "STANDBY", text

    # ── Public API — signatures match original ui.py exactly ──────────────────

    def set_status(self, text, color="#1e1e3a", playing=False):
        state, display = self._status_to_pill_state(text)
        self.status_pill.setState(state, display)
        self.video_panel.set_status(text, color, playing=playing)

    def set_parsed(self, *_):
        pass  # tokens display removed per design update

    def set_error(self, text):
        msg = (text or "").strip()
        if not msg:
            self.info_label.hide()
            self.info_label.setText("")
        else:
            self.info_label.setText(f"⚠ {msg}")
            self.info_label.show()

    def set_translate_enabled(self, enabled):
        self.btn_translate.setEnabled(bool(enabled))

    def set_replay_enabled(self, enabled):
        self.video_panel.btn_replay.setEnabled(bool(enabled))
        fs = self.video_panel._fs_viewer
        if fs is not None and fs.isVisible():
            fs.btn_replay.setEnabled(bool(enabled))

    def set_nav_enabled(self, prev, nxt):
        self.video_panel.btn_prev.setEnabled(bool(prev))
        self.video_panel.btn_next.setEnabled(bool(nxt))
        fs = self.video_panel._fs_viewer
        if fs is not None and fs.isVisible():
            fs.btn_prev.setEnabled(bool(prev))
            fs.btn_next.setEnabled(bool(nxt))

    def clear_input(self):
        self.text_input.clear()

    def set_input_enabled(self, enabled):
        e = bool(enabled)
        self.text_input.setEnabled(e)
        for chip in self._phrase_chips:
            chip.setEnabled(e)

    def set_voice_enabled(self, enabled: bool):
        self.btn_mic.setEnabled(bool(enabled))

    def set_mic_recording(self, recording: bool):
        if recording:
            self._style_mic_recording()
        else:
            self._style_mic_idle()

    def insert_text(self, text: str):
        self.text_input.setPlainText(text.strip())

    def show_frame(self, img):
        self.video_panel.show_frame(img)
