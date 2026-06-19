"""Decode uploaded browser audio (webm/opus, etc.) to 16 kHz mono float32.

Local engines (faster-whisper, BanglaSpeech2Text, Qwen3-ASR) want a normalized
waveform. We use PyAV (a faster-whisper dependency, so it's present whenever the
local engines are installed) to decode whatever MediaRecorder produced. Heavy
imports are done lazily so importing this module stays cheap for the core app.
"""

from __future__ import annotations

import io

TARGET_SR = 16000


def decode_to_mono16k(audio_bytes: bytes):
    """Return (samples: np.float32 ndarray in [-1, 1], sample_rate=16000)."""
    import av  # PyAV — installed with faster-whisper (requirements-local.txt)
    import numpy as np

    container = av.open(io.BytesIO(audio_bytes))
    resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=TARGET_SR)

    chunks: list = []
    for frame in container.decode(audio=0):
        for resampled in resampler.resample(frame):
            chunks.append(resampled.to_ndarray().reshape(-1))

    if not chunks:
        return np.zeros(0, dtype=np.float32), TARGET_SR

    pcm16 = np.concatenate(chunks).astype(np.float32)
    return pcm16 / 32768.0, TARGET_SR
