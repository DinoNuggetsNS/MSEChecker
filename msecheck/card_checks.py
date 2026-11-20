"""MSECheck - card checks."""
import re
from .vocabulary import VOCAB, dl, get_dict
from .templating import CREATURE_KW, NEEDS_COST, NEEDS_NUMBER, REF_AURA, REF_EQUIP, REF_KICK, REF_MODAL, REF_PW, REF_REVEAL, REF_SAGA, REF_SEARCH, REF_VEH, REF_X, RULES, SPELL, SYM_OK, TEMPLATES, _DUR_PHRASE, _DUR_RULES, _in_paren, _types, ref
from .mse_parser import nk
from .context import is_known, is_kw_line, kw_of_part, mk, near_keyword, suggest_word
from .scryfall_data import ORACLE, keyword_block, stat_text


# ----------------------------------------------------------------------------------------
# Per-card checks
# ----------------------------------------------------------------------------------------
def check_artist(card):
    """Flag a card that has no artist credit (empty or absent illustrator field). Only used for full sets."""
    if not (card["name"] or "").strip():
        return []
    if card["artist"].strip():
        return []
    return [mk("Needs review", "Credits", "artist-missing", card["name"], "", "This card has no artist credit. Add the illustrator's name "
               "(or the source of the artwork) so the art is properly credited.", field="illustrator")]


_FOREIGN_PAIRS = {("bona", "fide"), ("ad", "hoc"), ("de", "facto"), ("de", "jure"), ("vice", "versa"), ("a", "priori"), ("per", "se"),
                  ("status", "quo"), ("modus", "operandi"), ("carpe", "diem"), ("in", "situ"), ("sine", "qua"), ("qua", "non"),
                  ("pro", "bono"), ("quid", "pro"), ("pro", "quo"), ("habeas", "corpus"), ("mea", "culpa"), ("ex", "nihilo"),
                  ("deus", "ex"), ("ex", "machina"), ("coup", "de"), ("de", "grace"), ("deja", "vu"), ("faux", "pas"), ("fait", "accompli")}
_AFFIXES_SUF = ("less", "lessly", "lessness", "ness", "ish", "ly", "ful", "fully", "ing", "ings", "ed", "er", "ers", "est", "s", "es", "y", "ment",
                "ments", "able", "ably", "ible", "ous", "ize", "ized", "ise", "ised", "ity", "ism", "ist", "ists", "dom", "hood", "ship", "ward",
                "wards", "like", "some", "ie", "ies")
_AFFIXES_PRE = ("un", "re", "dis", "non", "over", "under", "out", "mis", "pre", "anti", "sub", "inter", "semi", "half", "self", "fore", "de", "in", "im")


def _plausible_word(low, prev, nxt, d, ctx):
    """True when an unknown flavor word is probably a genuine (if uncommon) word, so it should not be called a typo:
    a known word plus an ordinary prefix/suffix (sparkless, unsharpened, likeless), a clipped form of a longer word (improv),
    or half of a foreign phrase (bona fide)."""
    if (prev, low) in _FOREIGN_PAIRS or (low, nxt) in _FOREIGN_PAIRS:
        return True
    def known(w):
        return len(w) >= 3 and (w in d or w in VOCAB or w in ctx.set_words)
    for suf in _AFFIXES_SUF:
        if low.endswith(suf) and len(low) - len(suf) >= 3:
            stem = low[:-len(suf)]
            if known(stem) or known(stem + "e") or (len(stem) > 3 and stem[-1] == stem[-2] and known(stem[:-1])) or (stem.endswith("i") and known(stem[:-1] + "y")):
                return True
    for pre in _AFFIXES_PRE:
        if low.startswith(pre) and len(low) - len(pre) >= 4:
            rest = low[len(pre):]
            if known(rest):
                return True
            for suf in _AFFIXES_SUF:
                if rest.endswith(suf) and len(rest) - len(suf) >= 3 and (known(rest[:-len(suf)]) or known(rest[:-len(suf)] + "e")):
                    return True
    if len(low) >= 5 and any(w.startswith(low) and len(w) > len(low) for w in d):
        return True   # clipped word: improv(e/ise), demo(nstration) …
    if len(low) >= 6:   # two known words run together (moonlight, sunblade)
        for i in range(3, len(low) - 2):
            if known(low[:i]) and known(low[i:]):
                return True
    return False


