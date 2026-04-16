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
    try:
        el = page.locator(selector).first
        el.wait_for(timeout=4000)
        return el.inner_text().strip()
    except Exception:
        return default


def _extract_rating(text: str) -> float:
    m = re.search(r"(\d+\.?\d*)\s*star", text)
    if not m:
        m = re.search(r"(\d+\.?\d*)", text)
    return float(m.group(1)) if m else 0.0


def _extract_review_count(text: str) -> int:
    m = re.search(r"[\(,]?([\d,]+)[\),]?\s*(review|Rating)?", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return 0


# ── Detail panel se data nikalo ───────────────────────────────────────────────

def _parse_detail_panel(page) -> dict:
    details = {}

    # ── Name ──────────────────────────────────────────────────────────────────
    for sel in ["h1.DUwDvf", "h1", "[data-attrid='title']"]:
        try:
            name = page.locator(sel).first.inner_text(timeout=5000).strip()
            if name:
                details["name"] = name
                break
        except Exception:
            pass

    # ── Rating & Reviews ──────────────────────────────────────────────────────
    try:
        rating_block = page.locator("div.F7nice").first
        rating_block.wait_for(timeout=4000)
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

    if "total_reviews" not in details:
        try:
            rv = page.locator("button[jsaction*='review']").first.inner_text(timeout=2000)
            details["total_reviews"] = _extract_review_count(rv)
        except Exception:
            details["total_reviews"] = 0

    # ── Website ───────────────────────────────────────────────────────────────
    _NOT_WEBSITE = (
        "google.", "goo.gl", "googleapis",
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

    for sel in [
        "a[data-item-id='authority']",
        "a[aria-label*='website' i]",
        "a[data-tooltip='Open website']",
        "a[aria-label*='site' i]",
        "a[jsaction*='openweb']",
    ]:
        try:
            href = page.locator(sel).first.get_attribute("href", timeout=2000)
            if _is_real_website(href):
                details["website"] = href
                break
        except Exception:
            pass

    if "website" not in details:
        try:
            page.wait_for_timeout(500)
            all_anchors = page.locator("a[href]").all()
            for anchor in all_anchors[:40]:
                try:
                    href = anchor.get_attribute("href", timeout=300)
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

    # ── Photos count ──────────────────────────────────────────────────────────
    try:
        photo_btn = page.locator("button[aria-label*='photo' i]").first
        ph_text = photo_btn.inner_text(timeout=2000)
        m = re.search(r"(\d+)", ph_text)
        details["photos_count"] = int(m.group(1)) if m else 0
    except Exception:
        details["photos_count"] = 0

    return details


# ── Main scraping function ────────────────────────────────────────────────────

def collect_leads(topic: str, city: str, progress_callback=None) -> list[dict]:
    """
    Google Maps scrape karke leads collect karo.
    FIX: Pehle saare URLs collect karo, phir har ek pe directly navigate karo.
    Is tarah stale element timeout errors nahi aate.
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
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-infobars",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # ── 1. Google Maps search ────────────────────────────────────────────
        encoded = query.replace(" ", "+")
        search_url = f"https://www.google.com/maps/search/{encoded}"

        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        # Consent/popup dismiss karo
        for btn_text in ["Accept all", "I agree", "Reject all"]:
            try:
                btn = page.get_by_role("button", name=btn_text)
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass

        # ── 2. Results feed wait karo ────────────────────────────────────────
        feed_sel = 'div[role="feed"]'
        try:
            page.wait_for_selector(feed_sel, timeout=15000)
        except PlaywrightTimeout:
            print("⚠️  Results load nahi hue.")
            browser.close()
            return []

        # ── 3. Scroll karke URLs collect karo ───────────────────────────────
        print(f"  📜 Scrolling to load results...")
        collected_urls: set[str] = set()
        prev_count   = 0
        stale_rounds = 0

        for attempt in range(40):
            # Feed scroll
            page.evaluate(
                f"""
                var el = document.querySelector('{feed_sel}');
                if (el) el.scrollTop = el.scrollHeight + 9999;
                """
            )
            page.wait_for_timeout(2000)

            # Saare place links collect karo
            links = page.locator(f'{feed_sel} a[href*="/maps/place/"]').all()
            for lnk in links:
                try:
                    href = lnk.get_attribute("href", timeout=500)
                    if href:
                        base = href.split("?")[0]
                        collected_urls.add(base)
                except Exception:
                    pass

            cur = len(collected_urls)
            print(f"  ... scroll {attempt+1}: {cur} URLs collected", end="\r")

            if cur >= MAX_RESULTS:
                print()
                break

            # BUG FIX: prev_count se compare karo, collected_urls se nahi
            if cur == prev_count:
                stale_rounds += 1
                if stale_rounds >= 4:
                    print(f"\n  ℹ️  {cur} results mil gayi — aur nahi hain")
                    break
            else:
                stale_rounds = 0

            prev_count = cur

        print()

        # ── 4. Har URL pe directly navigate karo (stale element issue FIX) ──
        url_list = list(collected_urls)[:MAX_RESULTS]
        total = len(url_list)
        print(f"  ✅ {total} business URLs collected, ab details le rahe hain...")
        emit({"type": "found", "total": total})

        for i, place_url in enumerate(url_list, 1):
            try:
                # Direct URL navigate — koi element hold nahi, no stale errors
                page.goto(place_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)

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

            except Exception as e:
                print(f"  [{i}] ⚠️  Skip ({e})")
                continue

        browser.close()

    print(f"\n✅ Total {len(leads)} leads collected")
    return leads


# ── Backward-compat aliases ───────────────────────────────────────────────────

def search_businesses(topic: str, city: str) -> list[dict]:
    return collect_leads(topic, city)


def get_place_details(place_id: str) -> dict:
    return {}
