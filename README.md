# The Floor — AI Debater (MVP)
https://ai-debater-seven.vercel.app/ check this out


A local, no-paid-API-required AI debate opponent: pick a category, spin for a
topic, take a stance, research for 5 minutes while the AI researches in
parallel, then debate live by voice with a talking avatar.

## What it uses (all free)

- **LLM**: [Groq](https://console.groq.com) — free API key, generous free
  tier, very fast inference (needed for real-time debate to feel natural).
- **Web search**: DuckDuckGo via `duckduckgo-search` — no key required.
- **Speech-to-text**: your browser's built-in Web Speech API (Chrome/Edge).
  No key, no server round-trip.
- **Text-to-speech**: your browser's built-in `speechSynthesis`. No key.
- **Avatar**: a custom animated SVG face (no avatar API), mouth-synced to
  when the AI is speaking.

## 1. Get a free Groq API key

1. Go to https://console.groq.com and sign up (free).
2. Create an API key.
3. In `backend/`, create a file called `.env`:

```
GROQ_API_KEY=your_key_here
```

(Optional: set `GROQ_MODEL=llama-3.3-70b-versatile` or another Groq-hosted
model — see https://console.groq.com/docs/models for current free models.)

## 2. Run the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Check it's alive: open http://localhost:8000/api/health — you should see
`"groq_key_set": true`.

## 3. Run the frontend

The frontend is plain HTML/JS, no build step. Simplest option:

```bash
cd frontend
python3 -m http.server 5500
```

Then open http://localhost:5500 in **Chrome** (Web Speech API support is
best there). Allow camera access when prompted.

## How it works

1. **Welcome → category → wheel**: topics come from a curated bank per
   category in `backend/topics.py` (edit freely to add your own).
2. **Stance**: you pick for/against, the AI automatically takes the other
   side.
3. **Research (5 min, adjustable)**: on stance selection, the backend fires
   off `build_research_brief()` — DuckDuckGo search for both sides of the
   topic, summarized by Groq into a compact brief (key arguments, likely
   opponent points, pre-drafted rebuttals). This brief is what the AI draws
   on live, so it isn't reasoning from scratch mid-debate. Meanwhile you get
   a notes panel to do your own research in.
4. **Live debate**: hold the mic button, speak, release — the browser
   transcribes it locally, sends the transcript + running history to
   `/api/debate`, Groq generates a short spoken-style rebuttal, and the
   browser speaks it aloud while the avatar's mouth animates.
5. **Scorecard**: on ending, Groq reviews the full transcript and scores
   your argument quality, flags weak points, and gives one improvement tip.

## Deploying (so you're not running localhost every time)

Two pieces, deployed separately: the **backend** (needs a real server — it
calls Groq) and the **frontend** (static files, can go anywhere that serves
HTML).

### 1. Deploy the backend — Render (free tier)

1. Push this project to a GitHub repo (Render deploys from GitHub).
2. Go to https://render.com → **New** → **Blueprint** → connect your repo.
   Render will detect `render.yaml` at the project root and configure
   everything automatically (it points at `backend/` as the root, sets the
   build/start commands).
   - If you'd rather not use the blueprint: **New → Web Service**, root
     directory `backend`, build command `pip install -r requirements.txt`,
     start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. In the service's **Environment** tab, add:
   - `GROQ_API_KEY` = your Groq key
   - `CORS_ORIGINS` = the frontend URL you'll get in step 2 below (you can
     leave this blank / come back and set it once you have that URL —
     it defaults to allowing all origins if unset)
4. Deploy. You'll get a URL like `https://ai-debater-backend.onrender.com`.
   Check it's alive at `https://<your-url>/api/health`.

Free tier note: Render's free web services spin down after inactivity and
take ~30-50s to wake on the next request — the first request after a while
will be slow, that's expected, not a bug.

Alternatives if you prefer: **Railway** and **Fly.io** both work the same
way and have similar free/low-cost tiers — the `backend/` folder is a
standard FastAPI app, nothing here is Render-specific except `render.yaml`.

### 2. Deploy the frontend — Netlify (free)

1. In `frontend/config.js`, replace the URL with your live backend:
   ```js
   window.API_BASE_URL = "https://ai-debater-backend.onrender.com";
   ```
2. Go to https://app.netlify.com/drop and drag the `frontend/` folder in.
   That's it — no build step, it's static files. You'll get a URL like
   `https://your-app.netlify.app`.
   - CLI alternative: `npx netlify-cli deploy --dir=frontend --prod`
   - Vercel or GitHub Pages work identically for this since it's plain
     HTML/JS/CSS.
3. Go back to Render and set `CORS_ORIGINS` to your Netlify URL (comma-
   separate multiple origins if needed) so the backend only accepts
   requests from your deployed frontend.

### Important: camera/mic need HTTPS

Browsers only allow `getUserMedia` (camera) and `SpeechRecognition` (mic)
on secure origins. `localhost` gets a special exception, which is why it
worked before — but once deployed, both Render and Netlify serve over
HTTPS by default, so this isn't something you need to configure, just be
aware it's why it won't work if you ever try plain HTTP.

After this, your link is permanent: `https://your-app.netlify.app` — no
more spinning up terminals.

## Known limitations (this is an MVP, not the full architecture)

- STT is push-to-talk, not continuous/streaming — good enough for testing,
  but real barge-in/interruption handling would need a proper streaming
  pipeline (see the Pipecat/LiveKit suggestion from the architecture plan).
- Latency will feel higher than a production build since there's no
  speculative/precomputed response generation yet — the research brief is
  the only precompute step.
- Single in-memory session store — fine for local use, not multi-user.
- Avatar lip-sync is randomized mouth shapes timed to speech duration, not
  true viseme-accurate lip-sync. Swap in a real viseme library or a hosted
  avatar API (D-ID/HeyGen) if you want more polish later.

## Next steps worth building

- Swap push-to-talk for streaming STT + voice activity detection for a more
  natural back-and-forth.
- Add the fallacy-detection/fact-check-ticker features from the product plan.
- Persist sessions to Postgres instead of the in-memory dict.
