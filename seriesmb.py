import requests
import json
import time

BASE_URL = "https://moviebox.id/api"
OUTPUT_FILE = "series.m3u"
MAX_EPISODES = 100
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

def get_series_list(page=1):
    url = f"{BASE_URL}/series?page={page}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def get_series_detail(series_id):
    url = f"{BASE_URL}/series/{series_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def count_episodes(detail):
    total = 0
    for season in detail.get("seasons", []):
        total += len(season.get("episodes", []))
    return total

def build_m3u(series_detail, fh):
    title = series_detail.get("title", "Unknown")
    poster = series_detail.get("poster", "")
    for season in series_detail.get("seasons", []):
        sn = season.get("season_number", 1)
        for ep in season.get("episodes", []):
            ep_num = ep.get("episode_number", 1)
            stream = ep.get("stream_url")
            if not stream:
                continue
            fh.write(
                f'#EXTINF:-1 tvg-name="{title} S{sn}E{ep_num}" '
                f'tvg-logo="{poster}",{title} S{sn}E{ep_num}\n'
            )
            fh.write(stream + "\n")

def main():
    page = 1
    taken = 0
    skipped = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        while True:
            data = get_series_list(page)
            items = data.get("results", [])
            if not items:
                break

            for s in items:
                sid = s.get("id")
                if not sid:
                    continue

                detail = get_series_detail(sid)
                total_eps = count_episodes(detail)

                if total_eps > MAX_EPISODES:
                    skipped += 1
                    continue

                build_m3u(detail, f)
                taken += 1
                time.sleep(0.5)

            page += 1

    print(f"Done. Taken: {taken}, Skipped: {skipped}")

if __name__ == "__main__":
    main()
