from playwright.sync_api import sync_playwright
import json, sys, time, os
from urllib.parse import urlparse

# =========================
# KONFIGURASI
# =========================
# Gunakan URL film sebagai argumen baris perintah, atau gunakan default
FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://tv7.lk21official.cc/little-amelie-character-rain-2025"

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
    Fungsi untuk memeriksa setiap respons jaringan yang diterima.
    """
    url = response.url.lower()

    # 1. BLOKIR IKLAN
    for b in BLOCKED_KEYWORDS:
        if b in url:
            return

    # 2. FILTER BERDASARKAN URL
    # Hanya lanjutkan jika URL mengandung salah satu kata kunci yang diizinkan
    if not any(h in url for h in ALLOWED_HINTS):
        return

    # 3. FILTER BERDASARKAN CONTENT-TYPE
    try:
        content_type = response.headers.get("content-type", "").lower()

        # Target Content-Types:
        # - Playlist HLS/DASH
        # - Video (MP4, TS)
        if (
            "application/vnd.apple.mpegurl" in content_type or # Tipe umum untuk .m3u8
            "application/x-mpegurl" in content_type or         # Tipe lain untuk .m3u8
            "application/dash+xml" in content_type or          # Tipe untuk .mpd (DASH)
            "video/" in content_type or                        # Tipe umum untuk video (video/mp4, video/x-flv, dll.)
            ".m3u8" in url or ".mpd" in url                    # Pastikan URL playlist tertangkap
        ):
            if url not in streams:
                # Pastikan URL adalah URL lengkap dan bukan hanya fragmen (misalnya file .ts)
                # Umumnya yang bisa diputar di VLC adalah URL playlist (.m3u8/.mpd)
                if ".m3u8" in url or ".mpd" in url or ".mp4" in url:
                    print(f"[FILM STREAM FOUND (Playlist/File)] {url}")
                    streams.append(url)
                else:
                    print(f"[FILM STREAM FOUND (Fragmen)] {url}")
                    # Jika itu fragmen (.ts), tetap simpan jika kita tidak menemukan playlist
                    streams.append(url) 

    except Exception:
        # Abaikan error jika gagal membaca header
        pass

# =========================
# FUNGSI UTAMA
# =========================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Inisialisasi Playwright
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
            # Gunakan User Agent desktop agar server menyajikan versi desktop
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        # Pasang sniffer ke event "response"
        page.on("response", sniff)

        print("[OPEN]", FILM_URL)
        page.goto(FILM_URL, wait_until="domcontentloaded")

        # =========================
        # TRIGGER PLAYER
        # =========================
        # Beri waktu elemen-elemen dimuat (termasuk iframe video)
        time.sleep(5) 

        try:
            # Klik di tengah layar untuk memulai pemutar (diperlukan untuk memicu .m3u8)
            print("[ACTION] Mencoba Klik di tengah layar (400, 300) untuk Play")
            page.mouse.click(400, 300)
            time.sleep(3)
            
            # Klik kedua, seringkali untuk menutup pop-up/iklan overlay
            page.mouse.click(400, 300) 
            time.sleep(5)

        except Exception as e:
            print(f"[ERROR] Gagal melakukan simulasi klik: {e}")
            pass

        # Beri waktu tambahan untuk semua request streaming dimuat (total sekitar 13 detik)
        print("[ACTION] Menunggu request jaringan selesai...")
        page.wait_for_timeout(5000)
        
        browser.close()

    # =========================
    # OUTPUT HASIL
    # =========================
    # Filter hanya menyimpan URL unik (walaupun sudah dilakukan di dalam sniff, untuk jaga-jaga)
    unique_streams = list(set(streams))
    
    # Utamakan URL playlist (.m3u8 atau .mpd) untuk hasil terbaik
    preferred_streams = [s for s in unique_streams if ".m3u8" in s or ".mpd" in s or ".mp4" in s]
    
    if not preferred_streams and unique_streams:
         # Jika tidak ada playlist, gunakan semua yang ditemukan
        final_streams = unique_streams
    elif preferred_streams:
        # Jika ada playlist, utamakan itu
        final_streams = preferred_streams
    else:
        # Jika tidak ada yang ditemukan
        final_streams = []

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
        print("\n**INSTRUKSI LANJUTAN**")
        print("Tautan .m3u8/.mpd yang ditemukan (jika ada) dapat disalin dan dimasukkan ke 'Buka Aliran Jaringan...' di VLC/MX Player.")
    else:
        print("\n**INSTRUKSI LANJUTAN**")
        print("Tidak ada tautan streaming yang ditemukan. Coba jalankan skrip lagi atau sesuaikan koordinat klik.")

if __name__ == "__main__":
    main()
