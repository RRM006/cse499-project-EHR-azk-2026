"""espeak-ng provider — local, offline, no API key, no Python dependency.

Chosen because it is NOT a new engine for this project: ADR-0040 already accepted
espeak-ng's Bengali voice on Arch (TC-V2 audio PASS), so Bangla now sounds the same on
both dev machines. It is robotic, which ADR-0028 already deems acceptable because the
on-screen text is always the primary channel.

The decisive property for a MEDICAL kiosk: the question text never leaves the machine.
M7 questions are derived from what the patient said, so shipping them to a cloud TTS
would export patient-derived content to a third party (rule #4). This does not.

Install: `winget install eSpeak-NG.eSpeak-NG` (Windows) · `pacman -S espeak-ng` (Arch).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import MAX_TEXT_CHARS, TtsProvider, TtsUnavailable

__all__ = ["EspeakNgProvider", "MAX_TEXT_CHARS", "WELL_KNOWN_BINARIES"]

# Where the official installers put it, checked after PATH. The Windows MSI updates the
# MACHINE PATH, which processes started before the install do not see — so a clinic that
# installs espeak-ng without rebooting would otherwise get "not installed" forever.
WELL_KNOWN_BINARIES = (
    r"C:\Program Files\eSpeak NG\espeak-ng.exe",
    r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe",
    "/usr/bin/espeak-ng",
    "/usr/local/bin/espeak-ng",
)

# MAX_TEXT_CHARS now lives in base.py (it is the endpoint's contract, not espeak's) and
# is re-exported above so existing importers keep working.
# espeak-ng renders far faster than real time; this only catches a hung process.
RENDER_TIMEOUT_S = 20


class EspeakNgProvider(TtsProvider):
    name = "espeak"
    media_type = "audio/wav"

    def __init__(
        self,
        binary: str = "",
        voice_bn: str = "bn",
        voice_en: str = "en-us",
        speed_wpm: int = 140,
    ) -> None:
        self._binary = binary
        self._voices = {"bn": voice_bn, "en": voice_en}
        self._speed_wpm = speed_wpm

    def resolve_binary(self) -> str | None:
        """Absolute path to the engine, or None if it is not installed.

        Kept public so the /api/config availability flag and the health of the seam can
        be reported without synthesizing anything.
        """
        if self._binary:
            return self._binary if Path(self._binary).is_file() else None
        # espeak-ng is the maintained fork; plain espeak is accepted as a fallback
        # because some distros still ship only that name.
        found = shutil.which("espeak-ng") or shutil.which("espeak")
        if found:
            return found
        return next((p for p in WELL_KNOWN_BINARIES if Path(p).is_file()), None)

    def available(self) -> bool:
        """The engine is a local binary, so presence IS knowable without synthesizing."""
        return self.resolve_binary() is not None

    def synthesize(self, text: str, lang: str) -> bytes:
        if not text or not text.strip():
            raise TtsUnavailable("Refusing to synthesize empty text.")
        if len(text) > MAX_TEXT_CHARS:
            raise TtsUnavailable(f"Text exceeds {MAX_TEXT_CHARS} characters.")
        voice = self._voices.get(lang)
        if not voice:
            raise TtsUnavailable(f"No espeak-ng voice configured for language {lang!r}.")
        binary = self.resolve_binary()
        if not binary:
            raise TtsUnavailable(
                "espeak-ng is not installed. Windows: winget install eSpeak-NG.eSpeak-NG"
                " · Arch: pacman -S espeak-ng"
            )

        # Write to a temp file rather than stdout: espeak-ng's WAV-to-stdout path is not
        # reliable across versions/platforms, and a real file gives a valid RIFF header.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tts.wav"
            argv = [
                binary,
                "-v", voice,
                "-s", str(self._speed_wpm),
                "-w", str(out),
                "--stdin",   # text via stdin, so Bangla never goes through argv encoding
            ]
            try:
                done = subprocess.run(
                    argv,
                    input=text.encode("utf-8"),   # UTF-8 in, no shell, no quoting risk
                    capture_output=True,
                    timeout=RENDER_TIMEOUT_S,
                    shell=False,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise TtsUnavailable("espeak-ng timed out.") from exc
            except OSError as exc:   # missing/unexecutable binary, permissions
                raise TtsUnavailable(f"Could not run espeak-ng: {exc}") from exc

            if done.returncode != 0:
                detail = done.stderr.decode("utf-8", "replace").strip()[:300]
                raise TtsUnavailable(f"espeak-ng failed (exit {done.returncode}): {detail}")
            if not out.is_file():
                raise TtsUnavailable("espeak-ng produced no output file.")
            audio = out.read_bytes()

        # A WAV header alone is ~44 bytes; anything that small is silence, which must be
        # reported as a failure rather than played as if Bangla had been spoken.
        if len(audio) <= 64 or not audio.startswith(b"RIFF"):
            raise TtsUnavailable("espeak-ng produced no audible audio.")
        return audio
