# mobox.py v23 — Versi Final (Target Master Playlist & Tombol Watch Online)

import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- KONSTANTA ---
MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"
# Batas untuk testing (mengambil 10 film pertama agar cepat)
TEST_LIMIT = 10 

# --- FUNGSI UTILITY ---

async def auto_scroll(page):
    """Scroll perlahan dan cek sampai ketinggian halaman tidak bertambah lagi."""
    last_height = await page.evaluate("document.body.scrollHeight")
    print("   - Memulai Auto Scroll...")
    for i in range(30):
        # Scroll 2000px per iterasi
        await page.evaluate("window.scrollBy(0, 2000)") 
        await page.wait_for_timeout(1000)

        new_height = await page.evaluate("document.body.scrollHeight")
        
        if new_height <= last_height:
            print(f"   - Scroll selesai di iterasi {i+1}. Ketinggian stabil.")
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
    
    # Listener untuk menangkap request jaringan
    def on_request(req):
        u = req.url
        # Tangkap M3U8 (Master Playlist) dan MP4
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd", ".ts"]):
            # Filter iklan dan tracking
            if "adservice" not in u and "tracking" not in u and "google" not in u:
                 streams.append(u)

    page.on("request", on_request)

    # Navigasi
    await page.goto(url, wait_until="domcontentloaded") 
    print(f"   - URL Redirect: {page.url}")
    
    # Tunggu sebentar
    await page.wait_for_timeout(4000)

    try:
        # --- STRATEGI V23: KLIK TOMBOL 'WATCH ONLINE' (DARI SOURCE HTML) ---
        print("   - Mencoba klik tombol 'Watch Online'...")

        # Selector berdasarkan source code mobile yang Anda kirim
        watch_selectors = [
            '.watch-btn',               # Class spesifik dari source.txt
            'div[class*="watch-btn"]',  # Variasi class
            'h3:has-text("Watch Online")', # Teks di dalam tombol
            '.pc-watch-btn'             # Versi PC dari source code
        ]
        
        clicked = False
        for selector in watch_selectors:
            try:
                # Coba klik jika elemen ada
                if await page.locator(selector).count() > 0:
                    await page.click(selector, timeout=2000, force=True)
                    print(f"   - BERHASIL klik tombol: {selector}")
                    clicked = True
                    break
            except Exception:
                continue
        
        # Jika tombol watch online tidak ketemu, coba klik video player langsung
        if not clicked:
             print("   - Tombol Watch Online tidak ditemukan, klik player video...")
             try:
                 await page.click('video', timeout=1000, force=True)
             except:
                 pass
        
        # Beri waktu cukup lama agar Master Playlist dimuat
        await page.wait_for_timeout(12000) 

    except Exception as e:
        print(f"   - Error interaksi: {e}")
        pass

    page.remove_listener("request", on_request)

    # --- FILTERING STREAM (V23) ---
    # Prioritaskan .m3u8 dan hindari URL trailer (-ld.mp4)
    
    if streams:
        unique_streams = list(set(streams))
        
        # 1. Cari Master Playlist (.m3u8) - INI PRIORITAS UTAMA
        m3u8_lists = [s for s in unique_streams if ".m3u8" in s]
        if m3u8_lists:
            # Urutkan berdasarkan panjang URL (biasanya URL asli lebih panjang/kompleks)
            m3u8_lists.sort(key=len, reverse=True)
            print(f"     -> Ditemukan M3U8 Master Playlist: {m3u8_lists[0]}")
            return m3u8_lists[0]

        # 2. Jika tidak ada m3u8, cari MP4 yang BUKAN trailer
        # Trailer biasanya punya suffix "-ld.mp4" (Low Definition)
        mp4_lists = [s for s in unique_streams if ".mp4" in s]
        full_movies = [s for s in mp4_lists if "-ld.mp4" not in s and "trailer" not in s.lower()]
        
        if full_movies:
            full_movies.sort(key=len, reverse=True)
            print(f"     -> Ditemukan MP4 Film Penuh (Non-LD): {full_movies[0]}")
            return full_movies[0]

        # 3. Fallback: Jika hanya ada trailer, ambil itu daripada kosong
        if mp4_lists:
            mp4_lists.sort(key=len, reverse=True)
            print("     -> Hanya ditemukan trailer/LD stream.")
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
        # Gunakan User Agent Android (Penting!)
        ANDROID_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"
        
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=ANDROID_USER_AGENT)
        page = await context.new_page()

        movies = await get_movies(page)
        print(f"✔ Film ditemukan: {len(movies)}")
        
        results = []
        # Proses 10 film untuk testing
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
