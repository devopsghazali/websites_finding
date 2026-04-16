# whatsapp.py - WhatsApp links banao (safe semi-automation)

import urllib.parse
import webbrowser
import time


def clean_phone(phone: str) -> str:
    """
    Phone number clean karo - India format mein convert karo.
    Example: +91 98765 43210 → 919876543210
    """
    if not phone:
        return ""

    # Sirf digits rakhho
    digits = "".join(filter(str.isdigit, phone))

    # India code add karo agar nahi hai
    if digits.startswith("91") and len(digits) == 12:
        return digits
    elif digits.startswith("0") and len(digits) == 11:
        return "91" + digits[1:]
    elif len(digits) == 10:
        return "91" + digits

    return digits


def make_wa_link(phone: str, message: str) -> str:
    """
    wa.me link banao - click karne par WhatsApp khulega.
    Safe, manual send - account ban ka koi risk nahi.
    """
    clean = clean_phone(phone)
    if not clean:
        return ""

    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{clean}?text={encoded_msg}"


def add_whatsapp_links(leads: list[dict]) -> list[dict]:
    """
    Har lead mein WhatsApp link add karo.
    """
    for lead in leads:
        phone = lead.get("phone", "")
        message = lead.get("whatsapp_message", "")
        lead["whatsapp_link"] = make_wa_link(phone, message)
        lead["phone_cleaned"] = clean_phone(phone)
    return leads


def open_whatsapp_links(leads: list[dict], delay: float = 3.0):
    """
    Semi-automation: ek ek karke links browser mein kholna.
    Har link ke beech delay hai taaki spam na ho.

    Args:
        leads: Leads list with whatsapp_link
        delay: Seconds between each opening
    """
    valid_leads = [l for l in leads if l.get("whatsapp_link")]

    if not valid_leads:
        print("⚠️ Koi valid phone number nahi mila!")
        return

    print(f"\n📱 WhatsApp links khul rahe hain ({len(valid_leads)} leads)...")
    print("⚠️  Manual send karo - SPAM mat karo!\n")

    for i, lead in enumerate(valid_leads, 1):
        name = lead.get("name", "Unknown")
        link = lead.get("whatsapp_link", "")

        print(f"[{i}/{len(valid_leads)}] Opening: {name}")
        print(f"  Message preview: {lead.get('whatsapp_message', '')[:80]}...")
        print(f"  Link: {link[:60]}...")

        webbrowser.open(link)

        if i < len(valid_leads):
            print(f"  ⏳ {delay}s wait kar raha hun...")
            time.sleep(delay)

    print("\n✅ Sabhi links khul gaye!")


def print_whatsapp_summary(leads: list[dict]):
    """Summary print karo."""
    with_phone = sum(1 for l in leads if l.get("phone_cleaned"))
    without_phone = len(leads) - with_phone

    print(f"\n📱 WhatsApp Summary:")
    print(f"  ✅ Phone number mila:    {with_phone}")
    print(f"  ❌ Phone number nahi mila: {without_phone}")
