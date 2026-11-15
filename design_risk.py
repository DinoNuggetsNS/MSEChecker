"""MSECheck - design risk."""
import re
from .vocabulary import VOCAB
from .templating import PHRASES, REF_MANA, REF_MODAL, REF_PW, STOP, _types, ref
from .context import mk
from .scryfall_data import ORACLE, _docs_with_all, _strip_name


# ----------------------------------------------------------------------------------------
# Design-risk checks: wording that tends to cause infinite loops, rules bugs or balance
# problems only after a card is printed and players start combining it with other cards.
# These are heuristics: most are "Needs review", not "Likely error".
# ----------------------------------------------------------------------------------------
DR = "Design risk"
_NUMW = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "x": 99, "all": 99}
_COLORS = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
_NOSTACK = r"first time|once each turn|each turn|only once|once per turn"
# “another target X”, “other target X”, “up to one other target X”, “target X other than ~ / this creature”
_OTHER_RX = r"\banother\b|\bother\b|\bnot (?:~|this \w+|itself)\b|\bexcept (?:for )?(?:~|this \w+|itself)\b|\bthat isn't (?:~|this \w+)\b"
_STATE_WORDS = (r"tapped|untapped|attacking|blocking|blocked|damaged|enchanted|equipped|exiled|face-down|face down|monstrous|renowned|"
                r"prepared|modified|suspected|token|entered|summoning[- ]sick")


def _self_safe(pre, quals, tail, selftypes=()):
    """True when a target can't (or needn't) be the source itself: optional (“up to”), another/other, an opponent's or something you
    don't control, a state the source isn't in (tapped, attacking, token …), or any “with / that / whose …” restriction."""
    text = (pre + " " + quals + " " + tail).lower()
    if re.search(_OTHER_RX, text):
        return True
    if re.search(r"\bup to\b|\bopponent|\bdon't control|\bdo not control|\bdefending player|\bnot yours\b|\bthat player controls|"
                 r"\btarget player controls|\beach other\b", text):
        return True
    if re.search(r"\b(?:%s)\b" % _STATE_WORDS, quals.lower()) and not re.search(r"\bnontoken\b", quals.lower()):
        return True
    if selftypes and re.search(r"\bnon(?:%s)\b" % "|".join(selftypes), quals.lower()):
        return True
    if re.match(r"\s*(?:with|having|whose|that|which|named|of an? |of the chosen|in a graveyard|in your graveyard|from)\b", tail.lower()):
        return True
    return False


REF_FLICKER = ref("Felidar Guardian", "the reference for flicker + planeswalker reset (note “another target permanent”)",
                  'o:"exile another target permanent you control, then return it"')
REF_ORING = ref("Banishing Light", "the modern “until this leaves the battlefield” template", 'o:"until this enchantment leaves the battlefield"')
REF_ANOTHER = ref("Hostage Taker", "uses “another target creature or artifact” so the ETB can't pick itself", 'o:"exile another target creature or artifact"')
REF_UNTAP = ref(None, "creatures that untap on enter", 'o:"enters" o:"untap target" t:creature')
REF_PUNISH = ref("Mindcrank", "the reference for life-loss feedback loops", '!"Mindcrank"')
REF_PIE = ref(None, "the Mana Pie / colour pie reference", 'o:"counter target spell"')


def _cost_tokens(cost):
    return re.findall(r"\{([^{}]*)\}", cost or "") or re.findall(r"\d+|[A-Za-z]/[A-Za-z](?:/[A-Za-z])?|[A-Za-z]", cost or "")


def _mv(cost):
    n = 0
    for t in _cost_tokens(cost):
        if t.isdigit():
            n += int(t)
        elif t.upper() in ("X", "Y", "Z"):
            continue
        elif re.match(r"2/[A-Za-z]", t):
            n += 2
        else:
            n += 1
    return n


