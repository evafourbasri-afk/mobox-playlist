from playwright.sync_api import sync_playwright
import json
import sys
import time

# ======================
# INPUT
# ======================
FILM_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://tv7.lk21official.cc/little-amelie-character-rain-2025"

OUTPUT_JSON = "streams.json"

# ======================
# MAIN
# ======================
def main():
    found_streams = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
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

        # ======================
        # NETWORK SNIFFER
        # ======================
        def handle_response(response):
            url = response.url.lower()

            if any(x in url for x in [
                ".m3u8",
                ".mp4",
                "index.m3u8",
                "master.m3u8"
            ]):
                if url not in found_streams:
                    print("[FOUND STREAM]", url)
                    found_streams.append(url)

        page.on("response", handle_response)

        print("[OPEN]", FILM_URL)
        page.goto(FILM_URL, wait_until="domcontentloaded")

        # Tunggu iframe & JS
        time.sleep(10)

        # Klik body (bypass click-to-play)
        try:
            page.mouse.click(200, 200)
            time.sleep(5)
        except:
            pass

        # Tunggu network idle
        page.wait_for_timeout(10000)

        browser.close()

    # ======================
    # OUTPUT
    # ======================
    result = {
        "source": FILM_URL,
        "total_streams": len(found_streams),
        "streams": found_streams
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("\n===== RESULT =====")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
