"""MSECheck - scryfall data."""
import gzip, io, json, math, os, re, threading, time, urllib.parse
from array import array
from collections import Counter
from .vocabulary import KEYWORDS, VOCAB
from .templating import TYPES
from .state import LOCK


# ----------------------------------------------------------------------------------------
# Optional real-card statistics from Scryfall's Oracle Cards bulk file
# ----------------------------------------------------------------------------------------
ORACLE = {"kw_pairs": {}, "texts": None, "cache": {}, "mcache": {}, "records": [], "postings": {}, "idf": {}, "doc_count": 0,
          "token_sets": [], "norms": [], "vocab": {}, "rev": [], "df": Counter(), "type_sets": [], "name_idx": {},
          "state": "idle", "message": "", "path": ""}
STATS = {  # rule id -> (trigger regex, companion regex, description of companion)
    "missing-shuffle": (r"search your library", r"shuffle", "“shuffle”"),
    "search-no-reveal": (r"search your library for (?!a card\b)[^.]*into your hand", r"reveal", "“reveal”"),
    "pump-no-duration": (r"target creature gets [+\-][\dx]+/[+\-][\dx]+", r"until end of turn|as long as|for as long as", "a duration"),
    "kicker-no-payoff": (r"\bkicker\b", r"\bkicked\b", "“kicked”"),
    "modal-no-bullets": (r"choose (?:one|two|three) —", r"•", "bulleted modes"),
}


try:  # optional speed-up: pip install orjson
    import orjson as _fastjson
    _loads = _fastjson.loads
except Exception:
    _loads = json.loads

_SKIP_LAYOUTS = {"token", "emblem", "art_series", "double_faced_token", "reversible_card"}


def _oracle_tokenize(text):
    text = (text or "").lower().replace("’", "'")
    return re.findall(r"[a-z][a-z'-]{1,}|[0-9]+|\{[^}]+\}", text)


def _strip_name(text, name):
    """MSE rules text often contains the card's own name; real Oracle text says "this creature", so blank it out."""
    name = (name or "").strip()
    return re.sub(re.escape(name), "~", text, flags=re.I) if len(name) > 2 else text


_OID = re.compile(rb'"oracle_id":\s*"([0-9a-f-]{36})"')


def _card_iter(stream, seen=None):
    """Yield card dicts from a JSON array, JSON-lines, or either of those gzipped.
    With `seen`, lines for oracle_ids already loaded are skipped WITHOUT parsing their JSON (about 3x faster on Default Cards)."""
    head = stream.peek(16)[:16].lstrip(b"\xef\xbb\xbf \t\r\n") if hasattr(stream, "peek") else b""
    if head[:1] == b"[":
        yield from _loads(stream.read().lstrip(b"\xef\xbb\xbf"))
        return
    for line in stream:
        line = line.strip().rstrip(b",")
        if len(line) > 2:
            if seen:
                m = _OID.search(line)
                if m and m.group(1).decode() in seen:
                    continue
            try:
                yield _loads(line)
            except Exception:
                continue


def _build_oracle(stream):
    """Read a Scryfall bulk file ONE entry per real card (Default Cards lists every printing) and build the search index."""
    records, texts, seen, kws, subtypes = [], [], set(), set(), set()
    for n, c in enumerate(_card_iter(stream, seen), 1):
        if n % 5000 == 0 and ORACLE["state"] == "loading":
            ORACLE["message"] = "Reading Scryfall data… %s printings scanned, %s unique cards kept" % (format(n, ","), format(len(records), ","))
        if not isinstance(c, dict) or c.get("layout") in _SKIP_LAYOUTS or c.get("set_type") == "funny":
            continue
        name = c.get("name") or ""
        if c.get("digital") and name.startswith("A-"):  # Arena Alchemy rebalances
            continue
        key = c.get("oracle_id") or name
        if not key or key in seen:
            continue
        faces = c.get("card_faces") or []
        text = c.get("oracle_text") or "\n".join(f.get("oracle_text") or "" for f in faces)
        tline = c.get("type_line") or ""
        if not text.strip() and not tline:
            continue
        seen.add(key)
        kws.update(k.lower() for k in (c.get("keywords") or []))
        for part in tline.split("//"):
            if "—" in part:
                subtypes.update(w.lower() for w in part.split("—", 1)[1].split())
        uris = c.get("image_uris") or (faces[0].get("image_uris") if faces else None) or {}
        records.append({"name": name or "Unknown card", "text": text.strip(), "type": tline,
                        "mana": c.get("mana_cost") or " // ".join(f["mana_cost"] for f in faces if f.get("mana_cost")),
                        "img": uris.get("small", ""),
                        "uri": c.get("scryfall_uri") or ("https://scryfall.com/search?q=" + urllib.parse.quote_plus('!"%s"' % name))})
        texts.append(text.lower())
    if not any(r["text"] for r in records):
        raise ValueError("No usable Oracle text found. Use Scryfall's Default Cards or Oracle Cards bulk data (JSON, JSONL, or .jsonl.gz).")
    # Words become integer ids so the index stays small even for ~35,000 cards.
    vocab, token_sets, df = {}, [], Counter()
    for rec in records:
        ids = frozenset(vocab.setdefault(w, len(vocab)) for w in _oracle_tokenize(rec["text"]))
        token_sets.append(ids)
        df.update(ids)
    n_docs = len(records)
    idf = {t: math.log(1 + n_docs / (1 + c)) for t, c in df.items()}
    postings, norms = {}, []
    for i, ids in enumerate(token_sets):  # FULL postings: nothing is sampled away, so every card can be found
        norms.append(math.sqrt(sum(idf[t] ** 2 for t in ids)) or 1.0)
        for t in ids:
            postings.setdefault(t, array("I")).append(i)
    rev = [None] * len(vocab)
    for w, t in vocab.items():
        rev[t] = w
    name_idx = {}
    for i, r in enumerate(records):
        name_idx.setdefault(r["name"].lower(), i)
    return dict(texts=texts, records=records, postings=postings, idf=idf, doc_count=n_docs, token_sets=token_sets,
                norms=norms, vocab=vocab, rev=rev, df=df, name_idx=name_idx, kws=kws, subtypes=subtypes,
                type_sets=[frozenset(re.findall(r"[a-z]+", r["type"].lower())) for r in records])


