from playwright.sync_api import sync_playwright
import json, sys, time, os
import re 

# =========================
# KONFIGURASI INPUT
# =========================
# PENTING: TARGET UTAMA ADALAH HALAMAN FILM INDUK (Bukan URL embed)
FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://tv7.lk21official.cc/little-amelie-character-rain-2025" 

OUTPUT_DIR = "output"
OUTPUT_FILE = f"{OUTPUT_DIR}/streams.json"

# URL yang kita harapkan ada di dalam iframe src
IFRAME_HINT = "cloud.hownetwork.xyz"

streams = []
extracted_iframe_url = None 

# =========================
# FILTER JARINGAN
# =========================
BLOCKED_KEYWORDS = [
    "donasi", "stopjudi", "organicowner", "doubleclick",
    "ads", "popads", "adservice", "popunder"
]

ALLOWED_HINTS = [
    IFRAME_HINT,
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

    for b in BLOCKED_KEYWORDS:
        if b in url:
            return

    if not any(h in url for h in ALLOWED_HINTS):
        return

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
    global extracted_iframe_url
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("==============================================")
    print(f"TARGET UTAMA (HALAMAN FILM): {FILM_URL}")
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = context.new_page()
        page.on("response", sniff)

        print(f"[ACTION] Membuka Halaman Film Induk: {FILM_URL}")
        page.goto(FILM_URL, wait_until="domcontentloaded", timeout=60000) # Memuat halaman utama

        # =========================
        # 1. TEMUKAN IFRAME DAN AMBIL URL-NYA
        # =========================
        try:
            print("[ACTION] Mencari iframe embed video...")
            # Menunggu iframe dengan src yang mengandung hint
            iframe_selector = f'iframe[src*="{IFRAME_HINT}"]'
            iframe_element = page.wait_for_selector(iframe_selector, timeout=15000)
            
            if iframe_element:
                extracted_iframe_url = iframe_element.get_attribute('src')
                print(f"[SUCCESS] Iframe ditemukan: {extracted_iframe_url}")
                
            else:
                 print("[FAILURE] Iframe tidak ditemukan dalam 15 detik.")
                 browser.close()
                 return 

        except Exception as e:
            print(f"[ERROR] Gagal menemukan iframe: {e}")
            browser.close()
            return
            
        # =========================
        # 2. NAVIGASI KE IFRAME YANG DITEMUKAN
        # =========================
        if extracted_iframe_url:
            print(f"[ACTION] Menavigasi ke URL Iframe yang diekstrak...")
            # Playwright akan menggunakan Referer yang benar (halaman induk)
            page.goto(extracted_iframe_url, wait_until="domcontentloaded", timeout=60000)
            
            # =========================
            # 3. TRIGGER PLAYER DI DALAM IFRAME
            # =========================
            time.sleep(5) 

            try:
                print("[ACTION] Mencoba Klik di tengah iframe (400, 300) untuk Play...")
                page.mouse.click(400, 300)
                time.sleep(5)
                
                print("[ACTION] Klik kedua untuk memastikan pemutaran.")
                page.mouse.click(400, 300) 
                time.sleep(5)

            except Exception as e:
                print(f"[ERROR] Gagal melakukan simulasi klik di iframe: {e}")
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
        "source": extracted_iframe_url if extracted_iframe_url else FILM_URL,
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
        print("\n::FAILURE:: Tidak ada tautan streaming yang valid ditemukan.")

if __name__ == "__main__":
    main()
