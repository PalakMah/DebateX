import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from topics import get_random_topic, list_categories
from research import build_research_brief
from groq_client import chat

app = FastAPI(title="AI Debater API")

allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (fine for a local/single-user MVP)
SESSIONS = {}


class ResearchRequest(BaseModel):
    session_id: str
    topic: str
    stance: str  # "for" or "against" -- this is the USER's stance


class Turn(BaseModel):
    speaker: str  # "user" or "ai"
    text: str


class DebateRequest(BaseModel):
    session_id: str
    topic: str
    user_stance: str
    history: List[Turn]
    user_message: str


class ScorecardRequest(BaseModel):
    topic: str
    history: List[Turn]


@app.get("/api/categories")
def categories():
    return {"categories": list_categories()}


@app.get("/api/topic/{category}")
def topic(category: str):
    return {"topic": get_random_topic(category)}


@app.post("/api/research")
def research(req: ResearchRequest):
    ai_stance = "against" if req.stance == "for" else "for"
    result = build_research_brief(req.topic, ai_stance)
    SESSIONS[req.session_id] = {
        "topic": req.topic,
        "ai_stance": ai_stance,
        "brief": result["brief"],
        "sources": result["sources"],
    }
    return result


@app.post("/api/debate")
def debate_turn(req: DebateRequest):
    session = SESSIONS.get(req.session_id, {})
    brief = session.get("brief", "(no research brief available)")
    ai_stance = session.get("ai_stance", "against" if req.user_stance == "for" else "for")

    history_text = "\n".join(
        f"{'You' if t.speaker == 'user' else 'AI'}: {t.text}" for t in req.history
    )

    system_prompt = f"""You are a sharp, articulate debate opponent in a live spoken debate.

Topic: "{req.topic}"
Your stance: {ai_stance.upper()}
The user's stance: {req.user_stance.upper()}

Your research brief (use this to ground your arguments, don't just repeat it verbatim):
{brief}

Rules:
- Speak like a real debater talking out loud, not a written essay. Short, punchy sentences.
- Directly engage with what the user just said -- rebut their specific point, don't recite generic talking points.
- Keep responses to 2-4 sentences (this will be spoken aloud, long responses feel unnatural).
- Be respectful but firm and persuasive. No "as an AI" disclaimers, stay fully in character as a debate opponent.
- If the user makes a strong point, you can concede it briefly before pivoting to your counter."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Debate so far:\n{history_text}\n\nUser's latest argument: {req.user_message}\n\nRespond as the AI debater."},
    ]

    reply = chat(messages, temperature=0.8, max_tokens=220)
    return {"text": reply}


@app.post("/api/scorecard")
def scorecard(req: ScorecardRequest):
    transcript = "\n".join(
        f"{'User' if t.speaker == 'user' else 'AI'}: {t.text}" for t in req.history
    )
    prompt = f"""Here is a debate transcript on the topic "{req.topic}":

{transcript}

Evaluate ONLY the User's performance. Return a compact scorecard with:
1. Overall score out of 10
2. Strongest argument they made
3. Any logical fallacies or weak points (be specific, quote them briefly)
4. One concrete tip to improve next time

Be honest and direct, this is a coaching tool."""

    result = chat([{"role": "user", "content": prompt}], temperature=0.4, max_tokens=400)
    return {"scorecard": result}


@app.get("/api/health")
def health():
    return {"status": "ok", "groq_key_set": bool(os.environ.get("GROQ_API_KEY"))}