def keyword_block(lines, base):
    """The leading run of keyword-only lines: [(line_index, [keyword, ...])]. `base(part)` maps one comma part to its keyword or None."""
    out = []
    for i, line in enumerate(lines):
        s = re.sub(r"\([^)]*\)", "", line).strip()
        if not s:
            continue
        parts = [p for p in re.split(r"[;,]", s) if p.strip()]
        ks = [base(p) for p in parts]
        if not parts or not all(ks):
            break
        out.append((i, ks))
    return out


def _kw_pairs(records):
    ks = sorted(KEYWORDS, key=len, reverse=True)

    def base(p):
        p = p.strip().lower()
        return next((k for k in ks if p.startswith(k) and (len(p) == len(k) or not p[len(k)].isalpha())), None)
    pairs = Counter()
    for r in records:
        seq = []
        for _, k in keyword_block(r["text"].split("\n"), base):
            seq += [x for x in k if x not in seq]
        for i in range(len(seq)):
            for j in range(i + 1, len(seq)):
                pairs[(seq[i], seq[j])] += 1
    return pairs


def _commit_oracle(b):
    kws, subtypes = b.pop("kws"), b.pop("subtypes")
    with LOCK:
        # Real data improves the checker itself: real keyword list, real creature types, real Oracle vocabulary.
        KEYWORDS.update(k for k in kws if isinstance(k, str) and re.fullmatch(r"[a-z][a-z' \-]{2,}", k.strip()))   # never an empty/odd keyword
        TYPES.update(subtypes)
        VOCAB.update(w for w, t in b["vocab"].items() if b["df"][t] >= 2 and re.fullmatch(r"[a-z]{3,}", w))
        b["kw_pairs"] = _kw_pairs(b["records"])
        ORACLE.update(b, cache={}, mcache={}, face_names=None, state="ready",
                      message="Loaded %s unique cards" % format(b["doc_count"], ","))
    return b["doc_count"]


def load_oracle(data):
    """Load uploaded bytes (JSON, JSONL, or gzip of either). Returns the number of unique cards indexed."""
    raw = bytes(data)
    stream = gzip.GzipFile(fileobj=io.BytesIO(raw)) if raw[:2] == b"\x1f\x8b" else io.BufferedReader(io.BytesIO(raw))
    try:
        return _commit_oracle(_build_oracle(stream))
    finally:
        stream.close()


def load_oracle_path(path):
    """Stream a bulk file straight from disk (no need to hold the whole thing in memory)."""
    with open(path, "rb") as fh:
        gz = fh.read(2) == b"\x1f\x8b"
        fh.seek(0)
        stream = gzip.GzipFile(fileobj=fh) if gz else fh
        return _commit_oracle(_build_oracle(stream))


def start_oracle_load(path):
    """Load a bulk file in the background so the page opens immediately."""
    path = os.path.expanduser((path or "").strip().strip('"'))
    if ORACLE["state"] == "loading":
        raise ValueError("Scryfall data is already loading.")
    if not os.path.isfile(path):
        raise ValueError("No file found at: %s" % path)
    ORACLE.update(state="loading", message="Reading Scryfall data…", path=path)

    def run():
        try:
            t0 = time.time()
            n = load_oracle_path(path)
            print("Loaded %s unique Scryfall cards in %.0fs from %s" % (format(n, ","), time.time() - t0, path))
        except Exception as e:
            ORACLE.update(state="error", message="Could not load Scryfall data: %s" % e)
            print(ORACLE["message"])
    threading.Thread(target=run, daemon=True).start()


def _docs_with_all(terms):
    """Cards containing EVERY term. `terms` is rarest-first, so we walk the smallest posting list."""
    ts, rest, out = ORACLE["token_sets"], terms[1:], []
    for i in ORACLE["postings"][terms[0]]:
        s = ts[i]
        if all(t in s for t in rest):
            out.append(i)
            if len(out) >= 2500:
                break
    return out


