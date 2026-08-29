# DebateX — Architecture & Design Notes
## 🚀 Live Demo

🔗 **Live Application:** [DebateX](https://debate-x-chi.vercel.app/)

### Backend
- **API:** [DebateX Backend](https://debatex-0bho.onrender.com)
- **Health Check:** [API Health](https://debatex-0bho.onrender.com/api/health)
  
DebateX is a voice-based AI debate opponent: pick a topic, take a stance, and
argue live against an LLM that has pre-researched the opposing side. This
document covers *why* it's built the way it is, not just how to run it. For
setup instructions, see the "Quick start" section at the bottom.

## 1. Design philosophy

Three constraints shaped every decision in this codebase:

1. **Zero paid dependencies.** Every capability (LLM inference, web search,
   speech-to-text, text-to-speech) had to have a genuinely free tier or be
   pushed to the browser. This is why STT/TTS live entirely client-side
   (Web Speech API) instead of calling a hosted speech API — it's not an
   optimization, it's the only way to keep the cost at zero.
2. **Latency budget for a live conversation.** A debate has to feel like a
   debate, not a chat app with a spinner. Every architectural choice
   downstream — the choice of Groq (fast inference) over a slower provider,
   the research-brief precompute step, the short `max_tokens` cap on debate
   replies — traces back to keeping the perceived response time low enough
   that voice-to-voice exchange doesn't feel broken.
3. **Minimum viable statefulness.** The app needs *some* memory (which
   stance, which research brief, what's been said) but deliberately avoids
   building real infrastructure for it. This is a legitimate architectural
   stance for an MVP, not an oversight — see §4 for the tradeoffs it
   accepts.

## 2. System architecture

```
┌─────────────────────────┐        HTTP/JSON        ┌──────────────────────────┐
│   Browser (frontend)     │ ───────────────────────▶│    FastAPI backend        │
│  - HTML/CSS/vanilla JS   │◀─────────────────────── │  - Route handlers         │
│  - Web Speech API (STT)  │                          │  - Session store (dict)  │
│  - speechSynthesis (TTS) │                          │  - Prompt construction   │
│  - SVG avatar animation  │                          └────────────┬─────────────┘
└──────────────────────────┘                                       │
                                                     ┌───────────────┼───────────────┐
                                                     ▼               ▼               ▼
                                          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
                                          │  Groq API    │  │ DuckDuckGo   │  │ Session dict │
                                          │ (LLM chat)   │  │  (search)    │  │ (in-memory)  │
                                          └──────────────┘  └──────────────┘  └──────────────┘
```

The frontend never talks to Groq or DuckDuckGo directly. This isn't just
convention — it's the only place the `GROQ_API_KEY` can safely live. A
purely client-side architecture (browser calling Groq directly) would leak
the key to anyone who opened dev tools. The backend's entire reason to
exist, computationally, is to be a secrets boundary plus a place to hold
session state between requests.

## 3. The core theoretical pattern: precompute, then reference

The most important architectural idea in this codebase is in
`backend/research.py`, and it's worth naming explicitly because it's a
general pattern, not a debate-specific trick:

> **Separate the expensive, non-time-critical reasoning step from the
> cheap, time-critical generation step.**

Concretely:

- When the user picks a stance, the backend runs `build_research_brief()`
  **once**: it fires two DuckDuckGo searches (supporting and opposing the
  AI's assigned side), then asks Groq to distill both into a structured
  brief — key arguments, likely opponent points, pre-drafted rebuttals.
  This can take several seconds; that's fine, because it happens during
  the 5-minute research window, off the interactive path.
- Every subsequent debate turn (`/api/debate`) is a *cheap* call: it
  retrieves the already-computed brief from the session dict and injects
  it into a system prompt, so the model is reading prepared notes rather
  than re-deriving arguments from scratch under time pressure.

This is structurally the same idea behind retrieval-augmented generation
(precompute a knowledge base, retrieve at query time) even though the
"database" here is a single cached string per session rather than a vector
store. If you're asked in an interview "how would you make an LLM feel
faster without changing the model," this is the canonical answer: **move
work out of the hot path**.

## 4. State management model

DebateX uses two different, deliberately inconsistent state strategies,
and understanding *why* they differ is the most instructive part of the
codebase:

| What | Where it lives | Why |
|---|---|---|
| Research brief, AI's stance | Backend, `SESSIONS` dict, keyed by `session_id` | Expensive to produce; must persist across turns without the client re-sending it every time. |
| Conversation history (transcript) | Frontend, in a JS array, re-sent in full on every request | Cheap to carry; keeping the backend stateless for this data means no server-side memory growth per turn, and the client is the natural source of truth for "what was said" since it's also rendering the transcript. |

The consequence: the backend is **partially stateful** (session-scoped
research data) and **partially stateless** (conversation history is
passed, not stored). This hybrid is a reasonable MVP tradeoff, but it has
a real limit — the in-memory `SESSIONS` dict has no eviction policy, no
TTL, and no cross-process sharing, so it cannot survive a server restart
or run behind more than one backend instance. The natural evolution is to
move this dict to Redis (or Postgres) keyed the same way, which changes
nothing about the API contract, only where the dict lives.

## 5. Prompt engineering framework

Both LLM call sites go through one shared client (`groq_client.py`), but
are tuned differently because they're solving different problems:

- **Debate turns** (`/api/debate`): `temperature=0.8`, `max_tokens=220`,
  full persona system prompt (stance, topic, research brief, tone rules).
  High temperature because a debate opponent should feel varied and
  assertive, not deterministic. Low token cap because the reply is spoken
  aloud — long responses feel unnatural and increase latency.
- **Scorecard** (`/api/scorecard`): `temperature=0.4`, `max_tokens=400`,
  no system prompt, single analytical instruction. Lower temperature
  because you want consistent, defensible scoring rather than creative
  variation; higher token budget because it's a structured written
  artifact, not something read aloud.

The general principle: **temperature and token budget are properties of
the task's epistemics, not global settings.** Generation tasks that
benefit from personality and variety want higher temperature; evaluation
tasks that should be reproducible want lower temperature. This is worth
being able to articulate independently of this codebase.

## 6. Request lifecycle (one full debate turn)

1. User holds the mic button → the browser's `SpeechRecognition` API
   transcribes speech **locally**, no network round-trip.
2. Frontend `POST`s `{session_id, topic, user_stance, history, user_message}`
   to `/api/debate`.
3. Backend looks up `session_id` in `SESSIONS` to retrieve the cached
   research brief and the AI's stance.
4. Backend builds a system prompt embedding the brief, then calls
   `groq_client.chat()` with the full history flattened into the user
   message.
5. Groq's completion returns as plain text, wrapped in `{"text": ...}`.
6. Browser's `speechSynthesis` reads the reply aloud while a `setInterval`
   cycles the SVG avatar's mouth path to fake lip-sync (not
   viseme-accurate — see limitations).

## 7. Security and scalability posture (what an MVP intentionally defers)

- **No authentication.** Anyone with the URL can call any endpoint and
  consume your Groq quota. Acceptable for local/personal use; a real
  deployment needs per-user auth or rate limiting.
- **`CORS_ORIGINS` defaults to `*`.** Fine for development, should be
  locked to the deployed frontend origin in production.
- **No retry/backoff on Groq calls.** A transient failure surfaces
  directly to the user; production code would wrap `chat()` with retries
  and a fallback message.
- **Synchronous request/response for a real-time use case.** There's no
  token streaming — the client waits for the full completion before
  anything is spoken. Moving to server-sent events or websockets would let
  the avatar start "talking" as tokens arrive, which is the natural next
  step if latency becomes the bottleneck instead of correctness.

## 8. Known limitations

- STT is push-to-talk, not continuous/streaming — no barge-in or
  interruption handling.
- Avatar lip-sync is randomized mouth shapes timed to speech duration, not
  true viseme-accurate lip-sync.
- Single in-memory session store — not multi-instance safe.

## 9. Quick start

```bash
# backend
cd backend
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env
uvicorn main:app --reload --port 8000

# frontend (new terminal)
cd frontend
python3 -m http.server 5500
```

Open `http://localhost:5500` in Chrome. Get a free Groq key at
console.groq.com. Full deployment instructions (Render + Netlify/Vercel)
are unchanged from the original MVP and can be added back here if you
want a deploy-focused section restored.
