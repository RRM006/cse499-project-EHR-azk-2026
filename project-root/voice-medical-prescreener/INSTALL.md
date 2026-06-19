# Installation Guide — Voice Medical Pre-Screener

Works identically on **Windows** and **Arch Linux**. Python 3.11+ (3.14 OK).

## 1. Core install (Browser STT + Groq cloud STT + Gemini correction)

```bash
# from the project root: voice-medical-prescreener/
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Arch Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp backend/.env.example backend/.env   # then fill in keys (see below)
```

Run it:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
# open http://localhost:8000  (Chrome/Edge for the mic)
```

> **Restart the server after editing `backend/.env`.** uvicorn's `--reload` only
> watches `.py` files, so `.env` key changes need a manual restart to take effect.

The core install gives you two working providers immediately:
- **Browser Web Speech API** — no key, Chrome/Edge only.
- **Groq · Whisper Large v3** — set `GROQ_API_KEY` in `backend/.env` (free key:
  https://console.groq.com/keys). Cloud; nothing to download.

Gemini correction needs `GEMINI_API_KEY` (https://aistudio.google.com/apikey).

## 2. Optional local STT engines

Each engine has its own requirements file so their dependencies never conflict.
Install only the ones you want (or all three — they're mutually compatible).

| Provider | Install command | Pulls | Auto-downloaded model |
|----------|-----------------|-------|-----------------------|
| Local Whisper | `pip install -r requirements-whisper.txt` | faster-whisper (CTranslate2, **no torch**) | OpenAI Whisper `WHISPER_MODEL_SIZE` |
| BanglaSpeech2Text | `pip install -r requirements-banglaspeech.txt` | transformers + torch (CPU) | `shhossain/whisper-<size>-bn` |
| Qwen3-ASR-1.7B | `pip install -r requirements-qwen.txt` | qwen-asr + onnxruntime + torch (CPU) | `Qwen/Qwen3-ASR-1.7B` |

After installing, **restart the server**; the provider flips from "Missing Python
Package" to "Available" in the dropdown.

> Why no `banglaspeech2text` PyPI package? It is unmaintained and pins
> `huggingface-hub==0.11.1`, which conflicts with faster-whisper. We run the same
> models through `transformers` instead — same accuracy, no dependency hell.

## 3. Where models are stored, disk usage, first-run time

All weights download to the **Hugging Face cache** on first transcription (not at
install time):
- Linux/macOS: `~/.cache/huggingface/hub`
- Windows: `C:\Users\<you>\.cache\huggingface\hub`
- Override with the `HF_HOME` environment variable.

| Model (default in this repo) | Approx. download | First-run download time* |
|------------------------------|------------------|--------------------------|
| Whisper `base` (faster-whisper) | ~150 MB | ~30–60 s |
| Whisper `small` | ~480 MB | ~1–2 min |
| `shhossain/whisper-base-bn` | ~290 MB | ~30–90 s |
| `shhossain/whisper-small-bn` | ~970 MB | ~2–4 min |
| `Qwen/Qwen3-ASR-1.7B` | ~3.4 GB | ~5–15 min |

Plus one-time **pip** download sizes: torch CPU ≈ 200 MB; onnxruntime ≈ 50 MB;
faster-whisper/ctranslate2 ≈ 40 MB. (*Times assume ~10 MB/s; scale to your link.)

Budget roughly **6–8 GB free disk** if you install all three local engines and
their default models.

## 4. Checking provider health

- In the UI: the **STT Provider** dropdown shows each provider's status badge
  (Available / Missing API Key / Missing Python Package / Missing Model /
  Unsupported Platform / Initialization Error) — hover for details.
- In the API: `GET http://localhost:8000/api/stt/providers` returns
  `installed / configured / ready / status / detail` for every provider.
- In the logs: the server prints an **STT provider health** table at startup.

## 5. Tests

```bash
pytest backend/tests/          # offline; no network, no model downloads
```