def _find_close(text, limit, type_line, name):
    O = ORACLE
    vocab, df, idf, ts, norms, recs, rev = (O[k] for k in ("vocab", "df", "idf", "token_sets", "norms", "records", "rev"))
    words = set(_oracle_tokenize(text))
    qids = {vocab[w] for w in words if w in vocab}
    unknown = sorted(w for w in words if w not in vocab and re.fullmatch(r"[a-z]{4,}", w))[:6]
    note, scored = "", []
    if qids:
        terms = sorted(qids, key=lambda t: (df[t], t))  # rarest word first
        # Search with ALL the words; if no real card has them all, drop the rarest word and search again,
        # repeating with fewer and fewer terms until some card matches.
        cand, start = [], 0
        for start in range(len(terms)):
            cand = _docs_with_all(terms[start:])
            if cand:
                break
        pool = set(cand)
        heat = Counter()  # also consider cards that share several of the rarest words
        for t in terms[:8]:
            for i in O["postings"][t]:
                heat[i] += idf[t]
        pool.update(i for i, _ in heat.most_common(600))
        qw = {t: idf[t] for t in qids}
        qnorm = math.sqrt(sum(v * v for v in qw.values())) or 1.0
        for i in pool:
            common = qids & ts[i]
            if common:
                cos = sum(qw[t] * idf[t] for t in common) / (qnorm * norms[i])
                scored.append((0.78 * cos + 0.22 * len(common) / len(qids | ts[i]), len(common), i))
        scored.sort(reverse=True)
        if start:
            note = ("No real card contains all %d distinct words of this text, so the search was relaxed to the %d most common "
                    "(ignored the rarest: %s)." % (len(terms), len(terms) - start, ", ".join(rev[t] for t in terms[:start][:8]) +
                                                   (", …" if start > 8 else "")))
    if not scored:  # nothing comparable in the rules text: fall back to the type line, then to similar names
        tq = set(re.findall(r"[a-z]+", type_line.lower()))
        if tq:
            for i, st in enumerate(O["type_sets"]):
                if tq & st:
                    scored.append((len(tq & st) / len(tq | st) + (0.05 if not recs[i]["text"] else 0), 0, i))
            scored.sort(reverse=True)
            note = ("None of this text's words appear in real Oracle text, so cards with the closest type line are shown." if text.strip()
                    else "This card has no rules text, so real cards with the closest type line are shown.")
        if not scored and name.strip():
            import difflib
            near = difflib.get_close_matches(name.lower(), list(O["name_idx"]), n=limit, cutoff=0.0)
            scored = [(0.0, 0, O["name_idx"][m]) for m in near]
            note = "Nothing comparable on this card, so the real cards with the most similar names are shown."
    if unknown and qids:
        note += (" " if note else "") + "Not found in any real card: %s." % ", ".join(unknown)
    items, seen = [], set()
    for s, n, i in scored:
        r = recs[i]
        k = r["name"].casefold()
        if k in seen:
            continue
        seen.add(k)
        items.append({"name": r["name"], "type": r["type"], "mana": r["mana"], "text": r["text"], "url": r["uri"], "img": r["img"],
                      "score": round(min(s, 1.0) * 100, 1), "shared": n, "of": len(qids)})
        if len(items) >= limit:
            break
    return {"note": note.strip(), "items": items}


def find_close_oracle_matches(rules_text, limit=5, type_line="", name=""):
    """Closest real cards to this text, as {"note", "items"}; None when no Scryfall data is loaded.
    Always returns at least one card whenever the data is loaded and there is anything to compare."""
    if not ORACLE.get("records"):
        return None
    key = (rules_text, limit, type_line, name)
    if key not in ORACLE["mcache"]:
        ORACLE["mcache"][key] = _find_close(rules_text or "", limit, type_line or "", name or "")
    return ORACLE["mcache"][key]


def close_for_finding(detected, rules_text, name, type_line):
    """Closest real card for the exact wording a finding flagged (falls back to the whole card when the line is too short)."""
    if not ORACLE.get("records"):
        return None
    known = sum(1 for w in set(_oracle_tokenize(detected)) if w in ORACLE["vocab"])
    return find_close_oracle_matches(_strip_name(detected if known >= 3 else rules_text, name), 2, type_line, name)


def stat_text(rule_id):
    if not ORACLE["texts"] or rule_id not in STATS:
        return ""
    if rule_id not in ORACLE["cache"]:
        trig, need, desc = STATS[rule_id]
        t, n = re.compile(trig), re.compile(need)
        hits = [x for x in ORACLE["texts"] if t.search(x)]
        ORACLE["cache"][rule_id] = (len(hits), sum(1 for x in hits if n.search(x)), desc)
    n, m, desc = ORACLE["cache"][rule_id]
    return (" In Scryfall's Oracle data, %s cards match this pattern and %.1f%% of them also include %s." % (format(n, ","), 100.0 * m / n, desc)) if n else ""
