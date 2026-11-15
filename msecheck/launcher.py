"""MSECheck - launcher."""
import argparse, os, re, shutil, subprocess, sys, tempfile, threading, time, webbrowser
from http.server import ThreadingHTTPServer
from . import state
from .version import VERSION
from .vocabulary import get_dict
from .state import HEARTBEAT
from .scryfall_data import start_oracle_load
from .web_ui import Handler


def app_dir():
    """Folder holding the .exe (frozen build) or the launcher script; bulk Scryfall files are looked for here."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def _log(msg):
    try:
        folder = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "MSECheck")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "shortcut.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def make_desktop_shortcut():
    """Create Desktop\\MSECheck.lnk pointing at this .exe. Returns True if the file now exists."""
    exe = sys.executable
    q = lambda t: t.replace("'", "''")          # escape for a PowerShell single-quoted string
    ps = (
        "$ErrorActionPreference='Stop';"
        "$d=[Environment]::GetFolderPath('Desktop');$l=Join-Path $d 'MSECheck.lnk';"
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($l);"
        "$s.TargetPath='%s';$s.WorkingDirectory='%s';$s.IconLocation='%s,0';$s.Description='MSECheck';$s.Save();"
        "Write-Output $l" % (q(exe), q(os.path.dirname(exe)), q(exe))
    )
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps],
                       capture_output=True, text=True, timeout=30, creationflags=0x08000000)
    path = (r.stdout or "").strip().splitlines()[-1] if (r.stdout or "").strip() else ""
    _log("powershell exit=%s path=%s stderr=%s" % (r.returncode, path, (r.stderr or "").strip()[:300]))
    return bool(path) and os.path.exists(path)


def ensure_desktop_shortcut():
    """Windows .exe build only: the first time it runs, ask whether to put an MSECheck shortcut on the Desktop.
    A "No" is remembered. A "Yes" that fails to create the file asks again next time. Details go to
    %LOCALAPPDATA%\\MSECheck\\shortcut.log."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    try:
        import ctypes
        folder = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "MSECheck")
        marker = os.path.join(folder, "shortcut_asked")
        if os.path.exists(marker) and open(marker).read().strip() in ("yes", "no"):
            return                                # (an older build wrote "asked" before the answer: ask again)
        os.makedirs(folder, exist_ok=True)
        # MB_YESNO | MB_ICONQUESTION | MB_SETFOREGROUND | MB_TOPMOST
        ans = ctypes.windll.user32.MessageBoxW(0, "Create a MSECheck shortcut on your Desktop?", "MSECheck", 0x04 | 0x20 | 0x10000 | 0x40000)
        _log("answer=%s" % ans)
        if ans != 6:                              # 6 = Yes
            open(marker, "w").write("no")
            return
        if make_desktop_shortcut():
            open(marker, "w").write("yes")
        else:
            ctypes.windll.user32.MessageBoxW(0, "Couldn't create the shortcut. Details are in:\n" + os.path.join(folder, "shortcut.log"),
                                             "MSECheck", 0x10 | 0x40000)
    except Exception as e:
        _log("error: %r" % (e,))


def _find_app_browser():
    """Edge or Chrome, for opening the checker as its own window (no tabs, no address bar)."""
    cands = []
    for env in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
        base = os.environ.get(env)
        if base:
            cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                      os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    cands += [shutil.which(n) for n in ("msedge", "microsoft-edge", "google-chrome", "chromium", "chromium-browser", "chrome")]
    return next((c for c in cands if c and os.path.isfile(c)), None)


def _quit_when_window_closes(srv, grace=20):
    """Used with the app-window fallback: stop once the page has stopped pinging for a while."""
    def watch():
        time.sleep(30)                       # give the window time to appear
        while True:
            time.sleep(3)
            last = HEARTBEAT["last"]
            if last is not None and time.time() - last > grace:
                srv.shutdown()
                return
            if last is None and time.time() - state.START > 120:
                srv.shutdown()
                return
    threading.Thread(target=watch, daemon=True).start()


