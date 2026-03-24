"""
Example scraper for Noon.com UAE product pricing.
Demonstrates the approach used to collect source pricing data.
Note: HTML structure may change; this serves as a reference implementation.

This scraper is NOT meant to be run as-is — Noon.com uses JavaScript rendering,
so a simple requests + BeautifulSoup approach will only work on server-rendered
pages. For full JS rendering, you would need Playwright or Selenium.

Key considerations for marketplace scraping:
  - Always check robots.txt and Terms of Service before scraping
  - Use rate limiting (2-3 seconds between requests minimum)
  - Rotate user agents to avoid detection
  - Cache results locally to avoid redundant requests
  - Never scrape personal data or account-specific pages
"""

import time
import csv
import hashlib
from dataclasses import dataclass

# In production you would use: from bs4 import BeautifulSoup
# import requests

NOON_SEARCH_URL = "https://www.noon.com/uae-en/search/?q={query}"

# Rate limiting: minimum 3 seconds between requests to be respectful
REQUEST_DELAY = 3.0


@dataclass
class NoonProduct:
    """A single product listing from Noon.com."""
    title: str
    price_aed: float
    brand: str
    url: str

    @property
    def product_id(self) -> str:
        """Generate a deterministic ID from the product title."""
        return hashlib.sha1(self.title.lower().encode()).hexdigest()[:12]


def build_search_url(query: str) -> str:
    """Build a Noon.com search URL for a fragrance query."""
    return NOON_SEARCH_URL.format(query=query.replace(" ", "+"))


def parse_product_card(card_html) -> NoonProduct | None:
    """
    Parse a single product card from Noon.com search results.

    Noon.com renders product cards with this approximate structure:
      <div data-qa="product-card">
        <span data-qa="product-name">Product Title</span>
        <strong data-qa="product-price">AED 45.00</strong>
        <span data-qa="product-brand">Lattafa</span>
      </div>

    In practice, the actual selectors change frequently. The approach:
    1. Inspect the page in browser DevTools
    2. Identify data-qa or class-based selectors for each field
    3. Extract text content and parse numerics

    Returns None if the card can't be parsed (missing price, etc.)
    """
    # This is pseudocode — actual implementation would use BeautifulSoup:
    #
    # title = card_html.select_one('[data-qa="product-name"]')
    # price = card_html.select_one('[data-qa="product-price"]')
    # brand = card_html.select_one('[data-qa="product-brand"]')
    #
    # if not all([title, price]):
    #     return None
    #
    # price_text = price.get_text(strip=True)
    # price_aed = float(price_text.replace("AED", "").replace(",", "").strip())
    #
    # return NoonProduct(
    #     title=title.get_text(strip=True),
    #     price_aed=price_aed,
    #     brand=brand.get_text(strip=True) if brand else "Unknown",
    #     url=card_html.select_one("a")["href"],
    # )
    pass


def scrape_search_results(query: str, max_pages: int = 3) -> list[NoonProduct]:
    """
    Scrape Noon.com search results for a given query.

    Pagination: Noon uses ?page=N query parameter. Each page typically
    shows 40 products. We limit to max_pages to be respectful.

    JavaScript rendering: Noon.com heavily uses client-side rendering.
    A basic requests.get() will return a shell HTML without product data.
    Options for handling this:
      1. Use Playwright/Selenium to render the page (slower, more reliable)
      2. Find and call the underlying API endpoint directly (faster, but
         endpoints change and may require authentication)
      3. Use a headless browser service like ScrapingBee or Browserless

    For this project, we used approach #2: intercepting the XHR calls in
    browser DevTools to find the JSON API endpoint, then calling it directly
    with appropriate headers.
    """
    products = []

    for page in range(1, max_pages + 1):
        # url = f"{build_search_url(query)}&page={page}"
        # response = requests.get(url, headers={"User-Agent": "..."})
        # soup = BeautifulSoup(response.text, "html.parser")
        # cards = soup.select('[data-qa="product-card"]')
        #
        # for card in cards:
        #     product = parse_product_card(card)
        #     if product:
        #         products.append(product)
        #
        # # Rate limiting between pages
        # time.sleep(REQUEST_DELAY)
        pass

    return products


def save_to_csv(products: list[NoonProduct], output_path: str) -> None:
    """Save scraped products to CSV in the format expected by the cost engine."""
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "product_id", "title", "brand", "price_aed", "source", "url",
        ])
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


# ── Example usage ────────────────────────────────────────────────────────────
#
# if __name__ == "__main__":
#     queries = [
#         "lattafa perfume",
#         "armaf perfume",
#         "rasasi perfume",
#     ]
#
#     all_products = []
#     for q in queries:
#         print(f"Scraping: {q}")
#         results = scrape_search_results(q, max_pages=2)
#         all_products.extend(results)
#         time.sleep(REQUEST_DELAY)  # delay between different queries
#
#     save_to_csv(all_products, "data/raw/noon_prices.csv")
#     print(f"Saved {len(all_products)} products")
