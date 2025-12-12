# mobox.py v25 — Target Spesifik "lklk" / "Netflix" & Overlay Killer

import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- KONSTANTA ---
MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"
TEST_LIMIT = 10 

# --- FUNGSI UTILITY ---

async def auto_scroll(page):
    """Scroll perlahan dan cek sampai ketinggian halaman tidak bertambah lagi."""
    last_height = await page.evaluate("document.body.scrollHeight")
    print("   - Memulai Auto Scroll...")
    for i in range(30):
        await page.evaluate("window.scrollBy(0, 2000)") 
        await page.wait_for_timeout(1000)
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height <= last_height:
            break
        last_height = new_height

def build_m3u(items):
    out = ["#EXTM3U"]
    for x in items:
        if x.get("stream"):
            out.append(f'#EXTINF:-1 tvg-name="{x["title"]}", {x["title"]}')
            out.append(x["stream"])
    return "\n".join(out)

# --- FUNGSI PENGAMBIL STREAM ---

async def get_stream_url(page, url):
    streams = []
    
    # Listener request
    def on_request(req):
        u = req.url
        # Tangkap M3U8, MP4, MPD
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            if "adservice" not in u and "tracking" not in u and "google" not in u:
                 streams.append(u)

    page.on("request", on_request)

    await page.goto(url, wait_until="domcontentloaded") 
    print(f"   - URL Redirect: {page.url}")
    await page.wait_for_timeout(4000)

    try:
        # --- STRATEGI V25: HAPUS OVERLAY & KLIK TEKS SUMBER SPESIFIK ---
        
        # 1. Inject CSS untuk mematikan overlay (Iklan/QR)
        await page.add_style_tag(content="""
            .pc-scan-qr, .pc-download-content, .h5-detail-banner, 
            div[class*="dialog"], div[class*="overlay"], .footer-box { 
                display: none !important; z-index: -9999 !important; pointer-events: none !important;
            }
        """)

        print("   - Mencoba klik Tab Sumber Spesifik (lklk / Netflix)...")
        
        # 2. Klik berdasarkan TEKS yang ditemukan di source.txt
        # Urutan prioritas: lklk -> Netflix -> Plex -> Watch Online
        target_texts = ["lklk", "Netflix", "Plex", "Watch Online"]
        
        clicked = False
        for text in target_texts:
            try:
                # Cari elemen yang berisi teks tersebut
                # Gunakan locator yang presisi untuk teks di dalam span atau div
                locator = page.locator(f"span:text-is('{text}'), div:text-is('{text}'), h3:text-is('{text}')").first
                
                if await locator.is_visible():
                    print(f"   - Menemukan tombol sumber: {text}")
                    await locator.click(force=True)
                    print(f"   - BERHASIL KLIK: {text}")
                    clicked = True
                    break
            except Exception:
                continue
        
        if not clicked:
            print("   - Gagal klik teks spesifik. Mencoba klik tombol 'Watch' umum...")
            try:
                # Fallback ke class watch-btn
                await page.click('.watch-btn, .pc-watch-btn', timeout=2000, force=True)
            except:
                pass

        # Tunggu stream baru dimuat
        await page.wait_for_timeout(10000) 

    except Exception as e:
        print(f"   - Error interaksi: {e}")
        pass

    page.remove_listener("request", on_request)

    # --- FILTERING HASIL V25 ---
    if streams:
        unique_streams = list(set(streams))
        
        # 1. Cari M3U8 (Master Playlist)
        m3u8_lists = [s for s in unique_streams if ".m3u8" in s]
        if m3u8_lists:
            # Urutkan berdasarkan panjang URL
            m3u8_lists.sort(key=len, reverse=True)
            print(f"     -> Ditemukan M3U8: {m3u8_lists[0]}")
            return m3u8_lists[0]

        # 2. Cari MP4 (Non-Trailer)
        # Filter URL yang mengandung "-ld.mp4" (Low Definition) atau "trailer"
        mp4_lists = [s for s in unique_streams if ".mp4" in s]
        full_movies = [s for s in mp4_lists if "-ld.mp4" not in s and "trailer" not in s.lower()]
        
        if full_movies:
            full_movies.sort(key=len, reverse=True)
            print(f"     -> Ditemukan MP4 Full: {full_movies[0]}")
            return full_movies[0]
            
        # 3. Fallback (Trailer) jika tidak ada yang lain
        if mp4_lists:
            mp4_lists.sort(key=len, reverse=True)
            return mp4_lists[0]

    return None

# --- FUNGSI PENGAMBIL FILM ---

async def get_movies(page):
    print("   - Mengunjungi halaman utama...")
    await page.goto(MOVIEBOX_URL, wait_until="load")
    
    try:
        await page.wait_for_selector("div.movie-list, div.row, main", state="visible", timeout=15000)
    except PlaywrightTimeoutError:
        pass
    
    print("   - Melakukan scroll...")
    await auto_scroll(page)

    cards = await page.query_selector_all("a[href*='/movie/'], a[href*='/detail?id='], a:has(img)")
    
    movies = []
    unique_urls = set() 
    
    for c in cards:
        href = await c.get_attribute("href")
        if href and (href.startswith("/movie/") or "/detail" in href):
            title = (await c.inner_text() or "").strip()
            if len(title) < 2:
                 title_element = await c.query_selector('h3, p.title, span.title')
                 title = (await title_element.inner_text() if title_element else title).strip()

            url = MOVIEBOX_URL + href if href.startswith("/") else href

            if url and len(title) > 2 and url not in unique_urls:
                movies.append({"title": title, "url": url})
                unique_urls.add(url)

    return movies

# --- FUNGSI UTAMA ---

async def main():
    print("▶ Mengambil data MovieBox...")
    async with async_playwright() as p:
        # User Agent Android
        ANDROID_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"
        
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=ANDROID_USER_AGENT)
        page = await context.new_page()

        movies = await get_movies(page)
        print(f"✔ Film ditemukan: {len(movies)}")
        
        results = []
        print(f"⚙️ Memproses {min(len(movies), TEST_LIMIT)} film pertama...")

        for m in movies[:TEST_LIMIT]:
            print("▶ Ambil stream:", m["title"])
            m["stream"] = await get_stream_url(page, m["url"]) 
            if m["stream"]:
                print(f"   - BERHASIL: {m['stream']}")
            else:
                print("   - GAGAL mendapatkan URL stream.")
            results.append(m)

        await browser.close()
    
    playlist = build_m3u(results)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(playlist)

    print(f"\n✔ Selesai → {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
