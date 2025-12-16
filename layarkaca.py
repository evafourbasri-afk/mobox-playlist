from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import time
import random

class LayarKacaProvider:
    def __init__(self):
        self.main_url = "https://lk21.de"
        self.series_url = "https://series.lk21.de"
        self.search_url = "https://search.lk21.party"

    def search(self, query):
        print(f"--- MENCARI: {query} ---")
        try:
            url = f"{self.search_url}/search.php?s={query}"
            
            # MENGGUNAKAN CURL_CFFI dengan impersonate Chrome
            # Timeout diperpanjang jadi 30 detik
            response = requests.get(
                url, 
                impersonate="chrome110", 
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Gagal akses! Status Code: {response.status_code}")
                return []

            try:
                data = response.json()
            except json.JSONDecodeError:
                print("Error: Website tidak mengembalikan JSON.")
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
    
    # Kita coba cari yang pasti ada
    results = provider.search("Avengers")
    
    if results:
        with open("playlist_result.json", "w") as f:
            json.dump(results, f, indent=4)
        print("Data berhasil disimpan ke playlist_result.json")
    else:
        print("Tidak ada data yang ditemukan.")
