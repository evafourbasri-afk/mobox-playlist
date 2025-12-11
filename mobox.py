# mobox.py v2 — FIXED VERSION (MovieBox sekarang pakai lazy-load)
# Menunggu script selesai, auto scroll, lalu ambil URL streaming

import asyncio
from playwright.async_api import async_playwright

MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"

async def auto_scroll(page):
    """Scroll perlahan supaya lazy-loading MovieBox muncul."""
    for _ in range(20):
        await page.mouse.wheel(0, 2000)
        await page.wait_for_timeout(500)

async def get_stream_url(page, url):
    await page.goto(url, wait_until="networkidle")
    await page.wait_for_timeout(4000)

    streams = []

    def on_request(req):
        u = req.url
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            streams.append(u)

    page.on("request", on_request)

    await page.wait_for_timeout(5000)

    return streams[0] if streams else None

async def get_movies(page):
    await page.goto(MOVIEBOX_URL, wait_until="networkidle")
    await page.wait_for_timeout(3000)

    # Scroll supaya semua card film muncul
    await auto_scroll(page)

    cards = await page.query_selector_all("a[href*='/movie/']")

    movies = []
    for c in cards:
        href = await c.get_attribute("href")
        title = (await c.inner_text() or "").strip()

        if href and len(title) > 2:
            movies.append({
                "title": title,
                "url": MOVIEBOX_URL + href
            })

    return movies

def build_m3u(items):
    out = ["#EXTM3U"]
    for x in items:
        if x.get("stream"):
            out.append(f'#EXTINF:-1 tvg-name="{x["title"]}", {x["title"]}')
            out.append(x["stream"])
    return "\n".join(out)

async def main():
    print("▶ Mengambil data MovieBox...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        movies = await get_movies(page)

        print(f"✔ Film ditemukan: {len(movies)}")

        results = []
        for m in movies[:20]:
            print("▶ Ambil stream:", m["title"])
            m["stream"] = await get_stream_url(page, m["url"])
            results.append(m)

        await browser.close()

    playlist = build_m3u(results)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(playlist)

    print("✔ Selesai → mobox.m3u")

asyncio.run(main())
