# mobox.py v3 — PERBAIKAN LISTENER & KLIK

import asyncio
from playwright.async_api import async_playwright

MOVIEBOX_URL = "https://moviebox.ph"
OUTPUT_FILE = "mobox.m3u"

async def auto_scroll(page):
    """Scroll perlahan supaya lazy-loading MovieBox muncul."""
    for _ in range(20):
        # Menggunakan evaluate untuk scroll agar lebih stabil
        await page.evaluate("window.scrollBy(0, 2000)")
        await page.wait_for_timeout(500)

async def get_stream_url(page, url):
    streams = []

    # (1) Pindahkan listener request sebelum navigasi!
    def on_request(req):
        u = req.url
        # Tambahkan filter yang lebih ketat jika perlu, 
        # tapi .m3u8, .mp4, .mpd biasanya sudah cukup
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd"]):
            # Filter iklan jika memungkinkan
            if "adservice" not in u and "tracking" not in u:
                 streams.append(u)

    page.on("request", on_request)

    await page.goto(url, wait_until="networkidle")
    
    # Beri waktu JS selesai render awal
    await page.wait_for_timeout(3000)

    try:
        # (2) Tambahkan Klik Play Button
        # Coba klik elemen yang berpotensi menjadi tombol play/player utama.
        # Anda perlu menyesuaikan selector ini berdasarkan struktur MovieBox terbaru.
        # Contoh umum: 'button', 'video' tag, atau selector berdasarkan class/id.
        # Saya menggunakan selector umum untuk video player.
        play_button_selector = 'button[aria-label="Play"], button.vjs-big-play-button, div.player-button'
        
        # Coba klik salah satu elemen
        await page.click(play_button_selector, timeout=5000)
        print(f"   - Mencoba klik tombol play untuk {url}")
        
    except Exception as e:
        # Jika tombol play tidak ditemukan/tidak perlu diklik, tidak masalah
        print("   - Tidak dapat mengklik play button atau sudah autoplay.")
        pass

    # (3) Beri waktu untuk menangkap request setelah klik
    await page.wait_for_timeout(5000)

    # Hapus listener setelah selesai agar tidak mengganggu navigasi berikutnya
    page.remove_listener("request", on_request)

    # (4) Kembalikan URL streaming pertama yang ditemukan
    # Cek apakah URL yang ditemukan benar-benar URL konten (bukan URL playlist pertama yang biasanya redirect ke server CDN)
    return streams[0] if streams else None
