import requests
from bs4 import BeautifulSoup
import re
import json

class LayarKacaProvider:
    def __init__(self):
        # [span_0](start_span)Konfigurasi URL utama diambil dari file Kotlin[span_0](end_span)
        self.main_url = "https://lk21.de"
        self.series_url = "https://series.lk21.de"
        self.search_url = "https://search.lk21.party"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fix_url(self, url):
        if url.startswith("//"):
            return "https:" + url
        return url

    def search(self, query):
        """
        Meniru fungsi search pada Kotlin yang mengambil JSON dari API search.lk21.party
        [span_1](start_span)Referensi logika:[span_1](end_span)
        """
        try:
            # [span_2](start_span)Request ke endpoint search sesuai baris[span_2](end_span)
            response = requests.get(f"{self.search_url}/search.php?s={query}", headers=self.headers)
            data = response.json()
            results = []

            # [span_3](start_span)Loop melalui array 'data'[span_3](end_span)
            for item in data.get("data", []):
                title = item.get("title")
                slug = item.get("slug")
                type_ = item.get("type")
                poster = "https://poster.lk21.party/wp-content/uploads/" + item.get("poster", "")

                # [span_4](start_span)Logika pemisahan URL berdasarkan tipe (movie vs series)[span_4](end_span)
                if type_ == "series":
                    url = f"{self.series_url}/{slug}"
                else:
                    url = f"{self.main_url}/{slug}"

                results.append({
                    "title": title,
                    "url": url,
                    "poster": poster,
                    "type": type_
                })
            return results
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def load(self, url):
        """
        Meniru fungsi load() untuk mengambil detail film/series.
        Mengambil title, poster, deskripsi, dan episode list.
        [span_5](start_span)Referensi logika:[span_5](end_span)
        """
        try:
            # [span_6](start_span)Mengambil konten halaman (Logika Jsoup di Kotlin diganti BeautifulSoup)[span_6](end_span)
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            # [span_7](start_span)Ekstraksi Metadata Dasar[span_7](end_span)
            title_tag = soup.select_one("div.movie-info h1")
            title = title_tag.text.strip() if title_tag else "Unknown"
            
            poster_tag = soup.select_one("meta[property='og:image']")
            poster = poster_tag['content'] if poster_tag else None
            
            desc_tag = soup.select_one("div.meta-info")
            description = desc_tag.text.strip() if desc_tag else ""

            # [span_8](start_span)Cek apakah ini Series atau Movie berdasarkan keberadaan elemen #season-data[span_8](end_span)
            season_script = soup.select_one("script#season-data")
            is_series = season_script is not None

            result = {
                "title": title,
                "poster": poster,
                "description": description,
                "type": "series" if is_series else "movie",
                "episodes": []
            }

            # [span_9](start_span)Logika parsing Episode jika Series[span_9](end_span)
            if is_series and season_script:
                json_data = json.loads(season_script.string)
                for season_key in json_data:
                    season_arr = json_data[season_key]
                    for ep in season_arr:
                        # [span_10](start_span)Membangun URL episode[span_10](end_span)
                        ep_slug = ep.get("slug")
                        ep_url = f"{self.main_url}/{ep_slug}" if ep_slug else url
                        
                        result["episodes"].append({
                            "season": ep.get("s"),
                            "episode": ep.get("episode_no"),
                            "url": ep_url,
                            "title": f"Episode {ep.get('episode_no')}"
                        })
            
            return result

        except Exception as e:
            print(f"Error loading details: {e}")
            return None

    def load_links(self, url):
        """
        Meniru fungsi loadLinks() untuk mengambil iframe player.
        [span_11](start_span)Referensi logika:[span_11](end_span)
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            
            # [span_12](start_span)Mencari list player di ul#player-list[span_12](end_span)
            player_list = soup.select("ul#player-list > li")
            
            for li in player_list:
                a_tag = li.select_one("a")
                if a_tag and a_tag.has_attr("href"):
                    provider_url = a_tag['href']
                    
                    # [span_13](start_span)Mengambil Iframe sebenarnya (mimic getIframe logic)[span_13](end_span)
                    iframe_url = self._get_iframe(provider_url)
                    if iframe_url:
                        links.append(iframe_url)
                        
            return links
        except Exception as e:
            print(f"Error extracting links: {e}")
            return []

    def _get_iframe(self, url):
        """
        [span_14](start_span)Meniru fungsi private getIframe()[span_14](end_span)
        """
        try:
            # [span_15](start_span)Memerlukan referer khusus sesuai kode asli[span_15](end_span)
            headers = self.headers.copy()
            headers["Referer"] = f"{self.series_url}/"
            
            res = requests.get(url, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            iframe = soup.select_one("div.embed-container iframe")
            if iframe:
                return iframe['src']
        except:
            return None
        return None

# --- CONTOH PENGGUNAAN ---
if __name__ == "__main__":
    provider = LayarKacaProvider()
    
    # 1. Test Search
    print("--- SEARCH: Aveng ---")
    search_res = provider.search("Aveng")
    print(json.dumps(search_res[:2], indent=2)) # Tampilkan 2 hasil pertama

    if search_res:
        first_movie = search_res[0]
        
        # 2. Test Load Details
        print(f"\n--- LOAD: {first_movie['title']} ---")
        details = provider.load(first_movie['url'])
        print(f"Type: {details['type']}")
        print(f"Plot: {details['description'][:100]}...")

        # 3. Test Extract Links
        print(f"\n--- LINKS: {first_movie['title']} ---")
        # Catatan: Ini akan mengambil link stream dari halaman tersebut
        links = provider.load_links(first_movie['url'])
        print(links)
