import pyaudio
import wave
import requests
import os
import tempfile

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIwY2Q3NTNlZS0xYjExLTQ5NTQtODhjNC01Y2E4YWM5MjZmZDUiLCJpc1ByaW1hcnkiOmZhbHNlLCJ0b2tlbklkIjoiYmFmZmIxNDAtMjZhMy0xMWYxLTlhODktNjIxNWVjMTVkMjFlIiwiaWF0IjoxNzc0MjYyMDA4fQ.OiWIRXgsx0UxttyAoGJppD199TGQn-1QPAkEAFRqtVY"
API_URL = "https://api.hispeech.ai/api/v1/transcriptions/upload"

CHUNK          = 1024
FORMAT         = pyaudio.paInt16
CHANNELS       = 1
RATE           = 16000
RECORD_SECONDS = 10


def record_audio(filename: str, seconds: int = RECORD_SECONDS) -> None:
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK)
    frames = []
    for _ in range(int(RATE / CHUNK * seconds)):
        frames.append(stream.read(CHUNK))
    stream.stop_stream()
    stream.close()
    p.terminate()
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))


def transcribe_audio(filename: str) -> str:
    headers = {"x-auth-token": API_KEY}
    with open(filename, 'rb') as f:
        files = {"file": (os.path.basename(filename), f, "audio/wav")}
        data  = {"wait_for_result": "true", "secure_mode": "false"}
        response = requests.post(API_URL, headers=headers, files=files, data=data)
    if response.status_code == 200:
        result = response.json()
        if result.get("success") in ("true", True):
            return result.get("transcription", "")
        raise Exception(f"API error: {result.get('error')}")
    raise Exception(f"HTTP {response.status_code}: {response.text}")