import re
import time
import random
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://en.wikipedia.org"
# NBA All-Star Game pages list (yearly index)
INDEX_URL = f"{BASE}/wiki/NBA_All-Star_Game"

OUT_CSV = Path("data/raw/all_star_selections.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SLEEP_MIN = 0.3
SLEEP_MAX = 0.8

MIN_YEAR = 1990
MAX_YEAR = 2024  # completed seasons only


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def extract_year_links(index_html: str) -> list[tuple[int, str]]:
    """
    From the NBA All-Star Game Wikipedia page, extract yearly game links like:
    /wiki/2020_NBA_All-Star_Game
    """
    soup = BeautifulSoup(index_html, "html.parser")
    year_links = {}

    for a in soup.select('a[href^="/wiki/"]'):
        href = a.get("href", "")
        # only actual year game pages
        m = re.search(r"^/wiki/(\d{4})_NBA_All-Star_Game$", href)
        if not m:
            continue
        year = int(m.group(1))
        if year < MIN_YEAR or year > MAX_YEAR:
            continue
        year_links[year] = urljoin(BASE, href)

    return sorted(year_links.items(), key=lambda x: x[0])


def parse_rosters(year: int, year_html: str) -> list[dict]:
    soup = BeautifulSoup(year_html, "html.parser")

    # Most pages have roster tables with these ids (or very similar):
    # - East roster / West roster
    # - Team LeBron / Team Giannis etc.
    roster_tables = []

    for t in soup.select("table.wikitable"):
        tid = (t.get("id") or "").lower()
        caption = t.find("caption")
        cap = caption.get_text(" ", strip=True).lower() if caption else ""

        # Heuristics: roster tables usually have "roster" in id or caption
        # and contain columns like Player / Pos / Team.
        header = " ".join(th.get_text(" ", strip=True) for th in t.select("tr th")).lower()

        is_roster = (
            ("roster" in tid) or ("roster" in cap) or
            ("east" in tid and "roster" in header) or
            ("west" in tid and "roster" in header) or
            ("team" in cap and "roster" in header)
        )

        # more robust: must have Player + (Team or Pos) in header
        has_player = "player" in header
        has_team_or_pos = ("team" in header) or ("pos" in header) or ("nba team" in header) or ("club" in header)

        if is_roster and has_player and has_team_or_pos:
            roster_tables.append(t)

    # Fallback: if above didn't work, try to grab the two most "roster-like" tables
    if not roster_tables:
        candidates = []
        for t in soup.select("table.wikitable"):
            header = " ".join(th.get_text(" ", strip=True) for th in t.select("tr th")).lower()
            if "player" in header and (("team" in header) or ("pos" in header)):
                # score by number of player links
                score = len(t.select('td a[href^="/wiki/"]'))
                candidates.append((score, t))
        candidates.sort(key=lambda x: x[0], reverse=True)
        roster_tables = [t for _, t in candidates[:2]]  # usually East+West

    records = []
    for t in roster_tables:
        # find player column index
        first_header_row = t.select_one("tr")
        cols = [c.get_text(" ", strip=True).lower() for c in first_header_row.find_all(["th", "td"])] if first_header_row else []
        try:
            player_idx = next(i for i, c in enumerate(cols) if "player" in c)
        except StopIteration:
            player_idx = 0

        for tr in t.select("tr"):
            tds = tr.find_all("td")
            if len(tds) <= player_idx:
                continue
            cell = tds[player_idx]
            a = cell.select_one('a[href^="/wiki/"]')
            if not a:
                continue
            name = a.get_text(" ", strip=True)
            if len(name) < 4:
                continue

            records.append({
                "season_year": year,
                "player_name": name,
                "source": "en.wikipedia"
            })

    if not records:
        return []

    df = pd.DataFrame(records).drop_duplicates(subset=["season_year", "player_name"])
    return df.to_dict("records")


def main():
    print(">>> Fetching index:", INDEX_URL)
    index_html = fetch(INDEX_URL)

    year_links = extract_year_links(index_html)
    print(f">>> Found {len(year_links)} year pages ({MIN_YEAR}-{MAX_YEAR}).")

    all_rows = []
    for year, url in year_links:
        print(f">>> [{year}] {url}")
        try:
            html = fetch(url)
            rows = parse_rosters(year, html)
            print(f"    -> rows: {len(rows)}")
            all_rows.extend(rows)
        except Exception as e:
            print(f"    !! error: {e!r}")

        time.sleep(SLEEP_MIN + random.random() * (SLEEP_MAX - SLEEP_MIN))

    df = pd.DataFrame(all_rows).drop_duplicates()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f">>> Saved {len(df):,} rows -> {OUT_CSV}")


if __name__ == "__main__":
    main()