#!/usr/bin/env python3
"""Top up thumbs.json — the base64 thumbnails the artifact build inlines.

Only instruments missing from the cache are downloaded, so a routine refresh
pulls a handful of photos rather than the full ~100 MB. Needs sips + cwebp
(macOS + `brew install webp`); the GitHub Pages build doesn't use any of this.
"""
import json, os, base64, subprocess, tempfile, hashlib
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen, Request

CACHE_FILE = "thumbs.json"
WIDTH, QUALITY = 320, 52

cache = json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {}
items = json.load(open("instruments.json"))
todo = [x for x in items if x["url"] not in cache and x["image"]]
print(len(cache), "cached,", len(todo), "to fetch")

tmp = tempfile.mkdtemp()


def build(x):
    raw = os.path.join(tmp, hashlib.md5(x["image"].encode()).hexdigest()[:12])
    try:
        with urlopen(Request(x["image"], headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
            open(raw, "wb").write(r.read())
        png = raw + ".png"
        subprocess.run(["sips", "-s", "format", "png", "-Z", "480", raw, "--out", png],
                       check=True, capture_output=True)
        webp = raw + ".webp"
        subprocess.run(["cwebp", "-quiet", "-q", str(QUALITY), "-resize", str(WIDTH), "0",
                        png, "-o", webp], check=True, capture_output=True)
        return x["url"], "data:image/webp;base64," + base64.b64encode(open(webp, "rb").read()).decode()
    except Exception as e:
        print("skip", x["model"], e)
        return None


with ThreadPoolExecutor(max_workers=6) as ex:
    for got in ex.map(build, todo):
        if got:
            cache[got[0]] = got[1]

live = {x["url"] for x in items}
for dead in [u for u in cache if u not in live]:
    del cache[dead]

json.dump(cache, open(CACHE_FILE, "w"))
print("thumbs.json now holds", len(cache), "images")
