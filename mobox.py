# mobox.py v30 — Final "Click-to-Play" Strategy

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- KONSTANTA & CONFIG ---
MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"
TEST_LIMIT = 50  # Jumlah film yang akan discan (Set angka besar jika ingin semua)

# User Agent Android (Sangat penting agar server memberikan tampilan mobile & player HTML5)
ANDROID_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"

# --- FUNGSI UTILITY ---

async def auto_scroll(page):
    """Scroll ke bawah untuk memuat Lazy Load image/content."""
    print("   - Melakukan scroll halaman...")
    last_height = await page.evaluate("document.body.scrollHeight")
    no_change_count = 0
    
    for _ in range(15): # Coba scroll 15 kali
        await page.evaluate("window.scrollBy(0, 1500)") 
        await page.wait_for_timeout(800)
        new_height = await page.evaluate("document.body.scrollHeight")
        
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 2: # Berhenti jika 2x tidak ada perubahan
                break
        else:
            no_change_count = 0
        last_height = new_height

def build_m3u(items):
    out = ["#EXTM3U"]
    for x in items:
        if x.get("stream"):
            out.append(f'#EXTINF:-1 group-title="MovieBox", {x["title"]}')
            out.append(x["stream"])
    return "\n".join(out)

# --- FUNGSI PENGAMBIL STREAM (CORE LOGIC) ---

async def get_stream_url(page, url):
    found_streams = []
    
    # 1. SETUP LISTENER NETWORK
    # Kita akan memberi skor pada setiap URL yang tertangkap.
    # Skor 100 = Target Utama (Bocoran)
    # Skor 50  = Stream Biasa
    # Skor 10  = Trailer / Low Quality
    
    def on_request(req):
        u = req.url
        
        # Filter Sampah (Iklan/Analytics)
        if any(bad in u for bad in ["google", "facebook", "analytics", "adservice", "doubleclick"]):
            return

        score = 0
        is_target = False

        # RULE A: Target "Bocoran" (Prioritas Tertinggi)
        if ("hakunaymatata" in u or "/resource/" in u or "bcdnxw" in u) and ".mp4" in u:
            score = 100
            is_target = True
        
        # RULE B: Stream Standar (.m3u8 / .mp4 / .mpd)
        elif any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            score = 50
            # Kurangi skor jika trailer
            if "trailer" in u.lower():
                score = 10
            # Kurangi skor jika Low Definition
            if "-ld.mp4" in u:
                score = 20

        if score > 0:
            found_streams.append({"url": u, "score": score})
            if is_target:
                print(f"     ★ JACKPOT DETECTED: {u[:50]}...")

    # Pasang listener
    page.on("request", on_request)

    print(f"   - Membuka: {url}")
    try:
        # Buka halaman
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except Exception:
        print("     ! Warning: Page load timeout (lanjut mencoba grab stream)")

    # 2. STRATEGI KLIK (TRIGGER PLAYER)
    # Link asli biasanya baru muncul setelah tombol play ditekan
    print("   - Mencoba memicu Player (Click Strategy)...")
    await page.wait_for_timeout(2000) # Tunggu sebentar agar elemen render

    try:
        # Daftar selector tombol play yang mungkin muncul di mobile
        play_buttons = [
            "div.play-button", 
            "div.icon-play", 
            ".vjs-big-play-button", 
            "div.mobile-play", 
            "div#player-container",
            "video"
        ]
        
        clicked = False
        # Cara 1: Coba klik elemen spesifik
        for selector in play_buttons:
            if await page.locator(selector).first.is_visible():
                await page.locator(selector).first.click(force=True)
                print(f"     -> Klik elemen: {selector}")
                clicked = True
                break
        
        # Cara 2: Blind Click (Klik tengah layar - efektif untuk mobile player)
        if not clicked:
            print("     -> Melakukan Blind Click (Tengah Layar)...")
            vp = page.viewport_size
            if vp:
                await page.mouse.click(vp['width'] / 2, vp['height'] / 3)

    except Exception as e:
        print(f"     ! Gagal interaksi klik: {e}")

    # 3. TUNGGU RESPONSE
    # Beri waktu agak lama (12 detik) karena request video butuh buffering awal
    await page.wait_for_timeout(12000)
    
    # Lepas listener
    page.remove_listener("request", on_request)

    # 4. PROSES HASIL
    if found_streams:
        # Urutkan: Skor Tertinggi -> URL Terpanjang (biasanya link asli parameternya panjang)
        found_streams.sort(key=lambda x: (x["score"], len(x["url"])), reverse=True)
        
        best = found_streams[0]
        
        # Cek jika yang terbaik masih trailer (skor rendah), coba cari lagi
        if best["score"] <= 20 and len(found_streams) > 1:
            print(f"     -> Opsi terbaik tampaknya trailer ({best['url'][:30]}...), cek opsi lain.")
        
        final_url = best["url"]
        print(f"     ✔ DAPAT: {final_url[:60]}...")
        return final_url

    return None

