"""MSECheck - mse parser."""
import re


# ----------------------------------------------------------------------------------------
# MSE file parsing
# ----------------------------------------------------------------------------------------
TAG = re.compile(r"</?(?:[A-Za-z][^>]*|\d+)>")


def _symbols(s):
    return "".join("{%s}" % t for t in re.findall(r"\d+|[A-Za-z]/[A-Za-z](?:/[A-Za-z])?|[A-Za-z]", s))


_SYMTOK = re.compile(r"(?:\{[^{}]*\}|\d+|[WUBRGCXYZSTQE]|[A-Z]/[A-Z](?:/[A-Z])?|\d/[A-Z])+")


def _sym_content(inner):
    """MSE wraps mana/ability symbols in <sym>/<sym-auto>, but <sym-auto> can also wrap whole sentences.
    Turn the content into {X} symbols only when it really is a run of symbols; keep ordinary text as written."""
    t = TAG.sub("", inner)
    if re.fullmatch(r"\s*(?:%s\s*)*" % _SYMTOK.pattern, t):
        return _symbols(t)
    return t


def plain(raw):
    """Convert MSE tagged text into readable plain text; symbols become {X} style."""
    s = re.sub(r"<sym(?:-auto)?[^>]*>(.*?)</sym(?:-auto)?>", lambda m: _sym_content(m.group(1)), raw, flags=re.S)
    return TAG.sub("", s)


class Field:
    __slots__ = ("key", "value", "start", "end", "multi", "lines")


class Block:
    __slots__ = ("kind", "start", "end", "fields")


def split_kv(body):
    k, _, v = body.partition(":")
    return k.strip(), (v[1:] if v.startswith(" ") else v)


def fval(f):
    return "\n".join(f.lines) if f.multi else f.value


