"""Application configuration.

All settings are loaded from ``backend/.env`` (gitignored) via pydantic-settings.
Environment variables override file values, which makes this safe for future
deployment (Docker/host env) without code changes. Nothing here is hardcoded.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is backend/app/core/config.py -> parents[2] == the `backend/` dir.
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_SQLITE_PATH = BACKEND_DIR / "prescreener.db"
DEFAULT_DOCUMENTS_DIR = BACKEND_DIR / "data" / "documents"

# Kiosk turn-taking modes (ADR-0047/0048). "auto" = voice-first hands-free loop;
# "manual" = the original tap-to-talk path, never deleted.
VOICE_LOOP_MODES = ("auto", "manual")

# Server-side TTS providers (services/tts). "browser" = no server provider at all, the
# pre-existing ADR-0027 behaviour; "espeak" = local espeak-ng, which is the same engine
# ADR-0040 already accepted for Bangla on Arch.
TTS_PROVIDERS = ("browser", "espeak", "edge")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- speech-to-text source (Module 1 = browser Web Speech API; future-swappable) ---
    stt_provider: str = "browser_webspeech"

    # --- correction provider (swappable: gemini | groq | openrouter) ---
    correction_provider: str = "gemini"
    correction_model: str = "gemini-flash-latest"

    # --- Gemini (OpenAI-compatible endpoint) ---
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # --- correction fallback providers (optional, wired up later) ---
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # --- extra free fallback buckets (optional; blank key = bucket skipped) ---
    # Cerebras: free tier ~1M tokens/day, OpenAI-compatible, very fast.
    # Mistral "Experiment" tier: ~1B tokens/month BUT trains on inputs — rule #4:
    # synthetic/consented data ONLY; leave blank unless you accept that.
    cerebras_api_key: str = ""
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_model: str = "llama-3.3-70b"
    mistral_api_key: str = ""
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_model: str = "mistral-small-latest"

    # --- per-bucket model names (ADR-0026: three independent free quota buckets) ---
    gemini_flash_model: str = "gemini-flash-latest"
    gemini_flash_lite_model: str = "gemini-flash-lite-latest"
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # --- follow-up loop (M7–M9) ---
    # Loop guardrails from the capstone brief: stop on completeness OR max turns
    # (avoids patient fatigue). All tunable without code changes.
    # P1-3 (2.0 build): the main loop also has a FLOOR — it keeps asking useful,
    # history-grounded questions until at least `followup_min_questions` were asked,
    # even when the 0.7 completeness threshold is already met. The KIOSK-7
    # `scope=fields` resume loop is NOT affected by the floor.
    followup_min_questions: int = 4
    followup_max_questions: int = 5
    completeness_threshold: float = 0.7
    # F3: the KIOSK-7 resume loop's OWN budget, on top of followup_max_questions.
    # It used to share the main cap, so the main loop's 4-5 questions consumed the
    # whole allowance and the resume loop had nothing left to ask — the patient
    # reached the review page with required fields still empty and no way to fill
    # them. The resume loop asks about ONE named field at a time (F2), so its
    # questions are cheap, specific, and bounded by how many fields are empty.
    followup_resume_max_questions: int = 8

    # --- patient voice loop (faculty Requirement 3 + 3b; ADR-0047 + ADR-0048) ---
    # VOICE IS THE PRIMARY patient interaction; typing is ALWAYS available as the
    # fallback/accessibility route (ADR-0048 supersedes ADR-0027's voice-only rule).
    # VOICE_LOOP picks the kiosk's turn-taking behaviour:
    #   auto   — voice-first (default): the mic opens itself once TTS finishes and a
    #            VISIBLE 3-2-1 countdown submits the answer.
    #   manual — the S25-era tap-to-talk path, kept selectable for noisy rooms and as
    #            the like-for-like comparison baseline (ADR-0045 pattern: the old path
    #            is never deleted). An unrecognized value falls back to "auto" —
    #            see `resolved_voice_loop`.
    # The timings below are served to the browser by GET /api/config so a clinic can
    # tune them for elderly patients WITHOUT editing JavaScript. They are read at
    # startup only, so a .env change needs a server RESTART.
    voice_loop: str = "auto"
    # The visible 3-2-1 countdown IS the silence window itself (human's S28 decision):
    # speech stops -> the countdown shows -> silence to zero submits. Any resumed
    # speech CANCELS it and listening continues — it is a confirmation window, never a
    # hard cutoff (a clipped answer would be a rule #1 defect, not a UX nit).
    voice_countdown_ms: int = 3000
    # Wait this long after TTS ends before opening the mic, so the browser can never
    # transcribe the AI's own question into the patient's verbatim record (echo guard).
    voice_tts_guard_ms: int = 400
    # Mic open this long with no speech at all -> repeat the question once, then offer
    # typing. Never an infinite wait, never a silent empty submit.
    voice_no_speech_ms: int = 10000
    # Hard cap on a single answer -> submit whatever was captured (runaway guard).
    voice_max_answer_ms: int = 120000
    # S34 (ADR-0055): after a SPOKEN answer is captured, read it back and wait for the
    # patient to accept or repeat it. It is the only moment a patient can hear what the
    # machine understood, and the alternative — submitting on the recogniser's say-so —
    # is how a misheard sentence reaches the doctor unchallenged. Costs one tap per
    # spoken turn, so a clinic that wants the S25-era hands-free flow can set it false.
    # TYPED answers are never gated: the patient is already looking at their own text.
    voice_answer_confirm: bool = True
    # S34 (ADR-0055): the review screen submits itself after this long so an unattended
    # kiosk cannot strand a completed pre-screening on the summary page. Any manual
    # action (Confirm & Submit, Speak Again) cancels it, and it never runs while the
    # server says something is still REQUIRED — see updateSubmitVisibility() in kiosk.js.
    # 0 disables the auto-submit entirely and leaves the patient in full control.
    voice_review_timeout_ms: int = 60000
    # S35 (ADR-0056): how long the spoken phone number is shown and read back before it
    # is accepted on its own. ADR-0053 required a tap here, and its reason still stands —
    # a wrong digit sends the patient's OTP to a stranger. What changed is the DEFAULT
    # when the patient does nothing: an elderly patient who does not know a press is
    # expected used to sit in front of a kiosk that had silently stopped. The number is
    # still shown large and still read back digit by digit; this is the window, not a
    # bypass. Set 0 to restore ADR-0053's tap-required behaviour exactly.
    voice_phone_confirm_ms: int = 10000

    # --- Bangla TTS fallback (services/tts) ---
    # Windows ships NO Bengali voice at all (verified against Microsoft's supported-voices
    # list), so on Windows the browser can never speak Bangla no matter what the patient
    # or the clinic does. TTS_PROVIDER names the SERVER-SIDE fallback used only when the
    # browser has no bn* voice of its own:
    #   browser — none; behave exactly as before (text stays the fallback, ADR-0028).
    #   espeak  — local espeak-ng, offline, no key, no patient text leaves the machine.
    #             Robotic (formant synthesis) — rejected on quality in the S29 live listen.
    #   edge    — Microsoft neural bn-BD via edge-tts. Natural, free, no key. ⚠ sends the
    #             question text to Microsoft (ADR-0050, an explicit rule #4 decision).
    # DEFAULT = edge: naturalness was the whole point of TTS-2, and tts_local_fallback
    # below means a kiosk with no internet still speaks (robotically) rather than falling
    # silent. Set TTS_PROVIDER=espeak for a fully offline/private demo.
    tts_provider: str = "edge"
    tts_espeak_path: str = ""
    # espeak-ng voice per UI language. Bangla is what this whole seam exists for.
    tts_voice_bn: str = "bn"
    tts_voice_en: str = "en-us"
    # Words per minute. espeak's default (175) is too fast for an unwell patient.
    tts_speed_wpm: int = 140
    # edge-tts voices. bn-BD-NabanitaNeural (female) / bn-BD-PradeepNeural (male) are the
    # two Bangladeshi voices; bn-IN-* exist but are Indian Bengali, a different accent.
    tts_edge_voice_bn: str = "bn-BD-NabanitaNeural"
    tts_edge_voice_en: str = "en-US-AriaNeural"
    # Speaking rate as a percentage offset. Slightly slow: the patient may be unwell,
    # elderly, or hearing the question for the first time.
    tts_edge_rate: str = "-10%"
    # S35: pitch and volume, NEUTRAL by default. The voice is already neural; pushing
    # its prosody around is how a synthesizer starts sounding like a cartoon rather than
    # a calm assistant. These are here so a clinic can compensate for a noisy waiting
    # room or a hard-of-hearing patient — not as a "make it sound human" dial.
    tts_edge_pitch: str = "+0Hz"
    tts_edge_volume: str = "+0%"
    # Give up on the network and fall back to the local engine after this long.
    tts_edge_timeout_s: int = 12
    # When the configured provider fails (no internet, service down), render with local
    # espeak-ng instead of returning nothing. A robotic question beats a silent kiosk.
    # Set false to keep ADR-0049's original behaviour: any failure is a bare 503.
    tts_local_fallback: bool = True

    # --- patient identification (kiosk phone + OTP; ADR-0030 + P4-1 ADR-0045) ---
    # OTP_CHANNEL picks the delivery seam (services/otp):
    #   dev     — DevLogSender: code printed to the server log, no SMS.
    #   textbee — TextBeeSender: real SMS via a TextBee.dev Android gateway device.
    # The 000000 universal bypass (dev_otp) is honored ONLY when otp_channel == "dev"
    # AND otp_dev_bypass is true — the check lives inside the dev branch of
    # verify_otp_code, so it is structurally impossible under a production channel.
    otp_channel: str = "dev"
    otp_dev_bypass: bool = True
    dev_otp: str = "000000"
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    textbee_api_key: str = ""
    textbee_device_id: str = ""
    textbee_base_url: str = "https://api.textbee.dev/api/v1"

    # --- persistence ---
    # Leave empty to use the default local SQLite file. Set a full SQLAlchemy URL
    # (e.g. postgresql+psycopg://...) later to move to Postgres without code changes.
    database_url: str = ""

    # Where generated .docx (and later PDF) session exports are written. Leave empty
    # to use the default under backend/data/documents. Point this at any path (or a
    # mounted volume) in deployment without code changes — never hardcoded.
    # Accepts either env var: DOCUMENT_OUTPUT_PATH (canonical) or DOCUMENTS_DIR (legacy).
    documents_dir: str = Field(
        "", validation_alias=AliasChoices("document_output_path", "documents_dir")
    )

    @property
    def resolved_voice_loop(self) -> str:
        """The validated kiosk turn-taking mode. Case-insensitive; anything
        unrecognized falls back to the safe voice-first default rather than breaking
        startup on a .env typo (same spirit as `resolved_database_url`)."""
        mode = (self.voice_loop or "").strip().lower()
        return mode if mode in VOICE_LOOP_MODES else "auto"

    @property
    def resolved_tts_provider(self) -> str:
        """The validated server-side TTS provider. Same forgiving contract as
        `resolved_voice_loop`: an unrecognized .env value degrades to "browser" (i.e.
        the pre-existing behaviour) instead of breaking startup."""
        name = (self.tts_provider or "").strip().lower()
        return name if name in TTS_PROVIDERS else "browser"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        # as_posix() keeps the URL valid on Windows (forward slashes).
        return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

    @property
    def resolved_documents_dir(self) -> Path:
        return Path(self.documents_dir) if self.documents_dir else DEFAULT_DOCUMENTS_DIR


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the .env file is parsed only once per process."""
    return Settings()
