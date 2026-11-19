"""Download Scryfall's set list and set symbols (SVG) for the floating-symbol hover tips.
Usage: python tools/fetch_sets.py OUTDIR   - writes OUTDIR/index.json and OUTDIR/<code>.svg. Never fails the build: on any
problem it still writes an index (possibly empty) and the app falls back to its built-in symbols without names."""
import json, os, sys, time, urllib.request

HDR = {"User-Agent": "MSECheck-build/1.0", "Accept": "application/json;q=0.9,*/*;q=0.8"}
KEEP = {"core", "expansion", "masters", "draft_innovation", "starter", "commander", "funny", "box", "arsenal", "planechase"}
out = sys.argv[1] if len(sys.argv) > 1 else "setsdata"
os.makedirs(out, exist_ok=True)
index = []
try:
    sets = json.load(urllib.request.urlopen(urllib.request.Request("https://api.scryfall.com/sets", headers=HDR), timeout=60))["data"]
    seen = set()
    for s in sorted(sets, key=lambda s: s.get("released_at") or "9999"):
        if s.get("digital") or s.get("set_type") not in KEEP or not s.get("icon_svg_uri") or not s.get("released_at"):
            continue
        code = s["code"]
        try:
            time.sleep(0.1)                                   # Scryfall asks for 50-100 ms between requests
            svg = urllib.request.urlopen(urllib.request.Request(s["icon_svg_uri"].split("?")[0], headers=HDR), timeout=30).read()
        except Exception as e:
            print("skip", code, e)
            continue
        if svg in seen or b"<svg" not in svg:                 # many sets share one icon: keep the first (oldest) set that uses it
            continue
        seen.add(svg)
        open(os.path.join(out, code + ".svg"), "wb").write(svg)
        index.append({"c": code, "n": s["name"], "y": int(s["released_at"][:4])})
except Exception as e:
    print("Could not fetch set symbols:", e)
json.dump(index, open(os.path.join(out, "index.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("Wrote", len(index), "set symbols to", out)
