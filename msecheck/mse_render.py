"""MSECheck - draw the cards with Magic Set Editor itself, using MSE's command-line mode.

MSE has to be installed on this computer. MSECheck finds it, writes your working copy of the set to a temporary file,
asks MSE to render every card to a PNG, and shows those pictures in place of the card text.
"""
import glob, hashlib, os, re, shutil, subprocess, sys, tempfile, threading, time
from . import state
from .state import ST

R = {"state": "idle", "message": "", "total": 0, "done": 0, "dir": "", "sig": "", "detail": ""}
_T = None


def _folder():
    return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "MSECheck")


def _log(msg):
    try:
        os.makedirs(_folder(), exist_ok=True)
        with open(os.path.join(_folder(), "mse_render.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def _saved():
    try:
        p = open(os.path.join(_folder(), "mse_path.txt"), encoding="utf-8").read().strip()
        return p if os.path.isfile(p) else None
    except Exception:
        return None


def save_path(p):
    p = (p or "").strip().strip('"')
    if os.path.isdir(p):
        for n in ("mse.exe", "magicseteditor.exe", "mse.com", "magicseteditor.com", "mse"):
            if os.path.isfile(os.path.join(p, n)):
                p = os.path.join(p, n)
                break
    if not os.path.isfile(p):
        raise ValueError("That file doesn't exist. Paste the full path to mse.exe (for example C:\\Program Files\\Magic Set Editor\\mse.exe).")
    os.makedirs(_folder(), exist_ok=True)
    open(os.path.join(_folder(), "mse_path.txt"), "w", encoding="utf-8").write(p)
    return p


def _from_registry():
    """Windows remembers which program opens .mse-set files."""
    if os.name != "nt":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".mse-set") as k:
            prog = winreg.QueryValue(k, "")
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog + r"\shell\open\command") as k:
            cmd = winreg.QueryValue(k, "")
        m = re.match(r'\s*"([^"]+)"|\s*(\S+)', cmd)
        return (m.group(1) or m.group(2)) if m else None
    except Exception:
        return None


def find_mse():
    cands = [state.MSE_PATH, os.environ.get("MSE_PATH"), _saved(), _from_registry(), shutil.which("mse"), shutil.which("magicseteditor")]
    home = os.path.expanduser("~")
    roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.path.join(os.environ.get("LOCALAPPDATA") or "", "Programs"),
             os.path.join(home, "Desktop"), os.path.join(home, "Downloads"), os.path.join(home, "Documents"), "C:\\"]
    for root in filter(None, roots):
        for pat in ("*Magic*Set*Editor*", "MSE*", "mse*"):
            for d in glob.glob(os.path.join(root, pat)):
                for n in ("mse.exe", "magicseteditor.exe"):
                    cands.append(os.path.join(d, n))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def _console_exe(exe):
    """mse.com is MSE's console launcher; it can read commands from stdin, mse.exe (the window) cannot."""
    d = os.path.dirname(exe)
    for n in ("mse.com", "magicseteditor.com"):
        if os.path.isfile(os.path.join(d, n)):
            return os.path.join(d, n)
    return exe


def _sig():
    return hashlib.md5((ST.get("text") or "").encode("utf-8")).hexdigest()


def _have():
    d = R["dir"]
    if not d or not os.path.isdir(d):
        return []
    return sorted(int(f[:-4]) for f in os.listdir(d) if re.fullmatch(r"\d+\.png", f))


def status():
    have = _have()
    return {"found": find_mse(), "state": R["state"], "message": R["message"], "detail": R["detail"], "total": R["total"],
            "done": len(have) if R["state"] == "running" else R["done"], "have": have if R["state"] == "done" else [],
            "stale": R["state"] == "done" and R["sig"] != _sig()}


def image(idx):
    p = os.path.join(R["dir"] or "", "%d.png" % idx)
    return open(p, "rb").read() if R["dir"] and os.path.isfile(p) else None


def start(set_bytes, total):
    """Begin drawing in the background. set_bytes is the working copy of the .mse-set file."""
    global _T
    if R["state"] == "running":
        return
    exe = find_mse()
    if not exe:
        raise ValueError("Magic Set Editor wasn't found on this computer.")
    if R["dir"]:
        shutil.rmtree(R["dir"], ignore_errors=True)
    work = tempfile.mkdtemp(prefix="msecheck_")
    setfile = os.path.join(work, "set.mse-set")
    out = os.path.join(work, "out")
    os.makedirs(out)
    open(setfile, "wb").write(set_bytes)
    R.update(state="running", message="Starting Magic Set Editor…", total=total, done=0, dir=out, sig=_sig(), detail="")
    _T = threading.Thread(target=_run, args=(exe, setfile, out, total), daemon=True)
    _T.start()


def _popen(args, **kw):
    return subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            creationflags=0x08000000 if os.name == "nt" else 0, **kw)


def _wait(proc, feed, out, total, limit):
    """Feed commands to MSE and wait, updating the progress count."""
    try:
        if feed is not None:
            proc.stdin.write(feed)
            proc.stdin.close()
    except Exception:
        pass
    t0, text = time.time(), []
    reader = threading.Thread(target=lambda: text.append(proc.stdout.read()), daemon=True)
    reader.start()
    while proc.poll() is None and time.time() - t0 < limit:
        n = len(_have())
        R["done"] = n
        R["message"] = "Drawing your cards with Magic Set Editor… %d of %d" % (n, total)
        time.sleep(0.5)
    if proc.poll() is None:
        proc.kill()
        text.append("\n(timed out)")
    reader.join(2)
    return "".join(text)[-1500:]


def _run(exe, setfile, out, total):
    cli, o = _console_exe(exe), out.replace("\\", "/")
    # 1) MSE's interactive script mode: render every card with MSE's own write_image_file()
    script = ('for each card in set.cards do write_image_file(card, file: "%s/" + position(of: card, in: set) + ".png")\n:quit\n' % o)
    log = ""
    try:
        _log("exe=%s set=%s" % (cli, setfile))
        proc = _popen([cli, "--cli", setfile], cwd=os.path.dirname(cli))
        log = _wait(proc, script, out, total, 1800)
        _log("cli output: " + log.replace("\n", " | ")[:600])
        # 2) fall back to MSE's --export option
        if not _have():
            R["message"] = "Trying MSE's export option…"
            proc = _popen([cli, "--export", setfile, o + "/{position(of:card,in:set)}.png"], cwd=os.path.dirname(cli))
            log2 = _wait(proc, None, out, total, 1800)
            _log("export output: " + log2.replace("\n", " | ")[:600])
            log = (log + "\n" + log2).strip()
        n = len(_have())
        if n:
            R.update(state="done", done=n, message="Drew %d of %d cards." % (n, total), detail="")
        else:
            R.update(state="error", message="Magic Set Editor didn't draw any pictures.", detail=log.strip()[-900:])
    except Exception as e:
        _log("error: %r" % (e,))
        R.update(state="error", message="Couldn't run Magic Set Editor: %s" % e, detail=log[-900:])
