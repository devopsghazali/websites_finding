# main.py - Lead Generation Tool - CLI Entry Point
# Usage: python main.py

import sys
import os
# Windows console UTF-8 fix (emojis ke liye)
sys.stdout.reconfigure(encoding='utf-8')

# ── Banner ──────────────────────────────────────────────────────────────────
def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║       🇮🇳  India Local Business Lead Generator           ║
║       Find businesses with no website → send outreach    ║
╚══════════════════════════════════════════════════════════╝
""")

# ── Imports ──────────────────────────────────────────────────────────────────
from scraper import collect_leads
from filter import filter_leads, print_filter_summary
from message_gen import generate_messages_bulk, _fallback_message
from whatsapp import add_whatsapp_links, print_whatsapp_summary, open_whatsapp_links
from exporter import export_csv, export_json, print_leads_table
from tracker import mark_bulk_as_contacted, show_full_history


# ── Main Menu ────────────────────────────────────────────────────────────────
def show_menu() -> str:
    print("Kya karna chahte ho?\n")
    print("  [1] Naye leads dhundho aur outreach karo")
    print("  [2] Contact history dekho (pehle se contact ki gayi list)")
    print("  [3] Exit\n")
    return input("Choice (1/2/3): ").strip()


# ── Main Flow ────────────────────────────────────────────────────────────────
def run_search():
    """Search → Filter → Message → WhatsApp → Track flow."""

    # ── Step 1: User Input ──────────────────────────────────────────────────
    print("\n📝 Search Setup\n" + "─" * 40)

    topic = input("Topic kya hai? (e.g. restaurants, salons, gyms): ").strip()
    if not topic:
        print("❌ Topic empty nahi hona chahiye.")
        return

    city = input("City kaunsi? (e.g. Lucknow, Delhi, Mumbai): ").strip()
    if not city:
        print("❌ City empty nahi honi chahiye.")
        return

    # ── Step 2: Scrape ──────────────────────────────────────────────────────
    try:
        leads = collect_leads(topic, city)
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("💡 Hint: .env file mein GOOGLE_MAPS_API_KEY set karo")
        return

    if not leads:
        print("⚠️ Koi business nahi mila. Topic ya city change karke try karo.")
        return

    # ── Step 3: Filter (tracker check included) ─────────────────────────────
    # filter_leads ke andar hi already_contacted automatically skip ho jaati hain
    filtered = filter_leads(leads)
    print_filter_summary(filtered)

    hot_leads = filtered["hot"]
    warm_leads = filtered["warm"]
    already_contacted = filtered.get("already_contacted", [])
    all_target_leads = hot_leads + warm_leads

    if not all_target_leads:
        if already_contacted:
            print(f"\n⚠️ Saari {len(already_contacted)} businesses pehle contact ho chuki hain.")
            print("💡 Naya topic ya city try karo.")
        else:
            print("\n✅ Saare businesses ki strong online presence hai. Koi target nahi.")
        return

    # ── Step 4: Show Table ──────────────────────────────────────────────────
    if hot_leads:
        print(f"\n🔥 HOT Leads ({len(hot_leads)}):")
        print_leads_table(hot_leads)

    if warm_leads:
        print(f"\n🌤️  WARM Leads ({len(warm_leads)}):")
        print_leads_table(warm_leads)

    # ── Step 5: Generate Messages ───────────────────────────────────────────
    print("\n✍️  Message Generation:")
    print("  [1] Template file use karo (FREE - message_template.txt)")
    print("  [2] AI se generate karo (Anthropic API key chahiye)")
    msg_choice = input("Choice (1/2) [default: 1]: ").strip()

    use_ai = msg_choice == "2"
    all_target_leads = generate_messages_bulk(all_target_leads, use_ai=use_ai)

    # ── Step 6: WhatsApp Links ──────────────────────────────────────────────
    all_target_leads = add_whatsapp_links(all_target_leads)
    print_whatsapp_summary(all_target_leads)

    # ── Step 7: Export ──────────────────────────────────────────────────────
    print("\n💾 Saving data...")
    csv_path = export_csv(all_target_leads)
    json_path = export_json(all_target_leads)

    # ── Step 8: Open WhatsApp (Optional) ───────────────────────────────────
    valid_leads = [l for l in all_target_leads if l.get("whatsapp_link")]

    if valid_leads:
        open_wa = input(
            f"\n📱 {len(valid_leads)} leads ke WhatsApp links browser mein kholna chahte ho? (y/n): "
        ).strip().lower()

        if open_wa == "y":
            delay_input = input("Har message ke baad kitne seconds wait kare? (default: 3): ").strip()
            try:
                delay = float(delay_input) if delay_input else 3.0
            except ValueError:
                delay = 3.0

            open_whatsapp_links(valid_leads, delay=delay)

            # ── Step 9: Mark as Contacted ───────────────────────────────────
            # Sirf unhe mark karo jinke links khule (phone number tha)
            method = input("\n📝 Kaise contact kiya? (whatsapp/email) [default: whatsapp]: ").strip().lower()
            if method not in ("whatsapp", "email"):
                method = "whatsapp"

            mark_bulk_as_contacted(valid_leads, method=method)
            print(f"🗄️  {len(valid_leads)} leads contact history mein save ho gayi.")
            print("💡 Agali baar inhe automatically skip kiya jayega!")

    else:
        print("\n⚠️ Koi phone number nahi mila - WhatsApp links nahi ban sake.")
        print("💡 Manually CSV se phone numbers use karo.")

        # Manual mark option
        manual_mark = input(
            "\nKya manually CSV dekh kar contact karoge? Mark as contacted? (y/n): "
        ).strip().lower()
        if manual_mark == "y":
            method = input("Kaise contact kiya? (whatsapp/email) [default: whatsapp]: ").strip().lower()
            if method not in ("whatsapp", "email"):
                method = "whatsapp"
            mark_bulk_as_contacted(all_target_leads, method=method)

    # ── Done ────────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("✅ Done! Summary:")
    print(f"  🔥 HOT leads:             {len(hot_leads)}")
    print(f"  🌤️  WARM leads:            {len(warm_leads)}")
    print(f"  ✅ Already contacted:     {len(already_contacted)} (skipped)")
    print(f"  📄 CSV:                   {csv_path}")
    print(f"  📋 JSON:                  {json_path}")
    print("═" * 60)


# ── Entry Point ──────────────────────────────────────────────────────────────
def main():
    print_banner()

    while True:
        choice = show_menu()

        if choice == "1":
            run_search()
        elif choice == "2":
            show_full_history()
        elif choice == "3":
            print("👋 Bye!")
            sys.exit(0)
        else:
            print("❌ 1, 2, ya 3 daalo.\n")

        print()  # spacing before menu shows again


if __name__ == "__main__":
    main()
