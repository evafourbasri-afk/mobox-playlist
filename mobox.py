# mobox.py v9 — Perbaikan NameError dan Logika Scraping Agresif

import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"

async def auto_scroll(page):
    """Scroll perlahan dan cek sampai ketinggian halaman tidak bertambah lagi."""
    last_height = await page.evaluate("document.body.scrollHeight")
    for i in range(30):
        await page.evaluate("window.scrollBy(0, 2000)")
        await page.wait_for_timeout(1000)

        new_height = await page.evaluate("document.body.scrollHeight")
        
        if new_height <= last_height:
            print(f"   - Scroll selesai di iterasi {i+1}. Ketinggian stabil.")
            break
        
        last_height = new_height

# --- DEFINISI FUNGSI get_stream_url (KRITIS) ---
async def get_stream_url(page, url):
    streams = []
    candidate_requests = [] # Daftar untuk menampung request XHR/Fetch

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

    await page.goto(url, wait_until="networkidle")
    print(f"   - URL Redirect: {page.url}")
    await page.wait_for_timeout(3000)

    try:
        # Lakukan interaksi untuk memicu pemuatan
        print("   - Mencoba klik pemutar video...")
        
        play_selectors = [
            'button[aria-label*="Play"]', 
            'div.vjs-big-play-button',       
            '#playButton',                     
            'video',
            'div[role="button"]',
            'div.player-wrapper'
        ]
        
        clicked = False
        for selector in play_selectors:
            try:
                await page.click(selector, timeout=2000, force=True)
                clicked = True
                break
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue

        # Coba klik di Iframe
        for frame in page.main_frame().child_frames():
            try:
                await frame.click('video, button[aria-label*="Play"]', timeout=1000, force=True)
                clicked = True
                break
            except Exception:
                pass
        
        if clicked:
            print("   - Interaksi berhasil memicu request.")
        else:
            print("   - Gagal interaksi, mengandalkan autoplay.")


    except Exception as e:
        print(f"   - Error saat interaksi/klik: {e}")
        pass

    # Beri waktu untuk request selesai
    await page.wait_for_timeout(7000) 

    # --- Memeriksa Respons API ---
    print(f"   - Memeriksa {len(candidate_requests)} request API/XHR...")
    for req in candidate_requests:
        try:
            response = await req.response()
            if response and response.status == 200:
                text = await response.text()
                
                if ".m3u8" in text or ".mp4" in text:
                    print(f"   - Ditemukan string media di respons dari: {req.url}")
                    
                    # Mencari pola URL streaming lengkap
                    found_urls = re.findall(r'(https?:\/\/[^\s"\']*\.(?:m3u8|mp4|mpd|ts)[^\s"\']*)', text)
                    
                    for fu in found_urls:
                        if "thumb" not in fu and "ad" not in fu and "tracking" not in fu:
                            streams.append(fu)

        except Exception as e:
            pass

    page.remove_listener("request", on_request)

    # Kembalikan URL streaming terbaik
    if streams:
        unique_streams = list(set(streams))
        unique_streams.sort(key=len, reverse=True) 
        return unique_streams[0]
    else:
        return None
# --- AKHIR DEFINISI get_stream_url ---


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

    # Selector Catch-all yang berhasil menemukan 374 film sebelumnya
    cards = await page.query_selector_all(
        "a[href*='/movie/'], " +     
        "a[href*='/detail?id='], " + 
        "a:has(img)"                 
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

def build_m3u(items):
    out = ["#EXTM3U"]
    for x in items:
        if x.get("stream"):
            out.append(f'#EXTINF:-1 tvg-name="{x["title"]}", {x["title"]}')
            out.append(x["stream"])
    return "\n".join(out)

async def main():
    print("▶ Mengambil data MovieBox...")
    async with async_playwright() as p:
        # Menggunakan user-agent agar tampak seperti browser normal
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        movies = await get_movies(page)

        print(f"✔ Film ditemukan: {len(movies)}")
        
        results = []
        # Batasi ke 10 film untuk proses debugging cepat
        for m in movies[:10]:
            print("▶ Ambil stream:", m["title"])
            # BARIS INI KINI BENAR KARENA get_stream_url SUDAH DIDEFINISIKAN SEBELUMNYA
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
