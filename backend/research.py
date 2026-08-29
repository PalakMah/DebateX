from duckduckgo_search import DDGS
from groq_client import chat


def search_web(query: str, max_results: int = 6):
    """Free web search, no API key required."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            }
            for r in results
        ]
    except Exception as e:
        return []


def build_research_brief(topic: str, stance: str) -> dict:
    """
    Searches the web for the topic from the given stance's angle, then asks
    the LLM to distill it into a compact knowledge brief: key claims,
    supporting evidence, and likely counterarguments. This brief is what
    powers fast, grounded responses during the live debate.
    """
    side_query = f"{topic} arguments {'for' if stance == 'for' else 'against'}"
    opposing_query = f"{topic} arguments {'against' if stance == 'for' else 'for'}"

    supporting = search_web(side_query, max_results=5)
    opposing = search_web(opposing_query, max_results=5)

    def fmt(results):
        return "\n".join(f"- {r['title']}: {r['snippet']}" for r in results) or "(no results found)"

    prompt = f"""You are preparing a debate brief.

Topic: "{topic}"
Your assigned stance: {stance.upper()}

Search results supporting your stance:
{fmt(supporting)}

Search results supporting the opposing stance:
{fmt(opposing)}

Produce a compact debate brief with three sections:
1. KEY ARGUMENTS FOR YOUR STANCE (3-4 bullet points, each with a concrete fact or statistic if available)
2. LIKELY OPPONENT ARGUMENTS (3-4 bullet points you should be ready to rebut)
3. PRE-DRAFTED REBUTTALS (one sharp rebuttal per opponent argument above)

Be concise and concrete. No preamble."""

    brief_text = chat(
        [{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=650,
    )

    sources = supporting + opposing
    return {"brief": brief_text, "sources": sources}