def _tabify(lines):
    if any(l.startswith("\t") for l in lines):
        return lines
    unit = min((len(l) - len(l.lstrip(" ")) for l in lines if l.strip() and l.startswith(" ")), default=0)
    if not unit:
        return lines
    out = []
    for l in lines:
        n = len(l) - len(l.lstrip(" "))
        out.append("\t" * (n // unit) + l[(n // unit) * unit:] if l.strip() else l)
    return out


def parse_mse(text):
    lines = _tabify(text.split("\n"))
    blocks, cur, fld = [], None, None
    for i, line in enumerate(lines):
        if not line.strip():
            if fld is not None and fld.multi and line.startswith("\t\t"):
                fld.lines.append("")
                fld.end = i + 1
            continue
        ind = len(line) - len(line.lstrip("\t"))
        body = line[ind:]
        if ind == 0:
            k, v = split_kv(body)
            if k in ("card", "keyword") and v == "":
                cur = Block()
                cur.kind, cur.start, cur.end, cur.fields = k, i, i + 1, []
                blocks.append(cur)
            else:
                cur = None
            fld = None
        elif ind == 1 and cur is not None:
            k, v = split_kv(body)
            fld = Field()
            fld.key, fld.value, fld.start, fld.end, fld.multi, fld.lines = k, v, i, i + 1, v == "", []
            cur.fields.append(fld)
            cur.end = i + 1
        elif ind >= 2 and fld is not None and cur is not None:
            fld.lines.append(line[2:])
            fld.end, fld.multi, cur.end = i + 1, True, i + 1
    return blocks


def render_field(key, value, multi):
    if (multi or "\n" in value) and value != "":
        return ["\t" + key + ":"] + ["\t\t" + l for l in value.split("\n")]
    if multi:
        return ["\t" + key + ":"]
    return ["\t%s: %s" % (key, value)]


def nk(k):
    """Normalise field names: MSE 2.0.2 writes rule_text, older files write 'rule text'."""
    return k.replace("_", " ").strip()


_NOT_RULES = re.compile(r"flavor|code|copyright|note|illustrator|artist|credit|watermark|version|time|image|stylesheet|"
                        r"styling|rarity|symbol|border|frame|color|extra|separator|name|type|cost|power|toughness|loyalty")


def is_rules_field(key):
    """Any text-like field that holds rules text, whatever this stylesheet calls it
    (rule text, rule_text_2, level 1 text, chapter 1, text 3, ability ...)."""
    k = nk(key).lower()
    return bool(re.search(r"text|rule|abilit|chapter", k)) and not _NOT_RULES.search(k)


def make_cards(blocks):
    cards = []
    for b in [b for b in blocks if b.kind == "card"]:
        F = {}
        for f in b.fields:
            F.setdefault(nk(f.key), f)

        def P(k):
            return plain(fval(F[k])).strip() if k in F else ""
        subs = [f for f in b.fields if re.fullmatch(r"sub type( \d+)?", nk(f.key))]
        sups = [f for f in b.fields if re.fullmatch(r"super type( \d+)?", nk(f.key))]
        n = len(cards)
        # One entry per card face ("super type", "super type 2", ...), each with that face's own power/toughness.
        faces = []
        for suf in sorted({(re.search(r"(\d+)$", nk(f.key)) or [None, ""])[1] for f in sups}):
            sp = " " + suf if suf else ""
            ft = " ".join(plain(fval(f)).strip() for f in b.fields if re.fullmatch(r"(?:super|sub) type" + re.escape(sp), nk(f.key)))
            faces.append({"type": ft.strip(), "power": P("power" + sp), "toughness": P("toughness" + sp), "suf": suf})
        # Planeswalker templates keep each loyalty cost (+2, 0, -1) in its own field ("loyalty cost 1", ...),
        # separate from the ability text, so the text itself often has no "+2:" in it.
        lcosts = {}
        for f in b.fields:
            mm = re.fullmatch(r"loyalty cost\s*(\d*)", nk(f.key), re.I)
            if mm and plain(fval(f)).strip():
                lcosts[mm.group(1)] = plain(fval(f)).strip().strip("[]")
        rules = []
        for f in b.fields:
            if not is_rules_field(f.key):
                continue
            txt = plain(fval(f))
            num = re.search(r"(\d+)\s*$", nk(f.key))
            cost = lcosts.get(num.group(1)) if num else (lcosts.get("") if len(lcosts) == 1 else None)
            if cost and txt.strip() and not re.match(r"\s*\[?[+\-−–]?(?:\d+|X)\]?\s*:", txt):
                txt = "%s: %s" % (cost, txt)
            rules.append({"key": f.key, "plain": txt})
        cards.append({
            "idx": n, "name": P("name"), "names": [plain(fval(f)).strip() for f in b.fields if re.fullmatch(r"name( \d+)?", nk(f.key)) and plain(fval(f)).strip()], "supertype": " ".join(plain(fval(f)).strip() for f in sups).strip() or P("type"),
            "subtype": " ".join(plain(fval(f)).strip() for f in subs).strip(), "subkey": subs[0].key if subs else "sub type",
            "cost": P("casting cost"), "cost2": " ".join(plain(fval(f)).strip() for f in b.fields
                                                          if re.fullmatch(r"casting cost \d+", nk(f.key))), "power": P("power"), "toughness": P("toughness"), "loyalty": P("loyalty"), "rarity": P("rarity"), "faces": faces,
            "filled": [nk(f.key) for f in b.fields if fval(f).strip() and not re.match(
                r"(time |stylesheet|has styling|styling data|image|card color|notes|rarity|illustrator)", nk(f.key))],
            "rules": rules, "loyalty_costs": list(lcosts.values()),
            "flavor": [{"key": f.key, "plain": plain(fval(f))} for f in b.fields
                       if re.fullmatch(r"flavou?r(?: text)?(?: \d+)?", nk(f.key).lower()) and plain(fval(f)).strip()],
            # MSE leaves an empty illustrator out of the file altogether, so "no field" and "empty field" both mean no credit
            "artist": " ".join(plain(fval(f)).strip() for f in b.fields
                               if re.fullmatch(r"(?:illustrator|artist)", nk(f.key).lower())).strip(),
        })
    return cards
