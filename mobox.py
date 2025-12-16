# mobox.py v33 — GitHub Actions Edition (Headless Force)

import asyncio
from playwright.async_api import async_playwright

# --- KONFIGURASI ---
MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"
TEST_LIMIT = 50       

# !!! PENTING UNTUK GITHUB ACTIONS !!!
# Wajib True karena server tidak punya layar monitor.
HEADLESS_MODE = True 

# --- HEADERS ---
REFERER_URL = "https://fmoviesunblocked.net/"
CUSTOM_HEADERS = {
    "Referer": REFERER_URL,
    "Origin": REFERER_URL
}
ANDROID_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"

# --- FUNGSI UTILITY ---

async def auto_scroll(page):
    print("   - Scrolling halaman...")
    # Scroll lebih agresif
    await page.evaluate("""
        async () => {
            for (let i = 0; i < 10; i++) {
                window.scrollBy(0, window.innerHeight);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        }
    """)

def build_m3u(items):
    out = ["#EXTM3U"]
    for x in items:
        if x.get("stream"):
            out.append(f'#EXTINF:-1 group-title="MovieBox", {x["title"]}')
            # Format khusus OTT Navigator / Tivimate
            final_url = f"{x['stream']}|Referer={REFERER_URL}"
            out.append(final_url)
    return "\n".join(out)

# --- CORE LOGIC ---

async def get_stream_url(page, url):
    found_streams = []
    
    # Filter
    BLACKLIST = ["trailer", "preview", "promo", "teaser", "googleads"]
    TARGETS = ["hakunaymatata", "bcdnxw", "/resource/", "aoneroom"]

    def on_request(req):
        u = req.url
        if not any(ext in u for ext in [".mp4", ".m3u8"]): return

        # Buang Trailer
        if any(bl in u.lower() for bl in BLACKLIST):
            print(f"     [SKIP] Trailer dibuang")
            return

        score = 0
        if any(t in u for t in TARGETS): score = 100
        else: score = 50

        if score > 0:
            found_streams.append({"url": u, "score": score})
            if score == 100: print(f"     ★ JACKPOT: {u[:40]}...")

    page.on("request", on_request)

    print(f"   - Membuka: {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except: pass

    # --- TEKNIK BARU: JS FORCE CLICK (Tanpa Mouse) ---
    # Karena di headless mode mouse sering meleset, kita pakai perintah Javascript
    # untuk memaksa elemen video melakukan "play()".
    
    print("   - Memicu Video via Javascript...")
    await page.wait_for_timeout(4000)

    try:
        # Script JS untuk mencari video/tombol dan menekannya secara paksa
        await page.evaluate("""
            () => {
                // 1. Coba cari tag <video> dan force play
                const vids = document.querySelectorAll('video');
                vids.forEach(v => {
                    v.muted = true; // Video seringkali butuh mute agar bisa autoplay
                    v.play(); 
                });

                // 2. Coba cari tombol play umum dan klik()
                const selectors = [
                    '.jw-display-icon-container', 
                    '.vjs-big-play-button', 
                    '.play-button',
                    '#player'
                ];
                selectors.forEach(s => {
                    const el = document.querySelector(s);
                    if (el) el.click();
                });
            }
        """)
        
        # Backup: Klik tengah layar via Playwright (Blind Click)
        vp = page.viewport_size
        if vp:
            await page.mouse.click(vp['width'] / 2, vp['height'] / 3)

    except Exception as e:
        print(f"     ! JS Error: {e}")

    # Tunggu agak lama agar request film asli keluar
    print("   - Menunggu buffer (12 detik)...")
    await page.wait_for_timeout(12000)
    
    page.remove_listener("request", on_request)

    if found_streams:
        found_streams.sort(key=lambda x: (x["score"], len(x["url"])), reverse=True)
        best = found_streams[0]
        
        if "trailer" not in best["url"].lower():
            print(f"     ✔ DAPAT: {best['url'][:60]}...")
            return best["url"]
        else:
            print("     ✖ Hanya dapat trailer.")
    else:
        print("     ✖ Nihil.")

    return None

# --- MAIN ---

async def main():
    async with async_playwright() as p:
        # Args tambahan agar lancar di Linux Server (GitHub Actions)
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gl-drawing-for-tests"]
        )
        
        context = await browser.new_context(
            user_agent=ANDROID_USER_AGENT,
            extra_http_headers=CUSTOM_HEADERS,
            viewport={"width": 412, "height": 915},
            ignore_https_errors=True
        )
        page = await context.new_page()

        print("▶ Mengambil daftar film...")
        try:
            await page.goto(MOVIEBOX_URL, wait_until="domcontentloaded", timeout=60000)
        except: pass
        
        await auto_scroll(page)
        
        # Logika ambil judul film
        elements = await page.query_selector_all("a[href*='/movie/'], a[href*='/detail']")
        movies = []
        seen = set()
        for el in elements:
            href = await el.get_attribute("href")
            if not href: continue
            full_url = MOVIEBOX_URL + href if href.startswith("/") else href
            if full_url in seen: continue
            
            # Simple title extraction
            title = await el.inner_text()
            if not title: 
                try: title = await el.query_selector(".title").inner_text()
                except: title = "Unknown"
            
            title = title.replace("\n", " ").strip()
            if len(title) > 2:
                movies.append({"title": title, "url": full_url})
                seen.add(full_url)

        # Proses Grab
        results = []
        targets = movies[:TEST_LIMIT]
        print(f"\n⚙️ Memproses {len(targets)} film... (Headless: {HEADLESS_MODE})\n")

        for i, m in enumerate(targets):
            print(f"[{i+1}/{len(targets)}] {m['title']}")
            stream = await get_stream_url(page, m["url"])
            if stream:
                m["stream"] = stream
                results.append(m)
            print("-" * 40)

        await browser.close()
    
    if results:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(build_m3u(results))
        print(f"\n✔ SELESAI! Playlist disimpan: {OUTPUT_FILE}")
    else:
        print("\n✖ Gagal total.")

if __name__ == "__main__":
    asyncio.run(main())
