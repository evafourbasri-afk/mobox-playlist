# mobox.py v31 — Header Injection & Cookie Strategy

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- KONSTANTA & CONFIG ---
MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"
TEST_LIMIT = 50 

# Header Khusus (KUNCI AGAR VIDEO BISA DIPUTAR)
CUSTOM_HEADERS = {
    "Referer": "https://fmoviesunblocked.net/",
    "Origin": "https://fmoviesunblocked.net/"
}

# User Agent Android
ANDROID_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"

# --- FUNGSI UTILITY ---

async def auto_scroll(page):
    """Scroll ke bawah untuk memuat Lazy Load image/content."""
    print("   - Melakukan scroll halaman...")
    last_height = await page.evaluate("document.body.scrollHeight")
    no_change_count = 0
    
    for _ in range(15): 
        await page.evaluate("window.scrollBy(0, 1500)") 
        await page.wait_for_timeout(800)
        new_height = await page.evaluate("document.body.scrollHeight")
        
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 2: break
        else:
            no_change_count = 0
        last_height = new_height

def build_m3u(items):
    """Membuat file M3U dengan format Headers untuk IPTV Player (Tivimate/OTT Nav)."""
    out = ["#EXTM3U"]
    
    # String header untuk ditambahkan ke belakang URL (Syntax umum IPTV)
    # Contoh: http://url.mp4|Referer=...&Origin=...
    header_suffix = f"|Referer={CUSTOM_HEADERS['Referer']}&Origin={CUSTOM_HEADERS['Origin']}&User-Agent={ANDROID_USER_AGENT}"
    
    for x in items:
        if x.get("stream"):
            out.append(f'#EXTINF:-1 group-title="MovieBox", {x["title"]}')
            # Tempelkan headers di belakang URL agar player bisa memutarnya
            final_url = x["stream"] + header_suffix
            out.append(final_url)
    return "\n".join(out)

# --- FUNGSI PENGAMBIL STREAM (CORE LOGIC) ---

async def get_stream_url(page, url):
    found_streams = []
    
    # Keyword target sesuai bocoran
    TARGET_DOMAINS = ["hakunaymatata", "bcdnxw"]
    
    def on_request(req):
        u = req.url
        
        # Filter Sampah
        if any(bad in u for bad in ["google", "facebook", "analytics", "adservice", "doubleclick"]):
            return

        score = 0
        is_target = False

        # RULE A: Target Utama (Bocoran + Ekstensi Video)
        if any(t in u for t in TARGET_DOMAINS) and any(ext in u for ext in [".mp4", ".m3u8"]):
            score = 100
            is_target = True
        
        # RULE B: Stream Standar
        elif any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            score = 50
            if "trailer" in u.lower(): score = 10
            if "-ld.mp4" in u: score = 20

        if score > 0:
            found_streams.append({"url": u, "score": score})
            if is_target:
                print(f"     ★ JACKPOT DETECTED: {u[:60]}...")

    # Pasang listener
    page.on("request", on_request)

    print(f"   - Membuka: {url}")
    try:
        # Kita set timeout agak panjang
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
    except Exception:
        print("     ! Warning: Page load timeout (lanjut mencoba grab stream)")

    # STRATEGI KLIK (TRIGGER PLAYER)
    print("   - Mencoba memicu Player (Click Strategy)...")
    await page.wait_for_timeout(2000) 

    try:
        # Selector tombol play umum
        play_buttons = [
            "div.play-button", "div.icon-play", ".vjs-big-play-button", 
            "div.mobile-play", "div#player-container", "video", 
            "div.cover", "img[src*='play']"
        ]
        
        clicked = False
        # 1. Coba klik elemen visual
        for selector in play_buttons:
            if await page.locator(selector).first.is_visible():
                await page.locator(selector).first.click(force=True)
                print(f"     -> Klik elemen: {selector}")
                clicked = True
                break
        
        # 2. Blind Click (Tengah Layar)
        if not clicked:
            print("     -> Melakukan Blind Click (Tengah Layar)...")
            vp = page.viewport_size
            if vp:
                await page.mouse.click(vp['width'] / 2, vp['height'] / 3)

    except Exception as e:
        print(f"     ! Gagal interaksi klik: {e}")

    # Tunggu buffering (Headers sudah diinject di context, jadi request harusnya sukses)
    await page.wait_for_timeout(10000)
    
    page.remove_listener("request", on_request)

    if found_streams:
        # Urutkan: Score Tertinggi -> URL Terpanjang
        found_streams.sort(key=lambda x: (x["score"], len(x["url"])), reverse=True)
        
        best = found_streams[0]
        if best["score"] <= 20 and len(found_streams) > 1:
            print(f"     -> Opsi terbaik tampaknya trailer, cek opsi lain.")
        
        print(f"     ✔ DAPAT: {best['url'][:80]}...")
        return best["url"]

    return None

