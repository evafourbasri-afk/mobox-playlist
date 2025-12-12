# mobox.py v17 — Versi Final (Targeting Tombol Download untuk Film Penuh)

import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- KONSTANTA ---
MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"
# Batas untuk testing (mengambil 10 film pertama)
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
    candidate_requests = [] 

    # Listener untuk menangkap request jaringan
    def on_request(req):
        u = req.url
        # 1. Tangkap URL media langsung
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd", ".ts"]):
            if "adservice" not in u and "tracking" not in u:
                 streams.append(u)
        
        # 2. Tangkap semua request yang mungkin berupa API Call
        if req.resource_type in ["xhr", "fetch"]:
             candidate_requests.append(req) 

    page.on("request", on_request)

    # Navigasi dengan wait_until yang lebih stabil
    await page.goto(url, wait_until="domcontentloaded") 
    print(f"   - URL Redirect: {page.url}")
    await page.wait_for_timeout(3000)

    try:
        # --- STRATEGI V17: TARGET TOMBOL DOWNLOAD ---
        print("   - Mencoba mengklik pemicu 'Download video'...")

        # Selector yang menargetkan tombol download (berdasarkan class/teks umum)
        download_selectors = [
            'button:has-text("Download")',
            'a:has-text("Download video")',
            'div[class*="download-btn"]', # Selector dari gambar inspect element
            'div[class*="download"] a',
        ]
        
        clicked_download = False
        for selector in download_selectors:
            try:
                # Menunggu tombol terlihat dan mengkliknya
                await page.wait_for_selector(selector, state="visible", timeout=3000)
                await page.click(selector, timeout=2000, force=True)
                print(f"   - BERHASIL mengklik tombol Download: {selector}")
                clicked_download = True
                break
            except Exception:
                continue
        
        if not clicked_download:
             print("   - Gagal mengklik tombol Download. Mencoba klik play default.")
             # Jika download gagal, coba klik play default sebagai fallback
             try:
                 await page.click('video', timeout=1000, force=True)
             except Exception:
                 pass
        
        # Beri waktu lebih lama setelah klik Download untuk request stream penuh terpicu
        await page.wait_for_timeout(15000) 

    except Exception as e:
        print(f"   - Error saat interaksi/klik: {e}")
        pass

    # --- ANALISIS RESPONS API (V17: Filtering Ketat) ---
    print(f"   - Memeriksa {len(candidate_requests)} request API/XHR...")
    
    streams_candidates = [] 
    
    for req in candidate_requests:
        try:
            response = await req.response()
            
            if response and response.status == 200:
                text = await response.text()
                
                if any(ext in text for ext in [".m3u8", ".mp4", ".mpd"]):
                    
                    found_urls = re.findall(r'(https?:\/\/[^\s"\']*\.(?:m3u8|mp4|mpd|ts)[^\s"\']*)', text)
                    
                    for fu in found_urls:
                        # Prioritas: URL tidak mengandung "thumb", "ad", atau "trailer"
                        if "thumb" not in fu and "ad" not in fu and "tracking" not in fu and "trailer" not in fu.lower():
                            streams_candidates.append(fu)
                            print(f"     -> Ditemukan KANDIDAT STREAM FILM PENUH di: {req.url}")

        except Exception:
            pass

    page.remove_listener("request", on_request)

    # Kembalikan URL streaming terbaik (terpanjang dan non-trailer)
    if streams_candidates:
        unique_streams = list(set(streams_candidates))
        
        # Pisahkan dan prioritaskan URL yang tidak mengandung kata 'trailer'
        full_movies = [s for s in unique_streams if "trailer" not in s.lower()]

        if full_movies:
            # Jika ada non-trailer, ambil yang terpanjang (kemungkinan besar film penuh)
            full_movies.sort(key=len, reverse=True)
            return full_movies[0]
        else:
            # Jika hanya trailer yang tersisa, ambil yang terpanjang (untuk konsistensi log)
            unique_streams.sort(key=len, reverse=True)
            print(f"     -> Hanya ditemukan trailer. Mengambil yang terpanjang.")
            return unique_streams[0]
    else:
        return None

# --- FUNGSI PENGAMBIL FILM (TERBUKTI BERHASIL) ---

async def get_movies(page):
    print("   - Mengunjungi halaman utama...")
    await page.goto(MOVIEBOX_URL, wait_until="load")
    
    try:
        await page.wait_for_selector("div.movie-list, div.row, main", state="visible", timeout=15000)
        print("   - Elemen utama halaman berhasil dimuat.")
    except PlaywrightTimeoutError:
        print("   - Peringatan: Elemen utama halaman tidak terdeteksi dalam 15s.")
        pass
    
    print("   - Melakukan scroll untuk lazy-loading...")
    await auto_scroll(page)

    cards = await page.query_selector_all(
        "a[href*='/movie/'], " + "a[href*='/detail?id='], " + "a:has(img)"                 
    )
    
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
        # User Agent Android untuk melewati blokir mobile-only
        ANDROID_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"
        
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=ANDROID_USER_AGENT 
        )
        page = await context.new_page()

        movies = await get_movies(page)

        print(f"✔ Film ditemukan: {len(movies)}")
        
        results = []
        # Menggunakan limit 10 film untuk testing
        print(f"⚙️ Memproses {min(len(movies), TEST_LIMIT)} film pertama untuk testing...")

        for m in movies[:TEST_LIMIT]:
            print("▶ Ambil stream:", m["title"])
            m["stream"] = await get_stream_url(page, m["url"]) 
            if m["stream"]:
                print(f"   - BERHASIL mendapatkan URL stream.")
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