# --- FUNGSI PENGAMBIL LIST FILM ---

async def get_movies(page):
    print("▶ Mengakses halaman utama MovieBox...")
    await page.goto(MOVIEBOX_URL, wait_until="domcontentloaded")
    
    # Tunggu sebentar loading awal
    try:
        await page.wait_for_selector("a[href*='/movie/'], a[href*='/detail']", timeout=10000)
    except:
        pass

    await auto_scroll(page)

    # Selektor CSS untuk mengambil link film
    # Kita ambil semua link yang mengarah ke /movie/ atau /detail
    elements = await page.query_selector_all("a[href*='/movie/'], a[href*='/detail']")
    
    movies = []
    seen_urls = set()

    for el in elements:
        href = await el.get_attribute("href")
        if not href: continue
        
        # Normalisasi URL
        full_url = MOVIEBOX_URL + href if href.startswith("/") else href
        
        if full_url in seen_urls: continue
        
        # Ambil Judul
        title = (await el.inner_text()).strip()
        # Jika text kosong, coba cari di elemen anak (h3, span, dll)
        if not title:
            title_el = await el.query_selector(".title, h3, span.name")
            if title_el:
                title = (await title_el.inner_text()).strip()
        
        # Cleanup judul
        title = title.replace("\n", " ").strip()
        
        if title and len(title) > 2:
            movies.append({"title": title, "url": full_url})
            seen_urls.add(full_url)

    print(f"✔ Total film ditemukan di halaman depan: {len(movies)}")
    return movies

# --- MAIN ---

async def main():
    async with async_playwright() as p:
        print("⚙️ Meluncurkan Browser (Headless)...")
        browser = await p.chromium.launch(headless=True)
        
        # Context dengan User Agent Android
        context = await browser.new_context(
            user_agent=ANDROID_USER_AGENT,
            viewport={"width": 412, "height": 915} # Resolusi HP umum
        )
        page = await context.new_page()

        # 1. Ambil List Film
        movies = await get_movies(page)
        
        results = []
        # Batasi jumlah test sesuai konstanta
        target_movies = movies[:TEST_LIMIT]
        
        print(f"\n⚙️ Memulai proses grabbing untuk {len(target_movies)} film...\n")

        for i, m in enumerate(target_movies):
            print(f"[{i+1}/{len(target_movies)}] {m['title']}")
            stream = await get_stream_url(page, m["url"])
            
            if stream:
                m["stream"] = stream
                results.append(m)
            else:
                print("     ✖ GAGAL / Tidak ada stream.")
            
            print("-" * 40)

        await browser.close()
    
    # Simpan ke M3U
    if results:
        content = build_m3u(results)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✔ SUKSES! Playlist disimpan di: {OUTPUT_FILE}")
        print(f"✔ Total Channel: {len(results)}")
    else:
        print("\n✖ Gagal membuat playlist (tidak ada stream ditemukan).")

if __name__ == "__main__":
    asyncio.run(main())
