from playwright.sync_api import sync_playwright
import json, sys, time, os

# =========================
# KONFIGURASI INPUT
# =========================
# Kita gunakan URL Halaman Induk sebagai default.
FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://tv7.lk21official.cc/little-amelie-character-rain-2025"

OUTPUT_DIR = "output"
OUTPUT_FILE = f"{OUTPUT_DIR}/streams.json"

streams = []

# =========================
# FILTER JARINGAN
# =========================
BLOCKED_KEYWORDS = [
    "donasi", "stopjudi", "organicowner", "doubleclick",
    "ads", "popads", "adservice", "popunder", "google"
]

ALLOWED_HINTS = [
    "cloud.hownetwork.xyz",
    ".m3u8",
    ".mpd",
    ".ts",
    ".mp4",
    "video"
]

# =========================
# FUNGSI SNIFFER
# =========================
def sniff(response):
    try:
        url = response.url.lower()

        # 1. Cek Blokir
        for b in BLOCKED_KEYWORDS:
            if b in url:
                return

        # 2. Cek apakah ini video/playlist
        # Kita melonggarkan filter URL agar menangkap lebih banyak potensi link
        content_type = response.headers.get("content-type", "").lower()
        
        is_playlist = ".m3u8" in url or ".mpd" in url
        is_video_mime = "application/vnd.apple.mpegurl" in content_type or "video/" in content_type
        
        # Logika tangkap:
        if is_playlist or is_video_mime:
            if url not in streams:
                if ".m3u8" in url:
                    print(f"[FOUND M3U8] {url}")
                else:
                    print(f"[FOUND MEDIA] {url}")
                streams.append(url)

    except Exception:
        pass

# =========================
# FUNGSI UTAMA
# =========================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("==============================================")
    print(f"TARGET: {FILM_URL}")
    print("==============================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--mute-audio"]
        )

        # User Agent Satu Baris (Aman dari Syntax Error)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = context.new_page()
        page.on("response", sniff)

        print(f"[ACTION] Membuka Halaman...")
        try:
            page.goto(FILM_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[WARNING] Loading halaman lambat: {e}")

        # ==========================================
        # STRATEGI KLIK AGRESIF (UNTUK MEMICU VIDEO)
        # ==========================================
        print("[ACTION] Tunggu 5 detik agar halaman stabil...")
        time.sleep(5)

        # Klik 1: Biasanya menutup iklan overlay atau memuat iframe
        print("[ACTION] Klik Tengah #1 (Pemicu Iframe)...")
        try:
            page.mouse.click(400, 300)
        except: pass
        time.sleep(5)

        # Klik 2: Biasanya untuk Play video
        print("[ACTION] Klik Tengah #2 (Play Video)...")
        try:
            page.mouse.click(400, 300)
        except: pass
        time.sleep(5)

        # Klik 3: Cadangan jika masih belum play
        print("[ACTION] Klik Tengah #3 (Cadangan)...")
        try:
            page.mouse.click(400, 300)
        except: pass
        
        # ==========================================
        # CARI IFRAME (OPSIONAL - HANYA LOGGING)
        # ==========================================
        # Kita tidak akan pindah halaman (goto) ke iframe karena itu bikin error redirect.
        # Kita cukup cari src-nya untuk info saja.
        print("[ACTION] Memindai Iframe di halaman...")
        iframes = page.frames
        for frame in iframes:
            try:
                src = frame.url
                if "http" in src and "google" not in src:
                    print(f"[INFO] Iframe terdeteksi: {src}")
                    # Kadang link video ada di src iframe itu sendiri
                    if ".m3u8" in src:
                        streams.append(src)
            except: pass

        print("[ACTION] Menunggu trafik jaringan selesai (15 detik)...")
        page.wait_for_timeout(15000)
        
        browser.close()

    # =========================
    # OUTPUT HASIL
    # =========================
    # Bersihkan duplikat
    unique_streams = list(set(streams))
    
    # Prioritaskan .m3u8
    final_streams = [s for s in unique_streams if ".m3u8" in s]
    if not final_streams:
        final_streams = unique_streams # Kalau gak ada m3u8, ambil apa aja yg ketemu

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

if __name__ == "__main__":
    main()
