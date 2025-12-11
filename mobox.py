# mobox.py v5 — Penanganan Redirect ke Lok-lok.cc & Interaksi Baru

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"

async def auto_scroll(page):
    """Scroll perlahan supaya lazy-loading MovieBox muncul."""
    for _ in range(20):
        await page.evaluate("window.scrollBy(0, 2000)")
        await page.wait_for_timeout(500)


async def get_stream_url(page, url):
    streams = []

    # (1) Pindahkan listener request sebelum navigasi
    def on_request(req):
        u = req.url
        # Filter request streaming yang relevan (.m3u8, .mp4, .mpd)
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            # Filter iklan
            if "adservice" not in u and "tracking" not in u:
                 streams.append(u)

    page.on("request", on_request)

    await page.goto(url, wait_until="networkidle")
    print(f"   - URL saat ini: {page.url}") # Cek apakah sudah redirect

    # (2) Tambahkan waktu tunggu setelah redirect
    await page.wait_for_timeout(3000)

    try:
        # (3) Selector yang lebih spesifik untuk pemutar video
        # Di halaman video player, tombol play biasanya berbentuk ikon atau elemen besar.
        
        # Selector umum yang sering digunakan di player (mungkin di iframe atau di halaman utama)
        play_selectors = [
            'button.vjs-big-play-button',       # Video.js player
            'div.play-btn-large',              # Selector umum untuk tombol play besar
            '#playButton',                     # ID umum
            'div[role="button"]',              # Elemen yang dapat diklik
            'video',                           # Coba klik elemen video itu sendiri
            'div.video-player-container'       # Coba klik container player
        ]

        clicked = False
        for selector in play_selectors:
            try:
                # Menunggu elemen terlihat dan mencoba klik
                # Gunakan state="visible" agar Playwright menunggu elemen benar-benar siap
                await page.wait_for_selector(selector, state="visible", timeout=5000)
                await page.click(selector, force=True)
                print(f"   - Berhasil klik dengan selector: {selector}")
                clicked = True
                break
            except PlaywrightTimeoutError:
                continue # Coba selector berikutnya
            except Exception as e:
                # Tangani error klik lainnya, misalnya element not interactable
                print(f"   - Gagal klik {selector}: {e}")
                continue
        
        if not clicked:
            print("   - Tidak dapat mengklik tombol play utama.")

        # (4) Coba Interaksi dalam Iframe (Penting untuk Lok-lok)
        # Seringkali video player berada di dalam Iframe.
        print("   - Mencari Iframe...")
        for frame in page.main_frame().child_frames():
            try:
                # Coba klik tombol play di dalam Iframe
                await frame.click('button[aria-label*="Play"], video, .play-button', timeout=3000, force=True)
                print("   - Berhasil klik di dalam Iframe.")
                break
            except PlaywrightTimeoutError:
                pass 
            except Exception:
                pass

    except Exception as e:
        print(f"   - Error saat interaksi/klik: {e}")
        pass

    # (5) Beri waktu untuk menangkap request setelah interaksi
    await page.wait_for_timeout(7000) 

    # Hapus listener
    page.remove_listener("request", on_request)

    # (6) Kembalikan URL streaming pertama yang ditemukan
    return streams[0] if streams else None
# --- AKHIR PERBAIKAN get_stream_url ---

# ... (fungsi get_movies, build_m3u, dan main tetap sama) ...
# Pastikan Anda menggunakan kode lengkap yang menyertakan perbaikan ini.

async def get_movies(page):
    # Menggunakan kode Anda yang sudah ada, pastikan penemuan film berjalan baik
    # ... (kode get_movies Anda yang lama) ...
    await page.goto(MOVIEBOX_URL, wait_until="networkidle")
    await page.wait_for_timeout(3000)
    await auto_scroll(page)
    cards = await page.query_selector_all("a[href*='/movie/']")
    movies = []
    for c in cards:
        href = await c.get_attribute("href")
        title_element = await c.query_selector('h3, p.title, span.title')
        title = (await title_element.inner_text() if title_element else (await c.inner_text() or "")).strip()
        if href and len(title) > 2:
            movies.append({
                "title": title,
                "url": MOVIEBOX_URL + href
            })
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
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        movies = await get_movies(page)
        print(f"✔ Film ditemukan: {len(movies)}")
        results = []
        for m in movies[:10]:
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

asyncio.run(main())

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
        # Gunakan opsi slow_mo untuk debugging visual jika Anda menjalankannya secara lokal
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        movies = await get_movies(page)

        print(f"✔ Film ditemukan: {len(movies)}")

        results = []
        # Batasi jumlah film yang diambil untuk mempercepat proses debugging
        for m in movies[:10]: # Batasi ke 10 untuk uji coba
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

asyncio.run(main())
