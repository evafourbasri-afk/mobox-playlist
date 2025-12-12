# mobox.py v7 — Pengecekan API Response

# ... (import dan fungsi auto_scroll, build_m3u tetap sama) ...

async def get_stream_url(page, url):
    streams = []
    candidate_requests = [] # Daftar untuk menampung request XHR/Fetch

    def on_request(req):
        u = req.url
        # 1. Tangkap URL media langsung
        if any(ext in u for ext in [".m3u8", ".mp4", ".mpd", ".ts"]):
            if "adservice" not in u and "tracking" not in u:
                 streams.append(u)
        
        # 2. Tangkap semua request yang mungkin berupa API Call
        if req.resource_type in ["xhr", "fetch"]:
             candidate_requests.append(req) 

    page.on("request", on_request)

    await page.goto(url, wait_until="networkidle")
    print(f"   - URL Redirect: {page.url}")
    await page.wait_for_timeout(3000)

    try:
        # Lakukan interaksi untuk memicu pemuatan
        print("   - Mencoba klik pemutar video...")
        
        play_selectors = [
            'button[aria-label*="Play"]', 
            'div.vjs-big-play-button',       
            '#playButton',                     
            'video',
            'div[role="button"]',
            'div.player-wrapper' # Selector umum untuk container player
        ]
        
        clicked = False
        for selector in play_selectors:
            try:
                await page.click(selector, timeout=2000, force=True)
                clicked = True
                break
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue

        # Coba klik di Iframe
        for frame in page.main_frame().child_frames():
            try:
                await frame.click('video, button[aria-label*="Play"]', timeout=1000, force=True)
                clicked = True
                break
            except Exception:
                pass
        
        if clicked:
            print("   - Interaksi berhasil memicu request.")
        else:
            print("   - Gagal interaksi, mengandalkan autoplay.")


    except Exception as e:
        print(f"   - Error saat interaksi/klik: {e}")
        pass

    # Beri waktu untuk request selesai
    await page.wait_for_timeout(7000) 

    # --- PERBAIKAN 2: Memeriksa Respons API ---
    print(f"   - Memeriksa {len(candidate_requests)} request API/XHR...")
    for req in candidate_requests:
        try:
            # Ambil respons dari request yang berhasil
            response = await req.response()
            if response and response.status == 200:
                text = await response.text()
                
                # Cari string media di dalam body respons
                if ".m3u8" in text or ".mp4" in text:
                    # Ini sangat mungkin adalah URL streaming yang valid,
                    # meskipun kita perlu parsing JSON untuk mendapatkannya
                    print(f"   - Ditemukan string media di respons dari: {req.url}")
                    
                    # Coba parsing
                    # Asumsi: URL streaming adalah salah satu yang paling panjang
                    import re
                    # Mencari pola http://...m3u8 atau http://...mp4
                    found_urls = re.findall(r'(https?:\/\/[^\s"\']*\.(?:m3u8|mp4|mpd|ts)[^\s"\']*)', text)
                    
                    for fu in found_urls:
                        # Pastikan URLnya tidak berupa thumbnail kecil atau iklan
                        if "thumb" not in fu and "ad" not in fu and "tracking" not in fu:
                            streams.append(fu)

        except Exception as e:
            # Gagal mengambil respons (mis. request dibatalkan)
            pass

    page.remove_listener("request", on_request)

    # Kembalikan URL streaming pertama yang valid
    if streams:
        # Hapus duplikat dan ambil yang pertama
        unique_streams = list(set(streams))
        # Mengambil yang paling mungkin valid (misalnya yang paling panjang)
        unique_streams.sort(key=len, reverse=True) 
        return unique_streams[0]
    else:
        return None

# ... (pastikan Anda mengganti fungsi get_stream_url di mobox.py Anda dengan kode di atas) ...
