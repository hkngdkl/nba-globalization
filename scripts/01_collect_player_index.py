import time
import random
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE = "https://www.basketball-reference.com"
INDEX_URL = f"{BASE}/players/"
OUT_PATH = Path("data/raw/players_index.csv")

def fetch_html_with_browser(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # istersen False yapıp tarayıcıyı görürsün
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        # biraz bekleyelim (bot gibi görünmemek için)
        page.wait_for_timeout(1500 + int(random.random() * 1000))
        html = page.content()
        context.close()
        browser.close()
        return html

def main():
    html = fetch_html_with_browser(INDEX_URL)
    soup = BeautifulSoup(html, "html.parser")

    # /players/a/ ... /players/z/
    letter_links = []
    for a in soup.select("a[href^='/players/']"):
        href = a.get("href", "")
        if href.startswith("/players/") and href.count("/") == 3 and href.endswith("/"):
            if len(href) == len("/players/a/"):
                letter_links.append(href)

    letter_links = sorted(set(letter_links))
    if not letter_links:
        raise RuntimeError("Letter links not found. Site layout may have changed or page did not load correctly.")

    records = []
    for href in letter_links:
        url = BASE + href
        print("Fetching:", url)

        page_html = fetch_html_with_browser(url)
        s = BeautifulSoup(page_html, "html.parser")

        table = s.select_one("table#players")
        if table is None:
            print("  ⚠️ players table not found, skipping:", url)
            continue

        for a in table.select("a[href^='/players/'][href$='.html']"):
            name = a.get_text(strip=True)
            player_href = a.get("href", "")
            records.append({"player_name": name, "player_url": BASE + player_href})

        time.sleep(0.8 + random.random() * 0.6)  # nazik bekleme

    df = pd.DataFrame(records).drop_duplicates()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {len(df):,} players to {OUT_PATH}")

if __name__ == "__main__":
    main()
