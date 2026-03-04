"""
Bahrain News Scraper — runs via GitHub Actions.
Outputs data/news.json for the static GitHub Pages site.
"""

import os
import json
import re as _re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.verify = False

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SOURCES = {
    "bna": {
        "name": "Bahrain News Agency (BNA)",
        "url": "https://www.bna.bh/en/",
        "color": "#c41e3a",
    },
    "gdn": {
        "name": "Gulf Daily News (GDN)",
        "url": "https://www.gdnonline.com/",
        "color": "#0d47a1",
    },
    "newsofbahrain": {
        "name": "News of Bahrain",
        "url": "https://www.newsofbahrain.com/",
        "color": "#2e7d32",
    },
}

INSTAGRAM_ACCOUNTS = [
    {"handle": "@gulfair", "name": "Gulf Air", "url": "https://www.instagram.com/gulfair/"},
    {"handle": "@bahrainairport", "name": "Bahrain International Airport", "url": "https://www.instagram.com/bahrainairport/"},
    {"handle": "@bahdiplomatic", "name": "Bahrain MFA", "url": "https://www.instagram.com/bahdiplomatic/"},
    {"handle": "@moi_bahrain", "name": "Ministry of Interior", "url": "https://www.instagram.com/moi_bahrain/"},
    {"handle": "@gdnonline", "name": "Gulf Daily News", "url": "https://www.instagram.com/gdnonline/"},
    {"handle": "@alayam", "name": "Al Ayam", "url": "https://www.instagram.com/alayam/"},
    {"handle": "@newsofbahrain_", "name": "News of Bahrain", "url": "https://www.instagram.com/newsofbahrain_/"},
    {"handle": "@bnanewsen", "name": "BNA English", "url": "https://www.instagram.com/bnanewsen/"},
]

