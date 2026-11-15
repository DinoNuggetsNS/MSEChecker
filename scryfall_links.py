"""MSECheck - scryfall links."""
from .vocabulary import KEYWORDS
from .templating import surl
from .context import _kw_rx
from .scryfall_data import _strip_name
from .design_risk import key_terms


# ----------------------------------------------------------------------------------------
# Card-level Scryfall query
# ----------------------------------------------------------------------------------------
def card_query(card, ctx):
    """Scryfall search for a card's own text: at most two key terms, never the card name. No text -> no search."""
    text = "\n".join(f["plain"] for f in card["rules"] if f.get("plain")).strip()
    if not text:
        return "", []
    name = (card.get("name") or "").strip()
    low = _strip_name(text, name).lower()
    parts, shown = [], []
    for k in sorted(KEYWORDS, key=len, reverse=True):
        # only real keywords from Scryfall's list: a custom keyword (or an empty/short entry) would make the search return nothing
        if len(k.strip()) < 3 or k in ctx.custom or k in {c_.lower() for c_ in ctx.custom}:
            continue
        if k in low and _kw_rx(k, True).search(low):
            parts.append('keyword:"%s"' % k if " " in k else "keyword:" + k)
            shown.append(k)
            break
    for q in key_terms(low, name, 2 - len(parts)):
        if q[2:].strip('"') in shown:
            continue   # already covered by the keyword: or the same term
        parts.append(q)
        shown.append(q[2:].strip('"'))
    return (surl(" ".join(parts)), shown) if parts else ("", [])
