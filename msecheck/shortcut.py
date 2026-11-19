"""MSECheck - Desktop shortcut (Windows .exe build). The question is asked inside the app window, not in a system dialog."""
import os, subprocess, sys, time
from . import state


def _folder():
    return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "MSECheck")


def _log(msg):
    try:
        os.makedirs(_folder(), exist_ok=True)
        with open(os.path.join(_folder(), "shortcut.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def _marker():
    return os.path.join(_folder(), "shortcut_choice")


def _desktop_dir():
    """The real Desktop folder (follows OneDrive redirection)."""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.shell32.SHGetFolderPathW(0, 0x10, 0, 0, buf) == 0 and buf.value:   # CSIDL_DESKTOPDIRECTORY
            return buf.value
    except Exception:
        pass
    home = os.path.expanduser("~")
    for c in (os.path.join(home, "OneDrive", "Desktop"), os.path.join(home, "Desktop")):
        if os.path.isdir(c):
            return c
    return os.path.join(home, "Desktop")


def available():
    return os.name == "nt" and getattr(sys, "frozen", False) and state.SHORTCUT_ENABLED


def _exists():
    d = _desktop_dir()
    return any(os.path.exists(os.path.join(d, n)) for n in ("MSECheck.lnk", "MSECheck.url"))


def should_ask():
    """Ask unless the person said 'never' or the shortcut is really on the Desktop (a stale 'yes' note doesn't count)."""
    if not available():
        return False
    try:
        if os.path.exists(_marker()) and open(_marker()).read().strip() == "never":
            return False
        if _exists():
            return False
    except Exception:
        pass
    return True


def _icon():
    """Copy the bundled logo icon next to the app data (named by size, so Windows drops any cached old icon); fall back to the exe."""
    exe = sys.executable
    try:
        import shutil
        src = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(exe)), "MSECheck.ico")
        if os.path.exists(src):
            os.makedirs(_folder(), exist_ok=True)
            dst = os.path.join(_folder(), "MSECheck-logo-%d.ico" % os.path.getsize(src))
            if not os.path.exists(dst):
                shutil.copyfile(src, dst)
            return dst + ",0"
    except Exception as e:
        _log("icon copy failed: %r" % (e,))
    return exe + ",0"


def refresh():
    """If a Desktop shortcut already exists, rewrite it so it shows the current logo."""
    try:
        if available() and os.path.exists(os.path.join(_desktop_dir(), "MSECheck.lnk")):
            create()
    except Exception as e:
        _log("refresh failed: %r" % (e,))


def create():
    """Create Desktop\\MSECheck.lnk. Returns (ok, message)."""
    exe = sys.executable
    icon = _icon()
    desk = _desktop_dir()
    lnk = os.path.join(desk, "MSECheck.lnk")
    q = lambda t: t.replace("'", "''")
    ps = ("$ErrorActionPreference='Stop';$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
          "$s.TargetPath='%s';$s.WorkingDirectory='%s';$s.IconLocation='%s';$s.Description='MSECheck';$s.Save()"
          % (q(lnk), q(exe), q(os.path.dirname(exe)), q(icon)))
    err = ""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, text=True, timeout=40, creationflags=0x08000000)
        err = (r.stderr or "").strip()[:400]
        _log("powershell exit=%s lnk=%s stderr=%s" % (r.returncode, lnk, err))
        if os.path.exists(lnk):
            _remember("yes")
            return True, lnk
    except Exception as e:
        err = repr(e)
        _log("powershell error: %s" % err)
    # fallback: an internet-shortcut file that points at the .exe
    try:
        url = os.path.join(desk, "MSECheck.url")
        with open(url, "w", encoding="utf-8") as f:
            f.write("[InternetShortcut]\nURL=file:///%s\nIconFile=%s\nIconIndex=0\n" % (exe.replace("\\", "/"), icon.rsplit(",", 1)[0]))
        _log("fallback .url written: %s" % url)
        if os.path.exists(url):
            _remember("yes")
            return True, url
    except Exception as e:
        err = (err + " " + repr(e)).strip()
        _log("fallback error: %r" % (e,))
    return False, err or "Windows would not let MSECheck write to the Desktop."


def _remember(v):
    try:
        os.makedirs(_folder(), exist_ok=True)
        open(_marker(), "w").write(v)
    except Exception:
        pass


def never():
    _remember("never")