_FL_WORD = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*")


def check_flavor(card, ctx):
    """Spelling mistakes in flavor text, and nothing else: no style, grammar or wording checks."""
    out = []
    d = get_dict()
    if d is None:
        return out   # flavor text is ordinary English, so a real dictionary is needed to tell typos from words (pip install pyspellchecker)
    own = set(re.findall(r"[a-z]{3,}", (" ".join(card.get("names") or [card["name"]]) + " " + card["supertype"] + " " + card["subtype"]).lower()))
    for fld in card.get("flavor", []):
        key = fld["key"]
        for line in fld["plain"].split("\n"):
            body = re.split(r"(?:^|\s)[\u2014\u2013]\s*", line, maxsplit=1)[0] if re.search(r"(?:^|\s)[\u2014\u2013]", line) else line
            flagged = set()
            for m in _FL_WORD.finditer(body):
                tok = m.group(0)
                if not tok.isascii() or tok.isupper() or len(tok) < 4:
                    continue
                base = tok
                if "'" in tok or "\u2019" in tok:
                    base, suf = re.split(r"['\u2019]", tok, maxsplit=1)
                    if suf.lower() not in ("s", "t", "re", "ve", "ll", "d", "m") or len(base) < 4:
                        continue
                low = base.lower()
                prefix = body[:m.start()]
                sentence_start = prefix.strip() == "" or re.search(r"[.!?:\u2026][\"'\u201c\u2018\u2019\s]*$", prefix) is not None
                if base[0].isupper():
                    continue                                   # a character or place name (legendary names are invented), at any position
                if low in flagged or low in own or low in ctx.names or ctx.flavor_freq[low] >= 2 or is_known(low, ctx):
                    continue
                if low in ctx.set_words or any(low in n for n in ctx.names):
                    continue
                _pm = re.findall(r"[A-Za-z]+", body[:m.start()])
                _nm = re.match(r"\W*([A-Za-z]+)", body[m.end():])
                if _plausible_word(low, _pm[-1].lower() if _pm else "", _nm.group(1).lower() if _nm else "", d, ctx):
                    continue                                   # a real word that just isn't in the dictionary
                sg = suggest_word(low, ctx)
                if not sg:
                    continue                                   # unknown but nothing it could be a typo of: a made-up word or name
                if dl(low, sg) > 1:
                    continue                                   # flavor text: only one-letter slips (wnid/wind, accross/across)
                if base[0].isupper() and dl(low, sg) > 1:
                    continue
                good = sg.capitalize() if base[0].isupper() else sg
                flagged.add(low)
                out.append(mk("Likely error", "Spelling", "flavor-spelling", line, base,
                              "“%s” may be a misspelling of “%s” (flavor text)." % (base, good),
                              {"field": key, "old": base, "new": good, "all": False}, None, key))
    return out


def _kw_wrong(a, b):
    """True when real cards almost always write b before a (never the other way round)."""
    p = ORACLE.get("kw_pairs") or {}
    r, f = p.get((b, a), 0), p.get((a, b), 0)
    return r >= 3 and r >= 4 * f


