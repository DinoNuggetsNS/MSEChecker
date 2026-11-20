"""MSECheck - templating."""
import re, urllib.parse


# ----------------------------------------------------------------------------------------
# References / templating rules
# ----------------------------------------------------------------------------------------
SCRY = "https://scryfall.com/search?q="


def surl(q):
    return SCRY + urllib.parse.quote_plus(q)


def ref(name, note, query):
    return {"name": name, "note": note, "query": query,
            "url": surl('!"%s"' % name) if name else surl(query), "qurl": surl(query)}


REF_SEARCH = ref("Cultivate", "a useful reference for search-and-shuffle wording", 'o:"search your library" o:"then shuffle"')
REF_ETB = ref("Mulldrifter", "a useful reference for enters-the-battlefield wording", 'o:"this creature enters"')
REF_DIES = ref("Blood Artist", "a useful reference for “dies” wording", 'o:"creature dies"')
REF_EXILE = ref("Swords to Plowshares", "a useful reference for exile wording", 'o:"exile target creature"')
REF_MV = ref("Pernicious Deed", "a useful reference for mana value wording", 'o:"mana value"')
REF_ANY = ref("Lightning Bolt", "a useful reference for “any target” wording", 'o:"damage to any target"')
REF_MODAL = ref("Cryptic Command", "a useful reference for modal “Choose …—” wording", 'o:"choose two —"')
REF_PUMP = ref("Giant Growth", "a useful reference for temporary-boost wording", 'o:"gets +3/+3 until end of turn"')
REF_DMG = ref("Lightning Bolt", "a useful reference for damage wording", 'o:"deals 3 damage to"')
REF_BOUNCE = ref("Unsummon", "a useful reference for returning a permanent to its owner's hand", 'o:"to its owner\'s hand"')
REF_PAYS = ref("Mana Leak", "a useful reference for “unless its controller pays” wording", 'o:"unless its controller pays"')
REF_MANA = ref("Dark Ritual", "a useful reference for mana-adding wording", 'o:"Add {B}{B}{B}"')
REF_UPKEEP = ref("Phyrexian Arena", "a useful reference for beginning-of-step trigger wording", 'o:"at the beginning of your upkeep"')
REF_AURA = ref("Pacifism", "a useful reference for Aura wording", 't:aura o:"enchanted creature"')
REF_EQUIP = ref("Bonesplitter", "a useful reference for Equipment wording", 't:equipment o:"equipped creature"')
REF_VEH = ref("Smuggler's Copter", "a useful reference for Vehicle wording", 't:vehicle o:crew')
REF_KICK = ref("Burst Lightning", "a useful reference for kicker wording", 'keyword:kicker o:"if this spell was kicked"')
REF_X = ref("Fireball", "a useful reference for X-spell wording", 'o:"X damage"')
REF_REVEAL = ref(None, "cards that search to hand and reveal", 'o:"search your library" o:"reveal it" o:"into your hand"')
REF_TOKEN = ref(None, "cards that create tokens", 'o:"create a" o:"creature token" o:"1/1"')
REF_TRIG = ref("Mulldrifter", "a useful reference for triggered-ability wording", 'o:"this creature enters"')
REF_SAGA = ref(None, "Sagas", "t:saga")
REF_PW = ref(None, "planeswalkers", "t:planeswalker")
REF_COUNTER = ref(None, "cards that put counters", 'o:"put a +1/+1 counter on"')
REF_END = ref("Sneak Attack", "a useful reference for end-step trigger wording", 'o:"at the beginning of the next end step"')

