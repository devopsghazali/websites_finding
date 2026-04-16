# email_finder.py - Business ka email dhundho (website ya search se)

import re
import time
import requests
import urllib.parse
from urllib.parse import urljoin, urlparse

EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}\b'
)

# False-positive filter — yeh "emails" nahi hain
_SKIP = {
    "example.com", "test.com", "domain.com", "email.com", "yourdomain",
    "yourname", "noreply", "no-reply", "donotreply", "support@sentry",
    ".png", ".jpg", ".gif", ".svg", ".woff", ".ttf",
    "schema.org", "w3.org", "openid", "apache.org",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _clean_emails(raw: list[str]) -> list[str]:
    out = []
    seen = set()
    for e in raw:
        e = e.lower().strip(".,;:\"'")
        if any(s in e for s in _SKIP):
            continue
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out[:3]   # max 3 per source


def find_emails_from_website(url: str, timeout: int = 8) -> list[str]:
    """
    Business website scrape karke email addresses dhundho.
    Home page + /contact + /about check karta hai.
    """
    if not url:
        return []

    try:
        parsed = urlparse(url)
        base   = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return []

    pages = [url]
    for path in ["/contact", "/contact-us", "/about", "/about-us",
                 "/reach-us", "/get-in-touch", "/enquiry"]:
        pages.append(urljoin(base, path))

    found = []
    for page_url in pages[:5]:
        try:
            r = requests.get(page_url, timeout=timeout,
                             headers=_HEADERS, allow_redirects=True)
            if r.status_code == 200:
                emails = EMAIL_RE.findall(r.text)
                found.extend(emails)
        except Exception:
            pass

    return _clean_emails(found)


def find_emails_via_search(business_name: str, city: str,
                           timeout: int = 8) -> list[str]:
    """
    DuckDuckGo search se email dhundho (website nahi hone par).
    Query: "Business Name" "City" email contact
    """
    query = f'"{business_name}" "{city}" email'
    url   = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

    try:
        r = requests.get(url, timeout=timeout, headers=_HEADERS)
        emails = EMAIL_RE.findall(r.text)
        return _clean_emails(emails)
    except Exception:
        return []


def find_email_for_lead(lead: dict) -> list[str]:
    """
    Ek lead ke liye best available strategy se email dhundho.

    - Website hai → website scrape karo
    - Website nahi → search engine se dhundho
    """
    website = lead.get("website", "").strip()

    if website:
        emails = find_emails_from_website(website)
        if emails:
            return emails

    # Fallback: search
    name = lead.get("name", "")
    city = lead.get("city", "")
    if name and city:
        return find_emails_via_search(name, city)

    return []
