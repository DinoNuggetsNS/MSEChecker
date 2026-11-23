"""MSECheck - extra design and polish checks (names, planeswalkers, stats, abilities, text fit, set-wide duplicates)."""
import re
from collections import defaultdict
from .context import mk
from .state import ST

_SMALL = {"of", "the", "a", "an", "and", "or", "in", "on", "to", "for", "at", "by", "from", "with", "into", "as"}
_REDUNDANT = [("flying", "reach", "Reach does nothing on a creature that already has flying (it can only be blocked by flying or reach creatures either way)."),
              ("first strike", "double strike", "Double strike already includes first strike."),
              ("hexproof", "shroud", "Hexproof and shroud contradict each other: shroud stops the controller from targeting it too."),
              ("defender", "vigilance", "Vigilance only matters when a creature attacks, and a creature with defender can't attack.")]
_PLACEHOLDER_ARTIST = {"unknown", "tbd", "tba", "?", "n/a", "na", "none", "artist", "artist name", "anonymous", "ai", "placeholder", "todo"}


def _types(card):
    return (card["supertype"] + " " + card["subtype"]).lower()


def _num(s):
    s = (s or "").strip()
    return int(s) if re.fullmatch(r"\d+", s) else None


def _mv(cost):
    """Mana value of a cost written either as {2}{W} or as 2W (X counts 0)."""
    n = 0
    for sym in re.findall(r"\{([^}]*)\}", cost or ""):
        t = sym.upper()
        n += int(t) if t.isdigit() else (0 if t == "X" else 1)
    rest = re.sub(r"\{[^}]*\}", "", cost or "")
    for d, l in re.findall(r"(\d+)|([A-Za-z])", rest):
        n += int(d) if d else (0 if l.upper() == "X" else 1)
    return n


