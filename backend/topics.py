import random

TOPIC_BANK = {
    "entrepreneurship": [
        "Startups should prioritize growth over profitability in their first three years",
        "Bootstrapping builds better founders than raising venture capital",
        "Solo founders are riskier bets than co-founder teams",
        "Most startup ideas fail because of bad timing, not bad execution",
        "Equity-based compensation is fairer than high fixed salaries for early employees",
        "A great product beats a great go-to-market strategy",
        "Founders should ignore their competitors entirely in the first year",
        "Working a corporate job first makes you a better founder later",
    ],
    "finance": [
        "Index fund investing is superior to active stock picking for most people",
        "Cryptocurrency is a net positive innovation for the global financial system",
        "Governments should regulate AI-driven high-frequency trading more strictly",
        "Universal basic income is a fiscally responsible policy",
        "Real estate is a better long-term investment than equities",
        "Central banks should not have raised interest rates as aggressively as they did",
        "Personal debt should be treated as a tool, not a risk to avoid",
        "Financial literacy should be a mandatory school subject over calculus",
    ],
    "geopolitics": [
        "Economic sanctions are an effective tool for changing state behavior",
        "Multilateral institutions like the UN are still relevant in a multipolar world",
        "Nations should prioritize energy independence over climate commitments",
        "Global supply chains should be regionalized rather than globalized",
        "Cyberwarfare should be governed by the same rules as conventional warfare",
        "Smaller nations benefit more from globalization than large ones",
        "Diplomacy is more effective than deterrence in preventing conflict",
        "Trade agreements do more to prevent war than military alliances",
    ],
    "tech-ai": [
        "Open-source AI models are safer for society than closed, proprietary ones",
        "AI will create more jobs than it eliminates over the next decade",
        "Social media platforms should be legally liable for algorithmic harm",
        "Autonomous weapons systems should be banned by international treaty",
        "AI-generated art deserves the same copyright protection as human-made art",
        "Big tech companies should be broken up to preserve competition",
        "Remote work is net positive for long-term innovation",
        "Superintelligent AI is a nearer-term risk than climate change",
    ],
    "self-growth": [
        "Discipline is more important than motivation for long-term success",
        "Failure is a more effective teacher than mentorship",
        "Constant self-optimization does more harm than good",
        "Reading books is a more valuable habit than consuming any other media",
        "Comfort zones should be avoided, not respected",
        "Public speaking skill matters more than technical skill for career growth",
        "Journaling is an overrated productivity habit",
        "You should choose a career for stability over passion in your twenties",
    ],
    "general": [
        "Social media has done more harm than good for society",
        "A four-day work week should be the global standard",
        "Zoos should be phased out entirely",
        "Nuclear energy is the most practical path to a carbon-neutral future",
        "College degrees are becoming less valuable than practical skills",
        "Cities should ban private cars from their downtown cores",
        "Standardized testing should be abolished in schools",
        "Tipping culture should be eliminated in favor of fair fixed wages",
    ],
}


def get_random_topic(category: str) -> str:
    key = category.lower().strip()
    pool = TOPIC_BANK.get(key)
    if not pool:
        pool = random.choice(list(TOPIC_BANK.values()))
    return random.choice(pool)


def list_categories():
    return list(TOPIC_BANK.keys())
