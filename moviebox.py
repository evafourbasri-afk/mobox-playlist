# moviebox.py
# Python >= 3.10
# pip install moviebox-api

import asyncio
import json
from moviebox_api import MovieBox

OUTPUT_JSON = "moviebox.json"
OUTPUT_M3U = "moviebox.m3u"

async def main():
    mb = MovieBox()

    # contoh pencarian
    keyword = "Avatar"
    results = await mb.search(keyword)

    playlist = []
    m3u = ["#EXTM3U"]

    for item in results[:5]:  # ambil 5 saja
        detail = await mb.get_detail(item.id)
        stream = await mb.get_stream(detail)

        data = {
            "title": detail.title,
            "year": detail.year,
            "type": detail.type,
            "stream_url": stream.url,
            "quality": stream.quality
        }

        playlist.append(data)

        m3u.append(
            f'#EXTINF:-1 group-title="MovieBox",{detail.title} ({detail.year})'
        )
        m3u.append(stream.url)

    # simpan JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(playlist, f, indent=2)

    # simpan M3U
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("✔ moviebox.json & moviebox.m3u berhasil dibuat")

if __name__ == "__main__":
    asyncio.run(main())
