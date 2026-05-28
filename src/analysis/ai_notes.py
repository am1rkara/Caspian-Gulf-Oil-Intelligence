"""
src/analysis/ai_notes.py
Groq-powered thesis section generator.
Returns five structured analyst notes keyed by thesis section.
"""

import os
from datetime import datetime, timezone, timedelta

try:
    from groq import Groq
    _groq_available = True
except ImportError:
    _groq_available = False

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are a commodity markets analyst specializing in Caspian energy and "
    "Gulf market structure. Write in cold institutional language. "
    "No dramatic phrasing. Maximum 4 sentences per section. "
    "Be specific — use the numbers provided. "
    "Never use the word 'crucial', 'critical', 'vital', or 'significant'."
)

_USER_TEMPLATE = """\
Current market data:
Brent: ${brent} | WTI: ${wti} | KZT/USD: {kzt}
KZT fair value: {kzt_fair_value} | Deviation: {kzt_deviation:+.0f} tenge
Hormuz status: {hormuz_status} ({hormuz_signals} signals/7d)
CPC utilization: ~{cpc_utilization:.0f}%
Fiscal buffer: ~${fiscal_buffer_low:.0f}–{fiscal_buffer_high:.0f}B/yr
Contango/backwardation: {contango_spread:+.2f} USD/bbl
Urals discount: -${urals_discount} | Urals realized: ~${urals_realized}

Last 24h headlines:
{formatted_headlines}

Write exactly five sections in this format:

SITUATION
[3-4 sentences on current oil market state and what is driving Brent]

TRANSMISSION
[3-4 sentences on how current Gulf dynamics transmit to Kazakhstan specifically — use the numbers above]

CONSTRAINTS
[3-4 sentences on what structural limits cap Kazakhstan upside today — reference CPC, Urals discount, route concentration]

POSITIONING
[3-4 sentences on KZT fair value deviation and what it implies about NBK policy or market positioning]

RISKS
[3-4 sentences on what in today's news or data could change the thesis — be specific about the asymmetry]"""


def _filter_recent_headlines(headlines: list, hours: int = 24) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    for h in headlines:
        pub = h.get("published_dt")
        if pub and pub.tzinfo is not None and pub > cutoff:
            recent.append(h)
    return recent[:20]


def _format_headlines(headlines: list) -> str:
    if not headlines:
        return "No headlines in last 24 hours."
    return "\n".join(
        f"- [{h.get('source', '?')}] {h.get('title', '')}" for h in headlines
    )


def _parse_sections(text: str) -> dict:
    keys = ("SITUATION", "TRANSMISSION", "CONSTRAINTS", "POSITIONING", "RISKS")
    result = {k.lower(): "" for k in keys}
    current = None
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped in keys:
            current = stripped.lower()
        elif current is not None:
            result[current] += line + "\n"
    return {k: v.strip() for k, v in result.items()}


def generate_thesis_notes(market_data: dict, headlines: list) -> dict:
    """
    Generate five structured thesis sections using Groq.

    Returns dict with keys:
      situation, transmission, constraints, positioning, risks,
      generated_at, source
    """
    _empty = {k: "" for k in ("situation", "transmission", "constraints",
                               "positioning", "risks")}

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {**_empty, "generated_at": None, "source": "no_key"}

    if not _groq_available:
        return {**_empty, "generated_at": None, "source": "no_package"}

    recent_headlines = _filter_recent_headlines(headlines)
    formatted = _format_headlines(recent_headlines)

    # Build prompt — gracefully handle missing/zero fields
    md = market_data
    kzt_fv   = md.get("kzt_fair_value", 0)
    kzt_dev  = md.get("kzt_deviation", 0)
    fv_str   = f"{kzt_fv:.0f}" if kzt_fv else "—"
    dev_val  = float(kzt_dev) if kzt_dev else 0.0

    prompt = _USER_TEMPLATE.format(
        brent=f"{md.get('brent', 0):.1f}",
        wti=f"{md.get('wti', 0):.1f}",
        kzt=f"{md.get('kzt', 0):.0f}",
        kzt_fair_value=fv_str,
        kzt_deviation=dev_val,
        hormuz_status=md.get("hormuz_status", "NORMAL"),
        hormuz_signals=md.get("hormuz_signals", 0),
        cpc_utilization=md.get("cpc_utilization", 0),
        fiscal_buffer_low=md.get("fiscal_buffer_low", 0),
        fiscal_buffer_high=md.get("fiscal_buffer_high", 0),
        contango_spread=md.get("contango_spread", 0.0),
        urals_discount=md.get("urals_discount", 0),
        urals_realized=f"{md.get('urals_realized', 0):.0f}",
        formatted_headlines=formatted,
    )

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        sections = _parse_sections(raw)
        return {
            **sections,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "source": "groq",
        }
    except Exception as e:
        return {
            **_empty,
            "generated_at": None,
            "source": "error",
            "error": str(e),
        }
