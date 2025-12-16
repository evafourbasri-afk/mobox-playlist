import cloudscraper # Ganti requests dengan ini
from bs4 import BeautifulSoup
import json
import time

class LayarKacaProvider:
    def __init__(self):
        self.main_url = "https://lk21.de"
        self.series_url = "https://series.lk21.de"
        self.search_url = "https://search.lk21.party"
        
        # Membuat scraper yang bisa bypass Cloudflare
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

    def search(self, query):
        print(f"--- MENCARI: {query} ---")
        try:
            # Gunakan self.scraper, bukan requests
            url = f"{self.search_url}/search.php?s={query}"
            response = self.scraper.get(url)
            
            # Cek jika status bukan 200 OK
            if response.status_code != 200:
                print(f"Gagal akses! Status Code: {response.status_code}")
                # Print sedikit isi response untuk debug
                print(f"Response server: {response.text[:200]}") 
                return []

            try:
                data = response.json()
            except json.JSONDecodeError:
                print("Error: Website tidak mengembalikan JSON. Mungkin IP GitHub diblokir.")
                print(f"Isi response: {response.text[:500]}") # Lihat isinya apa (HTML error?)
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

# --- BAGIAN EKSEKUSI ---
if __name__ == "__main__":
    provider = LayarKacaProvider()
    
    # 1. Test Search (Coba cari film umum)
    results = provider.search("Avengers")
    
    # 2. Simpan hasil ke file (PENTING: Agar ada yang bisa di-commit ke GitHub)
    if results:
        with open("playlist_result.json", "w") as f:
            json.dump(results, f, indent=4)
        print("Data berhasil disimpan ke playlist_result.json")
    else:
        print("Tidak ada data yang ditemukan, tidak ada file yang dibuat.")
