# Bahrain News & Information Hub

A live news aggregator for Bahrain, pulling English-language headlines from official media outlets.

**Live site:** [https://monogikon-art.github.io/bahrain-news/](https://monogikon-art.github.io/bahrain-news/)

## Sources
- **BNA** — Bahrain News Agency (`bna.bh`)
- **GDN** — Gulf Daily News (`gdnonline.com`)
- **News of Bahrain** (`newsofbahrain.com`)

## How it works
- A GitHub Actions workflow runs every 30 minutes
- The Python scraper fetches headlines from all 3 sources
- Results are saved to `data/news.json`
- The static `index.html` reads from that JSON — served via GitHub Pages

## Features
- English-only articles
- Date/time metadata with relative timestamps
- Sorted by most recent first
- Dark mode
- Emergency contacts, police numbers, Gulf Air hotlines
- Instagram accounts for Bahrain media & government
- Fully responsive design
