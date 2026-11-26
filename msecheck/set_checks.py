"""MSECheck - set checks."""
import difflib, re
from collections import Counter, defaultdict
from itertools import combinations
from .vocabulary import KEYWORDS, dl
from .templating import COUNTER_STOP, KNOWN_COUNTERS, TYPES, ref
from .context import mk
from .scryfall_data import ORACLE
from .state import ST


# ----------------------------------------------------------------------------------------
# Set-wide checks
# ----------------------------------------------------------------------------------------
_NUMWORDS = r"(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten)"


def _reminder_nums(s):
    """The numbers/costs/quantities in a reminder (so a scaled reminder like “two … counters” isn't swapped for “a … counter”)."""
    s = s.lower()
    return re.findall(r"\{[^}]*\}|\b\d+\b|\bx\b|\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\b", s)


_PARAM_STOP = {"for", "the", "and", "or", "of", "from", "with", "an", "a", "to", "in", "on", "your", "you"}


def _param_norm(ln, rem):
    """Normalised reminder with the keyword's own parameter words (“Affinity for tokens”) blanked out, so “each token you control” and
    “each artifact you control” count as the same wording."""
    mm = re.match(r"^[A-Z][A-Za-z'\-]{3,}\b(?P<mid>[^()]{0,40}?)\s*\(", ln)
    words = [w for w in re.findall(r"[a-z]+", (mm.group("mid") if mm else "").lower()) if w not in _PARAM_STOP and len(w) >= 3]
    for w in words:
        stem = w[:-1] if w.endswith("s") else w
        rem = re.sub(r"\b" + re.escape(stem) + r"(?:s|es)?\b", "#", rem, flags=re.I)
    return re.sub(r"(?:# ?){2,}", "# ", norm_reminder(rem)).strip(), bool(words)


def _param_key(ln):
    mm = re.match(r"^[A-Z][A-Za-z'\-]{3,}\b(?P<mid>[^()]{0,40}?)\s*\(", ln)
    ws = [(w[:-1] if w.endswith("s") else w) for w in re.findall(r"[a-z]+", (mm.group("mid") if mm else "").lower()) if w not in _PARAM_STOP and len(w) >= 3]
    return tuple(sorted(ws))


def norm_reminder(s, name=""):
    s = s.lower()
    s = re.sub(r"(?:\{[^}]*\}\s*)+|\b\d+\b|\bx\b|\bn\b", "# ", s)   # “{1}{U}” and “{U}” are both just “a cost”
    # a keyword's number changes the reminder: “Brood 1” → “a +1/+1 counter”, “Brood 2” → “two +1/+1 counters”
    s = re.sub(r"\b" + _NUMWORDS + r"\b(?=\s+(?:[+\-]#/[+\-]#\s+|[a-z\-]+\s+)?counters?\b)", "#", s)
    s = re.sub(r"\bcounters\b", "counter", s)
    s = re.sub(r"\ban\b", "a", s)                                                                           # “a trample counter” / “an indestructible counter”
    s = re.sub(r"\bthat\b(?=\s+(?:creature|permanent|artifact|token|card|spell|land|enchantment)\b)", "this", s)  # “This …” on a keyword card, “That …” when a token gets it
    s = re.sub(r"\b(?:white|blue|black|red|green|colorless)\b", "@", s)
    s = re.sub(r"\b(cards|creatures|permanents|lands|spells|tokens)\b", lambda m_: m_.group(1)[:-1], s)   # “top card” / “top 3 cards”
    s = re.sub(r"\b" + _NUMWORDS + r"\b", "#", s) if re.search(r"#", s) else s                              # “pay {2}” vs “pay two”
    return re.sub(r"\s+", " ", re.sub(r"[^\w#@]+", " ", s)).strip()


