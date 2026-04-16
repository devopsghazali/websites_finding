# demo_run.py - Test run (no input() needed)
# Usage: python demo_run.py

import sys
import os
# Windows console UTF-8 fix (emojis ke liye)
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from scraper import collect_leads
from filter import filter_leads, print_filter_summary
from message_gen import generate_messages_bulk
from whatsapp import add_whatsapp_links, print_whatsapp_summary
from exporter import export_csv, export_json, print_leads_table

# ── YAHAN CHANGE KARO ───────────────────────────────────────
TOPIC = "restaurants"
CITY  = "Lucknow"
# ────────────────────────────────────────────────────────────

print("=" * 60)
print(f"  Demo Run: {TOPIC} in {CITY}")
print("=" * 60)

# Step 1: Scrape
leads = collect_leads(TOPIC, CITY)

# Step 2: Filter
filtered = filter_leads(leads)
print_filter_summary(filtered)

hot   = filtered["hot"]
warm  = filtered["warm"]
targets = hot + warm

if not targets:
    print("\nKoi target lead nahi mili.")
    sys.exit(0)

# Step 3: Messages (template se - FREE)
targets = generate_messages_bulk(targets, use_ai=False)

# Step 4: WhatsApp links
targets = add_whatsapp_links(targets)
print_whatsapp_summary(targets)

# Step 5: Table
print("\n🔥 HOT Leads:")
print_leads_table(hot)
if warm:
    print("\n🌤️  WARM Leads:")
    print_leads_table(warm)

# Step 6: Sample message dekho
if targets:
    print("\n📩 Sample Message (pehli lead):")
    print("─" * 50)
    print(targets[0].get("whatsapp_message", ""))
    print("─" * 50)
    print(f"\n🔗 WhatsApp Link: {targets[0].get('whatsapp_link', 'N/A')}")

# Step 7: Export
csv_path  = export_csv(targets)
json_path = export_json(targets)

print(f"\n✅ Done! {len(targets)} leads saved.")
print(f"   CSV:  {csv_path}")
print(f"   JSON: {json_path}")
