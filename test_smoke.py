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

if __name__ == "__main__":
    unittest.main()
