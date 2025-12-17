import asyncio
import json
import time
from playwright.async_api import async_playwright

MAX_EPISODES = 100
OUTPUT_FILE = "series.m3u"

SERIES_LIST_URL = "https://moviebox.id/tv"
DETAIL_API_PREFIX = "https://moviebox.id/api/tv/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://moviebox.id/"
}

async def fetch_json(page, url):
    resp = await page.request.get(url, headers=HEADERS)
    if not resp.ok:
        return None
    try:
        return await resp.json()
    except:
        return None

def count_episodes(detail):
    total = 0
    for season in detail.get("seasons", []):
        total += len(season.get("episodes", []))
    return total

def write_series(series, fh):
    title = series.get("title", "Unknown")
    poster = series.get("poster", "")

    for season in series.get("seasons", []):
        sn = season.get("season_number", 1)
        for ep in season.get("episodes", []):
            en = ep.get("episode_number", 1)
            stream = ep.get("stream_url")
            if not stream:
                continue

            fh.write(
                f'#EXTINF:-1 tvg-name="{title} S{sn}E{en}" '
                f'tvg-logo="{poster}",{title} S{sn}E{en}\n'
            )
            fh.write(stream + "\n")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(SERIES_LIST_URL, timeout=60000)
        await page.wait_for_timeout(3000)

        series_ids = await page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll('[data-id]'))
                    .map(e => e.getAttribute('data-id'))
                    .filter(Boolean);
            }
        """)

        taken = 0
        skipped = 0

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

            for sid in series_ids:
                detail = await fetch_json(page, DETAIL_API_PREFIX + sid)
                if not detail:
                    continue

                total_eps = count_episodes(detail)
                if total_eps > MAX_EPISODES:
                    skipped += 1
                    continue

                write_series(detail, f)
                taken += 1
                await page.wait_for_timeout(500)

        await browser.close()

        print(f"Done. Taken={taken}, Skipped={skipped}")

if __name__ == "__main__":
    asyncio.run(main())