def _kw_order(card, ctx):
    if not ORACLE.get("kw_pairs"):
        return []
    out = []
    for fld in card["rules"]:
        lines = fld["plain"].split("\n")
        block = keyword_block(lines, lambda p: kw_of_part(p, ctx))
        seq = []
        for li, ks in block:
            seq += [(li, k) for k in ks]
        bad = next(((a, b) for i, a in enumerate(seq) for b in seq[i + 1:] if _kw_wrong(a[1], b[1])), None)
        if not bad:
            continue
        (la, ka), (lb, kb) = bad
        fix = None
        if la == lb and "(" not in lines[la] and ";" not in lines[la]:
            parts = [x.strip() for x in lines[la].split(",") if x.strip()]
            ks = [kw_of_part(x, ctx) for x in parts]
            for _ in range(len(parts) ** 2):
                sw = next((i for i in range(len(parts) - 1) if _kw_wrong(ks[i], ks[i + 1])), None)
                if sw is None:
                    break
                parts[sw], parts[sw + 1], ks[sw], ks[sw + 1] = parts[sw + 1], parts[sw], ks[sw + 1], ks[sw]
            new = ", ".join([parts[0][:1].upper() + parts[0][1:]] + [x[:1].lower() + x[1:] for x in parts[1:]])
            if new != lines[la].strip():
                fix = {"field": fld["key"], "old": lines[la].strip(), "new": new, "all": False}
        p = ORACLE["kw_pairs"]
        out.append(mk("Needs review", "Keyword order", "keyword-order", lines[la], ka.capitalize() + " … " + kb if la != lb else lines[la].strip(),
                      "On real cards “%s” is written before “%s” (%d cards one way, %d the other), but here it comes after. Keywords on a card "
                      "follow a fairly fixed order." % (kb, ka, p.get((kb, ka), 0), p.get((ka, kb), 0)), fix, None, fld["key"]))
    return out


_INVIS = "\u00a0\u200b\u200c\u200d\u2060\ufeff"


def _quote_map(card):
    """Look at the card's whole rules text at once, so a quotation that spans several lines (a poem, a quoted ability) is judged as a block
    instead of line by line. Returns ({(field_index, line_index): in_block}, {(field_index, line_index) of the line to blame, or empty}).
    Quotes are only called unbalanced when the opening and closing marks don't match over the WHOLE card."""
    inblock, depth, opener = {}, 0, None
    straight = 0
    for fi, fld in enumerate(card["rules"]):
        for li, line in enumerate(fld["plain"].split("\n")):
            ln = re.sub("([\u201c\u201d])(?:\\1|[" + _INVIS + "])+", r"\1", line)     # a doubled mark (““ or ””) counts once
            o, c = ln.count("\u201c"), ln.count("\u201d")
            straight += line.count('"')
            before = depth
            depth = max(0, depth + o - c)
            inblock[(fi, li)] = before > 0 or depth > 0
            if before == 0 and depth > 0:
                opener = (fi, li)
    blame = set()
    if depth > 0 and opener is not None:
        blame.add(opener)
    return inblock, blame, straight % 2 == 1


