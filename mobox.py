# mobox.py v6 — Perbaikan Penemuan Film (Film ditemukan: 0)

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"

async def auto_scroll(page):
    """Scroll perlahan dan cek sampai ketinggian halaman tidak bertambah lagi."""
    last_height = await page.evaluate("document.body.scrollHeight")
    for i in range(30): # Coba scroll maksimal 30 kali
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000) # Tunggu 1 detik agar konten dimuat

        new_height = await page.evaluate("document.body.scrollHeight")
        
        # Jika ketinggian halaman tidak bertambah, asumsikan sudah mencapai akhir
        if new_height == last_height:
            print(f"   - Scroll selesai di iterasi {i+1}.")
            break
        
        last_height = new_height

async def get_movies(page):
    print("   - Mengunjungi halaman utama...")
    await page.goto(MOVIEBOX_URL, wait_until="load")
    
    # Tunggu sebentar setelah halaman dimuat untuk rendering awal
    await page.wait_for_timeout(3000)

    # Scroll supaya semua card film muncul
    print("   - Melakukan scroll untuk lazy-loading...")
    await auto_scroll(page)

    # --- PERBAIKAN SELECTOR ---
    # Coba beberapa selector umum untuk tautan film/konten yang menuju halaman detail
    # Gunakan selector yang lebih umum dari sekedar href
    cards = await page.query_selector_all(
        "a[href*='/movie/'], " +   # Selector lama
        "a[href*='/detail?id=']"   # Selector alternatif, sering dipakai di situs streaming
    )
    
    # Jika cards masih kosong, coba selector card container
    if not cards:
        print("   - Selector tautan langsung gagal. Mencoba card container...")
        # Coba selector yang menunjuk ke container/div film, lalu cari tautan di dalamnya
        cards = await page.query_selector_all("div.movie-card a, div.card-item a")
        
    movies = []
    
    # Gunakan set untuk menghindari duplikasi URL
    unique_urls = set() 
    
    for c in cards:
        href = await c.get_attribute("href")
        
        # Ambil teks terdekat yang mungkin merupakan judul
        title = (await c.inner_text() or "").strip()
        
        # Jika inner_text kosong, coba cari elemen judul di dalam card
        if len(title) < 2:
             title_element = await c.query_selector('h3, p.title, span.title')
             title = (await title_element.inner_text() if title_element else title).strip()

        # Konstruksi URL lengkap
        if href and not href.startswith(MOVIEBOX_URL):
            url = MOVIEBOX_URL + href
        else:
            url = href

        if url and len(title) > 2 and url not in unique_urls:
            movies.append({
                "title": title,
                "url": url
            })
            unique_urls.add(url)

    return movies

# ... (fungsi get_stream_url, build_m3u, dan main tetap sama) ...
