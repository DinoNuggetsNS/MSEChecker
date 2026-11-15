"""MSECheck - reports."""
import csv, html, io
from .state import ST


# ----------------------------------------------------------------------------------------
# Reports
# ----------------------------------------------------------------------------------------
def flat_rows():
    for c in ST["last"]["cards"]:
        if not c["findings"]:
            yield (c["name"], "", "No errors found" if c["has_text"] else "No rules text in file", "", "", "", "", c["scryfall"], "")
        for f in c["findings"]:
            r = f["ref"] or {}
            yield (c["name"], f["sev"], f["cat"], f["detected"], f["why"], f["after"] or "",
                   ("%s — %s" % (r["name"], r["note"]) if r.get("name") else r.get("note", "")),
                   r.get("url") or c["scryfall"], "Heuristic check")


HEAD = ("Card", "Severity", "Category", "Detected text", "Why flagged", "Suggested wording", "Reference", "Scryfall link", "Source")


def export(fmt):
    s = ST["last"]["summary"]
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(HEAD)
        w.writerows(flat_rows())
        return buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", "mse-report.csv"
    if fmt == "txt":
        L = ["MSECheck report — %s" % ST["last"]["file"], "Cards: %d | clean: %d | findings: %d (%s)" % (
            s["cards"], s["clean"], s["total"], ", ".join("%s %d" % kv for kv in s["severity"].items())), ""]
        for c in ST["last"]["cards"]:
            L.append("== %s ==" % (c["name"] or "(unnamed)"))
            if not c["findings"]:
                L.append("  No errors found." if c["has_text"] else "  No rules text stored in the file for this card.")
            for f in c["findings"]:
                L += ["  [%s] %s" % (f["sev"], f["cat"]), "    Detected: " + f["detected"], "    Why: " + f["why"]]
                if f["after"]:
                    L.append("    Suggested: " + f["after"])
                if f["ref"]:
                    L.append("    Reference: " + (f["ref"]["name"] or f["ref"]["note"]) + " " + f["ref"]["url"])
            L += ["  Similar cards: " + c["scryfall"], ""]
        return "\n".join(L).encode("utf-8"), "text/plain; charset=utf-8", "mse-report.txt"
    rows = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % html.escape(x or "") for x in r) for r in flat_rows())
    page = ("<!doctype html><meta charset=utf-8><title>MSECheck report</title><style>body{font:14px system-ui;margin:2rem}"
            "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px;vertical-align:top}th{background:#eee}</style>"
            "<h1>MSECheck report</h1><p>%s — %d cards, %d clean, %d findings. A reference is a comparison, not proof of an error.</p>"
            "<table><tr>%s</tr>%s</table>" % (html.escape(ST["last"]["file"]), s["cards"], s["clean"], s["total"],
                                              "".join("<th>%s</th>" % h for h in HEAD), rows))
    return page.encode("utf-8"), "text/html; charset=utf-8", "mse-report.html"
