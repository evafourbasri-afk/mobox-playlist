import asyncio
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from pathlib import Path
import os
# import ast # Tidak diperlukan lagi karena parsing file dihilangkan

# --- KONFIGURASI DISEMATKAN LANGSUNG (HARDCODED) ---
BASE_URL = "https://new29.ngefilm.site"
ref = "https://new29.ngefilm.site"
# Daftar domain streaming. Sesuaikan jika player di situs berubah.
UNIVERSAL_DOMAINS = ['cdnplayer.net', 'streamgud.xyz', 'vidcloud.tv', 'gostrem.net']
# ---------------------------------------------------

OUTPUT_FILE = Path("ngefilm.m3u")
USER_DATA = "/tmp/ngefilm_profile"
USER_DATA_IFRAME = "/tmp/ngefilm_iframe_profile"
os.makedirs(USER_DATA, exist_ok=True)
os.makedirs(USER_DATA_IFRAME, exist_ok=True)

INDEX_URL = f"{BASE_URL}/page/"

def get_items():
    """Mengambil daftar film dari halaman indeks situs."""
    headers = {"User-Agent": "Mozilla/5.0"}
    all_results = []
    seen = set()
    
    # Mengambil dari halaman 8 hingga 14
    for page in range(8, 15):
        url = (
            f"{INDEX_URL}{page}/"
            "?s=&search=advanced&post_type=&index=&orderby=&genre="
            "&movieyear=&country=indonesia&quality="
        )
        print("🔎 Scraping:", url)
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
        except:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        articles = soup.select("div#gmr-main-load article")
        for art in articles:
            a = art.select_one("h2.entry-title a")
            if not a:
                continue
            detail = a["href"]
            slug = detail.rstrip("/").split("/")[-1]
            if slug in seen:
                continue
            seen.add(slug)
            title = a.get_text(strip=True)
            img = art.select_one("img")
            poster = img["src"] if img else ""
            all_results.append({
                "title": title,
                "slug": slug,
                "poster": poster,
                "detail": detail
            })
        print("➕ Total sementara:", len(all_results))

    print("\n🎉 TOTAL FINAL:", len(all_results), "\n")
    return all_results

def print_m3u(item, m3u8, out):
    """Menulis entri film ke dalam format M3U."""
    title = item["title"]
    poster = item["poster"]
    out.write(f'#EXTINF:-1 tvg-logo="{poster}" group-title="MOVIES FILM INDONESIA",{title}\n')
    out.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
    out.write(f"#EXTVLCOPT:http-referrer={ref}\n")
    out.write(f"{m3u8}\n\n")

async def process_item(item):
    """Menggunakan Playwright untuk menemukan tautan m3u8 dari iframe."""
    slug = item["slug"]
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            # Catatan: '/usr/bin/google-chrome' mungkin perlu disesuaikan 
            # jika Anda menjalankannya di lingkungan selain Linux/server
            executable_path="/usr/bin/google-chrome", 
            headless=True,
            args=[
                f"--user-data-dir={USER_DATA_IFRAME}",
                "--disable-gpu-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-infobars",
                "--ignore-certificate-errors",
                "--use-gl=swiftshader",
                "--no-sandbox",
                "--window-size=1280,720",
            ]
        )
        context = await browser.new_context()
        page = await context.new_page()

        # Cari iframe universal
        iframe = None
        for player in range(1, 6):
            urlp = f"{BASE_URL}/{slug}/?player={player}"
            try:
                await page.goto(urlp, timeout=0)
                await page.wait_for_timeout(3000)
            except:
                continue

            frames = await page.query_selector_all("iframe")
            for fr in frames:
                src = await fr.get_attribute("src")
                if src and any(d in src.lower() for d in UNIVERSAL_DOMAINS):
                    iframe = src
                    break
            if iframe:
                break

        if not iframe:
            print(f"❌ Skip {slug} — tidak ada iframe universal")
            await browser.close()
            return (item, None)

        # Extract m3u8 melalui network interception
        found = None
        async def intercept(route, request):
            nonlocal found
            url = request.url
            # Filter permintaan yang tidak relevan
            is_fake = url.endswith(".txt") or url.endswith(".woff") or url.endswith(".woff2")
            if ".m3u8" in url and not is_fake:
                if found is None:
                    found = url
                    print("🔥 STREAM:", url)
                # Lanjutkan request dengan header yang benar
                return await route.continue_(headers={"referer": iframe, "user-agent": "Mozilla/5.0"})
            return await route.continue_()

        await page.route("**/*", intercept)

        try:
            await page.goto(iframe, timeout=0)
        except:
            pass

        # Tunggu hingga m3u8 ditemukan (maksimal 15 detik)
        for _ in range(15):
            if found:
                break
            await asyncio.sleep(1)

        await browser.close()
        return (item, found)

async def main():
    """Fungsi utama untuk menjalankan scraper."""
    items = get_items()
    if not items:
        return

    # Batasi concurrency (operasi Playwright simultan)
    sem = asyncio.Semaphore(5)
    async def sem_task(item):
        async with sem:
            return await process_item(item)

    tasks = [sem_task(item) for item in items]
    
    # Jalankan semua tugas secara paralel
    results = await asyncio.gather(*tasks)

    # Menulis hasil ke file M3U
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")
        for item, m3u8 in results:
            if m3u8:
                print(f"✅ FOUND STREAM={m3u8} ({item['slug']})")
                print_m3u(item, m3u8, f)
            else:
                print(f"❌ NOT FOUND STREAM ({item['slug']})")

if __name__ == "__main__":
    asyncio.run(main())
