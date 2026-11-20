"""Run with:  python -m unittest discover tests"""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from msecheck.analysis import ST, analyze

SAMPLE = """card:
\tname: Test Bear
\tsuper type: Creature
\tsub type: Bear
\tcasting cost: 1G
\tpower: 2
\ttoughness: 2
\trule text:
\t\tTrample
"""

class Smoke(unittest.TestCase):
    def test_analyze_runs(self):
        ST.update(kind="text", filename="t", text=SAMPLE, orig_text=SAMPLE, findings={}, last=None, edited=False)
        res = analyze()
        self.assertEqual(res["cards"][0]["name"], "Test Bear")


class Extra(unittest.TestCase):
    def test_new_checks(self):
        def card(name, sup, sub="", cost="", pt=None, rules="", rar="common", loy=""):
            s = "card:\n\tname: %s\n\tsuper type: %s\n" % (name, sup) + ("\tsub type: %s\n" % sub if sub else "") + ("\tcasting cost: %s\n" % cost if cost else "")
            s += ("\tpower: %s\n\ttoughness: %s\n" % pt if pt else "") + ("\tloyalty: %s\n" % loy if loy else "") + "\trarity: %s\n\tillustrator: Bob\n" % rar
            return s + ("\trule text:\n" + "".join("\t\t%s\n" % l for l in rules.split("\n")) if rules else "")
        t = "mse_version: 0.3.8\ngame: magic\n" + card("Big Vanilla", "Creature", "Beast", "1G", ("6", "6")) + card("Dirt", "Land", "", "2") \
            + card("Walker", "Planeswalker", "", "3UU", None, "+1: Draw a card.") + card("Spam", "Sorcery", "", "2G", None, "Put a counter on target creature.")
        ST.update(kind="set", filename="x", text=t, orig_text=t, findings={}, last=None, edited=False)
        got = {c["name"]: {f["rule"] for f in c["findings"]} for c in analyze()["cards"]}
        self.assertIn("pt-vanilla-too-big", got["Big Vanilla"])
        self.assertIn("land-has-cost", got["Dirt"])
        self.assertIn("pw-no-starting-loyalty", got["Walker"])
        self.assertIn("counter-no-kind", got["Spam"])


if __name__ == "__main__":
    unittest.main()
