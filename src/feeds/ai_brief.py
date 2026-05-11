"""
src/feeds/ai_brief.py
Groq LLM daily intelligence brief from RSS headlines.
Cache TTL: 6 hours.
"""

import os
from datetime import datetime

try:
    from groq import Groq
    _groq_available = True
except ImportError:
    _groq_available = False

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a senior energy market analyst specializing in Gulf/MENA and Central Asian oil markets.
You write concise, precise intelligence briefs for commodity traders and sovereign wealth fund analysts.
Write factually, avoid hedging language, and quantify impacts where possible.
Do not use bullet points — write in flowing analytical prose."""

BRIEF_PROMPT_TEMPLATE = """Based on the following energy news headlines from the past 24 hours, write a 3-paragraph intelligence brief:

HEADLINES:
{headlines}

Write exactly 3 paragraphs:
Paragraph 1 — GULF/MENA: What moved in Gulf and Middle East energy markets and why. Focus on supply, OPEC+ dynamics, geopolitics.
Paragraph 2 — CENTRAL ASIA TRANSMISSION: How today's Gulf/global moves land in Kazakhstan and Central Asia. Consider CPC pipeline, Urals discount, KZT impact, fiscal implications.
Paragraph 3 — WATCH LIST: The 2-3 most important things to monitor in the next 24-48 hours, and what would change your view.

Be specific and analytical. If no major news today, say so plainly and note background structural themes."""


def generate_brief(articles: list[dict]) -> dict:
    """
    Takes list of article dicts from rss.get_articles().
    Returns: {brief_text, generated_at, model, source}
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return {
            "brief_text": (
                "**AI Brief unavailable** — `GROQ_API_KEY` not set.\n\n"
                "To enable: get a free key at console.groq.com → API Keys, "
                "then add `GROQ_API_KEY=your_key` to your `.env` file."
            ),
            "generated_at": None,
            "model": None,
            "source": "placeholder",
        }

    if not _groq_available:
        return {
            "brief_text": "**AI Brief unavailable** — `groq` package not installed. Run `pip install groq`.",
            "generated_at": None,
            "model": None,
            "source": "placeholder",
        }

    if not articles:
        headlines_text = "No headlines available from RSS feeds at this time."
    else:
        top = articles[:15]
        headlines_text = "\n".join(
            f"- [{a['source']}] {a['title']}" for a in top
        )

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": BRIEF_PROMPT_TEMPLATE.format(headlines=headlines_text)},
            ],
            temperature=0.3,
            max_tokens=700,
        )
        brief_text = response.choices[0].message.content.strip()
        return {
            "brief_text": brief_text,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "model": MODEL,
            "source": "groq",
        }
    except Exception as e:
        return {
            "brief_text": f"**AI Brief generation failed:** {e}\n\nCheck your GROQ_API_KEY and network connectivity.",
            "generated_at": None,
            "model": None,
            "source": "error",
        }
