from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import time

# --- KONFIGURASI PROXY DI SINI ---
# Kosongkan jika main di laptop sendiri.
# Isi jika main di GitHub Actions (Wajib cari Proxy yang aktif).
# Contoh: "http://username:password@192.168.1.1:8080"
MY_PROXY = "" 

class LayarKacaProvider:
    def __init__(self):
        self.main_url = "https://lk21.de"
        self.series_url = "https://series.lk21.de"
        self.search_url = "https://search.lk21.party"

    def search(self, query):
        print(f"--- MENCARI: {query} ---")
        try:
            url = f"{self.search_url}/search.php?s={query}"
            
            # Setting Proxy
            proxies = {"http": MY_PROXY, "https": MY_PROXY} if MY_PROXY else None

            # Request dengan impersonate Chrome
            response = requests.get(
                url, 
                impersonate="chrome110", 
                timeout=30,
                proxies=proxies
            )
            
            if response.status_code != 200:
                print(f"Gagal akses! Status Code: {response.status_code}")
                # Jika 522/403, berarti IP atau Proxy diblokir
                return []

            try:
                data = response.json()
            except json.JSONDecodeError:
                print("Error: Website tidak mengembalikan JSON (Mungkin kena Captcha).")
                return []

            results = []
            for item in data.get("data", []):
                title = item.get("title")
                slug = item.get("slug")
                type_ = item.get("type")
                poster = "https://poster.lk21.party/wp-content/uploads/" + item.get("poster", "")

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
            
            print(f"Ditemukan {len(results)} hasil.")
            return results

        except Exception as e:
            print(f"Error sistem: {e}")
            return []

if __name__ == "__main__":
    provider = LayarKacaProvider()
    results = provider.search("Avengers")
    
    if results:
        with open("playlist_result.json", "w") as f:
            json.dump(results, f, indent=4)
        print("Data berhasil disimpan.")
    else:
        print("Tidak ada data ditemukan.")
