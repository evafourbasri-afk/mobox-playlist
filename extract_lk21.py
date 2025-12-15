from playwright.sync_api import sync_playwright
import json, sys, time, os

# =========================
# KONFIGURASI INPUT (SUDAH DISET KE URL EMBED YANG DIBERIKAN)
# =========================
# URL target utama adalah URL embed video yang benar
FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://cloud.hownetwork.xyz/video.php?id=lhe9oikcwiavnbsljh01mcmkkc0xhavsmdaeim4czmp3vqsimcswob0jkh96bgzqe096" 

OUTPUT_DIR = "output"
OUTPUT_FILE = f"{OUTPUT_DIR}/streams.json"

# List untuk menyimpan semua URL streaming yang valid
streams = []

# =========================
# FILTER JARINGAN
# =========================

# Kata kunci yang harus diblokir (biasanya iklan/pop-up)
BLOCKED_KEYWORDS = [
    "donasi", "stopjudi", "organicowner", "doubleclick",
    "ads", "popads", "adservice", "popunder"
]

# Kata kunci yang diizinkan (host video atau format streaming)
ALLOWED_HINTS = [
    "cloud.hownetwork.xyz", # Host yang diketahui menyajikan video
    ".m3u8",                # Format Playlist HLS
    ".mpd",                 # Format Playlist DASH
    ".ts",                  # Fragmen video HLS
    ".mp4"                  # File video langsung
]

# =========================
# FUNGSI SNIFFER
# =========================
def sniff(response):
    """
    Fungsi untuk memeriksa setiap respons jaringan yang diterima,
    mencari file streaming (.m3u8, .mpd, atau .mp4).
    """
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

        # Target Content-Types untuk playlist/file video utama
        is_video_content = (
            "application/vnd.apple.mpegurl" in content_type or # Tipe .m3u8
            "application/x-mpegurl" in content_type or         # Tipe lain .m3u8
            "application/dash+xml" in content_type or          # Tipe .mpd (DASH)
            "video/" in content_type                           # Tipe umum untuk video (mp4, flv, etc.)
        )
        
        # Prioritaskan URL yang berakhiran playlist atau file
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
    
    # Verifikasi target
    print("==============================================")
    print(f"TARGET URL: {FILM_URL}")
    print("Memastikan skrip menargetkan langsung URL embed...")
    print("==============================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, # Ubah ke False jika ingin melihat proses di browser
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        # Pasang sniffer ke event "response"
        page.on("response", sniff)

        print(f"[OPEN] {FILM_URL}")
        # Buka langsung URL embed video
        page.goto(FILM_URL, wait_until="domcontentloaded", timeout=60000)

        # =========================
        # TRIGGER PLAYER
        # =========================
        time.sleep(5) # Beri waktu elemen dimuat

        try:
            # Karena kita langsung membuka URL embed, klik di tengah seharusnya memicu play
            print("[ACTION] Mencoba Klik di tengah layar (400, 300) untuk Play")
            page.mouse.click(400, 300)
            time.sleep(5)
            
            # Klik kedua, seringkali untuk menutup pop-up/iklan overlay
            page.mouse.click(400, 300) 
            time.sleep(5)

        except Exception as e:
            print(f"[ERROR] Gagal melakukan simulasi klik: {e}")
            pass

        # Beri waktu tambahan untuk semua request streaming dimuat
        print("[ACTION] Menunggu request jaringan selesai (Total 10 detik)...")
        page.wait_for_timeout(10000)
        
        browser.close()

    # =========================
    # OUTPUT HASIL
    # =========================
    unique_streams = list(set(streams))
    
    # Utamakan URL playlist/file video (ini yang bisa di-play di VLC/MX Player)
    final_streams = [s for s in unique_streams if ".m3u8" in s or ".mpd" in s or ".mp4" in s]
    
    # Jika tidak ada playlist/file video, gunakan semua yang ditemukan
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
        print("\n**KESUKSESAN**")
        print("Tautan .m3u8/.mpd/.mp4 yang ditemukan sudah siap digunakan.")
        print("Gunakan tautan pertama di VLC/MX Player melalui 'Buka Aliran Jaringan...'")
    else:
        print("\n**KEGAGALAN**")
        print("Tidak ada tautan streaming yang valid ditemukan meskipun menargetkan URL embed.")
        print("Situs mungkin menggunakan *token* sekali pakai yang mencegah *stream* diputar di luar browser.")

if __name__ == "__main__":
    main()
