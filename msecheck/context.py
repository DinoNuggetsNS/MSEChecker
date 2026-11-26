"""MSECheck - context."""
import re
from collections import Counter
from .vocabulary import KEYWORDS, VOCAB, _DICT, dl, get_dict
from .mse_parser import fval, nk, plain


# ----------------------------------------------------------------------------------------
# Analysis context
# ----------------------------------------------------------------------------------------
class Ctx:
    pass


_KWRX = {}


def _kw_rx(k, tail):
    """Compiled keyword regexes, built once (the Scryfall keyword list is ~800 long, so this matters)."""
    key = (k, tail)
    if key not in _KWRX:
        _KWRX[key] = re.compile((r"(?:^|[\n,;—•])\s*" if tail else "") + re.escape(k) + (r"\b" if tail else r"(?:$|[\s—{:(0-9])"))
    return _KWRX[key]


def kw_of_part(p, ctx):
    p = p.strip().lower()
    for k in ctx.kw_sorted:
        if p.startswith(k) and _kw_rx(k, False).match(p):
            return k
    return None


def is_kw_line(line, ctx):
    s = re.sub(r"\([^)]*\)", "", line).strip()
    if not s:
        return True
    parts = [p for p in re.split(r"[;,]", s) if p.strip()]
    return bool(parts) and all(kw_of_part(p, ctx) for p in parts)


def build_ctx(cards, blocks):
    c = Ctx()
    custom = []
    for b in blocks:
        if b.kind == "keyword":
            for f in b.fields:
                if nk(f.key) == "keyword":
                    custom.append(plain(fval(f)).strip().lower())
    c.custom = [k for k in custom if k]
    c.kws = set(k.lower() for k in KEYWORDS) | set(c.custom)
    c.kw_sorted = sorted(c.kws, key=len, reverse=True)
    c.kw_single = [k for k in c.kws if re.fullmatch(r"[a-z]{5,}", k)]
    c.kw_words = {w for k in c.kws for w in re.findall(r"[a-z]{3,}", k)}
    c.set_words = {w for card in cards for w in re.findall(
        r"[a-z]{3,}", (" ".join(card.get("names") or [card["name"]]) + " " + card["supertype"] + " " + card["subtype"]).lower())}
    c.names = {n.strip().lower() for card in cards for n in (card.get("names") or [card["name"]])}
    c.pool = list(VOCAB | c.set_words | c.kw_words)
    c.flavor_freq = Counter()
    for card in cards:
        c.flavor_freq.update({w.lower() for f in card.get("flavor", []) for w in re.findall(r"[^\W\d_]{4,}", f["plain"])})
    _all = "\n".join(f["plain"] for card in cards for f in card["rules"])
    c.modern = set()          # style comparisons ("enters" vs "enters the battlefield") only matter if the set already uses the newer wording somewhere
    if re.search(r"\b(?:when|whenever)\b[^.\n]*\benters?\b(?! the battlefield)", _all, re.I):
        c.modern.add("etb-modern")
    if re.search(r"\bdies\b", _all, re.I):
        c.modern.add("dies")
    c.freq, c.kw_use = Counter(), Counter()
    for card in cards:
        text = "\n".join(f["plain"] for f in card["rules"])
        c.freq.update(set(re.findall(r"[a-z]{4,}", text.lower())))
        used = set()
        for line in text.split("\n"):
            for part in re.split(r"[;,]", re.sub(r"\([^)]*\)", "", line)):
                k = kw_of_part(part, c) if part.strip() else None
                if k:
                    used.add(k)
        c.kw_use.update(used)
    return c


def mk(sev, cat, rule, line, match, why, fix=None, rf=None, field=None, suggest=None):
    return {"sev": sev, "cat": cat, "rule": rule, "detected": line, "match": match or "", "why": why, "fix": fix,
            "ref": rf, "field": field, "suggest": suggest, "source": "heuristic"}


def is_known(low, ctx):
    d = get_dict()
    if (low in VOCAB or low in ctx.set_words or low in ctx.kw_words or ctx.freq[low] >= 3 or
            (d is not None and low in d)):
        return True
    forms = {low + "s", low + "es", low + "d", low + "ed", low + "ing", low + "er", low + "ers"}
    for suf, alt in (("s", ""), ("es", ""), ("ed", ""), ("ed", "e"), ("d", ""), ("ing", ""), ("ing", "e")):
        if low.endswith(suf) and len(low) - len(suf) >= 4:
            forms.add(low[:-len(suf)] + alt)
    return any(f in ctx.set_words or f in ctx.kw_words or f in VOCAB for f in forms)


def suggest_word(low, ctx):
    thr = 1 if len(low) < 8 else 2
    best = None
    pools = [[w for w in ctx.pool if abs(len(w) - len(low)) <= 1]]
    d = get_dict()
    if d and _DICT["by_len"]:
        pools.append([w for n in (len(low) - 1, len(low), len(low) + 1) for w in _DICT["by_len"].get(n, [])])
    for pool in pools:
        for w in pool:
            if w[0] != low[0] or w == low:
                continue
            dist = dl(low, w)
            if dist <= thr and (best is None or dist < best[0]):
                best = (dist, w)
        if best:
            return best[1]
    return None


def near_keyword(low, ctx, positional):
    if low in ctx.kws or len(low) < 5:
        return None
    best = None
    for k in ctx.kw_single:
        if k[0] != low[0] or low.startswith(k):
            continue
        if not positional and len(k) < 7:
            continue
        thr = 1 if min(len(k), len(low)) < 7 else 2
        d = dl(low, k)
        if d <= thr and (best is None or d < best[0]):
            best = (d, k)
    return best[1] if best else None


def last_words_fix(line, key, tail_text, new_tail):
    return {"field": key, "old": tail_text, "new": new_tail, "all": False}