def _real_names(cards, add):
    """A set card that borrows a real Magic card's name must do exactly what the real card does."""
    names = ORACLE.get("name_idx") or {}
    if not names or ST["kind"] == "text":
        return
    faces = ORACLE.get("face_names")
    if faces is None:
        faces = ORACLE["face_names"] = {f.strip(): i for k, i in names.items() for f in k.split(" // ")}
    recs = ORACLE["records"]
    _self = r"\bthis (?:land|creature|artifact|enchantment|permanent|spell|card|equipment|aura|saga|vehicle|planeswalker|battle|class|case|room|token)\b"
    def norm(t, nm):
        t = re.sub(r"\([^)]*\)", "", t.lower().replace(nm.lower(), "~"))
        t = re.sub(_self, "~", t)
        t = re.sub(r"\benters the battlefield\b", "enters", t)                                  # older wording of the same card is fine
        t = re.sub(r"\b(?:is|are) put into (?:a|an|your|its owner's|their owners'?) graveyard from the battlefield\b", "dies", t)
        t = re.sub(r"\bcomes? into play\b", "enters", t)
        t = re.sub(r"\{t\}: add [^.]*\.", "", t)                                                  # a land's own mana ability (printed or as reminder text)
        return re.sub(r"[^a-z0-9~]", "", t)
    for c in cards:
        nm = c["name"].strip()
        n, ty = nm.lower(), (c["supertype"] + " " + c["subtype"]).lower()
        if not n or re.search(r"token|emblem|basic", ty):
            continue
        i = names.get(n)
        if i is None:
            i = faces.get(n)
        if i is None:
            continue
        real = norm(recs[i]["text"].replace(recs[i]["name"], "~"), nm)
        mine = norm("\n".join(f["plain"] for f in c["rules"] if f["plain"].strip()), nm)
        if mine == real or (mine and n not in names and mine in real):    # identical effect: fine
            continue
        if mine and real and difflib.SequenceMatcher(None, mine, real, autojunk=False).ratio() >= 0.9:    # nearly the same wording: also fine
            continue
        shown = re.sub(r"\s+", " ", recs[i]["text"].replace(recs[i]["name"], nm)).strip()
        add(c["idx"], "Likely error", "Real card names", "real-card-name", nm, nm,
            "“%s” is the name of a real Magic card with the effect “%s”" % (nm, ((shown[:180] + "…") if len(shown) > 180 else shown or "(no rules text)")) + ("" if shown.endswith((".", "”", ")")) else "."))


