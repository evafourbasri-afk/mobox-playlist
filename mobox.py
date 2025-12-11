# mobox.py
# FINAL VERSION — WORKING PLAYLIST BUILDER FOR MOVIEBOX.PH
# Menggunakan Playwright Chromium untuk bypass Cloudflare

import asyncio
from playwright.async_api import async_playwright

MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"


# ============================================
# Helper ambil streaming URL (.m3u8 / .mp4 / .mpd)
# ============================================
async def get_stream_url(page, item_url):
    await page.goto(item_url, wait_until="networkidle")
    await page.wait_for_timeout(4000)

    found_streams = []

    def on_request(req):
        url = req.url
        if any(ext in url for ext in [".m3u8", ".mp4", ".mpd"]):
            found_streams.append(url)

    page.on("request", on_request)

    await page.wait_for_timeout(5000)

    return found_streams[0] if found_streams else None


# ============================================
# Ambil daftar film dari homepage
# ============================================
async def get_movies(page):
    await page.goto(MOVIEBOX_URL, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    links = await page.query_selector_all("a")

    results = []

    for link in links:
        href = await link.get_attribute("href")
        title = (await link.inner_text() or "").strip()

        if href and "/movie/" in href and len(title) > 2:
            results.append({
                "title": title,
                "url": MOVIEBOX_URL + href
            })

    return results


# ============================================
# Build Playlist M3U
# ============================================
def build_m3u(items):
    out = ["#EXTM3U"]

    for i in items:
        if i.get("stream"):
            out.append(f'#EXTINF:-1 tvg-name="{i["title"]}", {i["title"]}')
            out.append(i["stream"])

    return "\n".join(out)


# ============================================
# MAIN SCRIPT
# ============================================
async def main():
    print("▶ Menjalankan MovieBox Scraper...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("▶ Mengambil daftar film...")
        movies = await get_movies(page)
        print(f"✔ Total film ditemukan: {len(movies)}")

        final_items = []

        # untuk testing ambil 20 dulu, bisa dilepas
        for m in movies[:20]:
            print(f"▶ Memproses: {m['title']}")
            stream = await get_stream_url(page, m["url"])
            m["stream"] = stream
            final_items.append(m)

        await browser.close()

    playlist = build_m3u(final_items)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(playlist)

    print("\n✔ Playlist berhasil dibuat:", OUTPUT_FILE)


# RUN
asyncio.run(main())
