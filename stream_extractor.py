from playwright.sync_api import sync_playwright
import json, sys, time, os

# =========================
# KONFIGURASI INPUT
# =========================
# URL embed video yang menjadi target utama
FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://cloud.hownetwork.xyz/video.php?id=lhe9oikcwiavnbsljh01mcmkkc0xhavsmdaeim4czmp3vqsimcswob0jkh96bgzqe096" 

OUTPUT_DIR = "output"
OUTPUT_FILE = f"{OUTPUT_DIR}/streams.json"

# URL halaman utama film yang akan disuntikkan sebagai Referer (Penting untuk mengatasi redirect)
REFERER_URL = "https://tv7.lk21official.cc/little-amelie-character-rain-2025"

# User-Agent yang sama dengan yang dikonfigurasi di browser context
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

streams = []

# =========================
# FILTER JARINGAN
# =========================

BLOCKED_KEYWORDS = [
    "donasi", "stopjudi", "organicowner", "doubleclick",
    "ads", "popads", "adservice", "popunder"
]

ALLOWED_HINTS = [
    "cloud.hownetwork.xyz", 
    ".m3u8",                
    ".mpd",                 
    ".ts",                  
    ".mp4"                  
]

# =========================
# FUNGSI SNIFFER
# =========================
def sniff(response):
    url = response.url.lower()

    # 1. BLOKIR IKLAN
    for b in BLOCKED_KEYWORDS:
        if b in url:
            return

    # 2. FILTER BERDASARKAN URL
    if not any(h in url for h in ALLOWED_HINTS):
        return

    # 3. FILTER BERDASARKAN CONTENT-TYPE
    try:
        content_type = response.headers.get("content-type", "").lower()

        is_video_content = (
            "application/vnd.apple.mpegurl" in content_type or 
            "application/x-mpegurl" in content_type or         
            "application/dash+xml" in content_type or          
            "video/" in content_type                           
        )
        
        is_preferred_url = ".m3u8" in url or ".mpd" in url or ".mp4" in url

        if is_video_content or is_preferred_url:
            if url not in streams:
                if is_preferred_url:
                    print(f"[FILM STREAM FOUND (Playlist/File)] {url}")
                else:
                    print(f"[FILM STREAM FOUND (Fragmen/Umum)] {url}")
                    
                streams.append(url)

    except Exception:
        pass

# =========================
# FUNGSI UTAMA
# =========================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("==============================================")
    print(f"TARGET URL: {FILM_URL}")
    print(f"REFERER URL: {REFERER_URL}")
    print("==============================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(
            user_agent=DEFAULT_USER_AGENT
        )

        page = context.new_page()
        page.on("response", sniff)

        # Aksi Kritis: Menetapkan Referer dan User-Agent sebagai Extra HTTP Headers
        # Ini memastikan header dikirim dengan benar, mengatasi ERR_TOO_MANY_REDIRECTS
        page.set_extra_http_headers({
            "Referer": REFERER_URL,
            "User-Agent": DEFAULT_USER_AGENT
        })
        
        print(f"[ACTION] Navigasi ke {FILM_URL} dengan Extra Headers...")
        
        # page.goto TANPA argumen 'referer' karena sudah diatur di page.set_extra_http_headers
        page.goto(
            FILM_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        # =========================
        # TRIGGER PLAYER
        # =========================
        time.sleep(5) 

        try:
            print("[ACTION] Mencoba Klik di tengah layar (400, 300) untuk Play")
            page.mouse.click(400, 300)
            time.sleep(5)
            
            print("[ACTION] Klik kedua (untuk menutup pop-up/lanjutkan play)")
            page.mouse.click(400, 300) 
            time.sleep(5)

        except Exception as e:
            print(f"[ERROR] Gagal melakukan simulasi klik: {e}")
            pass

        print("[ACTION] Menunggu request jaringan selesai (Total 10 detik)...")
        page.wait_for_timeout(10000)
        
        browser.close()

    # =========================
    # OUTPUT HASIL
    # =========================
    unique_streams = list(set(streams))
    final_streams = [s for s in unique_streams if ".m3u8" in s or ".mpd" in s or ".mp4" in s]
    
    if not final_streams and unique_streams:
        final_streams = unique_streams
    
    result = {
        "source": FILM_URL,
        "count": len(final_streams),
        "streams": final_streams,
        "status": "ok" if final_streams else "no_stream_found"
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("\n=== RESULT ===")
    print(json.dumps(result, indent=2))
    
    if final_streams:
        print("\n::SUCCESS:: Tautan .m3u8/.mpd/.mp4 berhasil ditemukan. Siap untuk diputar di VLC/MX Player.")
    else:
        print("\n::FAILURE:: Tidak ada tautan streaming yang valid ditemukan. Ini mungkin menunjukkan bahwa situs memerlukan token sesi atau JavaScript lanjutan.")

if __name__ == "__main__":
    main()