TEMPLATES = [
    ("old-cip", r"\bcomes into play\b", "Likely error", "Templating",
     "“Comes into play” is outdated templating; Oracle wording uses “enters”.", "enters", REF_ETB),
    ("old-cip-pl", r"\bcome into play\b", "Likely error", "Templating",
     "“Come into play” is outdated templating; Oracle wording uses “enter”.", "enter", REF_ETB),
    ("etb-modern", r"\b(enters?) the battlefield\b", "Suggestion", "Templating",
     "Current Oracle wording often shortens “enters the battlefield” to “enters”. Both read fine; this is a style comparison.",
     r"\1", REF_ETB),
    ("dies", r"\b(?:is|are) put into (?:a|an|your|its owner's|their owners'?) graveyard from the battlefield\b",
     "Suggestion", "Templating", "Magic uses “dies” for “put into a graveyard from the battlefield”.", None, REF_DIES),
    ("removed-game", r"\bremoved from the game\b", "Likely error", "Templating",
     "“Remove from the game” was replaced by “exile”.", "exiled", REF_EXILE),
    ("remove-game", r"\bremove\b[^.]{0,40}\bfrom the game\b", "Likely error", "Templating",
     "“Remove from the game” was replaced by “exile”.", None, REF_EXILE),
    ("cmc", r"\bconverted mana cost\b", "Likely error", "Templating",
     "“Converted mana cost” was renamed “mana value”.", "mana value", REF_MV),
    ("any-target",
     r"(damage to )target (?:creature or player or planeswalker|creature or player|creature, player, or planeswalker)",
     "Needs review", "Templating", "Damage that can hit creatures, players and planeswalkers is templated “any target”.",
     r"\1any target", REF_ANY),
    ("modal-dash", r"\b(Choose (?:one|two|three|one or both|one or more|up to (?:one|two|three)))\s?[-–:]",
     "Suggestion", "Templating", "Modal spells use an em dash: “Choose one —”.", r"\1 —", REF_MODAL),
    ("hand-in", r"\b(put (?:it|them|that card|those cards|this card)) in (your|their|its owner's|an opponent's) hand\b",
     "Likely error", "Templating", "Cards are put “into” a hand, not “in” it.", r"\1 into \2 hand", REF_SEARCH),
    ("his-her", r"\bhis or her\b", "Likely error", "Templating", "Magic templating uses “their” instead of “his or her”.",
     "their", None),
    ("in-play", r"\b(?:in|into) play\b", "Needs review", "Templating",
     "“In play” / “into play” is outdated; modern wording refers to the battlefield.", None, REF_ETB),
    ("end-of-turn", r"(?<!until )(?<!by )\bat (?:the )?end of turn\b", "Needs review", "Templating",
     "Delayed triggers use “at the beginning of the next end step”, not “at end of turn”.", None, REF_END),
    ("your-youre", r"\byour (attacking|blocking|tapping|untapping|controlling|casting|dealing|having)\b", "Likely error",
     "Spelling", "“your” should probably be “you're” here.", r"you're \1", None),
    ("ability-dash", r"^([A-Z][a-z]+(?: [a-z]+)?) [-–] (?=[A-Z])", "Suggestion", "Templating",
     "Ability words are followed by an em dash (—), not a hyphen.", r"\1 — ", None),
]
TEMPLATES = [(a, re.compile(b), c, d, e, f, g) for a, b, c, d, e, f, g in TEMPLATES]

TYPES = set("""armadillo art assembly-worker astartes azra balloon beeble brushwagg camarid capybara chicken coyote custodes cyborg deer
doctor dreadnought gamer gith graveborn homarid inquisitor lammasu licid lobster metathran mount necron nephilim noggle orb orgg
pentavite phelddagrif pincher platypus primarch prism processor rigger rukh sable scion sculpture skunk sloth snail spellshaper
splinter sponge surrakar tetravite thalakos time-lord toy trilobite triskelavite tyranid volver weasel
advisor aetherborn alien ally angel antelope ape archer archon army artificer assassin atog aurochs avatar
badger barbarian bard basilisk bat bear beast beaver beholder berserker bird blinkmoth boar bringer camel caribou carrier
cat centaur child chimera citizen cleric clown cockatrice construct coward crab crocodile cyclops dauthi demigod demon
deserter detective devil dinosaur djinn dog dragon drake drone druid dryad dwarf efreet egg elder eldrazi elemental
elephant elf elk employee eye faerie ferret fish flagbearer fox fractal frog fungus gargoyle germ giant gnoll gnome goat
goblin god golem gorgon gremlin griffin guest hag halfling hamster harpy hellion hippo hippogriff homunculus horror horse
human hydra hyena illusion imp incarnation inkling insect jackal jellyfish juggernaut kavu kirin kithkin knight kobold
kor kraken llama lamia leech leviathan lhurgoyf lizard manticore masticore mercenary merfolk minion minotaur mite mole
monger mongoose monk monkey moonfolk mouse mutant myr mystic naga nautilus nightmare nightstalker ninja noble nomad
nymph octopus ogre ooze orc otter ouphe ox oyster pangolin peasant pegasus performer pest phoenix phyrexian pilot pirate
plant porcupine possum praetor rabbit raccoon rhino robot rogue salamander samurai saproling satyr scarecrow scientist
scorpion scout serf serpent servo shade shaman shapeshifter shark sheep siren skeleton slith sliver slug snake soldier
soltari spawn specter sphinx spider spike spirit squid squirrel starfish survivor tentacle thopter thrull tiefling
treefolk troll turtle unicorn vampire vedalken viashino wall walrus warlock warrior wasp weird werewolf whale wizard wolf
wolverine wombat worm wraith wurm yeti zombie zubera equipment aura food clue treasure vehicle saga island forest swamp
mountain plains arcane trap lesson adventure curse shrine desert gate lair locus tower""".split())

