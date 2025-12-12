# mobox.py v28 — API Interception Strategy (Final)

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
    
    # Listener request (Fokus M3U8, MP4, dan API JSON yang mungkin memuat URL)
    def on_request(req):
        u = req.url
        
        # Prioritas 1: Langsung Ambil Stream Media
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            # Pastikan bukan iklan/tracking
            if "adservice" not in u and "tracking" not in u and "google" not in u:
                 streams.append(u)
        
        # Prioritas 2: Ambil API Call (Mungkin memuat data resolusi tinggi)
        # Mencari endpoint API umum yang sering membawa URL stream: /vod, /resource, /stream
        if "/vod" in u or "/resource" in u or "/stream" in u or "aoneroom" in u and ".json" in u:
            # Kita hanya menyimpan URL request API, nanti akan diolah setelah navigasi.
            streams.append(u) 

    page.on("request", on_request)

    await page.goto(url, wait_until="domcontentloaded") 
    print(f"   - URL Redirect: {page.url}")
    
    # Berikan waktu 15 detik agar semua AJAX/API call sempat dipicu dan terekam
    await page.wait_for_timeout(15000) 
    
    page.remove_listener("request", on_request)

    # 3. Filtering Hasil yang Ditingkatkan (Mencari Full Stream)
    if streams:
        unique_streams = list(set(streams))
        
        # **Langkah Baru:** Coba ambil Stream dari API Response (Jika ada)
        api_urls = [s for s in unique_streams if not any(ext in s for ext in [".m3u8", ".mp4", ".mpd"])]
        media_urls = [s for s in unique_streams if any(ext in s for ext in [".m3u8", ".mp4", ".mpd"])]
        
        for api_u in api_urls:
            if len(media_urls) >= 10: # Batasi overhead jika sudah banyak stream
                 break

            print(f"     -> Menganalisis API Response dari: {api_u}")
            try:
                # Ambil response dari API call
                api_response = await page.request.get(api_u)
                
                # Coba parse response sebagai JSON
                json_data = await api_response.json()
                
                # Cari URL stream di dalam JSON (pencarian rekursif sederhana)
                def search_for_stream(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if isinstance(v, str) and any(ext in v for ext in [".m3u8", ".mp4", ".mpd"]):
                                media_urls.append(v)
                            search_for_stream(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            search_for_stream(item)

                search_for_stream(json_data)
                
            except Exception as e:
                # Gagal parse JSON atau gagal request, lanjukan ke URL berikutnya
                pass

        # Ulangi filtering pada semua URL media yang ditemukan (termasuk dari API response)
        
        # Prioritas 1: Stream M3U8 Kualitas Tinggi (bukan trailer dan non-ld)
        high_quality_m3u8 = [
            s for s in media_urls 
            if "-ld.mp4" not in s and "trailer" not in s.lower() and s.endswith(".m3u8")
        ]
        if high_quality_m3u8:
            high_quality_m3u8.sort(key=len, reverse=True) 
            print(f"     -> Ditemukan M3U8 Kualitas Tinggi (Non-LD): {high_quality_m3u8[0]}")
            return high_quality_m3u8[0]

        # Prioritas 2: MP4 Kualitas Tinggi (bukan trailer dan non-ld)
        full_movies_mp4 = [
            s for s in media_urls 
            if "-ld.mp4" not in s and "trailer" not in s.lower() and s.endswith(".mp4")
        ]
        if full_movies_mp4:
            full_movies_mp4.sort(key=len, reverse=True)
            print(f"     -> Ditemukan MP4 Full (Non-LD): {full_movies_mp4[0]}")
            return full_movies_mp4[0]
            
        # Prioritas 3: Semua M3U8 (Fallback)
        m3u8_fallback = [s for s in media_urls if s.endswith(".m3u8")]
        if m3u8_fallback:
             m3u8_fallback.sort(key=len, reverse=True)
             print(f"     -> Fallback ke M3U8 (Termasuk LD): {m3u8_fallback[0]}")
             return m3u8_fallback[0]

        # Prioritas 4: Semua Stream Tersisa (Termasuk LD/Trailer sebagai upaya terakhir)
        if media_urls:
            media_urls.sort(key=len, reverse=True)
            print(f"     -> Fallback ke Stream Apapun (Termasuk LD): {media_urls[0]}")
            return media_urls[0]

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
