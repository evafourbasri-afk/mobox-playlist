# moviebox.py
# Python >= 3.10
# pip install moviebox-api

import asyncio
import json
from moviebox_api import MovieAuto

OUTPUT_JSON = "moviebox.json"
OUTPUT_M3U = "moviebox.m3u"

async def main():
    auto = MovieAuto()

    keyword = "Avatar"

    # auto.run() = search + select + get stream
    movie_file, subtitle_file = await auto.run(keyword)

    data = {
        "title": movie_file.title,
        "year": movie_file.year,
        "quality": movie_file.quality,
        "stream_url": movie_file.stream_url,
    }

    # JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump([data], f, indent=2)

    # M3U
    m3u = [
        "#EXTM3U",
        f'#EXTINF:-1 group-title="MovieBox",{movie_file.title} ({movie_file.year})',
        movie_file.stream_url
    ]

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("✔ moviebox.json & moviebox.m3u berhasil dibuat")

if __name__ == "__main__":
    asyncio.run(main())
