"""MSECheck - vocabulary."""
import os, re
from collections import defaultdict


# ----------------------------------------------------------------------------------------
# Vocabulary
# ----------------------------------------------------------------------------------------
SEV_ORDER = {"Likely error": 0, "Needs review": 1, "Suggestion": 2}

KEYWORDS = set("""flying,first strike,double strike,deathtouch,defender,haste,hexproof,indestructible,lifelink,
menace,reach,trample,vigilance,flash,ward,protection,prowess,scry,surveil,equip,enchant,kicker,multikicker,
flashback,cycling,landcycling,convoke,delve,emerge,escape,fabricate,fear,intimidate,landwalk,swampwalk,islandwalk,
forestwalk,mountainwalk,plainswalk,madness,morph,megamorph,manifest,mill,proliferate,regenerate,shroud,skulk,storm,
undying,persist,unearth,infect,annihilator,bestow,cascade,changeling,crew,devoid,embalm,eternalize,evoke,exploit,
extort,fading,flanking,haunt,investigate,jump-start,level up,mentor,miracle,myriad,offering,overload,populate,
rebound,retrace,riot,soulbond,spectacle,support,suspend,totem armor,transform,transmute,undaunted,vanishing,wither,
adapt,amass,afterlife,boast,bolster,connive,disturb,foretell,learn,magecraft,ninjutsu,plot,saddle,offspring,
impending,affinity,amplify,bushido,buyback,champion,cipher,compleated,conspire,craft,dash,daybound,nightbound,
decayed,dethrone,devour,echo,enlist,entwine,epic,evolve,exalted,explore,fuse,graft,gravestorm,hideaway,
horsemanship,improvise,ingest,melee,modular,mutate,outlast,partner,phasing,provoke,prowl,rampage,ravenous,
reinforce,renown,replicate,ripple,scavenge,shadow,splice,sunburst,tribute,training,unleash,afflict,aftermath,
awaken,backup,banding,battle cry,bloodthirst,casualty,cleave,incubate,toxic,squad,read ahead,prototype,
reconfigure,blitz,disguise,cloak,collect evidence,suspect,gift,valiant,spree,exhaust,station,warp,tiered,
domain,delirium,landfall,constellation,metalcraft,morbid,revolt,ferocious,coven,hellbent""".replace("\n", "").split(","))

_BASE = """a an and or the of to in on at by for from with without into onto under over until while when whenever if then than bracket brackets doing does done way ways
that this those these it its their your you they them he she his her own each every all any another other both either
neither only no not may must can cannot has have had is are was were be been being does do did enters enter entered
leaves leave left dies die died put puts return returns returned exile exiles exiled destroy destroys destroyed
sacrifice sacrifices sacrificed draw draws drew discard discards discarded search searches searched reveal reveals
revealed shuffle shuffles look looks top bottom random choose chooses chose create creates created token tokens
counter counters spell spells ability abilities activate activated activates trigger triggered triggers cast casts
cost costs pay pays paid mana color colors colorless white blue black red green artifact artifacts creature creatures
enchantment enchantments land lands planeswalker planeswalkers instant instants sorcery sorceries aura equipment
vehicle saga protect protected protecting protects survive survives survived surviving defeated conflict permanent permanents card cards library graveyard hand battlefield stack player players opponent opponents
controller controls control owner owners turn turns phase step upkeep combat attack attacks attacked attacking
attacker attackers block blocks blocked blocking blocker blockers damage damages dealt deals prevent prevents prevented
life lose loses lost gain gains gained power toughness equal equals greater less least most more number numbers amount
total times time twice once additional extra instead also same different named name names type types subtype
supertype basic legendary snow nonbasic nonland noncreature nontoken tapped tap taps untap untaps untapped attached
attach attaches enchanted equipped remains remain remaining end beginning next previous first last second third
target targets targeted targeting value values converted chosen mode modes one two three four five six seven eight
nine ten half rounded round down up face copy copies copied exactly unless except during after before between among
which what who whom whose where there here now again still even just like unlike through across around within
outside inside above below way ways rule rules game games permanently duration instead lethal combat unblocked
defending controlled control gets get got becomes become became has gains loses lose chosen choice choices
sorcery speed activate only any time battlefield hexproof indestructible regenerate regenerated regeneration
shield prevent redirect redirected redirects source sources spell's creature's player's card's permanent's
nonwhite nonblue nonblack nonred nongreen multicolored monocolored historic party outlaw wizard cleric rogue warrior
reveal revealed hidden unrevealed exile exiled face-up face-down library's graveyards revolt kicked kicker
mana-value land's abilities' trigger's effect effects replace replaces replaced replacement skip skips skipped
extra additional extra lands play plays played playing cast casting castable able unable can't couldn't
whenever pay paying payment total paid choose reduced reduce reduces increase increased increases double doubled
triple tripled halve halved max maximum minimum least about toward towards onto upon via per plus minus
untapped attacking blocking enchanted equipped fortified exiled returned drawn drawing discarded milled
search searching library libraries shuffle shuffling top bottom order order random randomly simultaneously
simultaneous otherwise therefore thereafter afterward afterwards later earlier eventually immediately
deal add remove change swap spend exchange detach take give make keep win tie roll flip count exceed match share
begin start finish pick name rest wait stay move join split merge reduce form fight regenerate enlist attach
creature nonartifact nonland blocked unblocked exiled owner's battlefield's opponent's controller's
list lists listed reselect reselects cast casts"""


def _inflect(w):
    s = {w, w + "s", w + "es", w + "ed", w + "d", w + "ing", w + "er", w + "ly"}
    if w.endswith("y"):
        s |= {w[:-1] + "ies", w[:-1] + "ied"}
    if w.endswith("e"):
        s.add(w[:-1] + "ing")
    if len(w) > 2:
        s |= {w + w[-1] + "ed", w + w[-1] + "ing"}
    return s


VOCAB = set()
for _w in re.findall(r"[a-z]{3,}", _BASE):
    VOCAB |= _inflect(_w)
for _k in KEYWORDS:
    VOCAB |= set(re.findall(r"[a-z]{3,}", _k))

_DICT = {"loaded": False, "words": None, "by_len": None}


def get_dict():
    """Optional full-English dictionary (pyspellchecker or a system word list)."""
    if not _DICT["loaded"]:
        _DICT["loaded"] = True
        words = None
        try:
            from spellchecker import SpellChecker
            words = set(SpellChecker().word_frequency.dictionary.keys())
        except Exception:
            for p in ("/usr/share/dict/words", "/usr/share/dict/american-english"):
                if os.path.exists(p):
                    with open(p, errors="ignore") as fh:
                        words = {w.strip().lower() for w in fh}
                    break
        _DICT["words"] = words
        if words:
            bl = defaultdict(list)
            for w in words:
                if w.isalpha():
                    bl[len(w)].append(w)
            _DICT["by_len"] = bl
    return _DICT["words"]


def dl(a, b):
    """Damerau-Levenshtein (optimal string alignment) distance."""
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            c = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]
