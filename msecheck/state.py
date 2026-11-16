"""MSECheck - state."""
import threading


# Shared application state. Other modules import these objects (or this module, for values that get rebound).

ST = dict(kind=None, filename="", orig=b"", orig_text="", text="", bom=False, crlf=False, ign_card=set(), ign_text=set(),
          ign_rule=set(), findings={}, last=None, edited=False)

LOCK = threading.RLock()

HEARTBEAT = {"last": None}

DESIGN_RISK = True            # turn off with --no-design-risk
START = None                    # set in launcher.main() once the server is up
SHORTCUT_ENABLED = True         # --no-shortcut turns the Desktop-shortcut question off
MSE_PATH = None                  # --mse PATH: where Magic Set Editor lives (otherwise MSECheck looks for it)