def _mana_count(text):
    """How much mana a run of symbols is: {3} = 3, {U}{U} = 2, {X} = 0 (not counting {T})."""
    n = 0
    for t in re.findall(r"\{([^{}]*)\}", text or ""):
        if t.isdigit():
            n += int(t)
        elif t.upper() in ("T", "Q", "X", "S", "E"):
            continue
        else:
            n += 1
    return n


def _self_norm(line, card):
    """Reminder text removed and the card's own name / “this creature” replaced by ~ so patterns can see self-references."""
    s = re.sub(r"\([^)]*\)", "", line).replace("\u2019", "'").replace("\u2018", "'")
    nm = card["name"].strip()
    if nm:
        s = re.sub(re.escape(nm), "~", s, flags=re.I)
        short = nm.split(",")[0].strip()
        if short and short != nm and len(short) > 2:
            s = re.sub(r"\b" + re.escape(short) + r"\b", "~", s)
    s = re.sub(r"\bthis (?:creature|artifact|enchantment|land|permanent|planeswalker|equipment|aura|vehicle|saga|spell|card|token)\b",
               "~", s, flags=re.I)
    return s.strip()


_PIE = [  # (pattern, colours allowed to do this, plain description)
    (r"\bcounter target (?:\w+ )?spell\b", set("U"), "counter a spell"),
    (r"\bdeals? (?:\d+|x) damage to (?:any target|target (?:creature|player|opponent|planeswalker))", set("R"), "deal direct damage"),
    (r"\bdestroy target (?:non\w+ )*creature\b", set("BWR"), "destroy a creature"),
    (r"\bgains? (?:\d+|x) life\b", set("WGB"), "gain life"),
]


_COMBO_NAMES = re.compile(r"Helm of Awakening|Cloud Key|Felidar|Saheeli|Restoration Angel|Kiki|Mindcrank|Duskmantle|Basalt|"
                          r"Power Artifact|Great Whale|Palinchron|Peregrine|Tolarian|Gaea|Splinter Twin|Pestermite|Deceiver|"
                          r"Melira|Kitchen Finks|Requiem Angel|Oblivion Ring|Faceless Butcher|Delina|It That Betrays")


def _soft(why):
    """Design-risk notes are friendly heads-ups, not verdicts: no named combo cards, phrased as 'keep in mind'."""
    why = re.sub(r"\s*\([^()]*\)", lambda m: "" if _COMBO_NAMES.search(m.group(0)) else m.group(0), why)
    why = re.sub(r"\s+([.,])", r"\1", why).strip()
    if not why.lower().startswith("keep in mind"):
        why = "Keep in mind: " + (why[0].lower() + why[1:] if len(why) > 1 and not why[1].isupper() else why)
    return why


