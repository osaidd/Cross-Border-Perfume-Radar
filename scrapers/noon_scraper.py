"""
Noon.com UAE product price scraper — reference implementation.

Demonstrates the approach used to collect UAE wholesale/proxy pricing data
for the Cross-Border Perfume Radar pipeline.

Noon.com uses heavy client-side JavaScript rendering. A plain
requests + BeautifulSoup fetch returns a shell HTML page with no product
data. Two practical options:
  1. Playwright / Selenium — renders the page in a real browser before parsing.
  2. XHR interception — intercept the JSON API call in browser DevTools and
     hit that endpoint directly with appropriate headers (faster, but the
     endpoint URL and auth tokens change occasionally).

This file implements the BeautifulSoup parsing layer that runs once the HTML
is available. Pair it with Playwright or the XHR approach to get live data.

Rate-limiting and compliance notes:
  - Minimum REQUEST_DELAY seconds between requests.
  - Always check https://www.noon.com/robots.txt before running.
  - Never scrape account pages, PII, or private data.
  - Cache results locally — do not hit the same URL twice per session.
"""

import time
import csv
import hashlib
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

# ── Constants ─────────────────────────────────────────────────────────────────

NOON_SEARCH_URL = "https://www.noon.com/uae-en/search/?q={query}"

# Minimum delay between requests — be respectful to the server.
REQUEST_DELAY = 3.0

# Fragrance brands to include; filter out unrelated results.
TARGET_BRANDS = {"lattafa", "rasasi", "afnan", "armaf", "ajmal", "al haramain"}

# HTTP headers that reduce the chance of receiving a bot-detection response.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-AE,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class NoonProduct:
    """A single product listing scraped from Noon.com."""

    title: str
    price_aed: float
    brand: str
    url: str

    @property
    def product_id(self) -> str:
        """Deterministic 12-char SHA-1 ID derived from the product title."""
        return hashlib.sha1(self.title.lower().encode()).hexdigest()[:12]


# ── URL helpers ───────────────────────────────────────────────────────────────

def build_search_url(query: str, page: int = 1) -> str:
    """Build a Noon.com search URL for a fragrance query."""
    base = NOON_SEARCH_URL.format(query=query.replace(" ", "+"))
    return f"{base}&page={page}" if page > 1 else base


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_product_card(card) -> "NoonProduct | None":
    """
    Parse a single product card element into a NoonProduct.

    Noon.com product cards use data-qa attributes for stable selection:

        <div data-qa="product-card">
          <span data-qa="product-name">Lattafa Khamrah EDP 100ml</span>
          <strong data-qa="product-price">AED 45.00</strong>
          <span data-qa="product-brand">Lattafa</span>
          <a href="/uae-en/lattafa-khamrah/p/...">...</a>
        </div>

    These selectors change with site redesigns — always verify in DevTools
    before running a new collection session.

    Returns None if required fields (title or price) are missing.
    """
    title_el = card.select_one('[data-qa="product-name"]')
    price_el = card.select_one('[data-qa="product-price"]')
    brand_el = card.select_one('[data-qa="product-brand"]')
    link_el = card.select_one("a[href]")

    if not title_el or not price_el:
        return None

    try:
        price_text = price_el.get_text(strip=True)
        price_aed = float(
            price_text.replace("AED", "").replace(",", "").strip()
        )
    except ValueError:
        return None

    brand = brand_el.get_text(strip=True) if brand_el else "Unknown"
    url = "https://www.noon.com" + link_el["href"] if link_el else ""

    return NoonProduct(
        title=title_el.get_text(strip=True),
        price_aed=price_aed,
        brand=brand,
        url=url,
    )


def parse_search_page(html: str) -> list[NoonProduct]:
    """
    Extract all product cards from a Noon.com search results HTML page.

    NOTE: Noon.com renders product cards client-side. Passing the raw
    response from requests.get() will typically return zero cards because
    the HTML is a JavaScript shell. Use Playwright or XHR interception to
    obtain fully-rendered HTML before calling this function.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('[data-qa="product-card"]')
    products = []
    for card in cards:
        product = parse_product_card(card)
        if product:
            brand_lower = product.brand.lower()
            if any(t in brand_lower for t in TARGET_BRANDS):
                products.append(product)
    return products


# ── Collection ────────────────────────────────────────────────────────────────

def scrape_search_results(query: str, max_pages: int = 3) -> list[NoonProduct]:
    """
    Scrape Noon.com search results for a fragrance query.

    Because Noon uses client-side rendering, this function fetches the page
    with requests and passes the HTML to parse_search_page(). In practice
    this returns 0 results from a plain fetch. To get real data:

      Option A — Playwright (recommended for reliability):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(build_search_url(query))
            page.wait_for_selector('[data-qa="product-card"]')
            html = page.content()
        products = parse_search_page(html)

      Option B — XHR interception (faster, more fragile):
        Intercept the JSON API call in browser DevTools Network tab while
        searching. The endpoint returns structured product JSON directly.
        Reproduce the request with the same headers and query params.

    This function is retained as a reference for the fetch + parse pattern.
    """
    products = []

    for page in range(1, max_pages + 1):
        url = build_search_url(query, page=page)

        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        response.raise_for_status()

        page_products = parse_search_page(response.text)
        products.extend(page_products)

        if page < max_pages:
            time.sleep(REQUEST_DELAY)

    return products


# ── Output ────────────────────────────────────────────────────────────────────

def save_to_csv(products: list[NoonProduct], output_path: str) -> None:
    """Save scraped products to CSV in the format expected by the cost engine."""
    fieldnames = ["product_id", "title", "brand", "price_aed", "source", "url"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in products:
            writer.writerow({
                "product_id": p.product_id,
                "title": p.title,
                "brand": p.brand,
                "price_aed": p.price_aed,
                "source": "noon.com",
                "url": p.url,
            })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape Noon.com UAE perfume prices."
    )
    parser.add_argument("--queries", nargs="+",
                        default=["lattafa perfume", "rasasi perfume",
                                 "afnan perfume", "armaf perfume"],
                        help="Search queries to run")
    parser.add_argument("--pages", type=int, default=2,
                        help="Max pages per query (default: 2)")
    parser.add_argument("--out", default="data/raw/noon_prices.csv",
                        help="Output CSV path")
    args = parser.parse_args()

    all_products: list[NoonProduct] = []
    for q in args.queries:
        print(f"Scraping: {q}")
        results = scrape_search_results(q, max_pages=args.pages)
        print(f"  → {len(results)} products (note: 0 expected without JS rendering)")
        all_products.extend(results)
        time.sleep(REQUEST_DELAY)

    save_to_csv(all_products, args.out)
    print(f"Saved {len(all_products)} products to {args.out}")