def _types(card):
    """Every face's types (a double-faced card's back face counts too), so a back-face land isn't judged by the front face's type line."""
    return " ".join([card["supertype"], card["subtype"]] + [f.get("type", "") for f in (card.get("faces") or [])[1:]]).lower()


def SPELL(card, line, m):
    ty = _types(card)
    return bool(ty.strip()) and any(t in ty for t in ("instant", "sorcery")) and not any(
        t in ty for t in ("creature", "artifact", "enchantment", "land", "planeswalker"))


def _in_paren(line, pos):
    return line.count("(", 0, pos) > line.count(")", 0, pos)


_DUR_RULES = {"pump-no-duration", "grant-no-duration", "spell-effect-no-duration"}
_DUR_PHRASE = r"\buntil\b|\bfor as long as\b|\bthis turn\b|\bas long as\b|\bfor the rest of\b|\bduring (?:your|the) next\b"


def _temp_by_design(card, line, m):
    """A keyword granted to a *copy* (“except it has haste”) or to something that is sacrificed/exiled/returned later doesn't need
    “until end of turn”: it can't last."""
    before = line[:m.start()].split(". ")[-1]
    if re.search(r"\bexcept\b", before, re.I):
        return True
    text = " ".join(f["plain"] for f in card["rules"]).lower()
    tail = line[m.end():].lower() + " " + text
    _gone = r"(?:sacrifice|exile|destroy|return)"
    _eot = r"at the beginning of (?:the |your |each )?(?:next )?end step"
    return bool(re.search(r"\b" + _gone + r"\b[^.]*\b" + _eot, tail)
                or re.search(_eot + r",[^.]*\b" + _gone + r"\b", tail)
                or re.search(r"\b(?:sacrifice|exile) (?:it|this token|that token|the token|those tokens|them)\b[^.]*\bat end of combat", tail))


def _effect(card, line, m):
    """True when the match is an effect being applied, not a condition (“whenever you gain life”, “can't gain life”)."""
    before = line[:m.start()].split(". ")[-1]
    return not re.search(r"\b(?:whenever|when|if|each time|that|which|source|can't|cannot|would|unless|doesn't|don't)\b", before, re.I)


def _r(rid, rx, sev, why, rf=None, cond=None, fix=None, flags=re.I, cat="Missing term", skip_if=()):
    return {"id": rid, "rx": re.compile(rx, flags), "sev": sev, "cat": cat, "why": why, "ref": rf, "cond": cond,
            "fix": fix, "skip_if": set(skip_if)}


_KW = (r"flying|first strike|double strike|deathtouch|haste|hexproof|indestructible|lifelink|menace|reach|trample|"
       r"vigilance|defender|shroud|protection from \w+")
