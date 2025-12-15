from playwright.sync_api import sync_playwright
import json, sys, time, os

FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://tv7.lk21official.cc/little-amelie-character-rain-2025"

OUTPUT_DIR = "output"
OUTPUT_FILE = f"{OUTPUT_DIR}/streams.json"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    streams = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        )

        page = context.new_page()

        def sniff(response):
            url = response.url.lower()
            if ".m3u8" in url or ".mp4" in url:
                if url not in streams:
                    print("[FOUND]", url)
                    streams.append(url)

        page.on("response", sniff)

        print("[OPEN]", FILM_URL)
        page.goto(FILM_URL, wait_until="domcontentloaded")

        time.sleep(8)

        try:
            page.mouse.click(400, 300)
            time.sleep(5)
        except:
            pass

        page.wait_for_timeout(12000)
        browser.close()

    # ⬇️ WAJIB TULIS FILE WALAU KOSONG
    result = {
        "source": FILM_URL,
        "count": len(streams),
        "streams": streams,
        "status": "ok" if streams else "no_stream_found"
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("\n=== SAVED ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
