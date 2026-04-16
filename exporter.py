# exporter.py - Data CSV / JSON mein save karo

import csv
import json
import os
from datetime import datetime
from config import OUTPUT_DIR, CSV_FILENAME


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def export_csv(leads: list[dict], filename: str = None) -> str:
    """
    Leads ko CSV mein export karo (Excel compatible).
    """
    ensure_output_dir()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_{timestamp}.csv"

    filepath = os.path.join(OUTPUT_DIR, filename)

    if not leads:
        print("⚠️ Export karne ke liye koi leads nahi hain.")
        return ""

    # CSV columns order
    fieldnames = [
        "lead_type",
        "name",
        "phone",
        "phone_cleaned",
        "website",
        "address",
        "city",
        "topic",
        "rating",
        "total_reviews",
        "photos_count",
        "reason",
        "whatsapp_message",
        "whatsapp_link",
        "google_maps_url",
        "place_id",
    ]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)

    print(f"💾 CSV saved: {filepath}")
    return filepath


def export_json(leads: list[dict], filename: str = None) -> str:
    """
    Leads ko JSON mein export karo (API / DB ke liye).
    """
    ensure_output_dir()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_{timestamp}.json"

    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

    print(f"💾 JSON saved: {filepath}")
    return filepath


def print_leads_table(leads: list[dict], max_rows: int = 10):
    """
    Terminal mein table format mein leads print karo.
    """
    if not leads:
        print("Koi leads nahi.")
        return

    print(f"\n{'='*80}")
    print(f"{'#':<4} {'Name':<30} {'Phone':<15} {'Rating':<8} {'Reviews':<10} {'Website':<10} {'Type':<6}")
    print(f"{'='*80}")

    for i, lead in enumerate(leads[:max_rows], 1):
        name = lead.get("name", "")[:28]
        phone = lead.get("phone", "N/A")[:13]
        rating = str(lead.get("rating", "N/A"))
        reviews = str(lead.get("total_reviews", 0))
        has_website = "Yes" if lead.get("website") else "No"
        lead_type = lead.get("lead_type", "")

        print(f"{i:<4} {name:<30} {phone:<15} {rating:<8} {reviews:<10} {has_website:<10} {lead_type:<6}")

    if len(leads) > max_rows:
        print(f"  ... aur {len(leads) - max_rows} leads hain (CSV mein dekho)")

    print(f"{'='*80}")
