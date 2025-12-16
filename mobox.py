# mobox.py v34 — Size Filtering Edition (Anti-Trailer Final)

import asyncio
from playwright.async_api import async_playwright

# --- KONFIGURASI ---
MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"
TEST_LIMIT = 50       

# Github Actions wajib True (Headless)
HEADLESS_MODE = True 

# Batas Ukuran File (dalam MB) untuk dianggap Film
# Jika di bawah ini, dianggap trailer dan DIBUANG.
MIN_FILE_SIZE_MB = 50 

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
    await page.evaluate("""
        async () => {
            for (let i = 0; i < 8; i++) {
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
            # Format khusus OTT Navigator
            final_url = f"{x['stream']}|Referer={REFERER_URL}"
            out.append(final_url)
    return "\n".join(out)

# --- FUNGSI CEK UKURAN FILE (LOGIKA BARU) ---

async def get_file_size_mb(page, url):
    """Mengirim request HEAD untuk cek ukuran file tanpa download."""
    try:
        # Gunakan API Request dari Playwright (lebih ringan daripada browser navigate)
        response = await page.request.head(url, headers=CUSTOM_HEADERS, timeout=5000)
        
        # Cek header Content-Length
        size_bytes = response.headers.get("content-length")
        
        if size_bytes:
            size_mb = int(size_bytes) / (1024 * 1024) # Konversi ke MB
            return size_mb
        else:
            # Jika server tidak kasih info size (jarang terjadi di CDN video)
            return 0
    except Exception as e:
        # Jika error koneksi ke file video
        return 0

# --- CORE LOGIC ---

async def get_stream_url(page, url):
    candidate_streams = [] # Kita tampung dulu semua calon kandidat
    
    # Filter Keyword Dasar
    BLACKLIST = ["trailer", "preview", "promo", "teaser", "googleads"]
    TARGETS = ["hakunaymatata", "bcdnxw", "/resource/", "aoneroom"]

    def on_request(req):
        u = req.url
        # Hanya ambil ekstensi video
        if not any(ext in u for ext in [".mp4", ".m3u8"]): return

        # Buang jika URL mengandung kata 'trailer' secara eksplisit
        if any(bl in u.lower() for bl in BLACKLIST): return

        # Simpan ke daftar kandidat untuk dicek ukurannya nanti
        priority = 100 if any(t in u for t in TARGETS) else 50
        candidate_streams.append({"url": u, "priority": priority})

    page.on("request", on_request)

    print(f"   - Membuka Page: {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except: pass

    # --- JS FORCE PLAY (Agar file asli terpancing keluar) ---
    print("   - Memicu Player...")
    await page.wait_for_timeout(3000)
    try:
        await page.evaluate("""
            () => {
                const vids = document.querySelectorAll('video');
                vids.forEach(v => { v.muted = true; v.play(); });
                const selectors = ['.jw-display-icon-container', '.vjs-big-play-button', '#player'];
                selectors.forEach(s => { 
                    const el = document.querySelector(s);
                    if(el) el.click();
                });
            }
        """)
    except: pass

    # Tunggu trafik network terekam
    print("   - Menunggu Network (10 detik)...")
    await page.wait_for_timeout(10000)
    
    page.remove_listener("request", on_request)

    # --- FILTER FINAL BERDASARKAN UKURAN (SIZE CHECK) ---
    if candidate_streams:
        print(f"     -> Menganalisa {len(candidate_streams)} link video...")
        
        # Urutkan: Prioritas Keyword dulu, baru panjang URL
        candidate_streams.sort(key=lambda x: (x["priority"], len(x["url"])), reverse=True)
        
        valid_movie = None
        
        for item in candidate_streams:
            u = item["url"]
            
            # Cek Ukuran File
            print(f"     -> Cek Size: {u[-30:]} ... ", end="")
            size = await get_file_size_mb(page, u)
            print(f"{size:.2f} MB")
            
            if size > MIN_FILE_SIZE_MB:
                print(f"     ✔ LOLOS! (> {MIN_FILE_SIZE_MB} MB). Ini Film Asli.")
                valid_movie = u
                break # Ketemu film asli, stop looping
            else:
                print(f"     ✖ DIBUANG (Trailer/Iklan).")
        
        if valid_movie:
            return valid_movie
        else:
            print("     ✖ Semua link yang tertangkap hanyalah Trailer/Kecil.")
            return None

    else:
        print("     ✖ Tidak ada stream tertangkap.")
        return None

# --- MAIN ---

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        context = await browser.new_context(
            user_agent=ANDROID_USER_AGENT,
            extra_http_headers=CUSTOM_HEADERS,
            viewport={"width": 412, "height": 915},
            ignore_https_errors=True
        )
        page = await context.new_page()

        print("▶ Grab List Film...")
        try:
            await page.goto(MOVIEBOX_URL, wait_until="domcontentloaded", timeout=60000)
        except: pass
        await auto_scroll(page)
        
        elements = await page.query_selector_all("a[href*='/movie/'], a[href*='/detail']")
        movies = []
        seen = set()
        for el in elements:
            href = await el.get_attribute("href")
            if not href: continue
            full_url = MOVIEBOX_URL + href if href.startswith("/") else href
            if full_url in seen: continue
            
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
        print(f"\n⚙️ Memproses {len(targets)} film... (Min Size: {MIN_FILE_SIZE_MB} MB)\n")

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
        print(f"\n✔ SELESAI! Playlist: {OUTPUT_FILE}")
    else:
        print("\n✖ Gagal total.")

if __name__ == "__main__":
    asyncio.run(main())
