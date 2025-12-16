# mobox.py v32 — Anti-Trailer & OTT Fix Edition

import asyncio
from playwright.async_api import async_playwright

# --- KONFIGURASI UTAMA ---
MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"
TEST_LIMIT = 20       # Jumlah film yang mau diambil
HEADLESS_MODE = False # Set ke False agar bisa melihat browser bekerja (Debugging)
                      # Set ke True jika nanti sudah lancar dan ingin berjalan di background

# --- HEADER & AGENT ---
# Header ini wajib agar video mau jalan
REFERER_URL = "https://fmoviesunblocked.net/"

CUSTOM_HEADERS = {
    "Referer": REFERER_URL,
    "Origin": REFERER_URL
}

ANDROID_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"

# --- FUNGSI UTILITY ---

async def auto_scroll(page):
    """Scroll halaman agar gambar/link ter-load."""
    print("   - Scrolling halaman...")
    last_height = await page.evaluate("document.body.scrollHeight")
    
    for _ in range(10): 
        await page.evaluate("window.scrollBy(0, 1500)") 
        await page.wait_for_timeout(800)
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height: break
        last_height = new_height

def build_m3u(items):
    """
    Membuat file M3U yang kompatibel dengan OTT Navigator / Tivimate.
    Hanya menyertakan header Referer agar tidak bentrok.
    """
    out = ["#EXTM3U"]
    
    for x in items:
        if x.get("stream"):
            out.append(f'#EXTINF:-1 group-title="MovieBox", {x["title"]}')
            # Format: URL|Referer=...
            # Kita tidak masukkan User-Agent disini agar OTT Navigator pakai default-nya sendiri
            final_url = f"{x['stream']}|Referer={REFERER_URL}"
            out.append(final_url)
            
    return "\n".join(out)

# --- FUNGSI PENGAMBIL STREAM (LOGIKA BARU) ---