def check_card(card, ctx):
    out = []
    out += _kw_order(card, ctx)
    inblock, qblame, odd_straight = _quote_map(card)
    _all = "\n".join(f["plain"] for f in card["rules"]).lower()
    leveled = bool(re.search(r"level|class|special|chapter", " ".join(f["key"] for f in card["rules"]).lower())
                   or re.search(r"\btranscend\b|\blevel up\b|\bclass\b", _all + " " + (card["supertype"] + " " + card["subtype"]).lower()))
    for fi, fld in enumerate(card["rules"]):
        key = fld["key"]
        lines = fld["plain"].split("\n")
        for i, line in enumerate(lines):
            s = line.strip()
            if not s:
                continue
            if not re.sub("[\u201c\u201d\"\\s" + _INVIS + "]", "", s):
                continue        # a line holding only quote marks / invisible characters has nothing to check
            in_q = inblock.get((fi, i), False)
            if leveled and re.fullmatch(r"(?:\{[^}]+\}\s*)+:\s*[A-Za-z' \-]{0,24}", s):
                continue        # a level / class heading such as "{1}{R}: Wizard": cost plus a short label, the abilities live in their own field
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            nxt_any = nxt
            if not nxt.strip():
                _fi = [f_["key"] for f_ in card["rules"]].index(key)
                for f_ in card["rules"][_fi + 1:]:
                    if f_["plain"].strip():
                        nxt_any = f_["plain"].split("\n")[0]
                        break
            if i + 1 < len(lines) and not nxt.strip():
                nxt_any = next((x for x in lines[i + 1:] if x.strip()), nxt_any)

            def add(sev, cat, rule, match, why, fix=None, rf=None, suggest=None, _l=line, _k=key):
                out.append(mk(sev, cat, rule, _l, match, why, fix, rf, _k, suggest))

            def fx(old, new, all_=True, _k=key):
                return {"field": _k, "old": old, "new": new, "all": all_}

            kwline = is_kw_line(line, ctx)
            mp_idx = None
            kw_flagged = False

            # ---- spacing ----
            m = re.search(r"[\u00a0\u200b\u200c\u200d\u2060\ufeff]", line)
            if m:
                add("Likely error", "Spacing", "hidden-char", line[max(0, m.start() - 6):m.end() + 6],
                    "Contains an invisible or non-breaking character that can break matching and wrapping.",
                    fx(m.group(0), " " if m.group(0) == "\u00a0" else ""))
            m = re.search(r" {2,}", line.strip())
            if m:
                st = line.strip()
                add("Likely error", "Spacing", "double-space", st[max(0, m.start() - 8):m.end() + 8],
                    "Two or more spaces in a row.", fx(m.group(0), " "))
            m = re.search(r"(?<=\S) +([,.;:!?])(?=\s|$|\))", line)
            if m:
                add("Likely error", "Spacing", "space-before-punct", line[max(0, m.start() - 8):m.end() + 4],
                    "A space appears before punctuation.", fx(m.group(0), m.group(1)))
            m = re.search(r"([a-z\)])([,;])([A-Za-z])", line)
            m2 = re.search(r"([a-z\)])(\.)([A-Z])", line)
            for mm in (m, m2):
                if mm:
                    add("Likely error", "Spacing", "missing-space",  line[max(0, mm.start() - 8):mm.end() + 8],
                        "Punctuation is not followed by a space.", fx(mm.group(0), mm.group(1) + mm.group(2) + " " + mm.group(3)))
            m = re.search(r"\(\s+|\s+\)", line)
            if m:
                add("Needs review", "Spacing", "paren-space", line[max(0, m.start() - 8):m.end() + 8],
                    "Space just inside a parenthesis.", fx(m.group(0), "(" if m.group(0).startswith("(") else ")"))
            if line != line.rstrip():
                add("Suggestion", "Spacing", "trailing-space", s[-20:], "Line ends with trailing whitespace.")

            # ---- repeated words ----
            for m in re.finditer(r"\b([A-Za-z']+)\s+\1\b", line, flags=re.I):
                w = m.group(1).lower()
                if (len(w) < 2 and w != "a") or w in ("had", "that"):
                    continue
                # deliberate repetition: laughter and chants (“Ha ha ha”, “Na na na”) or any word repeated three or more times
                if w in ("ha", "he", "ho", "hee", "heh", "la", "na", "no", "bye", "yo", "ah", "oh", "hah", "haha", "hoo", "tick", "tock", "knock") \
                        or re.search(r"\b" + re.escape(w) + r"(?:[\s,!.?-]+" + re.escape(w) + r"\b){2,}", line, re.I):
                    continue
                add("Likely error", "Repeated word", "repeated-word", m.group(0), "“%s” appears twice in a row." % w,
                    fx(m.group(0), m.group(1)))

            # ---- brackets / quotes / symbols ----
            if line.count("(") != line.count(")"):
                add("Likely error", "Punctuation", "paren-mismatch", "(" if line.count("(") > line.count(")") else ")",
                    "Unmatched parenthesis on this line.")
            if line.count("{") != line.count("}"):
                add("Likely error", "Punctuation", "brace-mismatch", "{", "Unmatched curly brace on this line.")
            if (fi, i) in qblame or (odd_straight and line.count('"') % 2 and i == max(j for j, x in enumerate(lines) if '"' in x)):
                add("Needs review", "Punctuation", "quote-mismatch", '"', "A quotation opened here is never closed anywhere on this card.")
            for m in re.finditer(r"\{([^{}]*)\}", line):
                if not SYM_OK.match(m.group(1)):
                    add("Needs review", "Symbols", "bad-symbol", m.group(0), "Unrecognised mana/ability symbol.")

            # ---- capitalisation / ending punctuation ----
            if kwline:
                if re.match(r"[a-z]", s) and kw_of_part(s.split(",")[0].split(";")[0], ctx):
                    w = re.match(r"[a-z\-]+", s).group(0)
                    add("Suggestion", "Keyword consistency", "kw-case", w,
                        "Keywords are capitalised at the start of an ability line.", fx(w, w.capitalize(), False))
            else:
                if re.match(r"[a-z]", s) and not in_q:
                    add("Needs review", "Capitalization", "lowercase-start", s[:20],
                        "This ability starts with a lowercase letter.")
                core = re.sub(r"[\"”’')\]\s]+$", "", s)      # a closing ] (bracketed, removable text) is not the end of the sentence
                if (core and core[-1] not in ".!?:—-…;" and not s.endswith(")") and not s.startswith("•") and not in_q
                        and not re.search(r"[,;][\"\u201d\u2019']$", s)):     # a comma inside the closing quote continues into the next sentence
                    words = s.split()
                    tail = " ".join(words[-4:])
                    mp_idx = len(out)
                    _fixed = re.sub(r"\s*\]$", ".]", tail) if tail.endswith("]") else tail + "."     # period goes inside the bracket
                    add("Needs review", "Punctuation", "missing-period", words[-1],
                        "This ability ends with a comma, so the sentence looks unfinished." if core[-1] == "," else
                        "This ability does not end with a period.", fx(tail, _fixed, False))

            # ---- keywords that need a cost/number, creature keywords on spells ----
            if kwline:
                for part in re.split(r"[;,]", re.sub(r"\([^)]*\)", "", line)):
                    p = part.strip().lower()
                    if p in NEEDS_COST | NEEDS_NUMBER and p not in ctx.custom:
                        what = "a cost" if p in NEEDS_COST else "a number"
                        add("Likely error", "Missing term", "kw-needs-value", part.strip(),
                            "“%s” needs %s after it (for example “%s %s”)." % (p.capitalize(), what, p.capitalize(),
                                                                           "{2}" if p in NEEDS_COST else "2"),
                            None, ref(None, "cards using this keyword", 'keyword:"%s"' % p))
                    elif p in ("protection", "enchant"):
                        add("Likely error", "Missing term", "kw-needs-value", part.strip(),
                            "“%s” needs %s." % (p.capitalize(), "a quality (“Protection from red”)" if p == "protection" else
                                               "an object (“Enchant creature”)"), None, ref(None, "cards using this keyword", 'keyword:"%s"' % p))
                    elif p in CREATURE_KW and SPELL(card, line, None):
                        add("Needs review", "Missing term", "spell-creature-keyword", part.strip(),
                            "“%s” on an instant/sorcery has no effect unless it is granted to a creature "
                            "(e.g. “Target creature gains %s until end of turn”)." % (p.capitalize(), p),
                            None, ref(None, "cards using this keyword", 'keyword:"%s"' % p))

            # ---- modal spells need bullet modes ----
            mm = re.match(r"(?:Choose|choose) (?:one|two|three|one or both|one or more|up to \w+)\b", s)
            if mm and "•" not in s:
                nb, j = 0, i + 1
                while j < len(lines) and lines[j].strip().startswith("•"):
                    nb, j = nb + 1, j + 1
                if nb < 2:
                    add("Likely error", "Missing term", "modal-no-bullets", mm.group(0),
                        "A “Choose …” ability needs at least two bulleted modes (•) listed after it." + stat_text("modal-no-bullets"),
                        None, REF_MODAL)

            # ---- missing term: search without reveal ----
            if (re.search(r"\bsearch(?:es)? [^.]*?library for (?!a card\b)[^.]*?(?:into|to) (?:your|their|its owner's) hand\b", low_ := line.lower())
                    and "reveal" not in low_):
                add("Needs review", "Missing term", "search-no-reveal", "into your hand",
                    "A restricted library search that puts a card into hand normally says “reveal it” first, so the "
                    "other players can verify the card. Unrestricted searches (“a card”) are the usual exception."
                    + stat_text("search-no-reveal"), None, REF_REVEAL)

            # ---- missing term: shuffle after a library search ----
            low = line.lower()
            if (re.search(r"\bsearch(?:es)? (?:your|their|its owner's|its controller's|that player's|each player's|"
                          r"an opponent's|target \w+'s) library\b", low)
                    and "shuffle" not in low and not nxt.lower().lstrip().startswith("shuffle")):
                words = s.split()
                tail = " ".join(words[-4:])
                fix = fx(tail, tail[:-1] + ", then shuffle.", False) if tail.endswith(".") else None
                m = re.search(r"search(?:es)? .{0,25}library", line, flags=re.I)
                add("Needs review", "Missing term", "missing-shuffle", m.group(0) if m else "Search",
                    "This resembles a search effect that may need an additional instruction to shuffle the library. "
                    "Whether that instruction is missing depends on the full ability and context.",
                    fix, REF_SEARCH)

            # ---- templating ----
            hit = set()
            for rid, rx, sev, cat, msg, repl, rf in TEMPLATES:
                m = rx.search(line)
                if m and _in_paren(line, m.start()):
                    continue   # reminder text isn't rules text
                if m and not (rid == "in-play" and hit & {"old-cip", "old-cip-pl"}):
                    hit.add(rid)
                    fix = fx(m.group(0), m.expand(repl)) if repl is not None else None
                    add(sev, cat, rid, m.group(0), msg, fix, rf)

            for r in RULES:
                if r["skip_if"] & hit:
                    continue
                m = r["rx"].search(line)
                if not m or (r["cond"] and not r["cond"](card, line, m)):
                    continue
                if r["id"] == "activated-incomplete" and re.search(r":\s*$", line) and not re.match(r"\s*:", line) and nxt_any.strip():
                    continue   # the effect is written on the following line
                if r["id"] in _DUR_RULES and re.search(_DUR_PHRASE, line[:m.start()].split(". ")[-1], re.I):
                    continue   # “Until end of turn, target creature gains …” already has its duration
                hit.add(r["id"])
                fix = fx(m.group(0), r["fix"](m)) if r["fix"] else None
                add(r["sev"], r["cat"], r["id"], m.group(0), r["why"] + stat_text(r["id"]), fix, r["ref"])

            # ---- "This creature is all colors." : a characteristic-defining color ability uses the card's name (~) ----
            for m in re.finditer(r"\bThis (?:creature|artifact|enchantment|permanent|land|planeswalker|battle|card) is "
                                 r"(all colors|colorless|(?:white|blue|black|red|green)(?:(?:, and|,| and) (?:white|blue|black|red|green))*)(?=\s*(?:\.|$|\())", line):
                if m.start() == 0 or re.search(r"[.!?\u201d)]\s*$", line[:m.start()]):
                    add("Likely error", "Templating", "cda-this-creature", m.group(0),
                        "A characteristic-defining ability that sets a color uses the card's name (shown as ~), not “this creature”. "
                        "Real cards read “~ is %s.”" % m.group(1), None, None, "~ is " + m.group(1))

            # ---- "if you do" with nothing optional before it ----
            if re.search(r"\bif you do\b", line, re.I):
                before = (lines[i - 1] if i else "") + " " + line[:re.search(r"\bif you do\b", line, re.I).start()]
                if not re.search(r"\b(?:may|pay|sacrifice|discard|reveal|exile|remove|tap|return|put)\b", before, re.I):
                    add("Needs review", "Missing term", "if-you-do-orphan", "If you do",
                        "“If you do” refers to an optional or earlier action, but nothing before it (“you may …”, a cost, etc.) sets one up.",
                        None, ref(None, "cards using “if you do”", 'o:"you may" o:"if you do"'))

            # ---- keyword near-misses + spelling ----
            flagged = set()
            for m in re.finditer(r"[A-Za-z]{4,}", line):
                tok = m.group(0)
                low = tok.lower()
                if low.endswith("n") and line[m.end():m.end() + 2] in ("'t", "\u2019t", "\u2018t"):
                    continue  # doesn't, isn't, wasn't … the regex only sees “doesn”
                prefix = line[:m.start()]
                at_start = prefix.strip() == "" or re.search(r"[.:—•]\s*$", prefix) is not None
                if tok.isupper() or (tok[0].isupper() and not at_start):
                    continue
                positional = prefix.strip() == "" or (len(line) <= 60 and re.search(r"[,;]\s*$", prefix) is not None)
                k = near_keyword(low, ctx, positional)
                d = get_dict()
                if k and not (d and low in d and len(k) < 7) and low not in ctx.set_words and low not in VOCAB:
                    good = k.capitalize() if tok[0].isupper() else k
                    n = ctx.kw_use.get(k, 0)
                    extra = (" The set uses “%s” correctly on %d card%s." % (k.capitalize(), n, "" if n == 1 else "s")) if n else ""
                    add("Likely error", "Custom mechanic consistency" if k in ctx.custom else "Keyword consistency",
                        "kw-misspelled", tok,
                        "“%s” looks like a misspelling of the keyword “%s”.%s" % (tok, k.capitalize(), extra),
                        fx(tok, good), None if k in ctx.custom else ref(None, "cards using this keyword", 'keyword:"%s"' % k))
                    flagged.add(low)
                    kw_flagged = True
                    continue
                if low in flagged or is_known(low, ctx):
                    continue
                sg = suggest_word(low, ctx)
                if sg:
                    good = sg.capitalize() if tok[0].isupper() else sg
                    add("Likely error", "Spelling", "spelling", tok, "“%s” may be a misspelling of “%s”." % (tok, good),
                        fx(tok, good))
                    flagged.add(low)
            if kw_flagged and mp_idx is not None and out[mp_idx]["rule"] == "missing-period":
                out.pop(mp_idx)

    return out


