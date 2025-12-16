# mobox_final.py
# FINAL SAFE VERSION — API LIST (ADAPTER) + PLAYWRIGHT → M3U

import asyncio
from playwright.async_api import async_playwright

# ================= CONFIG =================
LIMIT = 5
OUTPUT_FILE = "mobox.m3u"

REFERER_URL = "https://fmoviesunblocked.net/"
MIN_FILE_SIZE_MB = 50
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

# ================= SIZE CHECK =================
async def get_file_size_mb(page, url):
    try:
        res = await page.request.head(url, headers=CUSTOM_HEADERS, timeout=5000)
        size = res.headers.get("content-length")
        return int(size) / (1024 * 1024) if size else 0
    except:
        return 0

# ================= STREAM GRAB =================
async def get_stream_url(page, detail_url):
    candidates = []
    BLACKLIST = ["trailer", "preview", "promo", "ads"]

    def on_request(req):
        u = req.url.lower()
        if not (".mp4" in u or ".m3u8" in u):
            return
        if any(b in u for b in BLACKLIST):
            return
        candidates.append(req.url)

    page.on("request", on_request)

    try:
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
    except:
        pass

    await page.wait_for_timeout(3000)
    try:
        await page.evaluate("""
            () => {
                document.querySelectorAll('video').forEach(v => {
                    v.muted = true;
                    v.play();
                });
            }
        """)
    except:
        pass

    await page.wait_for_timeout(8000)
    page.remove_listener("request", on_request)

    for u in candidates:
        size = await get_file_size_mb(page, u)
        if size >= MIN_FILE_SIZE_MB:
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
