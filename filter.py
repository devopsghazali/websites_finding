# filter.py - Businesses ko smart filter karo

from config import MIN_REVIEWS_THRESHOLD, MAX_RATING_THRESHOLD
from tracker import filter_already_contacted, print_tracker_summary


def has_no_website(lead: dict) -> bool:
    """Check karo website hai ya nahi."""
    website = lead.get("website", "").strip()
    return not website or website == ""


def is_weak_online_presence(lead: dict) -> bool:
    """
    Weak online presence identify karo:
    - No website
    - Low rating (needs improvement)
    - Very few reviews (not well known)
    - Few photos
    """
    no_website = has_no_website(lead)
    low_reviews = lead.get("total_reviews", 0) < MIN_REVIEWS_THRESHOLD
    low_photos = lead.get("photos_count", 0) < 3

    # At least 2 weak signals hone chahiye
    weak_signals = sum([no_website, low_reviews, low_photos])
    return weak_signals >= 1


def filter_leads(leads: list[dict]) -> dict:
    """
    Leads ko categorize karo:
    - hot_leads: no website + weak presence (best targets)
    - warm_leads: has website but weak presence
    - skip: strong online presence
    - already_contacted: pehle se contact ho chuka hai (tracker se)

    Returns dict with categories.
    """
    # ── Step 1: Pehle tracker se already contacted remove karo ──────────────
    fresh_leads, already_contacted = filter_already_contacted(leads)
    print_tracker_summary(fresh_leads, already_contacted)

    # ── Step 2: Fresh leads ko categorize karo ──────────────────────────────
    hot_leads = []
    warm_leads = []
    skipped = []

    for lead in fresh_leads:
        no_website = has_no_website(lead)
        weak = is_weak_online_presence(lead)

        if no_website and weak:
            lead["lead_type"] = "HOT"
            lead["reason"] = _get_reason(lead)
            hot_leads.append(lead)
        elif no_website:
            lead["lead_type"] = "HOT"
            lead["reason"] = "No website"
            hot_leads.append(lead)
        elif weak:
            lead["lead_type"] = "WARM"
            lead["reason"] = _get_reason(lead)
            warm_leads.append(lead)
        else:
            lead["lead_type"] = "SKIP"
            lead["reason"] = "Strong online presence"
            skipped.append(lead)

    return {
        "hot": hot_leads,
        "warm": warm_leads,
        "skipped": skipped,
        "already_contacted": already_contacted,
    }


def _get_reason(lead: dict) -> str:
    """Reason string banao ki yeh lead kyun target hai."""
    reasons = []
    if has_no_website(lead):
        reasons.append("No website")
    if lead.get("total_reviews", 0) < MIN_REVIEWS_THRESHOLD:
        reasons.append(f"Only {lead.get('total_reviews', 0)} reviews")
    if lead.get("photos_count", 0) < 3:
        reasons.append("Few photos")
    if lead.get("rating", 5) < MAX_RATING_THRESHOLD:
        reasons.append(f"Rating {lead.get('rating', 0)}/5")
    return " | ".join(reasons) if reasons else "Weak presence"


def print_filter_summary(filtered: dict):
    """Summary print karo."""
    print(f"\n📊 Filter Results:")
    print(f"  🔥 HOT Leads (no website):       {len(filtered['hot'])}")
    print(f"  🌤️  WARM Leads (weak online):      {len(filtered['warm'])}")
    print(f"  ⏭️  Skipped (strong presence):     {len(filtered['skipped'])}")
    print(f"  ✅ Already contacted (skip):      {len(filtered.get('already_contacted', []))}")
