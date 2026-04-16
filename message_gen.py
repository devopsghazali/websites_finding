# message_gen.py - Message generator
# Default: message_template.txt se (zero cost, no API)
# Optional: Anthropic API se (agar key ho toh)

import os

TEMPLATE_FILE = "message_template.txt"


# ── Template-based (FREE - No API needed) ───────────────────────────────────

def load_template() -> str:
    """
    message_template.txt file se template load karo.
    # wali lines (comments) ignore hoti hain.
    """
    if not os.path.exists(TEMPLATE_FILE):
        raise FileNotFoundError(
            f"'{TEMPLATE_FILE}' nahi mila! "
            "message_template.txt file project folder mein honi chahiye."
        )

    lines = []
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip()
            # Comment lines skip karo
            if not stripped.startswith("#"):
                lines.append(stripped)

    # Leading/trailing blank lines hatao
    full_text = "\n".join(lines).strip()
    return full_text


def fill_template(template: str, lead: dict) -> str:
    """
    Template mein lead ka data fill karo.
    Agar koi variable missing hai toh gracefully handle karo.
    """
    variables = {
        "name":    lead.get("name", "Business Owner"),
        "topic":   lead.get("topic", "business"),
        "city":    lead.get("city", "your city"),
        "rating":  str(lead.get("rating", "N/A")),
        "reviews": str(lead.get("total_reviews", 0)),
    }
    try:
        return template.format(**variables)
    except KeyError as e:
        print(f"⚠️  Template mein unknown variable: {e} — as-is rakh raha hun")
        return template


def generate_from_template(lead: dict) -> str:
    """Template file se message banao (FREE)."""
    template = load_template()
    return fill_template(template, lead)


# ── Anthropic API-based (Optional - only if key available) ──────────────────

def generate_with_ai(lead: dict) -> str:
    """
    Anthropic API se AI-generated message banao.
    Sirf tab call karo jab ANTHROPIC_API_KEY .env mein ho.
    """
    try:
        import anthropic
        from config import ANTHROPIC_API_KEY
        if not ANTHROPIC_API_KEY:
            raise ValueError("No API key")
    except (ImportError, ValueError):
        print("⚠️  Anthropic API key nahi hai — template use kar raha hun")
        return generate_from_template(lead)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    name     = lead.get("name", "Business Owner")
    topic    = lead.get("topic", "business")
    city     = lead.get("city", "your city")
    rating   = lead.get("rating", "N/A")
    reviews  = lead.get("total_reviews", 0)
    has_site = bool(lead.get("website", "").strip())

    prompt = f"""Write a SHORT WhatsApp outreach message (max 5 lines) for a local Indian business:
- Name: {name}
- Type: {topic}
- City: {city}, India
- Rating: {rating}/5
- Reviews: {reviews}
- Has Website: {'Yes' if has_site else 'No'}

Rules: Be friendly, not salesy. Mention no-website if applicable. Offer one benefit. End with a question. Sign as "- Digital Growth Team". Under 60 words. Output only the message."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ── Bulk generator ───────────────────────────────────────────────────────────

def generate_messages_bulk(leads: list[dict], use_ai: bool = False) -> list[dict]:
    """
    Saare leads ke liye messages generate karo.

    Args:
        leads:  Target leads list
        use_ai: True = Anthropic API use karo
                False = Template file use karo (default, FREE)
    """
    mode = "AI (Anthropic)" if use_ai else "Template file"
    print(f"\n✍️  Messages generate ho rahi hain [{mode}] ({len(leads)} leads)...")

    template = None
    if not use_ai:
        try:
            template = load_template()
            print(f"📄 Template loaded from '{TEMPLATE_FILE}'")
        except FileNotFoundError as e:
            print(f"❌ {e}")
            return leads

    for i, lead in enumerate(leads, 1):
        print(f"  [{i}/{len(leads)}] {lead.get('name', 'Unknown')}")
        if use_ai:
            lead["whatsapp_message"] = generate_with_ai(lead)
        else:
            lead["whatsapp_message"] = fill_template(template, lead)

    return leads


# ── Fallback (used by main.py when user skips generation) ───────────────────

def _fallback_message(lead: dict) -> str:
    """Quick fallback — template file se, ya hardcoded agar file nahi."""
    try:
        return generate_from_template(lead)
    except FileNotFoundError:
        name  = lead.get("name", "there")
        topic = lead.get("topic", "business")
        city  = lead.get("city", "your city")
        return (
            f"Hi {name},\n\n"
            f"I noticed your {topic} in {city} on Google Maps "
            f"and wanted to connect about growing your online presence.\n\n"
            f"Would you be open to a quick chat?\n\n"
            f"- Digital Growth Team"
        )
