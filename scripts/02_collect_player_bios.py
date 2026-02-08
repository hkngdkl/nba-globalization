import re
import time
import random
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# -----------------------------
# Paths
# -----------------------------
INDEX_CSV = Path("data/raw/players_index.csv")
OUT_CSV = Path("data/raw/players_bios.csv")
CACHE_DIR = Path("data/raw/cache/player_pages")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Scrape settings
# -----------------------------
HEADLESS = True
MIN_SLEEP = 0.8
MAX_SLEEP = 1.6
TIMEOUT_MS = 60_000

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# -----------------------------
# Helpers
# -----------------------------
def slug_from_player_url(url: str) -> str:
    """
    https://www.basketball-reference.com/players/j/jamesle01.html -> jamesle01
    """
    m = re.search(r"/players/[a-z]/([a-z0-9]+)\.html$", url)
    return m.group(1) if m else re.sub(r"\W+", "_", url)

def cache_path_for(url: str) -> Path:
    return CACHE_DIR / f"{slug_from_player_url(url)}.html"

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def extract_country_from_born(born_text: str) -> str | None:
    """
    born_text example:
      "Born: December 30, 1984 (Age: 39-...) Akron, Ohio us"
      or includes country name at end like "Serbia", "Greece", "Turkey".
    We'll try:
      1) If ends with 2-letter lower-case like 'us' we map to USA.
      2) Else take last token/phrase after last comma (often country).
    """
    if not born_text:
        return None

    t = clean_text(born_text)

    # basketball-reference sometimes uses a small country code link; text may include "us"
    # We'll look for trailing "us" token.
    if re.search(r"\bus\b$", t.lower()):
        return "United States"

    # Many pages: "... City, State" for US players; non-US: "... City, Country"
    # Heuristic: country is after the last comma.
    parts = [p.strip() for p in t.split(",")]
    if len(parts) >= 2:
        last = parts[-1]
        # If last looks like a US state (2 uppercase letters), assume USA
        if re.fullmatch(r"[A-Z]{2}", last):
            return "United States"
        # If last is alphabetic and not too short, treat as country/region
        if re.search(r"[A-Za-z]", last) and len(last) >= 3:
            return last

    # fallback: sometimes last word is country
    tokens = t.split()
    if tokens:
        last = tokens[-1]
        if last.lower() == "us":
            return "United States"
        if len(last) >= 3 and re.search(r"[A-Za-z]", last):
            return last

    return None

def extract_nba_debut_year(soup: BeautifulSoup) -> int | None:
    """
    On player pages there's often a line like:
      'NBA Debut: October 29, 2003'
    We'll parse the year.
    """
    text = soup.get_text(" ", strip=True)
    m = re.search(r"NBA Debut:\s*[A-Za-z]+\s+\d{1,2},\s+(\d{4})", text)
    if m:
        return int(m.group(1))
    return None

def extract_born_line_text(soup: BeautifulSoup) -> str | None:
    """
    Try to locate the 'Born:' label in the player page.
    """
    # Common structure: <strong>Born:</strong> ... (with surrounding text)
    born_strong = soup.find("strong", string=re.compile(r"^Born:$", re.I))
    if born_strong and born_strong.parent:
        # Parent is typically a <p> containing the full "Born: ..." line.
        return clean_text(born_strong.parent.get_text(" ", strip=True))

    # fallback: search any strong that contains 'Born'
    for st in soup.find_all("strong"):
        if st.get_text(strip=True).lower() == "born:" and st.parent:
            return clean_text(st.parent.get_text(" ", strip=True))

    return None

def fetch_html_playwright(url: str, headless: bool = True) -> str:
    """
    Fetch page HTML via a real browser context.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=UA, locale="en-US")
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        page.wait_for_timeout(1200 + int(random.random() * 900))
        html = page.content()
        context.close()
        browser.close()
        return html

def get_player_page_html(url: str) -> str:
    """
    Cache-first fetch.
    """
    cpath = cache_path_for(url)
    if cpath.exists():
        return cpath.read_text(encoding="utf-8", errors="ignore")

    html = fetch_html_playwright(url, headless=HEADLESS)
    cpath.write_text(html, encoding="utf-8")
    return html

# -----------------------------
# Main
# -----------------------------
def main():
    if not INDEX_CSV.exists():
        raise FileNotFoundError(f"Missing {INDEX_CSV}. Run 01_collect_player_index.py first.")

    players = pd.read_csv(INDEX_CSV)
    if "player_url" not in players.columns:
        raise ValueError("players_index.csv must include 'player_url' column.")

    # Resume support: if OUT_CSV exists, skip already processed player_url
    done_urls = set()
    if OUT_CSV.exists() and OUT_CSV.stat().st_size > 0:
        try:
            existing = pd.read_csv(OUT_CSV)
            if "player_url" in existing.columns:
                done_urls = set(existing["player_url"].dropna().unique().tolist())
                print(f"Resume: {len(done_urls):,} players already in {OUT_CSV}")
        except Exception:
            # If it fails to read, we won't resume (better to fix file)
            print("Warning: Could not read existing players_bios.csv; resume disabled.")

    records = []
    total = len(players)
    processed = 0
    saved_rows = 0

    for i, row in players.iterrows():
        name = str(row.get("player_name", "")).strip()
        url = str(row.get("player_url", "")).strip()
        if not url or url in done_urls:
            continue

        processed += 1
        print(f"[{i+1}/{total}] {name} -> {url}")

        try:
            html = get_player_page_html(url)
            soup = BeautifulSoup(html, "html.parser")

            born_line = extract_born_line_text(soup)  # "Born: ..."
            country = extract_country_from_born(born_line) if born_line else None
            debut_year = extract_nba_debut_year(soup)

            rec = {
                "player_name": name,
                "player_url": url,
                "born_line": born_line,
                "country": country,
                "debut_year": debut_year,
            }
            records.append(rec)

        except Exception as e:
            # store error but keep going
            records.append({
                "player_name": name,
                "player_url": url,
                "born_line": None,
                "country": None,
                "debut_year": None,
                "error": repr(e),
            })

        # Polite rate limit
        time.sleep(MIN_SLEEP + random.random() * (MAX_SLEEP - MIN_SLEEP))

        # Save in batches
        if len(records) >= 50:
            df_batch = pd.DataFrame(records)
            OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
            # append mode
            header = not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0
            df_batch.to_csv(OUT_CSV, mode="a", index=False, header=header)
            saved_rows += len(df_batch)
            print(f"  ✅ wrote batch ({len(df_batch)}) -> {OUT_CSV} (total written this run: {saved_rows})")
            records = []

    # flush remaining
    if records:
        df_batch = pd.DataFrame(records)
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        header = not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0
        df_batch.to_csv(OUT_CSV, mode="a", index=False, header=header)
        saved_rows += len(df_batch)
        print(f"  ✅ wrote final batch ({len(df_batch)}) -> {OUT_CSV} (total written this run: {saved_rows})")

    print("\nDone.")
    print(f"Output: {OUT_CSV}")
    print(f"Cache dir: {CACHE_DIR}")

if __name__ == "__main__":
    main()