def check_design(card, ctx):
    out = []
    ty = _types(card)
    if not ty.strip() and not card["rules"]:
        return out
    key0 = card["rules"][0]["key"] if card["rules"] else "rule text"
    mv = _mv(card["cost"])
    is_creature = "creature" in ty
    is_perm = any(t in ty for t in ("creature", "artifact", "enchantment", "land", "planeswalker", "battle"))
    selftypes = {t for t in ("creature", "artifact", "enchantment", "land", "planeswalker") if t in ty}
    lines = []
    for f in card["rules"]:
        raw = f["plain"].split("\n")
        for i, ln in enumerate(raw):
            if ln.strip():
                lines.append((f["key"], ln, _self_norm(ln, card), raw, i))
    full_low = "\n".join(l[2].lower() for l in lines)

    def add(sev, rid, ln, k, m, why, rf=None):
        txt = m.group(0) if hasattr(m, "group") else (m or "")
        if txt not in ln:
            txt = txt.replace("'", "\u2019")
        if txt not in ln:
            txt = ""
        out.append(mk(sev, DR, rid, ln, txt, why if rid == "dr-cost-reduction" else _soft(why), None, rf, k))

    # ---- mana-producing lines (for untap loops) ----
    produced = 0
    for _, orig, s, _, _ in lines:
        mm = re.search(r"\{T\}[^:]*:\s*add\s+((?:\{[^{}]+\})+)(?!\s*for each)", s, re.I)
        if mm and not re.search(r"for each|equal to", s, re.I):
            produced = max(produced, _mana_count(mm.group(1)))

    for k, orig, s, raw, idx in lines:
        low = s.lower()
        trig = eff = ""
        tm = re.match(r"(when|whenever|at)\b(.*?),\s*(.*)$", low)
        if tm:
            trig, eff = tm.group(2), tm.group(3)
        optional = bool(re.search(r"\byou may\b|\bmay\b", eff))
        once = bool(re.search(r"activate (?:this ability )?(?:only )?(?:once each turn|no more than once|only once|only as a sorcery)", low))

        # ===== 1 / 5. flicker and self-targeting mandatory triggers ==========================
        is_flicker = bool(re.search(r"\bexile\b[^.]*\btarget\b", low) and re.search(
            r"\b(?:then )?return (?:it|that card|that creature|that permanent|them|the exiled card)\b[^.]*\bto the battlefield\b|"
            r"\bthen return (?:it|that card|that permanent)\b|next end step, return", low))
        tgt = re.search(r"target ((?:[\w'-]+ ){0,4}?)(permanent|creature|artifact|enchantment|land|planeswalker)s?\b", low)
        if is_flicker and tgt:
            typ, quals = tgt.group(2), tgt.group(1)
            if typ == "permanent":
                add("Needs review", "dr-flicker-any-permanent", orig, k, tgt,
                    "This blink can target any permanent, including planeswalkers: blinking a planeswalker resets its loyalty, and "
                    "blinking a creature with an enters-the-battlefield effect can loop.",
                    REF_FLICKER)
            elif (typ in selftypes and tm and not optional and "~" in trig and "enters" in trig
                  and not _self_safe(low[max(0, tgt.start() - 24):tgt.start()], quals, low[tgt.end():].split(".")[0], selftypes)):
                add("Needs review", "dr-flicker-self", orig, k, tgt,
                    "A mandatory enters trigger that flickers “target %s” can pick itself, so it re-triggers forever. Use "
                    "“another target %s” or make it “you may”." % (typ, typ), REF_ANOTHER)
        elif tm and is_perm and not optional and re.search(r"~ (?:enters|attacks)", trig) \
                and re.search(r"\b(?:exile|destroy|sacrifice)\b|\breturn\b[^.]*\bto (?:its owner's|their owner's) hand", eff):
            for tg in re.finditer(r"target ((?:[\w'-]+ ){0,4}?)(permanent|creature|artifact|enchantment|land|planeswalker)s?\b", eff):
                typ, quals = tg.group(2), tg.group(1)
                tail = eff[tg.end():].split(".")[0]
                if typ != "permanent" and typ not in selftypes:
                    continue
                if _self_safe(eff[max(0, tg.start() - 24):tg.start()], quals, tail, selftypes):
                    continue
                add("Needs review", "dr-self-target", orig, k, tg,
                    "This mandatory trigger says “target %s” but the card is itself a %s, so with no other legal target it must "
                    "pick itself. Add “another”, “you don't control”, or “up to one”." % (typ, "/".join(sorted(selftypes)) or "permanent"),
                    REF_ANOTHER)
                break

        # ===== 2 / O-Ring race: split exile / return ===========================================
        if re.search(r"^when (?:~ )?enters[^,]*,[^.]*\bexile\b", low) and "until" not in low and \
                re.search(r"\bwhen ~ leaves the battlefield,[^.]*\breturn\b", full_low):
            add("Needs review", "dr-split-exile", orig, k, "exile",
                "The exile and the return are two separate triggers. If this leaves the battlefield while the enter trigger is on the "
                "stack, the exile happens afterwards and is permanent (the old Oblivion Ring / Faceless Butcher problem). "
                "Modern wording is one sentence: “Exile target … until ~ leaves the battlefield.”", REF_ORING)

        # ===== 3. self-copying / self-rolling triggers =========================================
        for sm_ in re.finditer(r"(?:^|\. )(?:when|whenever)\b([^,.]*),\s*([^.]*)", low):
            t_, e_ = sm_.group(1), sm_.group(2)
            if not (re.search(r"\b(?:cast or copy|copy|copies|roll|rolls|flip|flips)\b", t_)
                    and re.search(r"\b(?:copy|copies|roll|flip)\b", e_)
                    and not re.search(r"\bmay\b", e_) and not re.search(_NOSTACK, low)):
                continue
            add("Needs review", "dr-copy-loop", orig, k, sm_.group(0).strip(". ")[:40],
                "This trigger fires on a copy/roll/flip and its effect copies/rolls/flips again, so it can retrigger itself without end. "
                "Make the repeat “you may”, add “once each turn”, or use a hard cap (the Delina, Wild Mage errata).")

        # ===== 4 / 8. free activations and untap engines =======================================
        am = re.match(r"^([^:•—]{1,90}):\s*(.+)$", s)
        if am and not tm and not re.match(r"^[+\-−–]?(?:\d+|X)$", am.group(1).strip()) \
                and re.search(r"\{|pay|sacrifice|discard|tap|exile|remove|reveal|mill|untap|return", am.group(1), re.I) \
                and not re.match(r"(?:choose|level|chapter)\b", am.group(1), re.I):
            cost, aeff = am.group(1), am.group(2).lower()
            mana_cost = re.search(r"\{(?!T\}|Q\}|0\})[^}]+\}", cost)
            loopy = re.search(r"\buntap\b|return [^.]*to (?:its owner's|your|their) hand|exile [^.]*then return|\bcopy\b|\bcreate\b", aeff)
            if re.search(r"\{0\}", cost) and not once:
                add("Likely error" if loopy else "Needs review", "dr-zero-cost", orig, k, cost,
                    "An activated ability that costs {0} can be repeated any number of times in a turn. Add a real cost or "
                    "“Activate only once each turn.”")
            elif not mana_cost and not once and re.search(r"\buntap\b", aeff) \
                    and not re.search(r"\{T\}|\{Q\}|sacrifice|exile|discard", cost, re.I):
                add("Needs review", "dr-free-untap", orig, k, cost,
                    "A repeatable ability with no mana cost that untaps something can combine with other cards to loop. "
                    "Add a mana cost or “Activate only once each turn.”")
            elif not mana_cost and not once and loopy and not re.search(r"\{T\}|sacrifice|exile|discard", cost, re.I):
                add("Suggestion", "dr-free-ability", orig, k, cost,
                    "An ability paid only with a soft cost (life, counters…) that bounces, copies or creates can be chained. "
                    "Consider “Activate only once each turn.”")
            if re.search(r"untap ~", aeff) and produced:
                n = _mana_count(cost)
                if n and n <= produced:
                    add("Likely error", "dr-mana-untap-loop", orig, k, cost,
                        "This card taps for %d mana and untaps itself for %d, so it nets mana forever (Basalt Monolith + Power "
                        "Artifact). Make the untap cost more than the mana produced." % (produced, n))
        if tm and "~ enters" in trig:
            um = re.search(r"\buntap (?:up to (\w+) |all |(?:another|other) target |another |other |target |(\w+) )?(lands?|permanents?|creatures?|artifacts?|nonland permanents?)\b", eff)
            if um and not ((um.group(2) or "").lower() in ("that", "those", "it", "them", "each")
                           or re.search(r"\bgain control of\b|\bcontrol of target\b|\bdon't control\b|\bdo not control\b|\bopponent(?:'s)? controls?\b|"
                                        r"\bopponent's\b|\bdefending player\b|\bthat player controls\b", eff)):
                cnt = _NUMW.get((um.group(1) or um.group(2) or "").lower(), 0)
                if um.group(3).startswith("land") and cnt and mv and cnt >= mv:
                    add("Likely error", "dr-etb-untap", orig, k, um,
                        "This card untaps %d lands when it enters, and it only costs %d: it pays for itself and can be replayed "
                        "with bounce or flicker (Great Whale / Palinchron / Peregrine Drake)." % (cnt, mv), REF_UNTAP)
                else:
                    add("Needs review", "dr-etb-untap", orig, k, um,
                        "An enters trigger that untaps lands or permanents can loop with flicker or copy effects (Pestermite / "
                        "Deceiver Exarch + Splinter Twin, Palinchron). Check the cost against what it untaps.", REF_UNTAP)

        # ===== 7. mana scaling / doubling ======================================================
        mm = re.search(r"\badd\b[^.]*?\b(?:for each|for every|equal to|that much mana|an amount of mana)\b|\badd x\b", low)
        if mm and not re.search(r"activate (?:this ability )?(?:only )?(?:once each turn|no more than once|only once)", low):
            add("Needs review", "dr-mana-scaling", orig, k, mm,
                "Mana that scales with a board count can explode on cheap permanents (Tolarian Academy / Gaea's Cradle). "
                "Check the cost, cap, or tap/sacrifice requirement.%s" % ("  This card only costs %d." % mv if 0 < mv <= 3 else ""),
                REF_MANA)
        mm = re.search(r"tapped for mana[^.]*?(?:additional|twice|an extra|instead)|(?:adds?|produces?) (?:an additional|twice)", low)
        if mm and not re.search(r"\b(?:enchanted|equipped|fortified) (?:land|permanent|creature|artifact|basic land)\b|"
                                r"\b(?:this|~) (?:land|permanent|artifact|creature|enchantment) is tapped for mana\b|\bif ~ is tapped for mana\b", low):
            add("Needs review", "dr-mana-scaling", orig, k, mm,
                "Mana doubling replacement effects turn every other mana source into a combo piece. Make sure the cost and "
                "restrictions match that power.", REF_MANA)

        # ===== 9. token factories off token events ============================================
        tk = re.match(r"(?:whenever|when) (.*?) (dies|enters|leaves the battlefield|is put into a graveyard from the battlefield)(?: under your control)?,\s*(.*)$", low)
        if tk and "creature token" in tk.group(3) and "create" in tk.group(3) and "~" not in tk.group(1):
            subj = tk.group(1)
            if not re.search(r"non-?token", subj):
                tdesc = re.search(r"create (.*?)tokens?", tk.group(3))
                words = {w for w in re.findall(r"[a-z]{4,}", tdesc.group(1)) if w not in
                         {"tapped", "white", "blue", "black", "red", "green", "colorless", "creature", "artifact", "legendary", "that", "with", "have", "flying"}} if tdesc else set()
                clash = [w for w in words if re.search(r"\b%ss?\b" % w, subj) and not re.search(r"non-?%s" % w, subj)]
                excluded = any(re.search(r"non-?%s" % w, subj) for w in words)
                if excluded:
                    pass
                elif clash:
                    add("Likely error", "dr-token-loop", orig, k, tk.group(0)[:40],
                        "The token this makes (%s) is also caught by the trigger condition, so each token creates another "
                        "(Requiem Angel needs “non-Spirit”). Exclude the token type." % clash[0].capitalize())
                elif "creature" in subj:
                    add("Needs review", "dr-token-loop", orig, k, tk.group(0)[:40],
                        "A trigger on any creature dying/entering that makes a creature token catches its own tokens. "
                        "Add “nontoken” or exclude the token's type so it can't chain with sacrifice outlets.")

        # ===== 10 / feedback: punisher triggers with no cap ====================================
        if tm and not re.search(_NOSTACK, low):
            if re.search(r"\b(?:an opponent|each opponent|a player|each player)\b[^,]*\b(?:draws?|taps?|plays? a land|casts?|activates?|"
                         r"loses? life|puts?[^,]*into (?:their|a|an opponent's) graveyard)\b", trig) \
                    and re.search(r"\bloses? [^.]*life\b|\bdeals? \w+ damage\b|\bmills?\b", eff):
                add("Suggestion", "dr-punisher-uncapped", orig, k, tm.group(0)[:40],
                    "Keep in mind that damage, life loss or mill on every instance of an opponent's action has no cap, so it adds up "
                    "with repeatable effects. A small amount (as here) or a limit like “the first time each turn” keeps it in check.",
                    REF_PUNISH)
            elif (re.search(r"\blose[s]? life\b|\byou gain life\b|\bgains? life\b", trig)
                  and re.search(r"\b(?:loses?|gains?) (?:that much|that many|\d+|x) life\b|\bmills? that many\b", eff)):
                add("Needs review" if "that" not in eff else "Likely error", "dr-life-feedback", orig, k, tm.group(0)[:40],
                    "A trigger on gaining/losing life that itself gains/loses life (or uses “that much”) can feed on itself. "
                    "Add a once-each-turn limit.", REF_PUNISH)

        # ===== 11. planeswalker free value ====================================================
        pw = re.match(r"^\[?([+\-−–]?\d+|[+\-−–]?X|0)\]?\s*:\s*(.+)$", s)
        if pw and "planeswalker" in ty:
            cost_s, peff = pw.group(1), pw.group(2).lower()
            if not re.match(r"[\-−–]", cost_s):
                if re.search(r"\bdestroy target\b|\bexile target\b|deals? (?:\d+|x) damage to (?:any target|target|each)|"
                             r"gets? -\d+/-\d+|to its owner's hand", peff):
                    add("Needs review", "dr-pw-free-removal", orig, k, cost_s + ":",
                        "Removal on a 0 or + ability means the planeswalker removes a permanent every turn and also gains loyalty. "
                        "Make it a minus ability or add a real drawback.", REF_PW)
                tkn = re.search(r"create [^.]*?(\d+)/\d+[^.]*creature token", peff)
                if tkn and int(tkn.group(1)) >= 3:
                    add("Suggestion", "dr-pw-free-blocker", orig, k, cost_s + ":",
                        "A 0 or + ability that makes a big creature token each turn protects the planeswalker for free.", REF_PW)

        # ===== 12. sacrifice costs with no type ================================================
        sm = re.match(r"^([^:]*\bsacrifice (?:a|an|any number of|two|three|x) permanents?\b[^:]*):", low)
        if sm:
            add("Suggestion", "dr-sac-any-permanent", orig, k, "permanent",
                "“Sacrifice a permanent” as a cost lets tokens, lands and every other permanent feed this ability. "
                "Name a type (“a creature”, “an artifact”) or “another permanent you control”.")

        # ===== 15. sacrifice loops =============================================================
        if tm and re.search(r"\b(?:dies|is sacrificed|are sacrificed|sacrifices?)\b", trig) and not optional \
                and re.search(r"\b(?:each player |target player |each opponent |you )?sacrifices? (?:a|an|another|two|x|that)\b", eff) \
                and "~" not in trig:
            add("Needs review", "dr-sacrifice-loop", orig, k, tm.group(0)[:40],
                "A mandatory sacrifice triggered by a creature dying/being sacrificed can chain with itself, leaving players with "
                "no way to stop it (It That Betrays-style loops). Make it optional or add a once-each-turn limit.")

        # ===== 14. instant-speed sweepers ======================================================
        if "instant" in ty and "creature" not in ty:
            wm = re.search(r"\b(?:destroy|exile) all\b|deals? (?:\d+|x) damage to each (?:creature|permanent|nonland permanent)|"
                           r"all creatures [^.]*get -\d+/-\d+|return all [^.]*(?:to (?:their owners'?|its owner's) hands?)", low)
            if wm:
                onesided = re.search(r"don't control|do not control|opponents? control|target (?:player|opponent) controls", low)
                add("Suggestion" if onesided else "Needs review", "dr-instant-wipe", orig, k, wm,
                    "A board wipe at instant speed is much stronger than at sorcery speed. Consider a sorcery, a higher cost or a drawback."
                    + (" (It only hits one side, which softens this.)" if onesided else ""))

        # ===== 17. cost reduction =============================================================
        cr = re.search(r"\bcosts? (\{[^}]+\}|\d+|x) less to cast\b|\bcosts? (\{[^}]+\}) less\b", low)
        if (cr and not re.search(r"can't reduce|less than one|can't be reduced|more than", low)
                and not re.search(r"\bless to activate\b", low)               # activated abilities are fine
                and not (am and re.search(r"\{[TQ]\}", am.group(1)))):       # tap/untap costs keep it from being repeated for free
            self_cost = "~ costs" in low
            variable = bool(re.search(r"for each|x less|\{x\}", low))
            _fc = card.get("cost2") if (re.search(r"\d$", k) and card.get("cost2")) else card["cost"]
            toks = _cost_tokens(_fc)
            generic = sum(int(t) for t in toks if t.isdigit())
            colored = sum(1 for t in toks if not t.isdigit() and t.upper() not in ("X", "Y", "Z"))
            amt = _mana_count(cr.group(0))
            if not amt:
                nm_ = re.search(r"\b(\d+)\b", cr.group(0))
                amt = int(nm_.group(1)) if nm_ else 0
            # A card reducing only its own cost can only reach {0} if it has no coloured symbols and the reduction covers the generic part.
            if self_cost:
                can_be_free = bool(toks) and colored == 0 and (variable or amt >= generic)
            else:
                # a flat {1} only takes generic mana off one cost: it can't make anything meaningfully free
                can_be_free = variable   # a fixed generic reduction (“costs {2} less”) never makes a spell free by itself
            _fe = re.search(r"for each ([^.,;]*)", low)
            if _fe and not re.search(r"\b(?:artifact|permanent|spell|x)\b", _fe.group(1)):
                can_be_free = False   # “for each Angel / creature / land …” is bounded by the board, not a free-spell engine
            if can_be_free:
                add("Needs review" if variable else "Suggestion",
                    "dr-cost-reduction", orig, k, cr,
                    "Be aware this card can be reduced to less than one mana.")

        # ===== copy effects on activated abilities: legendary =================================
        if am and not tm:
            cm = re.search(r"create (?:a|an|one|x)? ?(?:\w+ )?(?:token that's a copy of|token that is a copy of|copy of) (?:another |other )?"
                           r"target ((?:[\w-]+ ){0,3}?)(creature|nonland permanent|permanent|artifact)\b", am.group(2).lower())
            if (cm and "nonlegendary" not in cm.group(1) and "legendary" not in cm.group(0)
                    and not re.match(r"\[?[+\-\u2212\u2013]?(?:\d+|X)\]?$", am.group(1).strip())          # loyalty abilities are once per turn
                    and not re.search(r"only once each turn|once each turn|no more than once", low)):
                add("Suggestion", "dr-copy-legendary", orig, k, cm,
                    "A repeatable copy effect that can copy legendary permanents triggers the legend rule, and with haste/ETB effects "
                    "it becomes a combo engine (Kiki-Jiki says “nonlegendary”). Consider restricting it.")

    # ===== persist / undying interaction ======================================================
    for k, orig, s, raw, idx in lines:
        low = s.lower()
        mm = re.search(r"can't have -1/-1 counters|can't have \+1/\+1 counters|remove (?:a|all|that many) -1/-1 counters?|"
                       r"remove (?:a|all|that many) \+1/\+1 counters?", low)
        if mm:
            add("Needs review", "dr-counter-immunity", orig, k, mm,
                "Preventing or removing -1/-1 (or +1/+1) counters makes persist/undying creatures return forever with a sacrifice outlet "
                "(Melira + Kitchen Finks). Check how this works with persist/undying in your set.")

    # ===== modal spells where every mode needs a target =======================================
    for k, orig, s, raw, idx in lines:
        mm = re.match(r"^choose (two|three|one or more|up to (?:two|three))\b", s.lower())
        if mm:
            modes, j = [], idx + 1
            while j < len(raw) and raw[j].strip().startswith("•"):
                modes.append(raw[j].lower())
                j += 1
            if len(modes) >= 2 and all("target" in m for m in modes) and mm.group(1) in ("two", "three"):
                add("Suggestion", "dr-modal-all-targets", orig, k, mm.group(0),
                    "Every mode needs a target, so the spell can't be cast unless the player has enough legal targets for the number "
                    "of modes they must choose. Make at least one mode untargeted, or use “one or more”.", REF_MODAL)

    # ===== 13. hybrid cost with colour-specific text =========================================
    pairs = [set(m.groups()) for m in (re.fullmatch(r"([WUBRG])/([WUBRG])", t.upper()) for t in _cost_tokens(card["cost"])) if m]
    if pairs and lines:
        for pat, allowed, what in _PIE:
            for k, orig, s, raw, idx in lines:
                mm = re.search(pat, s.lower())
                if not mm:
                    continue
                bad = {c for p in pairs for c in p if c not in allowed}
                if bad:
                    nm_bad = "/".join(_COLORS[c] for c in sorted(bad))
                    add("Needs review", "dr-hybrid-bleed", orig, k, mm,
                        "A hybrid card has to be legal as a mono-colour card in either colour. Here it could be played as mono-%s, "
                        "which usually can't %s. Check the colour pie." % (nm_bad, what), REF_PIE)
                break

    # ===== 20. P/T problems ====================================================================
    pt = (card["power"] + "/" + card["toughness"])
    if "*" in pt and not re.search(r"(?:power|toughness)[^.]*\bequal to\b|\*/\*", full_low):
        add("Needs review", "dr-cda-missing", card["name"], key0, "*",
            "Power or toughness is * but no rule text says what * equals.")
    if (card["power"] or card["toughness"]) and "creature" not in ty and "vehicle" not in ty and ty.strip() and "token" not in ty:
        add("Suggestion", "dr-pt-noncreature", card["name"], key0, card["power"] + "/" + card["toughness"],
            "This card has power/toughness filled in but is not a creature or Vehicle, so the values may be stale.")
    return out


