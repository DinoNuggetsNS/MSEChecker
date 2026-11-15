"""Download Scryfall's Oracle Cards bulk file and save it as oracle-cards.jsonl.gz (one card per line).
Used by the release build so the app ships with card data. Usage: python tools/fetch_oracle.py OUTPUT.jsonl.gz"""
import gzip, json, sys, urllib.request

HDR = {"User-Agent": "MSECheck-build/1.0", "Accept": "application/json;q=0.9,*/*;q=0.8"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=300)

meta = next(b for b in json.load(get("https://api.scryfall.com/bulk-data"))["data"] if b["type"] == "oracle_cards")
print("bulk-data entry:", {k: (v if len(str(v)) < 120 else str(v)[:120]) for k, v in meta.items()})
url = meta.get("download_uri") or next(v for v in meta.values() if isinstance(v, str) and v.startswith("https://") and v.endswith((".json", ".json.gz")))
print("Downloading", url)
cards = json.load(get(url))
with gzip.open(sys.argv[1], "wt", encoding="utf-8") as f:
    for c in cards:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print("Wrote", len(cards), "cards")
