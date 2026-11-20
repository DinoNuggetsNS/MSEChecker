"""MSECheck - analysis."""
import difflib, html, io, re, time, zipfile
from collections import Counter, defaultdict
from . import state
from .version import VERSION
from .vocabulary import SEV_ORDER, get_dict
from .templating import ref
from .mse_parser import fval, make_cards, nk, parse_mse, render_field
from .state import ST
from .context import build_ctx, mk
from .scryfall_data import ORACLE
from .card_checks import check_artist, check_card, check_flavor, check_structure
from .design_risk import check_design, similar_query
from .set_checks import check_set
from .extra_checks import check_extra_card, check_extra_set
from .scryfall_links import card_query


# App state & analysis
# ----------------------------------------------------------------------------------------


def diff_html(a, b):
    ta, tb = re.findall(r"\s+|\S+", a), re.findall(r"\s+|\S+", b)
    A, B = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes():
        sa, sb = html.escape("".join(ta[i1:i2])), html.escape("".join(tb[j1:j2]))
        if op == "equal":
            A.append(sa), B.append(sb)
        else:
            if sa:
                A.append("<del>%s</del>" % sa)
            if sb:
                B.append("<ins>%s</ins>" % sb)
    return "".join(A), "".join(B)


def hl(text, match):
    if match and match in text:
        i = text.index(match)
        return html.escape(text[:i]) + "<mark>" + html.escape(match) + "</mark>" + html.escape(text[i + len(match):])
    return html.escape(text)


