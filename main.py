import sys
import os
import shutil
import importlib.util
import mediapipe as mp

from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import QThread, pyqtSignal

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
ROOT       = os.path.dirname(os.path.abspath(__file__))
JSON_DIR   = os.path.join(ROOT, "data")
OUTPUT_DIR = os.path.join(ROOT, "output")
IDLE_PATH  = os.path.join(ROOT, "ui", "idle.mp4")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Build known_words from data/ folder — single and multi-word entries
def _load_known_words():
    if not os.path.isdir(JSON_DIR):
        return set()
    return set(
        f[:-5].lower()   # strip .json, lowercase — works for "բարև ձեզ.json" too
        for f in os.listdir(JSON_DIR)
        if f.endswith('.json')
    )

KNOWN_WORDS = _load_known_words()


# ─────────────────────────────────────────────
# Load modules from underscore folders
# ─────────────────────────────────────────────
def _load(folder, filename, module_name):
    path = os.path.join(ROOT, folder, filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_tok = _load("text_tokenizer",      "tokenizing.py", "tokenizing")
_gen = _load("movement_generation", "generation.py", "generation")

# Load voice module from project root
import importlib.util as _ilu
_vspec = _ilu.spec_from_file_location("voice_to_text", os.path.join(ROOT, "voice_to_text", "voice_to_text.py"))
_vmod  = _ilu.module_from_spec(_vspec)
_vspec.loader.exec_module(_vmod)
record_audio    = _vmod.record_audio
transcribe_audio = _vmod.transcribe_audio

parse                = _tok.parse
generate_from_phrase = _gen.generate_from_phrase

# Import UI
sys.path.insert(0, os.path.join(ROOT, "ui"))
from ui import MainWindow, VideoWorker


# ─────────────────────────────────────────────
# Background Generation Worker
# ─────────────────────────────────────────────
class GenerationWorker(QThread):
    status_update = pyqtSignal(str)  # "PARSING" | "GENERATING"
    done          = pyqtSignal(str)  # output video path
    error         = pyqtSignal(str)  # error message

    def __init__(self, text, output_path):
        super().__init__()
        self.text        = text
        self.output_path = output_path

    def run(self):
        try:
            self.status_update.emit("PARSING")
            tokens = parse(self.text, known_words=KNOWN_WORDS)
            self.status_update.emit("GENERATING")
            if not tokens:
                self.error.emit("Nothing to translate after parsing.")
                return
            generate_from_phrase(
                phrase        = tokens,
                json_dir      = JSON_DIR,
                output_video  = self.output_path,
                fps           = 30,
                width         = 640,
                height        = 480,
                interp_frames = 12,
                trim          = 20,
            )
            self.done.emit(self.output_path)

        except Exception as e:
            self.error.emit(str(e))



# ─────────────────────────────────────────────
# Voice Worker — records + transcribes in background
# ─────────────────────────────────────────────
class VoiceWorker(QThread):
    recording_started = pyqtSignal()        # mic is now recording
    done              = pyqtSignal(str)     # transcription result
    error             = pyqtSignal(str)     # error message

    def __init__(self, max_seconds: int = 120):
        super().__init__()
        self.max_seconds = max_seconds   # safety cap — never records more than this
        self._stop_flag  = False

    def stop_recording(self):
        """Called when user clicks mic button again to stop."""
        self._stop_flag = True

    def run(self):
        import tempfile, os, wave, pyaudio
        tmp_path = None
        try:
            self.recording_started.emit()

            CHUNK    = 1024
            FORMAT   = pyaudio.paInt16
            CHANNELS = 1
            RATE     = 16000

            p      = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True, frames_per_buffer=CHUNK)

            frames       = []
            max_chunks   = int(RATE / CHUNK * self.max_seconds)
            chunks_read  = 0

            while chunks_read < max_chunks and not self._stop_flag:
                frames.append(stream.read(CHUNK, exception_on_overflow=False))
                chunks_read += 1

            stream.stop_stream()
            stream.close()
            p.terminate()

            if not frames:
                self.error.emit("No audio recorded")
                return

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            with wave.open(tmp_path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))

            text = transcribe_audio(tmp_path)
            self.done.emit(text)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)


