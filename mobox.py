# mobox.py v4 — Perbaikan Selector & Interaksi

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"

async def auto_scroll(page):
    """Scroll perlahan supaya lazy-loading MovieBox muncul."""
    for _ in range(20):
        await page.evaluate("window.scrollBy(0, 2000)")
        await page.wait_for_timeout(500)

# --- FUNGSI KRITIS YANG DIPERBAIKI ---
async def get_stream_url(page, url):
    streams = []

    # (1) Pindahkan listener request sebelum navigasi
    def on_request(req):
        u = req.url
        # Filter request streaming yang relevan
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            # Filter iklan
            if "adservice" not in u and "tracking" not in u:
                 streams.append(u)

    page.on("request", on_request)

    await page.goto(url, wait_until="networkidle")
    await page.wait_for_timeout(3000)

    try:
        # (2) Coba Interaksi Utama
        # Selector lebih generik untuk pemutar video atau tombol play
        play_selectors = [
            'button[aria-label*="Play"]',     # Tombol play yang jelas
            'div.vjs-control-bar button',    # Pemutar video.js
            '#player',                       # Elemen player berdasarkan ID umum
            'video'                          # Elemen video itu sendiri
        ]

        clicked = False
        for selector in play_selectors:
            try:
                # Menunggu elemen terlihat dan mencoba klik
                await page.click(selector, timeout=5000, force=True)
                print(f"   - Berhasil klik dengan selector: {selector}")
                clicked = True
                break
            except PlaywrightTimeoutError:
                continue # Coba selector berikutnya
        
        if not clicked:
            print("   - Tidak dapat mengklik tombol play utama.")


        # (3) Coba Interaksi dalam Iframe (Penting!)
        # Periksa Iframe dan coba klik di dalamnya jika ada
        print("   - Mencari Iframe...")
        for frame in page.main_frame().child_frames():
            try:
                # Coba klik tombol play di dalam Iframe
                await frame.click('button[aria-label*="Play"], video', timeout=3000, force=True)
                print("   - Berhasil klik di dalam Iframe.")
                break
            except PlaywrightTimeoutError:
                pass # Lanjut ke Iframe berikutnya atau abaikan

    except Exception as e:
        print(f"   - Error saat interaksi: {e}")
        pass

    # (4) Beri waktu untuk menangkap request setelah interaksi
    await page.wait_for_timeout(7000) # Perpanjang waktu tunggu

    # Hapus listener
    page.remove_listener("request", on_request)

    # (5) Kembalikan URL streaming pertama yang ditemukan
    return streams[0] if streams else None
# --- AKHIR PERBAIKAN ---

async def get_movies(page):
    # (sisanya sama dengan kode Anda, memastikan penemuan film berfungsi)
    await page.goto(MOVIEBOX_URL, wait_until="networkidle")
    await page.wait_for_timeout(3000)

    # Scroll supaya semua card film muncul
    await auto_scroll(page)

    # Menggunakan selector yang lebih spesifik jika diperlukan
    cards = await page.query_selector_all("a[href*='/movie/']")

    movies = []
    for c in cards:
        # Mengambil title dari teks di sekitar link
        title_element = await c.query_selector('h3, p.title, span.title') # Coba beberapa struktur judul umum
        title = (await title_element.inner_text() if title_element else (await c.inner_text() or "")).strip()
        
        href = await c.get_attribute("href")
        
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
