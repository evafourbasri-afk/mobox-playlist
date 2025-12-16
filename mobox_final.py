# mobox_final.py
# FINAL FIXED VERSION — MovieBox → M3U
# SAFE for GitHub Actions (NO aiohttp, NO obfuscated import)

import asyncio
from playwright.async_api import async_playwright

# ================= CONFIG =================
LIMIT = 5
OUTPUT_FILE = "mobox.m3u"

REFERER_URL = "https://fmoviesunblocked.net/"
HEADLESS = True

CUSTOM_HEADERS = {
    "Referer": REFERER_URL,
    "Origin": REFERER_URL
}

ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/92.0 Mobile Safari/537.36"
)

# ================= API ADAPTER =================
def get_items():
    # GANTI isi adapter ini sesuai data kamu
    from providers.movies_adapter import get_movies
    return get_movies(limit=LIMIT)

# ================= M3U BUILDER =================
def build_m3u(items):
    out = ["#EXTM3U"]
    for it in items:
        if it.get("stream"):
            out.append(f'#EXTINF:-1 group-title="MovieBox", {it["title"]}')
            out.append(f'{it["stream"]}|Referer={REFERER_URL}')
    return "\n".join(out)

# ================= STREAM GRABBER (FINAL FIX) =================
async def get_stream_url(page, detail_url):
    candidates = []

    def on_request(req):
        u = req.url.lower()

        # Fokus stream HLS MovieBox
        if (
            ".m3u8" in u
            or "playlist" in u
            or "index.m3u8" in u
            or "/hls/" in u
        ):
            candidates.append(req.url)

    page.on("request", on_request)

    try:
        await page.goto(detail_url, wait_until="networkidle", timeout=60000)
    except:
        pass

    # ==== FORCE PLAY (KRUSIAL) ====
    await page.wait_for_timeout(4000)
    try:
        await page.evaluate("""
            () => {
                // klik semua kemungkinan tombol play
                document.querySelectorAll(
                    'button, .play, .vjs-big-play-button, .jw-icon-play'
                ).forEach(b => b.click());

                // paksa video play
                document.querySelectorAll('video').forEach(v => {
                    v.muted = true;
                    v.play();
                });
            }
        """)
    except:
        pass

    # ==== TUNGGU NETWORK STREAM ====
    await page.wait_for_timeout(15000)
    page.remove_listener("request", on_request)

    # ==== PILIH STREAM TERBAIK ====
    for u in candidates:
        if ".m3u8" in u:
            return u

    return None

# ================= MAIN =================
async def main():
    items = get_items()
    print(f"▶ API LIST: {len(items)} item")

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent=ANDROID_UA,
            extra_http_headers=CUSTOM_HEADERS,
            ignore_https_errors=True
        )
        page = await context.new_page()

        for i, it in enumerate(items, 1):
            print(f"[{i}/{len(items)}] {it['title']}")
            stream = await get_stream_url(page, it["url"])
            if stream:
                it["stream"] = stream
                results.append(it)
                print("✔ stream ditemukan")
            else:
                print("✖ stream tidak ditemukan")
            print("-" * 40)

        await browser.close()

    if results:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(build_m3u(results))
        print(f"✔ DONE → {OUTPUT_FILE}")
    else:
        print("✖ Tidak ada stream valid")

if __name__ == "__main__":
    asyncio.run(main())
