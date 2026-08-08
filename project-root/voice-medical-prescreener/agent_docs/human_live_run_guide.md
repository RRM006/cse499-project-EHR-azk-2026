# 🧑‍⚕️ Human Guide — Live Run, Bangla Voice, and Key Rotation

> The build is done (150 tests pass). These are the **3 things only a human can do**.
> Do them **in this order**. No coding needed — just clicking and speaking.
> Time needed: ~10 min setup, ~20 min for the live test.

---

## ✅ PART 0 — Start the app (do this first, every time)

1. Open a terminal in the project folder:
   `...\voice-medical-prescreener`
2. Paste this (Windows) and press Enter:
   ```
   .venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001
   ```
   (Arch Linux: `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8001`)
3. Leave that window open. You should see log lines ending with the entry-point list.
4. Open **Google Chrome** (not Edge/Firefox — the mic + voice work best in Chrome).

**The 4 pages you'll use:**
| Page | Address |
|---|---|
| Patient kiosk | http://localhost:8001/kiosk.html |
| Medic desk | http://localhost:8001/medic/ |
| Doctor | http://localhost:8001/doctor/ |
| Landing (links to all) | http://localhost:8001/ |

💡 If a page looks old/wrong after an update, press **Ctrl+F5** (hard refresh).

---

## 🔊 PART 1 — Install espeak-ng so Windows can speak Bangla (2 min, before testing audio)

> ⚠ **CORRECTED 2026-08-08 (ADR-0049). The old version of this section was wrong** and told you
> to add a Bengali voice in Settings → Speech. **That is impossible: Windows has no Bengali
> TTS voice at all** — Bengali appears nowhere in Microsoft's supported-voices list (neither
> `bn-BD` nor `bn-IN`, neither the classic nor the Natural-voices table). Searching "Bengali"
> in "Add voices" will never find one, however long you look. That is not a bug in the kiosk
> and not something you did wrong. Do not spend time on it.

Instead the kiosk now has a **server-side Bangla voice**: the backend renders the question
with **espeak-ng** and the browser plays the audio. An installed browser Bangla voice still
wins if one exists (that is the Arch path, PART 1B) — this is the fallback for Windows.

**Steps — ✅ ALREADY DONE on the Windows desktop (S29). Kept for the Arch laptop / a fresh machine:**
1. Open **PowerShell** and run (it will show a **UAC prompt** — click **Yes**):
   ```
   winget install eSpeak-NG.eSpeak-NG
   ```
2. **Restart the server** (`Ctrl+C`, then the usual `uvicorn` command). The backend looks for the
   engine and reports it to the kiosk. ⚠ The MSI updates the **machine** PATH, which processes
   started *before* the install cannot see — so the restart genuinely matters. (The code also
   checks `C:\Program Files\eSpeak NG\espeak-ng.exe` directly, so it works even without a reboot.)
3. Reload the kiosk with **Ctrl+Shift+R** (a plain reload can keep old JavaScript).

**How to know it worked:**
- Visit `http://localhost:8001/api/config` — you want **`"server_tts": true`**. If it says
  `false`, the engine was not found: reopen PowerShell and check `espeak-ng --version` works.
- Open the kiosk and start a consultation. The yellow **"no Bangla voice"** banner should now
  be **gone**, and you should **hear** each question. ✅ = banner gone + audible Bangla.
- Direct engine check, no kiosk needed — paste in PowerShell:
  ```
  espeak-ng -v bn -w test.wav --stdin
  ```
  then type some Bangla, press Enter, `Ctrl+Z`, Enter — and play `test.wav`.
- ⚠ **espeak-ng's Bangla is robotic**, exactly as on Arch (ADR-0040). That is expected and
  accepted: the on-screen text is always the primary channel (ADR-0028). If you later want a
  natural neural Bangla voice, ADR-0049 records the two options and where they plug in.

**If you would rather not install anything:** try opening the kiosk in **Microsoft Edge**
instead of Chrome. Edge may expose Microsoft's online `bn-BD` neural voices to the page, which
would sound far better — paste
`speechSynthesis.getVoices().filter(v=>v.lang.toLowerCase().startsWith('bn'))` in Edge's
Console (run it twice; the list loads asynchronously). If it returns voices, the kiosk will
prefer them automatically with no configuration. This is unverified — worth 30 seconds.

---

## 🐧 PART 1B — Enable a Bangla voice on Arch Linux (5 min)

On Linux the browser doesn't ship its own voices — it reads them from the system's
**speech-dispatcher** service, which in turn uses **espeak-ng** as the synthesizer.
On a fresh Arch box neither is installed, so the kiosk's 🔊 button is **silent** (it
still shows the question as text — the safety fallback — but plays no audio). This is a
system setup step, not a code fix.

> Note: this only affects the **spoken audio (TTS)**. The **microphone / speech-to-text**
> is unaffected by these packages.

**Steps:**
1. Install the two packages (one time):
   ```
   sudo pacman -S speech-dispatcher espeak-ng
   ```
   `espeak-ng` is the actual voice and **ships a Bengali (`bn`) voice**; `speech-dispatcher`
   is the bridge Chromium reads from (espeak-ng is already its default output module, so no
   config editing is needed).
2. Check the system can speak **before** touching the browser:
   ```
   espeak-ng --voices | grep -i 'bn\|beng'   # a Bengali line should appear
   spd-say "hello"                            # you should HEAR this
   ```
   (If `spd-say` is silent, start the service once with
   `systemctl --user start speech-dispatcher` and retry — normally it auto-starts on demand.)