_DUR = r"(?![^.;]*\b(?:until|as long as|for as long))"
RULES = [
    _r("pump-no-duration", r"\btarget [^.:;]*?\bgets? [+\-][\dX]+/[+\-][\dX]+" + _DUR, "Likely error",
       "A “gets +N/+N” effect on a target needs a duration such as “until end of turn”; without one it would last forever.",
       REF_PUMP),
    _r("grant-no-duration", r"\btarget [^.:;]*?\b(?:gains?|loses?) (?:" + _KW + r")\b" + _DUR, "Likely error",
       "Gaining or losing a keyword from a spell or ability needs a duration such as “until end of turn”.", REF_PUMP),
    _r("spell-effect-no-duration", r"\b(?:get|gets|gain|gains|lose|loses|have|has) (?:[+\-][\dX]+/[+\-][\dX]+|(?:" + _KW + r"))\b" + _DUR,
       "Likely error", "Instants and sorceries can't create lasting static effects; this needs a duration such as “until end of turn”.",
       REF_PUMP, cond=lambda c, l, m: SPELL(c, l, m) and not _temp_by_design(c, l, m), skip_if=("pump-no-duration", "grant-no-duration")),
    _r("on-to-onto", r"\bon to\b", "Likely error", "“on to” should be the single word “onto” (e.g. “put a card onto the battlefield”).", None,
       fix=lambda m: "Onto" if m.group(0)[0] == "O" else "onto", cat="Grammar"),
    _r("damage-no-amount", r"\bdeals damage to\b", "Likely error", "“deals damage” has no amount (e.g. “deals 3 damage”).", REF_DMG,
       # "deals damage to target player equal to the number of artifacts you control" states its amount after the target
       cond=lambda c, l, m: _effect(c, l, m) and not re.match(r"[^.:;]*\b(?:equal to|equal|that much|that many)\b", l[m.end():], re.I)),
    _r("life-no-amount", r"\b(?:gains?|loses?) life\b(?! equal)", "Needs review",
       "Life gain/loss normally states an amount (e.g. “gain 3 life”) unless it says “equal to …”.", None, cond=_effect),
    _r("draw-no-count", r"\bdraws? (?:card\b|cards\b(?! equal| until))", "Likely error",
       "“Draw” needs a number or “a card” (e.g. “draw a card”, “draw two cards”).", None,
       cond=lambda c, l, m: not re.match(r"[^.]*\b(?:equal to|for each|that many|that much|X)\b", l[m.end():]) and not re.search(r"(?:can't|cannot|can not|don't|do not|doesn't|won't|unable to|no longer|instead of|may not|never|"
                                          r"not|unless|rather than|without)\s+(?:\w+\s+)?$", l[:m.start()].replace("\u2019", "'"), re.I)),
    _r("plural-after-article", r"\b(?:a|an) (?:[a-z]+ )?(?:creatures|cards|lands|permanents|spells|players|tokens|artifacts|enchantments|planeswalkers)\b",
       "Likely error", "A singular article (“a”/“an”) is followed by a plural noun.", None, cat="Grammar"),
    _r("bounce-your-hand", r"\breturn target (?![^.]*\bcard\b)[^.]*?\bto your hand\b", "Needs review",
       "A permanent on the battlefield returns to its owner's hand, not “your hand”.", REF_BOUNCE),
    _r("unless-pays-nothing", r"\bunless [^.]*?\bpays?\s*(?:[.,]|$)", "Likely error",
       "“…unless they pay” has no cost stated.", REF_PAYS),
    _r("add-no-mana", r"\bAdd\s*(?:[.,]|$)", "Likely error", "“Add” has no mana symbols after it.", REF_MANA, flags=0),
    _r("at-beginning-of", r"\bAt (?:(?:the )?beginning (?!of\b)|beginning of\b)", "Likely error",
       "Step/phase triggers are worded “At the beginning of …”.", REF_UPKEEP, cat="Templating", flags=0),
    _r("trigger-no-effect", r"^(?:When|Whenever|At)\b[^.]*,\s*$", "Likely error",
       "This triggered ability stops after the comma, so it has no effect.", REF_TRIG, flags=0),
    _r("trigger-no-comma", r"^(?:When|Whenever|At the beginning of)\b[^,.—•:]*\.\s*$", "Needs review",
       "A triggered ability needs a comma between its condition and its effect.", REF_TRIG, flags=0),
    _r("whenever-etb", r"^Whenever this (?:creature|artifact|enchantment|land|permanent|Equipment|Aura|Vehicle) (?:enters|dies)\b",
       "Suggestion", "A trigger that can only happen once for this permanent is templated “When”, not “Whenever”.", REF_TRIG,
       fix=lambda m: "When" + m.group(0)[8:], cat="Templating", flags=0,
       cond=lambda c, l, m: not re.search(r"\b(?:attacks|blocks|becomes|deals|is dealt|is put|is turned|leaves|you cast|you gain|you draw)\b",
                                          re.split(r",|\.", l)[0], re.I)),
    _r("when-multi-event",
       r"^When\b[^,.:]*?\b(?:enters(?: the battlefield)?|dies|attacks|blocks|leaves the battlefield),? or "
       r"(?:enters(?: the battlefield)?|dies|attacks|blocks|leaves the battlefield|becomes|deals)\b",
       "Likely error", "A trigger with more than one event (e.g. “enters or attacks”) can happen many times, so it is worded “Whenever”, not “When”.",
       REF_TRIG, fix=lambda m: "Whenever" + m.group(0)[4:], cat="Templating", flags=0,
       # "enters or dies" is a legitimate "When" (each event happens once); only repeatable events like attacks/blocks need "Whenever"
       cond=lambda c, l, m: bool(re.search(r"\b(?:attacks|blocks)\b", m.group(0)))),
    _r("activated-incomplete", r"^\s*:|:\s*$", "Likely error", "An activated ability needs both a cost before the colon and an effect after it.",
       None, cond=lambda c, l, m: not re.match(r"\s*(?:choose|level|•)", l, re.I), flags=0),
    _r("token-no-creature", r"\b\d+/\d+ (?:[A-Za-z]+ ){1,6}?tokens?\b", "Likely error",
       "Creature tokens are worded “… creature token” (e.g. “1/1 white Soldier creature token”).", REF_TOKEN,
       cond=lambda c, l, m: not re.search(r"\b(?:creature|artifact|enchantment|land)\b", m.group(0).lower()),
       fix=lambda m: re.sub(r"\b(tokens?)$", r"creature \1", m.group(0)), cat="Templating"),
    _r("token-undefined", r"\bcreate (?:a|an|one|two|three|four|five|\d+|X) (?!(?:(?:tapped|snow|legendary) )*(?:Treasure|Food|Clue|Blood|Map|Powerstone|Mox|Gold|Junk|Shard|Incubator|Role|Walker|Lander|Mutagen|\d|copy|token that|copies|nontoken)\b)(?:[A-Za-z']+ ){0,3}?tokens?\b",
       "Needs review", "This token has no stated colour and type (and power/toughness, if it is a creature). That is fine if the token "
       "is defined elsewhere (e.g. a token card in your set) or by reminder text.", REF_TOKEN,
       cond=lambda c, l, m: not re.search(r"\bone or more\b|\bthat many\b|\bthose tokens\b|\bwould create\b|\bwould be created\b|^\s*if\b", l[:m.end()], re.I)
       # a token followed by reminder text (“Create a Mox token. (It's a colorless artifact with …)”) is defined right there,
       # and a non-creature (artifact/enchantment/land) token never has power/toughness
       and not re.match(r"[^.(]{0,60}\.?\s*\(", l[m.end():])
       and not re.search(r"\b(?:artifact|enchantment|land)\b", m.group(0), re.I)
       and not (re.match(r"\s*(?:when|whenever|each time|if|as long as|at)\b", l, re.I) and "," not in l[:m.start()])
       and not re.match(r"[^.]*\b(?:copy|copies|copied)\b", l[m.end():], re.I)
       and not re.search(r"\b(?:copy|copies)\b", m.group(0), re.I)
       and not re.match(r"\s*named\b", l[m.end():], re.I),
       flags=0),
    _r("counter-no-kind", r"\b(?:put|puts) (?:a|an|one|two|three|X|\d+) counters?\b(?! of)", "Needs review",
       "The kind of counter isn't named (e.g. “+1/+1 counter”).", REF_COUNTER,
       # “if you put a counter on a creature this turn” / “whenever a player puts a counter…” is a condition about ANY counter, which is valid
       cond=lambda c, l, m: not (re.search(r"^[^.]*\b(?:this way|same kind|that kind|any kind|your choice)\b", l[m.end():], re.I)
                                 or re.search(r"\b(?:if|when|whenever|unless|that|which|as long as|only if|didn't|haven't|hasn't)\b[^.,:]*$", l[:m.start()], re.I)
                                 or re.search(r"\b(?:you|they|player|players|opponent|opponents|who|has|have|had)\s*$", l[:m.start()], re.I))),
    _r("search-graveyard", r"\bsearch(?:es)? (?:your|target (?:player|opponent)'s|their) graveyard\b", "Suggestion",
       "Current wording returns cards from a graveyard instead of “searching” it (e.g. “Return target card from your graveyard to your hand”).", None),
    _r("spell-trigger", r"^(?:When|Whenever|At the beginning of)\b", "Needs review",
       "Instants and sorceries can't have a printed triggered ability; use an effect like “When … this turn, …”.", REF_TRIG,
       cond=lambda c, l, m: SPELL(c, l, m) and not re.search(r"\bthis turn\b|\bthe next (?:end step|upkeep|turn|combat)\b|\buntil\b|\bnext turn\b",
                                                          re.sub(r"\([^)]*\)", "", l).split(",")[0], re.I)
       # “When you cast this spell, …” (storm/cascade-style) and “… if this card is in your graveyard, …” work from the stack/graveyard
       and not re.match(r"(?:when|whenever) you cast (?:this spell|~|this card)\b", l, re.I)
       and not re.match(r"(?:when|whenever) you (?:discard|cycle|cast|exile|reveal|draw|put|sacrifice|play|channel|forecast) (?:this card|this spell|~|"
                        + re.escape((c["name"] or "~zz").split(",")[0].strip().replace("\u2019", "'")) + r"|" + re.escape((c["name"] or "~zz").strip()) + r")\b",
                        l.replace("\u2019", "'"), re.I)
       and not re.search(r"\b(?:in|from) your graveyard\b|\bin a graveyard\b", re.sub(r"\([^)]*\)", "", l), re.I), flags=0),
    _r("spell-activated", r"^[^.•—]{1,50}:\s*\S", "Needs review",
       "Instants and sorceries can't have activated abilities.", None,
       # reminder text such as "Cycling {2} ({2}, Discard this card: …)" legitimately contains a colon
       cond=lambda c, l, m: SPELL(c, l, m) and bool(re.search(r"^[^.•—]{1,50}:\s*\S", re.sub(r"\([^)]*\)", "", l)))
       # abilities that work from the graveyard/hand (“{2}{U}, Exile this card from your graveyard: …”, cycling-style) are legal
       and not re.search(r"\bfrom your (?:graveyard|hand)\b|\b(?:this card|this spell)\b|\bdiscard\b", re.sub(r"\([^)]*\)", "", l).split(":")[0], re.I), flags=0),
]
NEEDS_COST = set("""equip kicker multikicker cycling landcycling flashback ward madness morph megamorph evoke bestow overload suspend
unearth escape embalm eternalize foretell disturb buyback entwine echo ninjutsu prowl replicate miracle retrace emerge dash
blitz spectacle awaken impending offspring squad level up""".replace("level up", "").split()) | {"level up", "cumulative upkeep"}
NEEDS_NUMBER = set("crew annihilator bushido fabricate afterlife amass toxic modular rampage absorb dredge graft backup casualty".split())
CREATURE_KW = {"flying", "first strike", "double strike", "deathtouch", "defender", "haste", "hexproof", "indestructible",
               "lifelink", "menace", "reach", "trample", "vigilance"}


