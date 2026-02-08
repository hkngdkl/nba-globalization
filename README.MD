# NBA Globalization Since 1990

This project analyzes how the NBA has globalized over the past three decades by examining
the origins of players entering the league each year.

Unlike many analyses that rely on pre-built datasets, the dataset used in this project
was created from scratch by collecting publicly available player information and defining
a consistent NBA debut year for each player.

## Research Question
How has the share of Non-USA players entering the NBA changed since 1990?

## Dataset
- Self-collected NBA player biographical data
- Each player is counted only in their NBA debut year
- Covers debut years from 1990 to 2025

## Methodology
- Players classified as USA vs Non-USA based on country of origin
- Time-series analysis of yearly NBA entrants
- Period comparison using pie charts (1990–1999 vs 2000–2025)

## Key Findings
- In the 1990s, only about 10% of players entering the NBA were Non-USA
- Since 2000, that figure has increased to approximately 23%
- NBA growth in recent decades has increasingly relied on international talent

## Structure
nba-globalization/
├── data/
│   └── raw/
│       ├── players_bios.csv
│       └── all_star_selections.csv
├── notebooks/
│   └── 01_nba_globalization_story.ipynb
├── scripts/
│   ├── 01_collect_player_index.py
│   ├── 02_collect_player_bios.py
│   └── 03_collect_all_stars_wikipedia_en.py


## Tools
- Python
- Pandas
- Matplotlib
- Seaborn

## Notes
This project was created as part of the Codédex Monthly Data Challenge.