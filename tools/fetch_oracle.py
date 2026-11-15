"""Download Scryfall's Oracle Cards bulk file and save it as oracle-cards.jsonl.gz (one card per line).
Used by the release build so the app ships with card data. Usage: python tools/fetch_oracle.py OUTPUT.jsonl.gz"""
import gzip, json, shutil, sys, urllib.request

HDR = {"User-Agent": "MSECheck-build/1.0", "Accept": "application/json;q=0.9,*/*;q=0.8"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=600)

meta = next(b for b in json.load(get("https://api.scryfall.com/bulk-data"))["data"] if b["type"] == "oracle_cards")
out = sys.argv[1]
if meta.get("jsonl_download_uri"):                    # one card per line: copy straight into a .gz
    print("Downloading", meta["jsonl_download_uri"])
    with get(meta["jsonl_download_uri"]) as src, gzip.open(out, "wb") as dst:
        shutil.copyfileobj(src, dst)
else:                                                  # older API: a single JSON array
    url = meta.get("json_download_uri") or meta["download_uri"]
    print("Downloading", url)
    cards = json.load(get(url))
    with gzip.open(out, "wt", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
with gzip.open(out, "rt", encoding="utf-8") as f:
    n = sum(1 for line in f if line.strip())
print("Wrote", out, "with", n, "cards")
if n < 1000:
    raise SystemExit("Too few cards downloaded")
