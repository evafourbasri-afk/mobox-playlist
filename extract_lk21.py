from playwright.sync_api import sync_playwright
import json, sys, time

FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://tv7.lk21official.cc/little-amelie-character-rain-2025"

OUTPUT_FILE = "output/streams.json"

def main():
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
            if any(x in url for x in [".m3u8", ".mp4"]):
                if url not in streams:
                    print("[STREAM FOUND]", url)
                    streams.append(url)

        page.on("response", sniff)

        print("[OPEN]", FILM_URL)
        page.goto(FILM_URL, wait_until="domcontentloaded")

        time.sleep(10)

        try:
            page.mouse.click(300, 300)
            time.sleep(5)
        except:
            pass

        page.wait_for_timeout(10000)
        browser.close