CONTACTS = {
    "hotlines": [
        {"name": "MOFA 24/7 Hotline", "number": "+973 1722 7555"},
        {"name": "Help / Emergency", "number": "999"},
        {"name": "Accident Report", "number": "199"},
        {"name": "General Enquiries", "number": "80008008"},
    ],
    "police": [
        {"name": "Capital Governorate Police", "number": "17291555"},
        {"name": "Muharraq Governorate Police", "number": "17390185"},
        {"name": "North Governorate Police", "number": "17403111"},
        {"name": "Southern Governorate Police HQ", "number": "17664606"},
        {"name": "Airport Police Directorate", "number": "17330515"},
        {"name": "King Fahd Causeway Security", "number": "17796555"},
    ],
    "gulfair": [
        {"name": "Gulf Air General Info", "number": "+973 1715 4555"},
        {"name": "Gulf Air Rebooking", "number": "+973 1737 3737"},
    ],
    "websites": [
        {"name": "National Civil Protection Platform", "url": "https://www.ncpp.gov.bh/en/"},
        {"name": "National Communication Centre", "url": "https://www.ncc.gov.bh/en/index.aspx"},
        {"name": "King Fahd Causeway", "url": "https://kfca.sa/en"},
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NON_LATIN_RE = _re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')


def _is_english(text: str) -> bool:
    if not text:
        return False
    return not _NON_LATIN_RE.search(text)


def _parse_pub_date(date_str: str):
    if not date_str:
        return None
    cleaned = date_str.replace("|", " ").strip()
    try:
        return parsedate_to_datetime(cleaned)
    except Exception:
        pass
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d %b %Y %I:%M %p",
        "%d %b %Y",
        "%a, %d %b %Y",
        "%B %d, %Y",
        "%d %B %Y",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except Exception:
            continue
    return None


def _to_iso(date_str: str) -> str:
    dt = _parse_pub_date(date_str)
    if dt is None:
        return ""
    return dt.isoformat()


def _format_display_date(date_str: str) -> str:
    dt = _parse_pub_date(date_str)
    if dt is None:
        return date_str or ""
    if dt.hour or dt.minute:
        return dt.strftime("%d %b %Y, %I:%M %p").lstrip("0")
    return dt.strftime("%d %b %Y").lstrip("0")


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def scrape_bna() -> list:
    articles = []
    try:
        resp = SESSION.get("https://www.bna.bh/en/", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 15:
                continue
            if not _is_english(title):
                continue
            if ".aspx?cms=" not in href:
                if not any(c.isdigit() for c in href):
                    continue
            skip_words = ["View More", "His Royal Highness", "News Agencies",
                          "Society & People", "Graphic News", "Culture News",
                          "Economy", "Sports"]
            if any(title.startswith(sw) for sw in skip_words):
                continue
            if title in seen:
                continue
            seen.add(title)

            full_url = href if href.startswith("http") else f"https://www.bna.bh{href}"

            pub_raw = ""
            parent = a_tag.find_parent(["div", "article", "li", "section"])
            img = ""
            if parent:
                meta_div = parent.find(
                    class_=_re.compile(r"article-meta|article-news-block|meta")
                )
                if meta_div:
                    pub_raw = meta_div.get_text(strip=True)
                img_tag = parent.find("img")
                if img_tag:
                    img = img_tag.get("src", "") or img_tag.get("data-src", "")
                    if img and not img.startswith("http"):
                        img = f"https://www.bna.bh{img}"

            articles.append({
                "title": title,
                "link": full_url,
                "published": _format_display_date(pub_raw),
                "iso_date": _to_iso(pub_raw),
                "summary": "",
                "image": img,
                "source": "bna",
                "category": "Latest",
            })

            if len(articles) >= 25:
                break

    except Exception as e:
        print(f"[SCRAPE ERROR] BNA: {e}")

    return articles


def scrape_gdn() -> list:
    articles = []
    try:
        resp = SESSION.get("https://www.gdnonline.com/", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/Details/" not in href:
                continue
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            if title in seen:
                continue
            seen.add(title)

            full_url = href if href.startswith("http") else f"https://www.gdnonline.com{href}"

            img = ""
            parent = a_tag.find_parent(["div", "article", "li"])
            if parent:
                img_tag = parent.find("img")
                if img_tag:
                    img = img_tag.get("src", "") or img_tag.get("data-src", "")
                    if img and not img.startswith("http"):
                        img = f"https://www.gdnonline.com{img}"

            pub_raw = ""
            if parent:
                time_el = parent.find("time")
                if time_el:
                    pub_raw = time_el.get_text(strip=True)
                else:
                    date_el = parent.find(class_=_re.compile(r"date|penci-mega-date"))
                    if date_el:
                        pub_raw = date_el.get_text(strip=True)

            articles.append({
                "title": title,
                "link": full_url,
                "published": _format_display_date(pub_raw),
                "iso_date": _to_iso(pub_raw),
                "summary": "",
                "image": img,
                "source": "gdn",
                "category": "Latest",
            })

            if len(articles) >= 20:
                break

    except Exception as e:
        print(f"[SCRAPE ERROR] GDN: {e}")

    return articles


def scrape_newsofbahrain() -> list:
    articles = []
    try:
        resp = SESSION.get("https://www.newsofbahrain.com/", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for title_div in soup.find_all(class_="article-title"):
            a_tag = title_div.find("a", href=True) if title_div.name != "a" else title_div
            if not a_tag or not a_tag.get("href"):
                continue
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 10 or title in seen:
                continue
            seen.add(title)

            href = a_tag["href"]
            full_url = href if href.startswith("http") else f"https://www.newsofbahrain.com{href}"

            img = ""
            parent = a_tag.find_parent(["div", "article", "li"])
            if parent:
                img_tag = parent.find("img")
                if img_tag:
                    img = img_tag.get("src", "") or img_tag.get("data-src", "")
                    if img and not img.startswith("http"):
                        img = f"https://www.newsofbahrain.com{img}"

            pub_raw = ""
            if parent:
                time_span = parent.find("span", class_="time")
                if time_span:
                    pub_raw = time_span.get_text(strip=True)
                else:
                    time_el = parent.find("time")
                    if time_el:
                        pub_raw = time_el.get("datetime", "") or time_el.get_text(strip=True)

            articles.append({
                "title": title,
                "link": full_url,
                "published": _format_display_date(pub_raw),
                "iso_date": _to_iso(pub_raw),
                "summary": "",
                "image": img,
                "source": "newsofbahrain",
                "category": "Latest",
            })

            if len(articles) >= 20:
                break

        # Fallback: parse <h> tags with links
        if not articles:
            for h_tag in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
                a_tag = h_tag.find("a", href=True)
                if not a_tag:
                    continue
                title = a_tag.get_text(strip=True)
                href = a_tag["href"]
                if not title or len(title) < 10 or title in seen:
                    continue
                if "newsofbahrain.com" not in href and not href.startswith("/"):
                    continue
                seen.add(title)
                full_url = href if href.startswith("http") else f"https://www.newsofbahrain.com{href}"
                fb_pub = ""
                fb_parent = h_tag.parent
                if fb_parent:
                    fb_time = fb_parent.find("span", class_="time")
                    if fb_time:
                        fb_pub = fb_time.get_text(strip=True)
                articles.append({
                    "title": title,
                    "link": full_url,
                    "published": _format_display_date(fb_pub),
                    "iso_date": _to_iso(fb_pub),
                    "summary": "",
                    "image": "",
                    "source": "newsofbahrain",
                    "category": "Latest",
                })
                if len(articles) >= 20:
                    break

    except Exception as e:
        print(f"[SCRAPE ERROR] NewsOfBahrain: {e}")

    return articles


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Scraping Bahrain news sources...")

    articles = {}
    sources_meta = {}

    for key, src in SOURCES.items():
        print(f"  → {src['name']}...", end=" ", flush=True)
        if key == "bna":
            items = scrape_bna()
        elif key == "gdn":
            items = scrape_gdn()
        elif key == "newsofbahrain":
            items = scrape_newsofbahrain()
        else:
            items = []
        articles[key] = items
        sources_meta[key] = {
            "name": src["name"],
            "url": src["url"],
            "color": src["color"],
            "count": len(items),
        }
        print(f"{len(items)} articles")

    total = sum(len(v) for v in articles.values())

    payload = {
        "sources": sources_meta,
        "articles": articles,
        "instagram": INSTAGRAM_ACCOUNTS,
        "contacts": CONTACTS,
        "fetched_at": datetime.now(tz=__import__('datetime').timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "news.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Wrote {total} articles to {out_path}")


if __name__ == "__main__":
    main()