# ─────────────────────────────────────────────
# App Controller — all logic lives here
# ─────────────────────────────────────────────
class AppController:
    def __init__(self, window: MainWindow):
        self.window = window

        self._idle_worker  = None
        self._play_worker  = None
        self._gen_worker   = None
        self._voice_worker = None

        self._is_paused   = False
        self._loop        = False
        self._history     = []   # max 2 video paths
        self._history_idx = -1

        # Connect UI signals → controller methods
        window.translate_requested.connect(self._on_translate)
        window.replay_requested.connect(self._replay)
        window.prev_requested.connect(self._play_prev)
        window.next_requested.connect(self._play_next)
        window.save_requested.connect(self._save)
        window.voice_requested.connect(self._on_voice)
        window.video_panel.btn_play.clicked.connect(self._toggle_pause)
        window.video_panel.loop_check.stateChanged.connect(
            lambda s: setattr(self, '_loop', s == 2)   # Qt.Checked == 2
        )
        window.video_panel.speed_combo.currentIndexChanged.connect(
            self._on_speed_changed
        )

        # Start with idle
        self._start_idle()

    # ─────────────────────────────────────────
    # Voice
    # ─────────────────────────────────────────
    def _on_voice(self):
        """Toggle recording — first click starts, second click stops."""
        if self._voice_worker and self._voice_worker.isRunning():
            # Second click — stop recording, send what we have
            self._voice_worker.stop_recording()
            self.window.set_status("TRANSCRIBING...", "#00c6ff")
            self.window.set_mic_recording(False)
            self.window.set_voice_enabled(False)
            return
        # First click — start recording
        self.window.set_translate_enabled(False)
        self.window.set_status("PREPARING MIC...", "#00c6ff")
        self._voice_worker = VoiceWorker(max_seconds=120)
        self._voice_worker.recording_started.connect(self._on_voice_recording)
        self._voice_worker.done.connect(self._on_voice_done)
        self._voice_worker.error.connect(self._on_voice_error)
        self._voice_worker.start()

    def _on_voice_recording(self):
        self.window.set_mic_recording(True)
        self.window.set_status("🎤  RECORDING...", "#ff4444")

    def _on_voice_done(self, text: str):
        self.window.set_mic_recording(False)
        self.window.set_voice_enabled(True)
        self.window.set_translate_enabled(True)
        if text.strip():
            self.window.insert_text(text)
            self.window.set_status("TRANSCRIBED ✓", "#00e676")
        else:
            self.window.set_error("No speech detected")
            self.window.set_status("STANDBY", "#1e2e5a")

    def _on_voice_error(self, msg: str):
        self.window.set_mic_recording(False)
        self.window.set_voice_enabled(True)
        self.window.set_translate_enabled(True)
        self.window.set_error(f"Voice error: {msg}")
        self.window.set_status("ERROR", "#ff4466")

    # ─────────────────────────────────────────
    # Idle
    # ─────────────────────────────────────────
    def _start_idle(self):
        if not os.path.exists(IDLE_PATH):
            self.window.set_status("IDLE.MP4 NOT FOUND", "#ff4466")
            return
        # loop=True — worker seeks back to frame 0 seamlessly, no gap
        self._idle_worker = VideoWorker(IDLE_PATH, loop=True)
        self._idle_worker.frame_ready.connect(self.window.show_frame)
        self._idle_worker.start()
        self.window.set_status("STANDBY", "#1e2e5a")

    def _stop_idle(self):
        if self._idle_worker:
            self._idle_worker.stop()
            self._idle_worker = None

    # ─────────────────────────────────────────
    # Translation
    # ─────────────────────────────────────────
    def _on_translate(self, text):
        self._stop_idle()
        self._stop_playback()

        self.window.set_translate_enabled(False)
        self.window.set_replay_enabled(False)
        self.window.set_parsed("")
        self.window.set_error("")
        self.window.clear_input()
        self.window.set_status("PARSING...", "#ffaa00")

        # Alternate between result_0.mp4 and result_1.mp4
        idx         = len(self._history) % 2
        output_path = os.path.join(OUTPUT_DIR, f"result_{idx}.mp4")

        self._gen_worker = GenerationWorker(text, output_path)
        self._gen_worker.status_update.connect(self._on_gen_status)
        self._gen_worker.done.connect(self._on_gen_done)
        self._gen_worker.error.connect(self._on_gen_error)
        self._gen_worker.start()

    def _on_gen_status(self, status):
        colors = {"PARSING": "#ffaa00", "GENERATING": "#00c6ff"}
        self.window.set_status(status + "...", colors.get(status, "#aabbee"))

    def _on_gen_done(self, video_path):
        # Update history (max 2)
        self._history.append(video_path)
        if len(self._history) > 2:
            self._history.pop(0)
        self._history_idx = len(self._history) - 1

        self.window.set_translate_enabled(True)
        self.window.set_replay_enabled(True)
        self._update_nav()
        self._play_video(video_path)

    def _on_gen_error(self, msg):
        self.window.set_error(msg)
        self.window.set_translate_enabled(True)
        self.window.set_status("ERROR", "#ff4466")
        self._start_idle()

    # ─────────────────────────────────────────
    # Playback
    # ─────────────────────────────────────────
    def _get_speed(self):
        speeds = {"0.5×": 0.5, "1×": 1.0, "1.5×": 1.5, "2×": 2.0}
        txt = self.window.video_panel.speed_combo.currentText()
        return speeds.get(txt, 1.0)

    def _play_video(self, path):
        self._stop_playback()
        self._is_paused = False
        self._play_worker = VideoWorker(path, speed=self._get_speed())
        self._play_worker.frame_ready.connect(self.window.show_frame)
        self._play_worker.finished.connect(self._on_playback_finished)
        self._play_worker.start()
        self.window.set_status("PLAYING", "#00ffaa", playing=True)
        self.window.set_input_enabled(False)
        self.window.set_nav_enabled(False, False)

    def _stop_playback(self):
        if self._play_worker:
            self._play_worker.finished.disconnect()
            self._play_worker.stop()
            self._play_worker = None

    def _on_playback_finished(self):
        self.window.set_status("DONE  ✓", "#00e676")
        self.window.set_input_enabled(True)
        self._update_nav()
        if self._loop and self._history_idx >= 0:
            self._play_video(self._history[self._history_idx])
        else:
            self._start_idle()

    def _toggle_pause(self):
        if self._play_worker and self._play_worker.isRunning():
            if self._is_paused:
                self._play_worker.resume()
                self._is_paused = False
                self.window.set_status("PLAYING", "#00ffaa", playing=True)
            else:
                self._play_worker.pause()
                self._is_paused = True
                self.window.set_status("PAUSED", "#ffaa00", playing=False)

    def _replay(self):
        if self._history_idx < 0:
            return
        self._stop_idle()
        self._play_video(self._history[self._history_idx])

    def _play_prev(self):
        if self._history_idx > 0:
            self._history_idx -= 1
            self._stop_idle()
            self._play_video(self._history[self._history_idx])
            self._update_nav()

    def _play_next(self):
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self._stop_idle()
            self._play_video(self._history[self._history_idx])
            self._update_nav()

    def _on_speed_changed(self):
        if self._play_worker and self._play_worker.isRunning():
            self._play_worker.set_speed(self._get_speed())

    def _update_nav(self):
        self.window.set_nav_enabled(
            prev = self._history_idx > 0,
            nxt  = self._history_idx < len(self._history) - 1
        )

    # ─────────────────────────────────────────
    # Save
    # ─────────────────────────────────────────
    def _save(self):
        if self._history_idx < 0:
            self.window.set_status("NO VIDEO LOADED", "#ff4466")
            return
        src = self._history[self._history_idx]
        path, _ = QFileDialog.getSaveFileName(
            self.window, "Save Video", "translation.mp4", "Video (*.mp4)"
        )
        if path:
            try:
                shutil.copy(src, path)
                self.window.set_status("SAVED  ✓", "#00e676")
            except Exception:
                self.window.set_status("SAVE FAILED", "#ff4466")


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app    = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    controller = AppController(window)   # wires everything together
    window.show()
    sys.exit(app.exec())