# mobox.py v27 — JS Click & Keyboard Press (Final Attempt)

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
    
    # Listener request (Fokus M3U8/MP4)
    def on_request(req):
        u = req.url
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            # Pastikan bukan iklan/tracking
            if "adservice" not in u and "tracking" not in u and "google" not in u:
                 streams.append(u)

    page.on("request", on_request)

    await page.goto(url, wait_until="domcontentloaded") 
    print(f"   - URL Redirect: {page.url}")
    await page.wait_for_timeout(4000)

    try:
        # 1. Inject CSS (Overlay Killer)
        print("   - Inject CSS untuk menyembunyikan overlay/iklan...")
        # Tambahkan pointer-events: auto pada body untuk memastikan elemen di bawahnya dapat diklik
        await page.add_style_tag(content="""
            /* Target semua elemen pop-up/overlay/iklan dengan z-index tinggi */
            body > div[style*='z-index: 1000'] { 
                display: none !important; 
                visibility: hidden !important;
            }
            div[class*="dialog"], div[class*="modal"], div[class*="overlay"], 
            div[class*="popup"], .pc-scan-qr, .pc-download-content, 
            .h5-detail-banner, .footer-box { 
                display: none !important; 
                visibility: hidden !important;
                pointer-events: none !important;
                z-index: -9999 !important;
            }
            body { 
                pointer-events: auto !important;
            }
        """)
        
        # 2. Rangkaian Interaksi (JS Click & Keyboard Press)
        print("   - Memulai rangkaian interaksi: JS Click dan Keyboard Press...")
        
        # A. Coba klik Tombol 'film' menggunakan JavaScript (mengabaikan visibilitas DOM)
        js_click_success = await page.evaluate('''
            () => {
                const filmTab = document.querySelector('.type-item:has(span:text-is("film")), .source-tab:has(span:text-is("film"))');
                if (filmTab) {
                    filmTab.click(); // JS click
                    return true;
                }
                const watchBtn = document.querySelector('.pc-watch-btn, .watch-btn');
                if (watchBtn) {
                    watchBtn.click(); // Fallback ke Watch Online
                    return true;
                }
                return false;
            }
        ''')
        
        if js_click_success:
            print("     -> JS Click 'film' atau 'Watch Online' Berhasil dipicu.")
            # Setelah klik, coba fokus pada elemen tersebut dan tekan Enter (simulasi yang lebih humanis)
            try:
                 await page.locator('.type-item:has(span:text-is("film")), .source-tab:has(span:text-is("film")), .pc-watch-btn, .watch-btn').focus(timeout=3000)
                 await page.keyboard.press('Enter')
                 print("     -> Keyboard Enter Press Diterapkan.")
            except:
                 pass
        else:
             print("     -> Gagal menemukan target click melalui JS.")

        
        # C. Berikan jeda waktu lebih untuk memuat stream dari sumber alternatif
        await page.wait_for_timeout(15000) 

    except Exception as e:
        print(f"   - Error proses interaksi: {e}")
        pass

    page.remove_listener("request", on_request)

    # 3. Filtering Hasil yang Ditingkatkan (Mencari Full Stream)
    if streams:
        unique_streams = list(set(streams))
        
        # Prioritas 1: Stream M3U8 Kualitas Tinggi (bukan trailer dan non-ld)
        high_quality_m3u8 = [
            s for s in unique_streams 
            if "-ld.mp4" not in s and "trailer" not in s.lower() and s.endswith(".m3u8")
        ]
        if high_quality_m3u8:
            high_quality_m3u8.sort(key=len, reverse=True) 
            print(f"     -> Ditemukan M3U8 Kualitas Tinggi: {high_quality_m3u8[0]}")
            return high_quality_m3u8[0]

        # Prioritas 2: MP4 Kualitas Tinggi (bukan trailer dan non-ld)
        full_movies_mp4 = [
            s for s in unique_streams 
            if "-ld.mp4" not in s and "trailer" not in s.lower() and s.endswith(".mp4")
        ]
        if full_movies_mp4:
            full_movies_mp4.sort(key=len, reverse=True)
            print(f"     -> Ditemukan MP4 Full: {full_movies_mp4[0]}")
            return full_movies_mp4[0]
            
        # Prioritas 3: Semua M3U8 (Fallback)
        m3u8_fallback = [s for s in unique_streams if s.endswith(".m3u8")]
        if m3u8_fallback:
             m3u8_fallback.sort(key=len, reverse=True)
             print(f"     -> Fallback ke M3U8: {m3u8_fallback[0]}")
             return m3u8_fallback[0]

        # Prioritas 4: Semua Stream Tersisa (Termasuk LD/Trailer sebagai upaya terakhir)
        if unique_streams:
            unique_streams.sort(key=len, reverse=True)
            print(f"     -> Fallback ke Stream Apapun: {unique_streams[0]}")
            return unique_streams[0]

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
        # User Agent Android (Penting untuk struktur mobile)
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
