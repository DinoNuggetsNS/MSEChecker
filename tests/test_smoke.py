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

    def test_trigger_and_dies_and_x(self):
        def card(name, sup, sub, cost, rules, pt=None):
            s = "card:\n\tname: %s\n\tsuper type: %s\n" % (name, sup) + ("\tsub type: %s\n" % sub if sub else "") + "\tcasting cost: %s\n" % cost
            s += ("\tpower: %s\n\ttoughness: %s\n" % pt if pt else "") + "\trarity: rare\n\tillustrator: Bob\n\trule text:\n"
            return s + "".join("\t\t%s\n" % l for l in rules.split("\n"))
        t = "mse_version: 0.3.8\ngame: magic\n" \
            + card("Beanstalk", "Enchantment", "", "1G", "Whenever Beanstalk enters or you cast a spell with mana value 5 or greater, draw a card.") \
            + card("Land Eater", "Enchantment", "", "2G", "Whenever a land card is put into your graveyard from the battlefield, draw a card.") \
            + card("Bear Eater", "Enchantment", "", "2G", "Whenever a creature is put into your graveyard from the battlefield, draw a card.") \
            + card("Mod", "Creature", "Bear", "1G", "When Mod dies, draw a card.", ("1", "1")) \
            + card("Paolig", "Creature", "Demon", "1BB", "At the beginning of your end step, you may pay thrice X life. If you do, you draw X cards. X can\u2019t be greater than the amount of life you gained this turn.", ("2", "2")) \
            + card("Hero", "Token Creature", "Hero", "", "Prowess, prowess (Each instance of prowess triggers separately.)", ("1", "1"))
        ST.update(kind="set", filename="x", text=t, orig_text=t, findings={}, last=None, edited=False)
        r = analyze()
        got = {c["name"]: {f["rule"] for f in c["findings"]} for c in r["cards"]}
        self.assertIn("trigger-or-other-event", got["Beanstalk"])
        self.assertNotIn("dies", got["Land Eater"])
        self.assertIn("dies", got["Bear Eater"])
        self.assertNotIn("x-undefined", got["Paolig"])
        self.assertNotIn("dup-keyword", got["Hero"])


if __name__ == "__main__":
    unittest.main()