def check_extra_card(card, ctx):
    out = []
    name = (card["name"] or "").strip()
    ty = _types(card)
    rules = "\n".join(f["plain"] for f in card["rules"])
    low = rules.lower()
    key = card["rules"][0]["key"] if card["rules"] else None
    typeline = " — ".join(x for x in (card["supertype"], card["subtype"]) if x) or name
    is_token = "token" in ty
    is_basic = bool(re.search(r"\bbasic\b", ty))

    def add(sev, cat, rule, line, match, why, field=None):
        out.append(mk(sev, cat, rule, line, match, why, None, None, field))

    # ---- names ----
    if name and not is_token:
        words = name.split()
        if name[0].islower():
            add("Needs review", "Naming", "name-lowercase", name, words[0], "The card name starts with a lowercase letter. Card names are written in title case.")
        bad = [w for w in words[1:] if w in ("Of", "The", "And", "Or", "In", "On", "To", "For", "At", "By", "From", "With")
               and not (words[words.index(w) - 1].endswith((",", ":", "—", "-")))]
        if bad:
            add("Suggestion", "Naming", "name-small-words", name, bad[0],
                "Small words in the middle of a card name (“of”, “the”, “and”, “to”…) are lowercase on real cards, e.g. “Lord of the Pit”.")
        if len(name) > 32:
            add("Suggestion", "Naming", "name-long", name, name, "This name is %d characters long. Names over about 30 characters tend to be squeezed or cut off in the title bar." % len(name))

    # ---- artist placeholder ----
    if card["artist"].strip().lower() in _PLACEHOLDER_ARTIST:
        add("Needs review", "Credits", "artist-placeholder", name, card["artist"].strip(), "The artist credit looks like a placeholder. Put in the real illustrator's name.", "illustrator")

    # ---- types / stats ----
    one_face = len(card.get("faces") or []) <= 1
    if "creature" in ty and not card["subtype"].strip() and not is_token and one_face:
        add("Needs review", "Typeline consistency", "creature-no-subtype", typeline, "Creature", "Creatures have a creature type after the dash (“Creature — Elf Druid”). This one has none.")
    if "land" in ty and "creature" not in ty and card["cost"].strip() and one_face and not is_token:
        add("Needs review", "Typeline consistency", "land-has-cost", typeline, card["cost"].strip(), "Lands have no mana cost, but this one has %s." % card["cost"].strip())
    if "planeswalker" in ty and one_face and not is_token:
        if not card["loyalty"].strip() and not any("loyalty" in k and "cost" not in k for k in card.get("filled", [])):
            add("Likely error", "Missing term", "pw-no-starting-loyalty", typeline, "Planeswalker", "This planeswalker has no starting loyalty filled in.")
        if card["rarity"].strip().lower() in ("common", "uncommon"):
            add("Needs review", "Rarity", "pw-low-rarity", typeline, card["rarity"], "Planeswalkers are rare or mythic rare in real sets. A %s one is unusual." % card["rarity"].strip().lower())
    if "legendary" in ty and card["rarity"].strip().lower() == "common" and not is_token:
        add("Suggestion", "Rarity", "legend-common", typeline, "Legendary", "A legendary card at common is unusual because you can't build around playing several. Check the rarity is intended.")
    if "creature" in ty and not is_token and one_face:
        p, t = _num(card["power"]), _num(card["toughness"])
        if p is not None and t is not None:
            mv = _mv(card["cost"])
            plain_kw = not re.sub(r"[A-Za-z' ,]+(?:\([^)]*\))?", "", rules).strip()   # no numbers/symbols: basically vanilla or keyword soup
            if (p >= 13 or t >= 13):
                add("Needs review", "Stats", "pt-extreme", typeline, "%d/%d" % (p, t), "A %d/%d is very large. Check the stats are what you meant." % (p, t))
            elif card["cost"].strip() and not low.strip() and p + t > 2 * mv + 4:
                add("Suggestion", "Stats", "pt-vanilla-too-big", typeline, "%d/%d" % (p, t),
                    "A %d/%d with no abilities for mana value %d is well above the usual vanilla rate (about %d total stats). Add a drawback or lower the stats." % (p, t, mv, 2 * mv + 2))
            elif t <= 0 and not re.search(r"\bgets?\b|\b[+-]\d", low):
                add("Needs review", "Stats", "pt-zero-toughness", typeline, "%d/%d" % (p, t), "A creature with 0 toughness dies immediately unless something boosts it.")

    # ---- ability wording ----
    for fld in card["rules"]:
        for line in fld["plain"].split("\n"):
            s = line.strip()
            if not s:
                continue
            if re.match(r"^(?:\{[^}]+\}[,\s]*)+(?=[A-Za-z])", s) and ":" not in s.split(".")[0]:
                add("Likely error", "Punctuation", "cost-no-colon", s, re.match(r"^(?:\{[^}]+\}[,\s]*)+", s).group(0).strip(),
                    "This line starts like an activated ability cost but has no colon after the cost.", fld["key"])
            m = re.match(r"^choose (?:one|two|three|one or both|one or more|up to (?:one|two|three))(?=\s*(?:[—–:\-]|$))", s, re.I)
            if m:
                bullets = sum(1 for x in fld["plain"].split("\n") if x.strip().startswith("•"))
                if 0 < bullets < 2:
                    add("Likely error", "Missing term", "modal-one-option", s, m.group(0), "A “Choose …” card needs at least two bulleted modes, but this one has only one.", fld["key"])
    if re.search(r"(?:instant|sorcery)", ty) and "creature" not in ty and not is_token and one_face:
        for line in rules.split("\n"):
            unq = re.sub(r"“[^”]*”|\"[^\"]*\"", " ", re.sub(r"\([^)]*\)", " ", line))
            if re.match(r"^\s*\{[TQ]\}", unq):
                add("Likely error", "Templating", "tap-symbol-spell", line.strip(), "{T}", "Instants and sorceries shouldn't have activated abilities that tap.", key)
                break
    # repeated keywords / contradictory keyword pairs
    first = re.sub(r"\([^)]*\)", "", rules.split("\n")[0]) if rules.strip() else ""
    kws = [k.strip().lower() for k in re.split(r"[,;]", first) if k.strip()]
    seen, dup = set(), None
    for k in kws:
        if len(k) < 25 and re.fullmatch(r"[a-z ]+", k) and k in seen:
            dup = k
            break
        seen.add(k)
    if dup and (is_token or re.search(r"each instance|triggers separately|more than one instance|separately", low)
                or dup in ("prowess", "lifelink", "flanking", "bushido", "exalted", "afflict", "annihilator", "battle cry", "melee", "toxic",
                           "afterlife", "dethrone", "training", "modular", "rampage", "cascade", "storm", "ripple", "persist", "undying", "evolve")):
        dup = None   # deliberately stacked keywords
    if dup:
        add("Needs review", "Repeated word", "dup-keyword", first.strip(), dup, "The keyword “%s” is listed twice on this card." % dup, key)
    for a, b, why in _REDUNDANT:
        if re.search(r"(?m)^(?:[^\n(]*[,;] ?)?%s\b" % a, low) and re.search(r"(?m)^(?:[^\n(]*[,;] ?)?%s\b" % b, low):
            add("Suggestion", "Redundant keywords", "keyword-redundant", first.strip() or typeline, a, why, key)
    if "defender" in kws and re.search(r"\bwhenever [^.]*\battacks\b", low) and "can attack as though" not in low:
        add("Suggestion", "Redundant keywords", "defender-attacks", first.strip(), "defender", "This creature has defender, so it can't attack, but its text triggers when it attacks.", key)

    # ---- flavor ----
    fl = " ".join(f["plain"] for f in card["flavor"])
    ft = re.sub(r"(?m)^\s*[—–-].*$", "", fl).strip()
    if len(ft.split()) >= 4 and re.search(r"[A-Za-z0-9]$", ft):
        add("Suggestion", "Flavor text", "flavor-no-end-punct", fl.strip().split("\n")[0], ft[-12:], "The flavor text doesn't end with punctuation (a period, a closing quote…).")
    return out