def main():
    if sys.stdout is None:                   # built with --noconsole: there is nowhere to print
        sys.stdout = sys.stderr = open(os.devnull, "w")
    ap = argparse.ArgumentParser(description="MSECheck")
    ap.add_argument("--port", type=int, default=8876)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--browser", action="store_true", help="open in your normal web browser instead of the app window")
    ap.add_argument("--no-design-risk", action="store_true", help="turn off the loop / balance / design-risk checks")
    ap.add_argument("--cards", help="path to Scryfall bulk data (JSON, JSONL, or .jsonl.gz)")
    ap.add_argument("--no-shortcut", action="store_true", help="do not ask about a Desktop shortcut")
    a = ap.parse_args()
    if not a.no_shortcut and not a.no_browser:
        ensure_desktop_shortcut()
    state.DESIGN_RISK = not a.no_design_risk
    dirs = []
    for d in (app_dir(), os.getcwd(), getattr(sys, "_MEIPASS", None)):   # _MEIPASS: data bundled inside the .exe
        if not d:
            continue
        for e in (d, os.path.join(d, "templates")):
            if os.path.isdir(e) and e not in dirs:
                dirs.append(e)
    path = a.cards
    if path:
        path = os.path.expanduser(path.strip('"'))
        if not os.path.isfile(path):
            path = next((os.path.join(d, path) for d in dirs if os.path.isfile(os.path.join(d, path))), path)
    else:  # newest matching file wins (the date is in the file name)
        pat = re.compile(r"(?:oracle|default)-cards.*(?:\.json|\.jsonl|\.jsonl\.gz)$", re.I)
        path = next((os.path.join(d, f) for d in dirs for f in sorted(os.listdir(d), reverse=True) if pat.match(f)), None)
    if path and os.path.isfile(path):
        print("Loading Scryfall data from %s in the background (a big file can take a minute or two)..." % path)
        try:
            start_oracle_load(path)
        except Exception as e:
            print("Could not load %s: %s" % (path, e))
    else:
        print("No Scryfall bulk file found%s. Looked in: %s" % (" at " + path if path else "", "; ".join(dirs)))
        print("Pass one with --cards, or paste its path into the page.")
    srv = None
    for port in range(a.port, a.port + 25):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            print("Port %d is busy (an older copy may still be running) - trying the next one..." % port)
    if srv is None:
        raise SystemExit("Could not find a free port. Close other copies of the checker and try again.")
    url = "http://127.0.0.1:%d" % srv.server_address[1]
    print("MSECheck v%s running at %s  (Ctrl+C to stop)" % (VERSION, url))
    print("Spell check:", "full dictionary" if get_dict() else "built-in vocabulary (pip install pyspellchecker for more, and to check flavor text)")
    state.START = time.time()
    if a.no_browser:
        mode = "none"
    elif a.browser:
        mode = "browser"
    else:
        mode = "window"
        try:
            import webview                       # pywebview: a real native window, no browser at all
        except Exception:
            webview = None
    if mode == "window" and webview is not None:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            try:
                webview.settings["ALLOW_DOWNLOADS"] = True
            except Exception:
                pass
            try:
                webview.create_window("MSECheck", url, width=1280, height=860, min_size=(900, 600),
                                      text_select=True)   # pywebview blocks selecting/copying text unless this is on
            except TypeError:                             # very old pywebview without that option
                webview.create_window("MSECheck", url, width=1280, height=860, min_size=(900, 600))
            webview.start()                      # returns when the window is closed
            srv.shutdown()
            return
        except Exception as e:
            print("Could not open the app window (%s); falling back." % e)
    if mode == "window":
        exe = _find_app_browser()
        if exe:
            prof = os.path.join(tempfile.gettempdir(), "MSECheck-window")
            try:
                subprocess.Popen([exe, "--app=" + url, "--user-data-dir=" + prof, "--window-size=1280,860", "--no-first-run",
                                  "--no-default-browser-check"])
                _quit_when_window_closes(srv)
            except Exception as e:
                print("Could not open the app window (%s); using your browser." % e)
                mode = "browser"
        else:
            mode = "browser"
    if mode == "browser":
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nBye.")
