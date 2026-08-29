import os
from groq import Groq

# Free tier model on Groq. Swap for another Groq-hosted model if you like.
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
                "and put it in backend/.env as GROQ_API_KEY=..."
            )
        _client = Groq(api_key=api_key)
    return _client


def chat(messages, temperature=0.7, max_tokens=400) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()