def check_extra_set(cards, ctx, fl):
    if ST["kind"] == "text" or len(cards) < 2:
        return

    def add(idx, *a, **k):
        fl[idx].append(mk(*a, **k))
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", (s or "").lower())).strip()
    # same flavor text on two cards, and look-alike cards
    byflav, bysig = defaultdict(list), defaultdict(list)
    for c in cards:
        t = _types(c)
        if "token" in t or re.search(r"\bbasic\b", t):
            continue
        ft = norm(" ".join(f["plain"] for f in c["flavor"]))
        if len(ft) >= 20:
            byflav[ft].append(c["idx"])
        rt = norm("\n".join(f["plain"] for f in c["rules"]).replace(c["name"], "~") if c["name"] else "")
        if len(rt) >= 15:
            bysig[(rt, c["cost"].strip(), t, c["power"], c["toughness"])].append(c["idx"])
    for v in byflav.values():
        if len(v) > 1:
            for i in v:
                add(i, "Needs review", "Flavor text", "dup-flavor", cards[i]["name"], "flavor", "The same flavor text is on more than one card (%s)." % ", ".join("#%d" % (j + 1) for j in v if j != i))
    for v in bysig.values():
        if len(v) > 1:
            for i in v:
                add(i, "Suggestion", "Possible duplicate", "dup-card", cards[i]["name"], cards[i]["name"],
                    "This card is identical in cost, type, stats and rules to %s. Is it an accidental copy?" % ", ".join("“%s”" % cards[j]["name"] for j in v if j != i))
    # tokens: made by nothing / no token card for what is made
    toks = [c for c in cards if "token" in _types(c) and c["name"].strip()]
    others = [c for c in cards if "token" not in _types(c)]
    alltext = "\n".join("\n".join(f["plain"] for f in c["rules"]) for c in others).lower()
    if len(cards) >= 5:
        for t in toks:
            nm = t["name"].strip().lower()
            sub = t["subtype"].strip().lower()
            cands = {nm, nm.rstrip("s")} | {w for w in re.findall(r"[a-z]+", sub) if len(w) > 2}
            if not any(re.search(r"\b%s\b" % re.escape(x), alltext) for x in cands if x):
                add(t["idx"], "Suggestion", "Tokens", "token-unused", t["name"], t["name"], "No card in this file creates this token (“%s”)." % t["name"])
    if len(toks) >= 3:
        have = {w for t in toks for w in re.findall(r"[a-z]+", (t["name"] + " " + t["subtype"]).lower())}
        for c in others:
            for m in re.finditer(r"create[s]? (?:a|an|two|three|four|X|that many|\d+)[^.]*?\b(?:[A-Z][a-z]+)\s+(?:artifact )?(?:creature )?tokens?\b", "\n".join(f["plain"] for f in c["rules"])):
                typ = re.findall(r"\b([A-Z][a-z]{2,})\b", m.group(0).split("create", 1)[-1])
                typ = [x.lower() for x in typ if x.lower() not in ("create", "creature", "artifact", "token", "white", "blue", "black", "red", "green", "colorless", "legendary")]
                if typ and not any(x in have or x.rstrip("s") in have for x in typ):
                    add(c["idx"], "Suggestion", "Tokens", "token-no-card", c["name"], m.group(0)[:80], "This card makes a %s token, but there is no matching token card in the file." % typ[-1])
                    break