async def get_stream_url(page, url):
    found_streams = []
    
    # 1. SETUP FILTER
    # Kata kunci yang DILARANG (Trailer/Iklan)
    BLACKLIST = ["trailer", "preview", "promo", "teaser", "googleads", "doubleclick"]
    
    # Kata kunci TARGET UTAMA (Bocoran)
    TARGETS = ["hakunaymatata", "bcdnxw", "/resource/", "aoneroom"]

    def on_request(req):
        u = req.url
        
        # Filter Sampah
        if not any(ext in u for ext in [".mp4", ".m3u8", ".mpd"]):
            return

        # LOGIKA ANTI-TRAILER:
        # Jika ada kata 'trailer' di URL, langsung buang!
        if any(bl in u.lower() for bl in BLACKLIST):
            print(f"     [SKIP] Trailer dibuang: {u[-40:]}")
            return

        score = 0
        is_jackpot = False

        # Cek Target Utama
        if any(t in u for t in TARGETS):
            score = 100 # Prioritas Tertinggi
            is_jackpot = True
        
        # Cek Stream Standar
        else:
            score = 50
            if "-ld.mp4" in u: score = 20 # Low Quality

        if score > 0:
            found_streams.append({"url": u, "score": score})
            if is_jackpot:
                print(f"     ★ JACKPOT FILM ASLI: {u[:60]}...")

    # Pasang listener network
    page.on("request", on_request)

    print(f"   - Membuka: {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except:
        pass

    # 2. LOGIKA KLIK AGRESIF (MENEMBUS IFRAME)
    print("   - Mencoba menembus Player (Tunggu 3 detik)...")
    await page.wait_for_timeout(3000)

    try:
        # Cari semua frame (karena player sering sembunyi di iframe)
        frames = page.frames
        clicked = False
        
        # Daftar tombol play umum
        play_selectors = [
            ".jw-display-icon-container", ".vjs-big-play-button", 
            "div.play-button", "div#player", "button[aria-label='Play']",
            "video", "div.mobile-play", "img[src*='play']"
        ]

        # Coba klik di setiap frame
        for frame in frames:
            for sel in play_selectors:
                try:
                    if await frame.locator(sel).first.is_visible():
                        print(f"     -> Klik tombol di frame: {sel}")
                        await frame.locator(sel).first.click(force=True, timeout=1000)
                        clicked = True
                        break
                except: continue
            if clicked: break
        
        # KLIK CADANGAN (Tengah Layar)
        if not clicked:
            print("     -> Melakukan FORCE CLICK Tengah Layar...")
            vp = page.viewport_size
            if vp:
                # Klik tengah atas dan tengah pas
                await page.mouse.click(vp['width'] / 2, vp['height'] / 3)
                await page.wait_for_timeout(500)
                await page.mouse.click(vp['width'] / 2, vp['height'] / 2)

    except Exception as e:
        print(f"     ! Error klik: {e}")

    # 3. MENUNGGU STREAM ASLI MUNCUL
    # Film asli butuh waktu loading setelah klik. Trailer biasanya muncul duluan sebelum klik.
    # Kita tunggu agak lama.
    print("   - Menunggu buffer film asli (12 detik)...")
    await page.wait_for_timeout(12000)
    
    page.remove_listener("request", on_request)

    # 4. PILIH PEMENANG
    if found_streams:
        # Urutkan: Score Tertinggi -> URL Terpanjang
        found_streams.sort(key=lambda x: (x["score"], len(x["url"])), reverse=True)
        
        best = found_streams[0]
        
        # Final check: Pastikan bukan trailer yang lolos filter
        if "trailer" not in best["url"].lower():
            final_url = best["url"]
            print(f"     ✔ DAPAT STREAM: {final_url[:60]}...")
            return final_url
        else:
            print("     ✖ Hanya dapat trailer (dibuang).")
            
    else:
        print("     ✖ Tidak ada stream.")

    return None

# --- FUNGSI UTAMA ---

async def main():
    async with async_playwright() as p:
        print(f"⚙️ Launching Browser (Headless: {HEADLESS_MODE})...")
        browser = await p.chromium.launch(headless=HEADLESS_MODE)
        
        # Inject Headers & User Agent di level Context
        context = await browser.new_context(
            user_agent=ANDROID_USER_AGENT,
            extra_http_headers=CUSTOM_HEADERS,
            viewport={"width": 412, "height": 915},
            ignore_https_errors=True
        )
        
        page = await context.new_page()

        # 1. GRAB LIST MOVIE
        print("▶ Mengambil daftar film...")
        await page.goto(MOVIEBOX_URL, wait_until="domcontentloaded")
        await auto_scroll(page)
        
        elements = await page.query_selector_all("a[href*='/movie/'], a[href*='/detail']")
        movies = []
        seen = set()
        
        for el in elements:
            href = await el.get_attribute("href")
            if not href: continue
            full_url = MOVIEBOX_URL + href if href.startswith("/") else href
            
            if full_url in seen: continue
            
            # Ambil judul
            txt = await el.inner_text()
            if not txt.strip():
                try: txt = await el.query_selector(".title").inner_text()
                except: continue
            
            title = txt.replace("\n", " ").strip()
            if len(title) > 2:
                movies.append({"title": title, "url": full_url})
                seen.add(full_url)

        # 2. GRAB STREAM PER MOVIE
        results = []
        targets = movies[:TEST_LIMIT]
        print(f"\n⚙️ Memproses {len(targets)} film...\n")

        for i, m in enumerate(targets):
            print(f"[{i+1}/{len(targets)}] {m['title']}")
            stream = await get_stream_url(page, m["url"])
            if stream:
                m["stream"] = stream
                results.append(m)
            print("-" * 40)

        await browser.close()
    
    # 3. SAVE FILE
    if results:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(build_m3u(results))
        print(f"\n✔ SELESAI! Playlist: {OUTPUT_FILE}")
        print("  Info: Coba putar di OTT Navigator / Tivimate.")
        print("  Jika masih error, pastikan IP Address server sama dengan IP player.")
    else:
        print("\n✖ Gagal total (kosong).")

if __name__ == "__main__":
    asyncio.run(main())
