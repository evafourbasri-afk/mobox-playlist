# mobox.py v8 — Perbaikan Film ditemukan: 0 (Robustness dan Wait)

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"

async def auto_scroll(page):
    """Scroll perlahan dan cek sampai ketinggian halaman tidak bertambah lagi."""
    last_height = await page.evaluate("document.body.scrollHeight")
    for i in range(30): # Coba scroll maksimal 30 kali
        await page.evaluate("window.scrollBy(0, 2000)") # Scroll 2000px per iterasi
        await page.wait_for_timeout(1000) # Tunggu 1 detik

        new_height = await page.evaluate("document.body.scrollHeight")
        
        if new_height <= last_height:
            print(f"   - Scroll selesai di iterasi {i+1}. Ketinggian stabil.")
            break
        
        last_height = new_height

async def get_movies(page):
    print("   - Mengunjungi halaman utama...")
    # Navigasi ke halaman
    await page.goto(MOVIEBOX_URL, wait_until="load")
    
    try:
        # Taktik 1: Tunggu elemen container film utama terlihat
        # Ganti dengan selector yang Anda duga sebagai container film (misal: grid/list view)
        await page.wait_for_selector("div.movie-list, div.row, main", state="visible", timeout=15000)
        print("   - Elemen utama halaman berhasil dimuat.")
    except PlaywrightTimeoutError:
        print("   - Peringatan: Elemen utama halaman tidak terdeteksi dalam 15s.")
        pass
    
    # Scroll supaya semua card film muncul
    print("   - Melakukan scroll untuk lazy-loading...")
    await auto_scroll(page)

    # Taktik 2: Selector Catch-all
    # Mencari tautan di mana saja yang mengarah ke halaman detail film
    cards = await page.query_selector_all(
        "a[href*='/movie/'], " +     # Selector lama
        "a[href*='/detail?id='], " + # Selector alternatif
        "a:has(img)"                 # Tautan yang mengandung gambar (kemungkinan besar film)
    )
    
    movies = []
    unique_urls = set() 
    
    for c in cards:
        href = await c.get_attribute("href")
        # Hanya ambil link yang menuju halaman detail film (bukan link navigasi lain)
        if href and (href.startswith("/movie/") or "/detail" in href):
            
            title = (await c.inner_text() or "").strip()
            if len(title) < 2:
                 # Coba cari elemen judul di dalam card
                 title_element = await c.query_selector('h3, p.title, span.title')
                 title = (await title_element.inner_text() if title_element else title).strip()

            url = MOVIEBOX_URL + href if href.startswith("/") else href

            if url and len(title) > 2 and url not in unique_urls:
                movies.append({"title": title, "url": url})
                unique_urls.add(url)

    return movies

# ... (Fungsi get_stream_url, build_m3u tetap sama dengan V7) ...

async def main():
    print("▶ Mengambil data MovieBox...")
    async with async_playwright() as p:
        # Taktik 3: Gunakan user-agent agar tampak seperti browser normal
        browser = await p.chromium.launch(headless=True)
        # Menambahkan user-agent saat membuat context baru
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        movies = await get_movies(page)

        print(f"✔ Film ditemukan: {len(movies)}")
        
        # ... (proses mengambil stream dan menutup browser) ...
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