def check_structure(card):
    """Card-level completeness: things a card of this type is expected to contain."""
    out = []
    text = "\n".join(f["plain"] for f in card["rules"])
    ty = _types(card)
    if not text.strip():
        return out
    low = text.lower()
    key = card["rules"][0]["key"]
    typeline = " — ".join(x for x in (card["supertype"], card["subtype"]) if x) or card["name"]

    def add(sev, rid, match, why, rf=None, cat="Missing term"):
        out.append(mk(sev, cat, rid, typeline, match, why + stat_text(rid), None, rf, key))
    if "aura" in ty and not re.search(r"^enchant\b", low, re.M):
        add("Needs review", "aura-no-enchant", "Aura", "Aura cards need an “Enchant …” line saying what they can enchant.", REF_AURA)
    if "equipment" in ty and not re.search(r"\bequip\b", low):
        add("Needs review", "equipment-no-equip", "Equipment", "Equipment needs an “Equip {cost}” ability to attach it.", REF_EQUIP)
    if "vehicle" in ty and not re.search(r"\bcrew\b", low):
        add("Suggestion", "vehicle-no-crew", "Vehicle", "A Vehicle usually has a crew cost (“Crew N”).", REF_VEH)
    # Sagas: chapter numerals are usually drawn by the template from separate chapter fields, so the stored text
    # has no "I —". Accept numeral lines, chapter/level fields, or the standard lore-counter reminder text.
    if "saga" in ty and not (
            re.search(r"^\[?[IVX]+(?:\s*,\s*[IVX]+)*\]?\s*[—–\-:]", text, re.M)
            or any(re.search(r"chapter|level", nk(f["key"]).lower()) for f in card["rules"] if f["plain"].strip())
            or re.search(r"\blore counter\b", low)):
        add("Needs review", "saga-no-chapters", "Saga", "Sagas need chapter lines such as “I — …”.", REF_SAGA)
    # Planeswalkers: "+2:", "[+2]:", "−1:", or costs held in separate loyalty-cost fields.
    if "planeswalker" in ty and not (card.get("loyalty_costs") or
                                     re.search(r"^\s*\[?[+\-−–]?(?:\d+|X)\]?\s*:", text, re.M)):
        add("Needs review", "pw-no-loyalty", "Planeswalker", "Planeswalkers need loyalty abilities such as “+1: …”.", REF_PW)
    if "equipment" in ty and re.search(r"\benchanted (?:creature|permanent)", low):
        add("Needs review", "equipment-says-enchanted", "enchanted", "Equipment refers to “equipped creature”, not “enchanted creature”.", REF_EQUIP, "Templating")
    if "aura" in ty and re.search(r"\bequipped creature", low):
        add("Needs review", "aura-says-equipped", "equipped", "Auras refer to “enchanted creature”, not “equipped creature”.", REF_AURA, "Templating")
    if re.search(r"\bkicker\b|\bmultikicker\b", low) and not re.search(r"\bkicked\b", low):
        add("Needs review", "kicker-no-payoff", "Kicker", "The card has kicker but never says what happens “if it was kicked”.", REF_KICK)
    if re.search(r"\bkicked\b", low) and not re.search(r"\bkicker\b|\bmultikicker\b", low):
        add("Needs review", "kicked-no-kicker", "kicked", "The card refers to being kicked but has no Kicker ability.", REF_KICK)
    bare = re.sub(r"\{[^}]*\}", "", re.sub(r"\([^)]*\)", "", text))      # X inside reminder text isn't the card's own X
    bare = re.sub(r"\b(?:have|has|had|with|control|controls|put|puts|remove|removes|removed|of|for|gets?|gain|gains|lose|loses)\s+X\s+[a-z+/\-]+", " ", bare)  # "if you have X despair" / "X counters" count something
    if (re.search(r"(?<![\w{])X(?![\w}])", bare) and "X" not in (card["cost"] + " " + card.get("cost2", "")).upper() and "{X}" not in text
            and not re.search(r"\bX is\b|\bwhere X\b|\bX equals\b", text)
            and not re.search(r"(?m)^[^:\n]*(?<![\w{])X(?![\w}])[^:\n]*:", text)        # "Tap X untapped creatures you control: …" lets the player choose X
            and not re.search(r"^\s*\[?[+\-\u2212\u2013]?X\]?\s*:", text, re.M)          # a "[-X]:" loyalty ability defines X
            and not any("X" in c.upper() for c in card.get("loyalty_costs", []))):
        add("Needs review", "x-undefined", "X", "X is used but it is not in the mana cost and the text never says what X is.", REF_X)
    if ty.strip():
        unquoted = re.sub(r"\u201c[^\u201d]*\u201d|\"[^\"]*\"", " ", low)  # “…” is an ability given to a token/permanent; its “this artifact” is that object
        for t in ("creature", "artifact", "enchantment", "land", "planeswalker"):
            if re.search(r"\bthis %s\b" % t, unquoted) and t not in ty:
                add("Needs review", "this-wrong-type", "this " + t,
                    "The text says “this %s” but the card's type line does not include %s." % (t, t.capitalize()), None, "Reference consistency")
    return out
