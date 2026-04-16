# tracker.py - Contact history track karo
# Jinhe ek baar contact kar liya, unhe dobara nahi bhejna

import json
import os
from datetime import datetime

TRACKER_FILE = os.path.join("output", "contacted_db.json")


def _load_db() -> dict:
    """JSON file se database load karo."""
    os.makedirs("output", exist_ok=True)
    if not os.path.exists(TRACKER_FILE):
        return {}
    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_db(db: dict):
    """Database JSON file mein save karo."""
    os.makedirs("output", exist_ok=True)
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def _name_city_key(lead: dict) -> str:
    """Name + city se unique key banao (phone nahi hone par bhi track karo)."""
    name = lead.get("name", "").strip().lower()
    city = lead.get("city", "").strip().lower()
    if name and city:
        return f"nc:{name}|{city}"
    return ""


def is_already_contacted(lead: dict) -> bool:
    """
    Check karo kya yeh lead pehle contact ki ja chuki hai.
    place_id, phone number, ya name+city se match karta hai.
    """
    db = _load_db()
    place_id = lead.get("place_id", "")
    phone = lead.get("phone_cleaned", "") or lead.get("phone", "")
    nc_key = _name_city_key(lead)

    if place_id and place_id in db:
        return True
    if phone and phone in db:
        return True
    if nc_key and nc_key in db:
        return True
    return False


def mark_as_contacted(lead: dict, method: str = "whatsapp"):
    """
    Lead ko contacted mark karo.

    Args:
        lead: Business data dict
        method: 'whatsapp' ya 'email'
    """
    db = _load_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    record = {
        "name": lead.get("name", ""),
        "phone": lead.get("phone", ""),
        "address": lead.get("address", ""),
        "city": lead.get("city", ""),
        "topic": lead.get("topic", ""),
        "contacted_via": method,
        "contacted_at": now,
        "message_sent": lead.get("whatsapp_message", "")[:200],
    }

    place_id     = lead.get("place_id", "")
    phone_cleaned = lead.get("phone_cleaned", "") or lead.get("phone", "")
    nc_key       = _name_city_key(lead)

    if place_id:
        db[place_id] = record
    if phone_cleaned:
        db[phone_cleaned] = record
    if nc_key:
        db[nc_key] = record

    _save_db(db)


def mark_bulk_as_contacted(leads: list[dict], method: str = "whatsapp"):
    """
    Ek saath kai leads ko contacted mark karo.
    """
    for lead in leads:
        mark_as_contacted(lead, method)
    print(f"✅ {len(leads)} leads contacted database mein save ho gayi.")


def get_contact_history(lead: dict) -> dict | None:
    """
    Ek lead ka contact history return karo (kab aur kaise contact hua).
    """
    db = _load_db()
    place_id = lead.get("place_id", "")
    phone    = lead.get("phone_cleaned", "") or lead.get("phone", "")
    nc_key   = _name_city_key(lead)

    if place_id and place_id in db:
        return db[place_id]
    if phone and phone in db:
        return db[phone]
    if nc_key and nc_key in db:
        return db[nc_key]
    return None


def filter_already_contacted(leads: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Leads ko do groups mein baanto:
    - fresh: jinhe abhi tak contact nahi kiya
    - already_contacted: jo pehle se DB mein hain

    Returns:
        (fresh_leads, already_contacted_leads)
    """
    fresh = []
    already_done = []

    for lead in leads:
        if is_already_contacted(lead):
            history = get_contact_history(lead)
            lead["skip_reason"] = f"Already contacted via {history.get('contacted_via','?')} on {history.get('contacted_at','?')}"
            already_done.append(lead)
        else:
            fresh.append(lead)

    return fresh, already_done


def print_tracker_summary(fresh: list[dict], already_contacted: list[dict]):
    """Summary print karo."""
    print(f"\n🗄️  Contact History Check:")
    print(f"  🆕 Fresh leads (naye):          {len(fresh)}")
    print(f"  ✅ Already contacted (skip):    {len(already_contacted)}")
    if already_contacted:
        print(f"\n  Skipped (already contacted):")
        for lead in already_contacted:
            print(f"    - {lead.get('name', 'Unknown')}: {lead.get('skip_reason', '')}")


def show_full_history():
    """
    Poora contact history print karo - useful for review.
    """
    db = _load_db()
    if not db:
        print("📭 Abhi tak kisi ko contact nahi kiya gaya.")
        return

    # Unique records dhundho (place_id + phone dono save hote hain)
    seen = set()
    unique_records = []
    for key, record in db.items():
        name = record.get("name", "")
        if name not in seen:
            seen.add(name)
            record["_key"] = key
            unique_records.append(record)

    print(f"\n📋 Contact History ({len(unique_records)} unique businesses):\n")
    print(f"{'#':<4} {'Name':<30} {'City':<15} {'Via':<12} {'Date':<20}")
    print("─" * 85)

    for i, record in enumerate(unique_records, 1):
        name = record.get("name", "")[:28]
        city = record.get("city", "")[:13]
        via = record.get("contacted_via", "")[:10]
        date = record.get("contacted_at", "")[:18]
        print(f"{i:<4} {name:<30} {city:<15} {via:<12} {date:<20}")