# --- FUNGSI PENGAMBIL LIST FILM ---

async def get_movies(page):
    print("▶ Mengakses halaman utama...")
    try:
        await page.goto(MOVIEBOX_URL, wait_until="domcontentloaded", timeout=30000)
    except:
        pass
    
    await auto_scroll(page)

    elements = await page.query_selector_all("a[href*='/movie/'], a[href*='/detail']")
    movies = []
    seen_urls = set()

    for el in elements:
        href = await el.get_attribute("href")
        if not href: continue
        
        full_url = MOVIEBOX_URL + href if href.startswith("/") else href
        if full_url in seen_urls: continue
        
        title = (await el.inner_text()).strip()
        if not title:
            title_el = await el.query_selector(".title, h3, span.name")
            if title_el: title = (await title_el.inner_text()).strip()
        
        title = title.replace("\n", " ").strip()
        
        if title and len(title) > 2:
            movies.append({"title": title, "url": full_url})
            seen_urls.add(full_url)

    print(f"✔ Total film ditemukan: {len(movies)}")
    return movies

# --- MAIN ---

async def main():
    async with async_playwright() as p:
        print("⚙️ Meluncurkan Browser dengan CUSTOM HEADERS...")
        browser = await p.chromium.launch(headless=True)
        
        # --- DISINI KITA INJECT HEADERS DAN USER AGENT ---
        # Semua request (termasuk AJAX video) akan membawa header ini otomatis
        context = await browser.new_context(
            user_agent=ANDROID_USER_AGENT,
            extra_http_headers=CUSTOM_HEADERS, 
            viewport={"width": 412, "height": 915}
        )
        page = await context.new_page()

        movies = await get_movies(page)
        results = []
        target_movies = movies[:TEST_LIMIT]
        
        print(f"\n⚙️ Memulai proses grabbing untuk {len(target_movies)} film...\n")

        for i, m in enumerate(target_movies):
            print(f"[{i+1}/{len(target_movies)}] {m['title']}")
            
            # Reset header di context jika perlu, tapi biasanya global context sudah cukup.
            # Kita gunakan page yang sama atau buat page baru per film jika mau lebih fresh
            # Untuk efisiensi kita pakai page yang sama.
            
            stream = await get_stream_url(page, m["url"])
            if stream:
                m["stream"] = stream
                results.append(m)
            else:
                print("     ✖ GAGAL / Tidak ada stream.")
            print("-" * 40)

        await browser.close()
    
    if results:
        content = build_m3u(results)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✔ SUKSES! Playlist disimpan di: {OUTPUT_FILE}")
        print("  Catatan: Link di dalam M3U sudah menyertakan pipe (|) headers")
        print("  untuk Referer & Origin agar bisa diputar di Tivimate/VLC.")
    else:
        print("\n✖ Gagal membuat playlist.")

if __name__ == "__main__":
    asyncio.run(main())