SYM_OK = re.compile(r"^(?:[WUBRGCXYZSTQE]|\d{1,2}|[WUBRG]/[WUBRG]|[WUBRG]/P|2/[WUBRG]|[WUBRG]/[WUBRG]/P|CHAOS|PW)$")
STOP = set("""the and for with that this then when from into your their have each target creature creatures spell spells card
cards player players until end turn battlefield graveyard library control controller enters""".split())
PHRASES = ["search your library", "damage to any target", "damage to target", "draw a card", "+1/+1 counter", "-1/-1 counter", "create a", "destroy target",
           "exile target", "deals damage", "gain life", "lose life", "sacrifice", "return target", "dies", "discard",
           "counter target spell", "untap", "tap target", "mill", "proliferate", "regenerate"]
KNOWN_COUNTERS = {"+1/+1", "-1/-1", "loyalty", "charge", "time", "poison", "stun", "oil", "shield", "finality", "lore",
                  "level", "age", "fade", "verse", "energy", "experience", "rad", "quest", "storage", "divinity",
                  "flying", "first", "double", "lifelink", "trample", "vigilance", "deathtouch", "reach", "hexproof",
                  "indestructible", "menace", "death", "corpse", "depletion", "doom", "gold", "ice", "mining", "ki"}
COUNTER_STOP = STOP | {"two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "several", "many", "its", "their",
                       "your", "a", "an", "one", "any", "that", "each", "this", "another", "of", "no", "all", "those", "them",
                       "it", "remove", "put", "is", "be", "if", "or", "x", "up", "more", "same", "many", "such"}
