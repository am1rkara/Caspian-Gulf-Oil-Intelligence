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

SYSTEM_PROMPT = """You are a senior energy market analyst covering Gulf/MENA and Central Asian oil markets.
Write for commodity traders and sovereign wealth fund analysts.
Cold institutional language. No dramatic phrasing. Quantify where possible. No hedging."""

BRIEF_PROMPT_TEMPLATE = """Based on the following energy news headlines, respond in this exact format — no prose paragraphs:

HEADLINES:
{headlines}

TODAY'S KEY RISKS
- [risk 1, one line]
- [risk 2, one line]
- [risk 3, one line]

MARKET IMPACT
- [impact 1, one line]
- [impact 2, one line]

WATCH NEXT 24-48H
- [item 1, one line]
- [item 2, one line]

Use cold institutional language. No dramatic phrasing. Maximum 8 bullet points total.
If no significant news, state that plainly and note the dominant background risk."""


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
