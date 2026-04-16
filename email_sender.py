# email_sender.py - Personalized outreach emails bhejo via Gmail SMTP

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL    = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_APP_PASSWORD", "")   # Gmail App Password
SENDER_NAME     = os.getenv("SENDER_NAME", "Web Developer")
SENDER_PHONE    = os.getenv("SENDER_PHONE", "")
SENDER_PORTFOLIO= os.getenv("SENDER_PORTFOLIO", "")


# ── Email templates ───────────────────────────────────────────────────────────

def _subject(lead: dict) -> str:
    name = lead.get("name", "Aapka Business")
    city = lead.get("city", "")
    has_website = bool(lead.get("website", "").strip())
    if has_website:
        return f"'{name}' — Aapki Website Aur Behtar Ho Sakti Hai"
    else:
        return f"'{name}' ke Competitors Online Hain — Aap Nahi ({city})"


def _body_no_website(lead: dict) -> str:
    """HOT lead — website bilkul nahi hai."""
    name    = lead.get("name", "Aapka Business")
    city    = lead.get("city", "apni city")
    topic   = lead.get("topic", "businesses")
    rating  = lead.get("rating", "")
    rating_line = f"\n✅ Aapki Google rating {rating}/5 achchi hai — website hone se aur zyada customers aayenge." if rating and float(str(rating)) >= 4.0 else ""

    return f"""Namaste {name} Team,

Main {city} mein local businesses dekh raha tha aur Google Maps par aapka listing mila.

Maine notice kiya ki {name} abhi tak online nahi hai — matlab koi website nahi hai.{rating_line}

📉 Iska matlab kya hai?
• Jab koi Google par "{topic} in {city}" search karta hai — aap nahi dikhte
• Aapke competitors jo online hain, unhe aapke muqable ZYADA customers mil rahe hain
• 76% log kisi business ko visit karne se pehle online check karte hain

✅ Ek professional website se kya hoga:
• Google Search mein dikhna — 24/7 free marketing
• Menu / services / timings / location ek jagah
• Online enquiry / booking seedha aapke paas
• Customer trust — "yeh business serious hai"

💰 Main aapke liye ek website bana sakta hoon:
• Sirf ₹5,000–8,000 mein (ek baar ka kharcha)
• Mobile-friendly + Google pe optimize
• 7 din mein ready
• Free demo pehle — pasand aaye tabhi decide karein

Kya main aapko 5 minute ka free demo bana kar dikha sakta hoon?
Ek reply ya call kaafi hai — koi pressure nahi.

Best regards,
{SENDER_NAME}
{('📱 ' + SENDER_PHONE) if SENDER_PHONE else ''}
{('🌐 ' + SENDER_PORTFOLIO) if SENDER_PORTFOLIO else ''}

---
Yeh email sirf aapke liye personally likhi gayi hai kyunki aapka business Google Maps par mila.
Agar interested nahi hain toh reply karein — dobara contact nahi karoonga.
"""


def _body_weak_website(lead: dict) -> str:
    """WARM lead — website hai par weak hai."""
    name    = lead.get("name", "Aapka Business")
    city    = lead.get("city", "apni city")
    website = lead.get("website", "")
    reviews = lead.get("total_reviews", 0)

    low_reviews_line = ""
    if reviews < 20:
        low_reviews_line = f"\n• Sirf {reviews} reviews — zyada reviews dikhne se trust badhta hai"

    return f"""Namaste {name} Team,

Maine aapki website dekhi: {website}

Aapka business Google Maps par hai aur kuch kaam bhi ho raha hai — lekin mujhe laga main
kuch suggestions share karoon jo aapki online presence strong kar sakti hain:{low_reviews_line}
• Website ka design aur speed improve ho sakti hai (Google ranking ke liye important)
• Mobile users ke liye better experience
• Online enquiry / contact form easy hona chahiye
• Local SEO — "{name} {city}" Google par top pe aana

Main in sab mein help kar sakta hoon, bahut affordable cost mein.

Kya ek quick 10 minute ki call par baat kar sakte hain?

Best regards,
{SENDER_NAME}
{('📱 ' + SENDER_PHONE) if SENDER_PHONE else ''}
{('🌐 ' + SENDER_PORTFOLIO) if SENDER_PORTFOLIO else ''}
"""


# ── Send function ─────────────────────────────────────────────────────────────

def send_email(to_email: str, lead: dict) -> dict:
    """
    Ek personalized email bhejo.

    Returns:
        {'ok': True/False, 'error': str or None}
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return {"ok": False, "error": "SENDER_EMAIL ya SENDER_APP_PASSWORD .env mein set nahi hai"}

    if not to_email:
        return {"ok": False, "error": "Email address empty hai"}

    has_website = bool(lead.get("website", "").strip())
    subject = _subject(lead)
    body    = _body_weak_website(lead) if has_website else _body_no_website(lead)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        return {"ok": True, "error": None}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "Gmail login fail — App Password check karo (.env mein SENDER_APP_PASSWORD)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_bulk_emails(leads_with_emails: list[dict]) -> list[dict]:
    """
    Multiple leads ko emails bhejo.
    Each item: {'lead': {...}, 'email': 'x@y.com'}
    Returns list of results.
    """
    results = []
    for item in leads_with_emails:
        lead  = item.get("lead", {})
        email = item.get("email", "")
        res   = send_email(email, lead)
        res["name"]  = lead.get("name", "")
        res["email"] = email
        results.append(res)
        if res["ok"]:
            import time; time.sleep(1.5)   # Gmail rate limit se bachne ke liye
    return results