def check_set(cards, ctx, fl):
    def add(idx, *a, **k):
        fl[idx].append(mk(*a, **k))

    _real_names(cards, add)

    # naming consistency
    by = defaultdict(list)
    _basics = re.compile(r"^(?:snow-covered )?(?:plains|island|swamp|mountain|forest|wastes)$")
    for c in cards:
        _ty = (c["supertype"] + " " + c["subtype"]).lower()
        if not ("token" in _ty or re.search(r"\bbasic\b", _ty) or _basics.match(c["name"].strip().lower())):  # tokens/basics may share names
            by[re.sub(r"\s+", " ", c["name"]).strip().lower()].append(c["idx"])
        if c["name"] and (c["name"] != c["name"].strip() or "  " in c["name"]):
            add(c["idx"], "Likely error", "Naming consistency", "name-space", c["name"], c["name"],
                "The card name has leading, trailing or doubled spaces.")
    for k, v in by.items():
        if k and len(v) > 1:
            for i in v:
                others = ", ".join("#%d" % (j + 1) for j in v if j != i)
                add(i, "Likely error", "Naming consistency", "dup-name", cards[i]["name"], cards[i]["name"],
                    "Another card in the set has the same name (%s). Ignore this if it is intentional (e.g. token or "
                    "double-faced card)." % others)

    # typeline consistency
    use = Counter()
    holders = defaultdict(list)
    _NONCREATURE_SUBTYPES = {"aura", "saga", "equipment", "vehicle", "fortification", "curse", "shrine", "class", "case", "room",
                             "background", "attraction", "siege", "food", "clue", "treasure", "blood", "map", "powerstone", "gold",
                             "junk", "incubator", "contraption", "lesson", "trap", "arcane", "adventure", "omen", "mount", "plains",
                             "island", "swamp", "mountain", "forest", "desert", "gate", "lair", "locus", "cave", "sphere", "town"}
    for c in cards:
        if not re.search(r"creature|kindred|tribal|changeling", (c["supertype"] + " " + c["subtype"]).lower()):
            continue
        for w in set(c["subtype"].split()):
            if w.lower() in _NONCREATURE_SUBTYPES:
                continue
            use[w.lower()] += 1
            holders[w.lower()].append(c["idx"])
    for a, b in combinations(sorted(use), 2):
        if len(a) < 4 or len(b) < 4 or a[0] != b[0]:
            continue
        if dl(a, b) > (1 if min(len(a), len(b)) < 7 else 2):
            continue
        if a in TYPES and b in TYPES:
            continue  # both are real creature types (Bird / Bard): neither is a typo of the other
        def _typo(w):      # already reported as a misspelled creature type: don't also report it as a "variant"
            return w not in TYPES and any(t[0] == w[0] and len(t) >= 4 and abs(len(t) - len(w)) <= 2 and dl(w, t) <= (1 if len(w) < 7 else 2) for t in TYPES)
        (rare, rc), (com, cc) = sorted(((a, use[a]), (b, use[b])), key=lambda t: t[1])
        if (_typo(rare) and rc <= 3) or (_typo(com) and cc <= 3):
            continue
        if rc == cc == 1 or rc <= 2 < cc or rc < cc and rc <= 2:
            sev = "Likely error" if rc < cc else "Needs review"
            for w, other in ((rare, com), (com, rare)) if rc == cc else ((rare, com),):
                for i in holders[w]:
                    add(i, sev, "Typeline consistency", "subtype-variant", w.capitalize(), cards[i]["name"] + " — " + cards[i]["supertype"] + " — " + cards[i]["subtype"],
                        "The creature type “%s” is spelled differently from “%s”, which is used on %d other card%s."
                        % (w.capitalize(), other.capitalize(), use[other], "" if use[other] == 1 else "s"),
                        {"field": cards[i]["subkey"], "old": w.capitalize(), "new": other.capitalize(), "all": False})
    for w in sorted(use):
        if w in TYPES or len(w) < 5 or w in KEYWORDS:
            continue
        best = None
        for t in TYPES:
            if t[0] == w[0] and abs(len(t) - len(w)) <= 2 and len(t) >= 4:
                d = dl(w, t)
                if d <= (1 if len(w) < 7 else 2) and (best is None or d < best[0]):
                    best = (d, t)
        if best and use[w] <= 3:
            for i in holders[w]:
                add(i, "Likely error", "Typeline consistency", "subtype-misspelled", w.capitalize(),
                    cards[i]["name"] + " — " + cards[i]["supertype"] + " — " + cards[i]["subtype"],
                    "“%s” looks like a misspelling of the creature type “%s”. (Ignore this if it is an intentional custom type.)"
                    % (w.capitalize(), best[1].capitalize()),
                    {"field": cards[i]["subkey"], "old": w.capitalize(), "new": best[1].capitalize(), "all": False},
                    ref(None, "cards with this creature type", "t:" + best[1]))
    has_pt = any(c["power"] for c in cards)
    pt_sufs = {fc["suf"] for c in cards for fc in c.get("faces", ()) if fc["power"]}   # which faces' templates have P/T boxes
    for c in cards:
        # Check each face on its own: a double-faced card may be a creature on one side and, say, an enchantment on the other.
        fcs = c.get("faces") or [{"type": c["supertype"] + " " + c["subtype"], "power": c["power"], "toughness": c["toughness"], "suf": ""}]
        for fc in fcs:
            if fc["suf"] in pt_sufs and "creature" in fc["type"].lower() and not (fc["power"] and fc["toughness"]):
                add(c["idx"], "Needs review", "Typeline consistency", "creature-no-pt", c["name"],
                    fc["type"], "Creature card without power/toughness.")

    # per-line mechanics & references
    lines_by = []
    for c in cards:
        for f in c["rules"]:
            for ln in f["plain"].split("\n"):
                lines_by.append((c["idx"], f["key"], ln))
    cand = defaultdict(list)
    rem = defaultdict(list)
    for idx, key, ln in lines_by:
        m = re.match(r"^([A-Z][A-Za-z'\-]{3,})\b(?P<mid>[^()]{0,40}?)\s*\((?P<rem>.+)\)\s*$", ln)
        if m and (re.search(r"[\u201c\"]|\b(?:you|have|has|gain|gains|get|gets|control|controls|is|are|can)\b", m.group("mid"))):
            m = None        # an ordinary sentence with reminder text after it (“Creatures you control have …”), not a keyword line
        if m:
            w = m.group(1).lower()
            if w not in KEYWORDS or w in ctx.custom:
                cand[w].append((idx, key, ln))
            # reminder text legitimately differs between spells, creatures and other permanents (e.g. gift on an instant vs a creature)
            _t = (cards[idx]["supertype"] + " " + cards[idx]["subtype"]).lower()
            _cat = "creature" if "creature" in _t else ("spell" if re.search(r"instant|sorcery", _t) else "permanent")
            rem[(w, _cat)].append((idx, key, ln, m.group("rem")))
    near_builtin = lambda w: any(dl(w, k) <= 2 for k in ctx.kw_single if k not in ctx.custom and k[0] == w[0])
    names = [w for w in cand if len(w) >= 5 and not near_builtin(w) and w not in KEYWORDS and w not in ctx.custom]
    cnt = {w: len({i for i, _, _ in cand[w]}) for w in names}
    for a, b in combinations(sorted(names), 2):
        if a[0] != b[0] or dl(a, b) > (1 if min(len(a), len(b)) < 8 else 2):
            continue
        rare, com = (a, b) if cnt[a] <= cnt[b] else (b, a)
        sev = "Likely error" if cnt[rare] < cnt[com] else "Needs review"
        for w, o in ((rare, com),) if cnt[rare] < cnt[com] else ((a, b), (b, a)):
            for idx, key, ln in cand[w]:
                add(idx, sev, "Custom mechanic consistency", "mechanic-variant", w.capitalize(), ln,
                    "Your mechanic is written as “%s” here but “%s” on %d other card%s."
                    % (w.capitalize(), o.capitalize(), cnt[o], "" if cnt[o] == 1 else "s"),
                    {"field": key, "old": w.capitalize(), "new": o.capitalize(), "all": True}, field=key)
    # reminder text consistency
    for (w, _cat), items in rem.items():
        if len({i for i, *_ in items}) < 2:
            continue
        groups = Counter(_param_norm(ln_, r)[0] for _, _, ln_, r in items)
        top, tc = groups.most_common(1)[0]
        if tc == 1 and len(groups) == len(items):
            continue
        sample = next(r for _, _, ln_, r in items if _param_norm(ln_, r)[0] == top)
        by_param = defaultdict(Counter)       # “Affinity for monsters” always has its own wording: cards with the same parameter only have to match each other
        for _, _, ln_, r_ in items:
            _pk = _param_key(ln_)
            if _pk:
                by_param[_pk][_param_norm(ln_, r_)[0]] += 1
        for idx, key, ln, r in items:
            n, _has_param = _param_norm(ln, r)
            _pk = _param_key(ln)
            if _pk and sum(by_param[_pk].values()) >= 2:
                if n == by_param[_pk].most_common(1)[0][0] or len(by_param[_pk]) == 1:
                    continue
                top = by_param[_pk].most_common(1)[0][0]
            if re.search(r"\bcast (?:this|it|that|the)\b|\bcasting\b|\balternat(?:e|ive) cost\b|\brather than paying\b|\bfor its\b[^.]*\bcost\b", r, re.I):
                continue   # reminder text that describes how to cast the card varies with the alternate cost it carries
            if n != top and difflib.SequenceMatcher(None, n, top).ratio() > 0.5:
                add(idx, "Needs review", "Reminder text consistency", "reminder-variant", r, ln,
                    "The reminder text for “%s” differs from the version used on %d other card%s. Numbers/costs may "
                    "legitimately differ." % (w.capitalize(), tc, "" if tc == 1 else "s"),
                    field=key, suggest=ln.replace(r, sample) if (not _has_param and _reminder_nums(r) == _reminder_nums(sample)) else None)

    # reference consistency
    counter_use = defaultdict(set)
    for idx, key, ln in lines_by:
        for m in re.finditer(r"\b(?:cards?|tokens?) named ([A-Z][\w'’\- ]+?)(?=[.,;:)]|$)", ln):
            nm = m.group(1).strip()
            low_nm = nm.lower()
            known = [n for n in ctx.names if n and (low_nm == n or low_nm.startswith(n + " "))]
            if known:
                continue
            nm = re.split(r"\s+(?:from|to|in|on|with|and|or|is|are|enters|dies|you|your|this|that|can|has|have|gets?|deals?|"
                          r"under|until|onto|into|if|when|whenever)\b", nm)[0].strip() or nm
            if nm.lower() not in ctx.names:
                add(idx, "Needs review", "Reference consistency", "named-missing", m.group(0), ln,
                    "Refers to “%s”, which is not a card in this set. That may be intentional (a real Magic card or a "
                    "token kept elsewhere)." % nm, field=key, rf=ref(nm, "check whether this card exists as intended", 'name:"%s"' % nm))
        for m in re.finditer(r"([+\-]\d+/[+\-]\d+|[a-z][a-z\-]+) counters?\b", ln):
            t = m.group(1)
            if t not in COUNTER_STOP and t not in KNOWN_COUNTERS:
                counter_use[t].add((idx, key, ln))
    for a, b in combinations(sorted(counter_use), 2):
        if a[0] == b[0] and len(a) >= 5 and dl(a, b) <= 2:
            for t, o in ((a, b), (b, a)):
                for idx, key, ln in counter_use[t]:
                    add(idx, "Needs review", "Reference consistency", "counter-variant", "%s counter" % t, ln,
                        "The counter “%s” is similar to “%s” elsewhere in the set; one may be a typo." % (t, o), field=key)
