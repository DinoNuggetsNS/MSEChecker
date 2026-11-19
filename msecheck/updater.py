"""MSECheck - in-app updates (Windows .exe build): compares this build with the newest GitHub release and swaps the exe in place."""
import json, os, subprocess, sys, tempfile, threading, urllib.request
from . import state

REPO = "DinoNuggetsNS/MSEChecker"
_cache = {"t": 0, "v": None}


def current():
    try:
        from .build import TAG
        return TAG
    except Exception:
        return ""


def available():
    return os.name == "nt" and getattr(sys, "frozen", False) and bool(current())


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "MSECheck", "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout)


def check(force=False):
    """-> {"enabled", "current", "latest", "newer"}. Never raises."""
    import time
    out = {"enabled": available(), "current": current(), "latest": "", "newer": False}
    if not out["enabled"]:
        return out
    if not force and _cache["v"] and time.time() - _cache["t"] < 600:
        return _cache["v"]
    try:
        with _get("https://api.github.com/repos/%s/releases/latest" % REPO) as r:
            j = json.loads(r.read().decode("utf-8"))
        out["latest"] = j.get("tag_name", "")
        out["newer"] = bool(out["latest"]) and out["latest"] > out["current"]
        _cache.update(t=time.time(), v=out)
    except Exception:
        pass
    return out


def cleanup():
    """Delete the previous exe left behind by an update."""
    try:
        old = os.path.join(os.path.dirname(sys.executable), "MSECheck.old.exe")
        if available() and os.path.exists(old):
            os.remove(old)
    except Exception:
        pass


def apply():
    """Download the newest MSECheck.exe, swap it in, start it, and quit this copy. Returns (ok, message) on failure."""
    info = check(True)
    if not info["enabled"] or not info["newer"]:
        return False, "You already have the newest version."
    exe = sys.executable
    folder = os.path.dirname(exe)
    new, old = os.path.join(folder, "MSECheck.new.exe"), os.path.join(folder, "MSECheck.old.exe")
    try:
        url = "https://github.com/%s/releases/download/%s/MSECheck.exe" % (REPO, info["latest"])
        with _get(url, 180) as r, open(new, "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        if os.path.getsize(new) < 5_000_000:
            raise RuntimeError("the download looks incomplete")
        if os.path.exists(old):
            os.remove(old)
        os.replace(exe, old)          # a running exe can be renamed, just not overwritten
        try:
            os.replace(new, exe)
        except Exception:
            os.replace(old, exe)      # put the original back
            raise
    except Exception as e:
        try:
            if os.path.exists(new):
                os.remove(new)
        except Exception:
            pass
        return False, "Couldn't update (%s). Download MSECheck.exe from the Releases page instead." % e
    subprocess.Popen([exe], cwd=folder, close_fds=True, creationflags=0x00000008 | 0x00000200)   # DETACHED_PROCESS | NEW_GROUP
    threading.Timer(0.6, lambda: os._exit(0)).start()
    return True, info["latest"]