def game_of(text):
    m = re.search(r"^game:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def analyze():
    _t0 = time.time()
    blocks = parse_mse(ST["text"])
    cards = make_cards(blocks)
    if not cards:
        raise ValueError("No cards found. Is this a valid .mse-set (a zip containing a file named “set”)?")
    ctx = build_ctx(cards, blocks)
    fl = defaultdict(list)
    for c in cards:
        try:
            fl[c["idx"]] += check_card(c, ctx)
        except Exception as e:  # keep going: report the problem on that card
            fl[c["idx"]].append(mk("Needs review", "Checker", "checker-error", c["name"], c["name"],
                                   "The checker hit an unexpected problem on this card (%s). Please report it." % e))
    check_set(cards, ctx, fl)
    try:
        check_extra_set(cards, ctx, fl)
    except Exception:
        pass
    for c in cards:
        try:
            fl[c["idx"]] += check_structure(c)
            fl[c["idx"]] += check_extra_card(c, ctx)
        except Exception:
            pass
        try:
            fl[c["idx"]] += (check_artist(c) if ST["kind"] != "text" else []) + check_flavor(c, ctx)
        except Exception as e:
            fl[c["idx"]].append(mk("Needs review", "Checker", "checker-error", c["name"], c["name"],
                                   "The flavor-text checks hit an unexpected problem on this card (%s). Please report it." % e))
        if state.DESIGN_RISK:
            try:
                fl[c["idx"]] += check_design(c, ctx)
            except Exception as e:
                fl[c["idx"]].append(mk("Needs review", "Checker", "checker-error", c["name"], c["name"],
                                       "The design-risk checks hit an unexpected problem on this card (%s). Please report it." % e))
    ST["findings"] = {}
    out_cards, sev_count, cat_count, ignored_total, clean, no_text = [], Counter(), Counter(), 0, 0, 0
    for c in cards:
        items = sorted(fl[c["idx"]], key=lambda f: SEV_ORDER[f["sev"]])
        res, n_vis, n_ign = [], 0, 0
        rules_text = "\n".join(f["plain"] for f in c["rules"] if f["plain"].strip()).strip()
        tline = (c["supertype"] + (" — " + c["subtype"] if c["subtype"] else "")).strip()
        for n, f in enumerate(items):
            f["key"] = f["rule"] + "|" + (f["match"] or f["detected"])[:80].lower()
            f["id"] = "%d:%d" % (c["idx"], n)
            ign = f["rule"] in ST["ign_rule"] or f["key"] in ST["ign_text"] or (c["idx"], f["key"]) in ST["ign_card"] or c["idx"] in ST.get("ign_whole", ())
            after = None
            if f["fix"]:
                o = f["fix"]["old"]
                after = f["detected"].replace(o, f["fix"]["new"], 1) if o in f["detected"] else f["fix"]["new"]
            elif f.get("suggest"):
                after = f["suggest"]
            bh = ah = None
            if after is not None and after != f["detected"]:
                bh, ah = diff_html(f["detected"], after)
            else:
                after = None
            if not f["ref"]:
                q = similar_query(f["detected"], c["name"])
                if q:
                    f["ref"] = ref(None, "cards with similar wording", q)
            ST["findings"][f["id"]] = dict(f, card=c["idx"])
            if ign:
                n_ign += 1
                continue
            n_vis += 1
            sev_count[f["sev"]] += 1
            cat_count[f["cat"]] += 1
            res.append({"id": f["id"], "sev": f["sev"], "cat": f["cat"], "rule": f["rule"], "source": f["source"],
                        "detected": f["detected"], "detected_html": hl(f["detected"], f["match"]), "why": f["why"],
                        "after": after, "before_html": bh, "after_html": ah, "can_apply": bool(f["fix"]),
                        "ref": f["ref"]})
        ignored_total += n_ign
        qurl, qterms = card_query(c, ctx)
        has_text = any(f["plain"].strip() for f in c["rules"])
        no_text += not has_text
        clean += (n_vis == 0 and has_text)
        out_cards.append({"idx": c["idx"], "name": " // ".join(c["names"]) if len(c.get("names") or []) > 1 else (c["name"] or "(unnamed card #%d)" % (c["idx"] + 1)), "cost": c["cost"] + (" // " + c["cost2"] if c.get("cost2") else ""),
                          "type": tline,
                          "rules": rules_text, "findings": res,
                          "power": c["power"], "toughness": c["toughness"], "loyalty": c.get("loyalty", ""), "rarity": c.get("rarity", ""),
                          "flavor": "\n".join(f["plain"] for f in c["flavor"]), "artist": c["artist"],
                          "ignored": n_ign, "ign_whole": c["idx"] in ST.get("ign_whole", ()), "scryfall": qurl, "terms": qterms, "has_text": has_text, "filled": c["filled"],
                          "text_fields": [f["key"] for f in c["rules"] if f["plain"].strip()]})
    d = get_dict()
    result = {
        "file": ST["filename"], "mode": ST["kind"], "version": VERSION, "edited": ST["edited"], "oracle_cards": len(ORACLE["texts"] or []), "similarity_ready": bool(ORACLE.get("records")), "oracle_state": ORACLE["state"],
        "summary": {"cards": len(cards), "clean": clean, "no_text": no_text, "with_findings": len(cards) - clean - no_text,
                    "severity": {k: sev_count.get(k, 0) for k in SEV_ORDER}, "total": sum(sev_count.values()),
                    "ignored": ignored_total, "categories": cat_count.most_common(),
                    "custom_keywords": ctx.custom, "game": game_of(ST["text"]), "text_fields": Counter(
                        k for c in cards for k in {f["key"] for f in c["rules"] if f["plain"].strip()}).most_common(), "spellcheck": "full dictionary" if d else "built-in MTG vocabulary (flavor-text spelling needs: pip install pyspellchecker)"},
        "cards": out_cards}
    ST["last"] = result
    print("Analyzed %d cards in %.1fs" % (len(cards), time.time() - _t0))
    return result


def load_upload(name, data):
    ST.update(kind="set", filename=name, orig=data, ign_whole=set(), ign_card=set(), ign_text=set(), ign_rule=set(), edited=False)
    raw = data
    if zipfile.is_zipfile(io.BytesIO(data)):
        z = zipfile.ZipFile(io.BytesIO(data))
        member = "set" if "set" in z.namelist() else next((n for n in z.namelist() if n.lower().endswith("set")), None)
        if member is None:
            raise ValueError("The archive has no “set” file inside.")
        raw = z.read(member)
    ST["bom"], ST["crlf"] = raw.startswith(b"\xef\xbb\xbf"), b"\r\n" in raw
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    ST["orig_text"] = ST["text"] = text.replace("\r\n", "\n")


def load_text(name, text):
    lines = ["card:", "\tname: " + (name or "(single card)"), "\trule text:"] + ["\t\t" + l.replace("\t", " ") for l in text.replace("\r\n", "\n").split("\n")]
    ST.update(kind="text", filename="single card", orig=b"", ign_whole=set(), ign_card=set(), ign_text=set(), ign_rule=set(), edited=False,
              bom=False, crlf=False)
    ST["orig_text"] = ST["text"] = "\n".join(lines)


def apply_fix(fid):
    f = ST["findings"].get(fid)
    if not f or not f["fix"]:
        raise ValueError("That finding has no automatic correction. Use “Copy wording” and edit it in MSE.")
    blocks = parse_mse(ST["text"])
    cb = [b for b in blocks if b.kind == "card"]
    fix = f["fix"]
    fld = next((x for x in cb[f["card"]].fields if nk(x.key) == nk(fix["field"])), None)
    if fld is None:
        raise ValueError("Could not find the “%s” field on that card." % fix["field"])
    raw = fval(fld)
    n = raw.count(fix["old"])
    if n == 0:
        raise ValueError("Couldn't find that exact text in the raw card data (formatting tags are probably in the way). "
                         "Copy the wording and edit it in MSE.")
    if n > 1 and not fix["all"]:
        raise ValueError("That text appears %d times in this field, so it can't be changed safely. Copy the wording instead." % n)
    new_raw = raw.replace(fix["old"], fix["new"]) if fix["all"] else raw.replace(fix["old"], fix["new"], 1)
    lines = ST["text"].split("\n")
    lines[fld.start:fld.end] = render_field(fld.key, new_raw, fld.multi)
    ST["text"], ST["edited"] = "\n".join(lines), True
    return n if fix["all"] else 1


def apply_all(sevs):
    """Apply every automatic fix (for the given severities) that isn't ignored. Returns (applied, skipped)."""
    applied = skipped = 0
    for _ in range(4):                      # a fix can reveal another one, so go round a few times
        analyze()
        todo = [f for f in ST["findings"].values()
                if f["fix"] and f["sev"] in sevs and f["rule"] not in ST["ign_rule"] and f["key"] not in ST["ign_text"]
                and (f["card"], f["key"]) not in ST["ign_card"]]
        done = 0
        for f in todo:
            try:
                apply_fix(f["id"])
                done += 1
            except Exception:
                skipped += 1
        applied += done
        if not done:
            break
    return applied, skipped


def corrected_download():
    if ST["kind"] == "text":
        blocks = parse_mse(ST["text"])
        fld = next(x for x in blocks[0].fields if nk(x.key) == "rule text")
        return fval(fld).encode("utf-8"), "text/plain; charset=utf-8", "corrected-rules-text.txt"
    out = ST["text"].replace("\n", "\r\n") if ST["crlf"] else ST["text"]
    body = (b"\xef\xbb\xbf" if ST["bom"] else b"") + out.encode("utf-8")
    stem = re.sub(r"\.(mse-set|zip)$", "", ST["filename"], flags=re.I) or "set"
    if zipfile.is_zipfile(io.BytesIO(ST["orig"])):
        src = zipfile.ZipFile(io.BytesIO(ST["orig"]))
        member = "set" if "set" in src.namelist() else next(n for n in src.namelist() if n.lower().endswith("set"))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                dst.writestr(info, body if info.filename == member else src.read(info.filename))
        return buf.getvalue(), "application/octet-stream", stem + ".corrected.mse-set"
    return body, "text/plain; charset=utf-8", stem + ".corrected.mse-set"
