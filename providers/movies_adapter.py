# providers/movies_adapter.py
# Adapter aman (tanpa aiohttp dependency)

def get_movies(limit=5):
    """
    GANTI isi list ini dengan OUTPUT dari temanmu
    (bisa copy manual atau dump JSON 1x)
    """
    data = [
        {
            "title": "Avatar The Way of Water",
            "url": "https://moviebox.ph/movie/xxxxx"
        },
        {
            "title": "John Wick 4",
            "url": "https://moviebox.ph/movie/yyyyy"
        }
    ]

    return data[:limit]
