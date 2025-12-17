import asyncio
import json
from playwright.async_api import async_playwright

MAX_EPISODES = 100
OUTPUT_FILE = "series.m3u"

API_SERIES = "https://moviebox.id/api/tv?page={}"
API_DETAIL = "https://moviebox.id/api/tv/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://moviebox.id/"
}

def count_episodes(data):
    total = 0
    for season in data.get("seasons", []):
        total += len(season.get("episodes", []))
    return total

def write_series(data, fh):
    title = data.get("title", "Unknown")
    poster = data.get("poster", "")

    for season in data.get("seasons", []):
        sn = season.get("season_number", 1)
        for ep in season.get("episodes", []):
            en = ep.get("episode_number", 1)
            url = ep.get("stream_url")
            if not url:
                continue

            fh.write(
                f'#EXTINF:-1 tvg-name="{title} S{sn}E{en}" '
                f'tvg-logo="{poster}",{title} S{sn}E{en}\n'
            )
            fh.write(url + "\n")

async def main():
    taken = 0
    skipped = 0
    page_num = 1

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

            while True:
                resp = await page.request.get(
                    API_SERIES.format(page_num),
                    headers=HEADERS
                )

                if not resp.ok:
                    break

                data = await resp.json()
                items = data.get("results", [])

                if not items:
                    break

                for item in items:
                    sid = item.get("id")
                    if not sid:
                        continue

                    detail_resp = await page.request.get(
                        API_DETAIL.format(sid),
                        headers=HEADERS
                    )

                    if not detail_resp.ok:
                        continue

                    detail = await detail_resp.json()
                    total_eps = count_episodes(detail)

                    if total_eps > MAX_EPISODES:
                        skipped += 1
                        continue

                    write_series(detail, f)
                    taken += 1

                page_num += 1

        await browser.close()

    print(f"Done. Taken={taken}, Skipped={skipped}")

if __name__ == "__main__":
    asyncio.run(main())