_KT_CACHE = {}


def _has_results(terms):
    """True if some real card contains every one of these search terms (so the Scryfall link never comes back empty)."""
    if not ORACLE.get("texts"):
        return True
    key = tuple(terms)
    if key not in _KT_CACHE:
        needles = [t[2:].strip('"') for t in terms]
        vocab, df, texts = ORACLE["vocab"], ORACLE["df"], ORACLE["texts"]
        ids = {vocab[w] for n in needles for w in re.findall(r"[a-z]+", n) if w in vocab}
        if ids:  # only look at cards that contain all the words, then confirm the exact phrase
            pool = _docs_with_all(sorted(ids, key=lambda t: (df[t], t)))
        else:
            pool = range(len(texts))
        _KT_CACHE[key] = any(all(n in texts[i] for n in needles) for i in pool)
    return _KT_CACHE[key]


def key_terms(text, name="", n=2):
    """At most `n` (1-2) important search terms from this wording: one key phrase and/or distinctive words.
    The card's own name is removed first, so it can never end up in the search."""
    if n <= 0:
        return []
    low = _strip_name(text, name).lower()
    own = set(re.findall(r"[a-z]{3,}", (name or "").lower()))
    out, taken = [], ""
    hits = [p for p in PHRASES if p in low]
    if hits:
        taken = max(hits, key=len)
        out.append('o:"%s"' % taken)
    words = [w for w in dict.fromkeys(re.findall(r"[a-z]{4,}", low)) if w in VOCAB and w not in STOP and w not in own and w not in taken]
    vocab = ORACLE.get("vocab") or {}
    if vocab:  # most distinctive words first (rare in real cards), ignoring ones that are too rare to be useful
        idf, df = ORACLE["idf"], ORACLE["df"]
        good = [w for w in words if w in vocab and df[vocab[w]] >= 8]
        words = sorted(good or words, key=lambda w: -idf.get(vocab.get(w), 0))
    else:
        words.sort(key=lambda w: (-len(w), w))
    for w in words[:6]:
        if len(out) >= n:
            break
        cand = out + ["o:" + w]
        if not out or _has_results(cand):
            out = cand
    return out


def similar_query(line, name=""):
    return " ".join(key_terms(line, name, 2))
