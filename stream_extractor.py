from playwright.sync_api import sync_playwright
import json, sys, time, os

# =========================
# KONFIGURASI INPUT
# =========================
# Menggunakan URL embed video sebagai default jika tidak ada argumen.
FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://cloud.hownetwork.xyz/video.php?id=lhe9oikcwiavnbsljh01mcmkkc0xhavsmdaeim4czmp3vqsimcswob0jkh96bgzqe096" 

OUTPUT_DIR = "output"
OUTPUT_FILE = f"{OUTPUT_DIR}/streams.json"

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
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/
