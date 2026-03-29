"""
Shopee SG scraper — collects perfume listings from Shopee Singapore.

Uses Selenium WebDriver (headless Chrome) because Shopee is a JavaScript SPA
that loads product cards via XHR after initial page render. Standard HTTP
requests receive an empty shell; a real browser is required to trigger the
JS bundle and wait for product DOM nodes.

Usage (requires chromedriver on PATH):
    python scrapers/shopee_scraper.py --query "lattafa khamrah" --pages 2

Output is saved to data/raw/shopee_<query>_<date>.csv matching the schema
used in data/samples/sg_listings_sample.csv.
"""

import argparse
import csv
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ── Constants ────────────────────────────────────────────────────────────────

SHOPEE_SEARCH_URL = "https://shopee.sg/search?keyword={query}&page={page}&sortBy=sales"
SCROLL_PAUSE = 2.0
PAGE_LOAD_TIMEOUT = 15
REQUEST_DELAY = 4.0  # polite delay between page fetches


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class ShopeeProduct:
    product_title: str
    price_sgd: float
    sold_30d: int = 0
    rating: float = 0.0
    url: str = ""
    platform: str = "shopee"
    seen_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


# ── Driver setup ─────────────────────────────────────────────────────────────

def build_driver() -> webdriver.Chrome:
    """Return a headless Chrome WebDriver instance with anti-detection basics."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


# ── URL helpers ──────────────────────────────────────────────────────────────

def build_search_url(query: str, page: int = 0) -> str:
    """Build a Shopee search URL. Page is 0-indexed."""
    encoded = query.replace(" ", "+")
    return SHOPEE_SEARCH_URL.format(query=encoded, page=page)


# ── Parsing ──────────────────────────────────────────────────────────────────

def _extract_sold_count(text: str) -> int:
    """Parse sold count from strings like '1.2k sold' or '408 sold'."""
    text = text.lower().replace(",", "")
    match = re.search(r"([\d.]+)\s*k?\s*sold", text)
    if not match:
        return 0
    value = float(match.group(1))
    if "k" in text[match.start():match.end()]:
        value *= 1000
    return int(value)


def _extract_price(text: str) -> Optional[float]:
    """Parse SGD price from strings like '$29.90' or '29.90'."""
    match = re.search(r"\$?\s*([\d,]+\.?\d*)", text.replace(",", ""))
    if match:
        return float(match.group(1))
    return None


def parse_product_cards(driver: webdriver.Chrome) -> List[ShopeeProduct]:
    """
    Extract product data from the currently loaded Shopee search results page.

    Shopee renders product cards inside <div data-sqe="item"> containers.
    Each card contains nested spans/divs for title, price, sold count, and rating.
    """
    products = []

    # Wait for product grid to render (Shopee lazy-loads via JS)
    try:
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-sqe='item']"))
        )
    except Exception:
        return products

    cards = driver.find_elements(By.CSS_SELECTOR, "[data-sqe='item']")
    for card in cards:
        try:
            title_el = card.find_element(By.CSS_SELECTOR, "div.ie3A\\+n.bM\\+7UW")
            title = title_el.text.strip()
        except Exception:
            try:
                title = card.text.split("\n")[0].strip()
            except Exception:
                continue

        price = None
        sold = 0
        rating = 0.0

        for span in card.find_elements(By.TAG_NAME, "span"):
            span_text = span.text.strip()
            if "$" in span_text and price is None:
                price = _extract_price(span_text)
            if "sold" in span_text.lower():
                sold = _extract_sold_count(span_text)

        if price is None:
            continue

        try:
            link_el = card.find_element(By.TAG_NAME, "a")
            href = link_el.get_attribute("href") or ""
            url = f"https://shopee.sg{href}" if href.startswith("/") else href
        except Exception:
            url = ""

        products.append(ShopeeProduct(
            product_title=title,
            price_sgd=price,
            sold_30d=sold,
            rating=rating,
            url=url,
        ))

    return products


# ── Multi-page scrape ────────────────────────────────────────────────────────

def scrape_query(
    driver: webdriver.Chrome,
    query: str,
    max_pages: int = 3,
) -> List[ShopeeProduct]:
    """
    Scrape up to max_pages of Shopee search results for a given query.

    Scrolls to bottom of each page to trigger lazy-loading, then parses
    product cards before navigating to the next page.
    """
    all_products: List[ShopeeProduct] = []

    for page in range(max_pages):
        url = build_search_url(query, page=page)
        print(f"  [{page + 1}/{max_pages}] {url}")

        try:
            driver.get(url)
        except Exception as e:
            print(f"  Page load error: {e}")
            break

        # Scroll to bottom to trigger lazy-loaded cards
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        page_products = parse_product_cards(driver)
        all_products.extend(page_products)
        print(f"  Found {len(page_products)} products on page {page + 1}")

        if page < max_pages - 1:
            time.sleep(REQUEST_DELAY)

    return all_products


# ── CSV output ───────────────────────────────────────────────────────────────

def save_to_csv(products: List[ShopeeProduct], output_path: str) -> None:
    """Write scraped products to CSV matching sg_listings_sample.csv schema."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fieldnames = ["product_title", "price_sgd", "sold_30d", "rating", "url", "platform", "seen_at"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in products:
            writer.writerow({
                "product_title": p.product_title,
                "price_sgd": p.price_sgd,
                "sold_30d": p.sold_30d,
                "rating": p.rating,
                "url": p.url,
                "platform": p.platform,
                "seen_at": p.seen_at,
            })
    print(f"Saved {len(products)} products to {output_path}")


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape Shopee SG perfume listings")
    parser.add_argument("--query", required=True, help="Search query (e.g. 'lattafa khamrah')")
    parser.add_argument("--pages", type=int, default=3, help="Max pages to scrape (default: 3)")
    parser.add_argument("--out", default=None, help="Output CSV path")
    args = parser.parse_args()

    if args.out is None:
        safe_query = args.query.replace(" ", "_").lower()
        date_str = datetime.now().strftime("%Y%m%d")
        args.out = f"data/raw/shopee_{safe_query}_{date_str}.csv"

    print(f"Scraping Shopee SG for: {args.query}")
    driver = build_driver()
    try:
        products = scrape_query(driver, args.query, max_pages=args.pages)
        if products:
            save_to_csv(products, args.out)
        else:
            print("No products found.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
