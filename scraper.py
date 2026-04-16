# scraper.py - Google Maps se businesses scrape karo (FREE - koi API key nahi chahiye)

import time
import re
from config import MAX_RESULTS

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    raise ImportError(
        "Playwright install nahi hai!\n"
        "Run karo:  pip install playwright\n"
        "           playwright install chromium"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_text(page, selector: str, default: str = "") -> str:
    """Safely ek element ka text lo."""
    try:
        el = page.locator(selector).first
        el.wait_for(timeout=3000)
        return el.inner_text().strip()
    except Exception:
        return default


def _safe_attr(page, selector: str, attr: str, default: str = "") -> str:
    """Safely ek element ka attribute lo."""
    try:
        el = page.locator(selector).first
        el.wait_for(timeout=3000)
        val = el.get_attribute(attr)
        return val.strip() if val else default
    except Exception:
        return default


def _extract_rating(text: str) -> float:
    """'4.2 stars 150 reviews' ya '4.2' se rating nikalo."""
    m = re.search(r"(\d+\.?\d*)\s*star", text)
    if not m:
        m = re.search(r"(\d+\.?\d*)", text)
    return float(m.group(1)) if m else 0.0


def _extract_review_count(text: str) -> int:
    """'(1,234)' ya '1234 reviews' se count nikalo."""
    m = re.search(r"[\(,]?([\d,]+)[\),]?\s*(review|Rating)?", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return 0


# ── Detail panel se data nikalo ───────────────────────────────────────────────

def _parse_detail_panel(page) -> dict:
    """
    Jab koi business result open hota hai toh uska detail panel parse karo.
    Google Maps ka UI change hota rehta hai, isliye multiple selectors try karte hain.
    """
    details = {}

    # ── Name ──────────────────────────────────────────────────────────────────
    for sel in ["h1.DUwDvf", "h1", "[data-attrid='title']"]:
        try:
            name = page.locator(sel).first.inner_text(timeout=4000).strip()
            if name:
                details["name"] = name
                break
        except Exception:
            pass

    # ── Rating & Reviews ──────────────────────────────────────────────────────
    try:
        rating_block = page.locator("div.F7nice").first
        rating_block.wait_for(timeout=3000)
        rating_text = rating_block.inner_text()
        parts = rating_text.split()
        if parts:
            try:
                details["rating"] = float(parts[0])
            except ValueError:
                pass
        m = re.search(r"([\d,]+)\s*review", rating_text, re.I)
        if m:
            details["total_reviews"] = int(m.group(1).replace(",", ""))
    except Exception:
        pass

    # review count fallback
    if "total_reviews" not in details:
        try:
            rv = page.locator("button[jsaction*='review']").first.inner_text(timeout=2000)
            details["total_reviews"] = _extract_review_count(rv)
        except Exception:
            details["total_reviews"] = 0

    # ── Website (multi-strategy — more reliable) ─────────────────────────────
    # Domains jo website NAHI hain (directories, social, Google itself)
    _NOT_WEBSITE = (
        "google.", "goo.gl", "googleapis",           # ALL google domains
        "facebook.com", "instagram.com", "twitter.com", "x.com",
        "youtube.com", "wa.me", "t.me",
        "zomato.com", "swiggy.com", "dunzo.com",
        "justdial.com", "sulekha.com", "indiamart.com",
        "tradeindia.com", "99acres.com", "magicbricks.com", "olx.com",
    )

    def _is_real_website(href: str) -> bool:
        if not href or not href.startswith("http"):
            return False
        href_low = href.lower()
        return not any(d in href_low for d in _NOT_WEBSITE)

    # Strategy 1: Google Maps specific selectors (data-item-id is most reliable)
    for sel in [
        "a[data-item-id='authority']",
        "a[aria-label*='website' i]",
        "a[data-tooltip='Open website']",
        "a[aria-label*='site' i]",
        "a[jsaction*='openweb']",
    ]:
        try:
            href = page.locator(sel).first.get_attribute("href", timeout=1500)
            if _is_real_website(href):
                details["website"] = href
                break
        except Exception:
            pass

    # Strategy 2: Scan ALL anchor tags on page — pick first non-Google external link
    if "website" not in details:
        try:
            page.wait_for_timeout(500)   # brief extra wait for lazy-loaded links
            all_anchors = page.locator("a[href]").all()
            for anchor in all_anchors[:40]:   # scan first 40 links
                try:
                    href = anchor.get_attribute("href", timeout=200)
                    if _is_real_website(href):
                        details["website"] = href
                        break
                except Exception:
                    pass
        except Exception:
            pass

    # ── Phone ─────────────────────────────────────────────────────────────────
    for sel in [
        "button[data-item-id*='phone']",
        "button[aria-label*='phone' i]",
        "[data-tooltip='Copy phone number']",
    ]:
        try:
            phone_text = page.locator(sel).first.inner_text(timeout=2000).strip()
            if phone_text:
                details["phone"] = phone_text
                break
        except Exception:
            pass

    # phone fallback: look for tel: links
    if "phone" not in details:
        try:
            tel = page.locator("a[href^='tel:']").first.get_attribute("href", timeout=2000)
            if tel:
                details["phone"] = tel.replace("tel:", "").strip()
        except Exception:
            pass

    # ── Address ───────────────────────────────────────────────────────────────
    for sel in [
        "button[data-item-id='address']",
        "button[aria-label*='address' i]",
        "[data-tooltip='Copy address']",
    ]:
        try:
            addr = page.locator(sel).first.inner_text(timeout=2000).strip()
            if addr:
                details["address"] = addr
                break
        except Exception:
            pass

    # ── Photos count (approximate) ────────────────────────────────────────────
    try:
        photo_btn = page.locator("button[aria-label*='photo' i]").first
        ph_text = photo_btn.inner_text(timeout=2000)
        m = re.search(r"(\d+)", ph_text)
        details["photos_count"] = int(m.group(1)) if m else 0
    except Exception:
        details["photos_count"] = 0

    return details


# ── Main scraping functions ───────────────────────────────────────────────────

def collect_leads(topic: str, city: str, progress_callback=None) -> list[dict]:
    """
    Google Maps scrape karke leads collect karo. No API key needed!

    Args:
        topic:             e.g. 'restaurants', 'salons', 'gyms'
        city:              e.g. 'Lucknow', 'Delhi', 'Mumbai'
        progress_callback: optional callable(dict) for UI progress events

    Returns:
        List of business dicts (same format as pehle wala API scraper)
    """
    def emit(event: dict):
        if progress_callback:
            progress_callback(event)

    query = f"{topic} in {city} India"
    print(f"\n🔍 Searching Google Maps: '{query}' (free scraping mode)...")

    leads = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
        )
        page = context.new_page()

        # ── 1. Google Maps search ────────────────────────────────────────────
        encoded = query.replace(" ", "+")
        page.goto(
            f"https://www.google.com/maps/search/{encoded}",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        page.wait_for_timeout(3000)

        # Consent screen dismiss karo (EU/India popup)
        for btn_text in ["Accept all", "I agree", "Reject all"]:
            try:
                btn = page.get_by_role("button", name=btn_text)
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_timeout(1000)
                    break
            except Exception:
                pass

        # ── 2. Results feed dhundho ──────────────────────────────────────────
        feed_sel = 'div[role="feed"]'
        try:
            page.wait_for_selector(feed_sel, timeout=10000)
        except PlaywrightTimeout:
            print("⚠️  Results load nahi hue. Internet ya Google block check karo.")
            browser.close()
            return []

        # ── 3. Smart scroll — tab tak chalo jab tak MAX_RESULTS na milein ────
        print(f"  📜 Scrolling to load {MAX_RESULTS}+ results...")

        def _count_unique_links() -> int:
            links = page.locator(f'{feed_sel} a[href*="/maps/place/"]').all()
            hrefs = set()
            for lnk in links:
                try:
                    h = lnk.get_attribute("href")
                    if h: hrefs.add(h)
                except Exception:
                    pass
            return len(hrefs)

        prev_count   = 0
        stale_rounds = 0        # kitni baar count nahi badha

        for attempt in range(30):          # max 30 scroll attempts (~120 results)
            # Scroll to bottom of feed
            page.evaluate(
                f"""
                var el = document.querySelector('{feed_sel}');
                if (el) el.scrollTop = el.scrollHeight + 5000;
                """
            )
            page.wait_for_timeout(1800)    # Google ko load hone do

            cur_count = _count_unique_links()
            print(f"  ... scroll {attempt+1}: {cur_count} links", end="\r")

            if cur_count >= MAX_RESULTS:
                print()
                break                      # enough results mil gayi

            if cur_count == prev_count:
                stale_rounds += 1
                if stale_rounds >= 3:      # 3 baar count nahi badha = end of results
                    print(f"\n  ℹ️  Google Maps ne sirf {cur_count} results diye is topic/city ke liye")
                    break
            else:
                stale_rounds = 0

            prev_count = cur_count

        print()

        # ── 4. Saare result links collect karo ──────────────────────────────
        result_links = page.locator(f'{feed_sel} a[href*="/maps/place/"]').all()
        seen_hrefs   = set()
        unique_links = []
        for link in result_links:
            try:
                href = link.get_attribute("href")
                if href and href not in seen_hrefs:
                    seen_hrefs.add(href)
                    unique_links.append(link)
            except Exception:
                pass

        total = min(len(unique_links), MAX_RESULTS)
        print(f"  ✅ {len(unique_links)} businesses mili, processing {total}...")
        emit({"type": "found", "total": total})

        # ── 5. Har result pe click karke details lo ──────────────────────────
        for i, link in enumerate(unique_links[:MAX_RESULTS], 1):
            try:
                link.scroll_into_view_if_needed()
                link.click()
                page.wait_for_timeout(2500)   # panel load hone do

                detail = _parse_detail_panel(page)
                maps_url = page.url

                lead = {
                    "name": detail.get("name", f"Business #{i}"),
                    "phone": detail.get("phone", ""),
                    "website": detail.get("website", ""),
                    "address": detail.get("address", ""),
                    "rating": detail.get("rating", 0),
                    "total_reviews": detail.get("total_reviews", 0),
                    "photos_count": detail.get("photos_count", 0),
                    "google_maps_url": maps_url,
                    "place_id": "",
                    "city": city,
                    "topic": topic,
                }
                leads.append(lead)
                print(
                    f"  [{i}/{total}] {lead['name']} "
                    f"| website: {'YES' if lead['website'] else 'NO'} "
                    f"| phone: {'YES' if lead['phone'] else 'NO'}"
                )
                emit({
                    "type": "processing",
                    "current": i,
                    "total": total,
                    "name": lead["name"],
                    "has_website": bool(lead["website"]),
                    "has_phone": bool(lead["phone"]),
                })

                # Back button — sidebar wapas lao
                try:
                    back_btn = page.locator("button[aria-label='Back']").first
                    back_btn.click(timeout=2000)
                    page.wait_for_timeout(1000)
                except Exception:
                    # Back nahi mila toh same search URL pe wapas jao
                    page.goto(
                        f"https://www.google.com/maps/search/{encoded}",
                        wait_until="domcontentloaded",
                        timeout=20000,
                    )
                    page.wait_for_timeout(2000)
                    # Re-scroll briefly
                    for _ in range(3):
                        page.evaluate(
                            f"document.querySelector('{feed_sel}').scrollBy(0, 3000)"
                        )
                        page.wait_for_timeout(800)

            except Exception as e:
                print(f"  [{i}] ⚠️  Skip (error: {e})")
                continue

        browser.close()

    print(f"\n✅ Total {len(leads)} leads collected")
    return leads


# ── Backward-compat aliases (pehle wale code ke saath kaam kare) ──────────────

def search_businesses(topic: str, city: str) -> list[dict]:
    """collect_leads ka alias - pehle wale code ke saath compatible."""
    return collect_leads(topic, city)


def get_place_details(place_id: str) -> dict:
    """No-op stub - ab individual API calls nahi hoti."""
    return {}
