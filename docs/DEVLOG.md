# Devlog – NBA Globalization Dataset

## Issue: 403 Forbidden when scraping Basketball-Reference
**Date:** 2026-02-07  
**Where:** https://www.basketball-reference.com/players/  
**Error:** `requests.exceptions.HTTPError: 403 Client Error: Forbidden`

### What we tried
- Used `requests` with browser-like headers + session
- Still got 403

### Fix
- Switched to Playwright (headless Chromium) to fetch HTML as a real browser:
  - `pip install playwright`
  - `playwright install chromium`
- Used `page.goto(...); page.content()` to retrieve fully loaded HTML
- Parsed the same tables with BeautifulSoup
- Result: Successfully collected A–Z player index
  - Saved **5387** player records to `data/raw/players_index.csv`

### Key lesson
Some sites block raw HTTP scrapers; a headless browser can bypass 403 by behaving like a real user.

## Transition to Analysis & Storytelling

After successfully collecting and cleaning the player datasets, the main challenges shifted
from data acquisition to analysis and visualization.

At this stage, no major technical blockers were encountered. Most remaining work focused on:
- defining the correct unit of analysis (player debut year)
- validating assumptions behind time-series trends
- iteratively refining visualizations for storytelling clarity

As a result, further insights and decisions were documented directly in the analysis notebook
rather than in the devlog.