3. **Fully quit Chromium and reopen it** (voices are only read on a fresh start).

**How to know it worked** (same check as Windows):
- Open the kiosk and start a consultation. The yellow **"no Bangla voice"** hint banner at
  the top **disappears**, and you now **hear** the questions spoken. ✅ = banner gone + audio.
- Quick check without the kiosk: Chromium → F12 → Console, paste
  `speechSynthesis.getVoices().filter(v=>v.lang.startsWith('bn'))` and press Enter — a
  **non-empty** result means the Bengali voice is visible to the browser.

> ⚠ The espeak-ng Bengali voice sounds **robotic** — that's expected on Linux and is fine
> for a demo. The on-screen text stays the primary channel (ADR-0028), so audio is a bonus.

---

## 🎤 PART 2 — The live real-mic test (the main task, ~20 min)

Do the whole patient journey once with your **real microphone**. Along the way you'll
naturally hit every test case (TC-V1, V2, V3, F2, R1). Keep a notepad to jot results.

⚠ **Use fake/pretend patient info only** (make up a name and symptoms). Never real patient
data — the browser sends audio to Google and the AI APIs may keep inputs.

### Walkthrough

1. **Open** http://localhost:8001/kiosk.html
2. Enter any phone number, then the OTP code **`000000`** (six zeros). → Enter.
3. When Chrome asks, click **Allow** for the microphone.
4. Press the **speak** button and say a complaint out loud, e.g. (Banglish is fine):
   > "amar 3 din dhore matha betha ar halka jor ache, raate ghum hocche na"
   - 👀 **Watch the screen:** your words should appear **live** as you speak, and stay
     **exactly** as spoken. → this is **TC-V1** (raw transcript). ✅ = words appear and are
     not silently changed.
5. The assistant will **ask follow-up questions** — each one is **shown on screen AND spoken
   aloud** (if you did Part 1).
   - ✅ **TC-V2** = you hear the question AND see the same text.
   - It should only ask about **missing** things, one at a time, and **not repeat** what you
     already answered. → this is **TC-F2** (smart follow-up loop).
6. **Answer each question by voice** (don't type). The answer should turn into text and be
   accepted. → **TC-V3** (voice-only). ✅ = you never had to touch the keyboard.
   - (If the mic ever fails, a text box appears as a backup — that's expected, only for
     emergencies.)
7. When all 10 items are filled, the **summary** appears. Try:
   - the **English ↔ বাংলা** toggle — labels **and** your answers should both switch language.
   - the **Download Raw Transcript (.docx)** button — opens a Word file of your exact words.
   - **Confirm & Submit**.
8. **Switch to the medic page** (http://localhost:8001/medic/): your case is in the queue.
   Open it, check the risk/summary, pick a doctor, click **Submit & Forward**, and try the
   **Download Report (.docx)**.
9. **Switch to the doctor page** (http://localhost:8001/doctor/, log in as the doctor you
   assigned): open the case, check the patient card, then click **📝 Write Prescription**,
   type a diagnosis + a medicine, and **Generate Prescription** — a Word file downloads. ✅

### One extra 30-second test — red flag (TC-R1) 🚨
1. Start a **new** kiosk visit (phone + `000000`).
2. When asked your problem, say clearly: **"আমার বুকে প্রচণ্ড ব্যথা"** (severe chest pain).
3. Submit, open it in the medic page.
   - ✅ **PASS** = the risk shows **Critical** and a **Red Flag** line appears. (The system
     must flag life-threatening words even if the AI is having a bad day.)

### Jot these down (for your report)
- For ~10 sentences: did the text match what you said? (rough accuracy)
- Roughly how many seconds from speaking → text appearing? (latency)
- Which questions were spoken aloud vs text-only?
- Any question repeated or asked about something you'd already answered? (should be none)

---

## 🔑 PART 3 — Rotate the API keys (before showing anyone / any public demo)

The three AI keys were typed into chat during development, so treat them as "burned" — make
new ones before a demo. They live in **`backend/.env`** (this file is private and never
uploaded).

**For each provider: make a new key, then paste it over the old one in `backend/.env`.**

| In `backend/.env` | Provider | Get a fresh key here |
|---|---|---|
| `GEMINI_API_KEY=` | Google AI Studio | https://aistudio.google.com/apikey |
| `GROQ_API_KEY=` | Groq | https://console.groq.com/keys |
| `OPENROUTER_API_KEY=` | OpenRouter | https://openrouter.ai/keys |

**Steps:**
1. Open each link above, log in, **create a new key**, and **delete/revoke the old one** on
   that site.
2. Open `backend/.env` in a text editor (Notepad is fine).
3. Replace the value after each `=` with your new key. Example:
   `GEMINI_API_KEY=AIza....your-new-key....`
   (No quotes, no spaces around the `=`.)
4. Save the file.
5. **Restart the server** (close the terminal window from Part 0, run the command again) —
   `.env` is only read at startup.

💡 Never commit `backend/.env` to git (it's already ignored). Only `backend/.env.example`
(blank) is shared.

---

## Quick reference

- **OTP code:** `000000`
- **Start server:** `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001`
- **Hard refresh a page:** Ctrl+F5
- **Rule to remember:** use **made-up** patient info only during testing.
- Stuck? Tell Claude Code what you saw on screen and it can help debug.
