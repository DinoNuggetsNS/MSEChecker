# MSECheck

MSECheck checks custom Magic: The Gathering sets made in **Magic Set Editor** (`.mse-set` files). It looks for typos, templating mistakes, rules problems and design risks, and builds a Scryfall search link for every card.

It runs entirely on your computer. Your original file is never changed.

---

## Get it running (Windows)

### Option A: Download the app (easiest)

1. Go to the **[Releases page](../../releases)** of this repository.
2. Under the newest release, download **`MSECheck.exe`**.
3. Double-click it. MSECheck opens in its own window.

> Windows may show a blue "Windows protected your PC" box because the app isn't signed. Click **More info**, then **Run anyway**.

If there is no release yet, use Option B, or build the app yourself (see [Build the app](#build-the-app-yourself)).

### Option B: Run it from the code

1. **Install Python.** Download it from <https://www.python.org/downloads/>. On the first screen of the installer, tick **Add python.exe to PATH**, then click **Install Now**.
2. **Download this project.** On this page click the green **Code** button, then **Download ZIP**. Right-click the ZIP and choose **Extract All**.
3. **Open a terminal in that folder.** In File Explorer, open the extracted folder, click the address bar, type `cmd` and press Enter.
4. **Install the extras** (recommended). Paste this and press Enter:
   ```
   pip install -r requirements.txt
   ```
   This adds the spell checker for flavor text, the app-style window, and faster loading. MSECheck still works without them.
5. **Start it:**
   ```
   python MSECheck.py
   ```

---

## How to use it

1. Open MSECheck.
2. Drag your **`.mse-set`** file onto the page, or click **Choose File**. You can also open *Or check a single card's rules text* and paste text in.
3. Read the findings for each card:
   - **Likely error** - probably wrong.
   - **Needs review** - worth a look.
   - **Suggestion** - optional polish.
4. Use **Apply** on a finding to fix it, or **Ignore** to hide it. **Download corrected copy** saves a new file; the original is never overwritten.
5. **CSV**, **HTML** and **Text** export the full report.

### Optional: closest real card (Scryfall data)

1. Go to <https://scryfall.com/docs/api/bulk-data> and download **Oracle Cards**.
2. Put that file in the same folder as `MSECheck.py` (or `MSECheck.exe`). MSECheck finds it automatically and loads it in the background.

---

## Options

```
python MSECheck.py --browser          open in your normal web browser instead of its own window
python MSECheck.py --no-browser       just start the server
python MSECheck.py --port 9000        use a different port
python MSECheck.py --cards FILE       load a specific Scryfall file
python MSECheck.py --no-design-risk   turn off the loop / balance checks
```

## Build the app yourself

1. Do steps 1-3 of Option B.
2. Install the build tools:
   ```
   pip install -r requirements.txt -r requirements-build.txt
   ```
3. Run:
   ```
   build.bat
   ```
4. Your app is at `dist\MSECheck.exe`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick **Add python.exe to PATH**. |
| The window doesn't open | Run `python MSECheck.py --browser`. |
| "Port is busy" | An older copy is still running. Close it, or use `--port 9000`. |
| No spelling check on flavor text | Run `pip install pyspellchecker`. |

---

## For developers

| File | What it does |
|---|---|
| `MSECheck.py` | the file you run |
| `msecheck/vocabulary.py` | word lists, keywords, spelling data |
| `msecheck/templating.py` | the rule engine and templating rules |
| `msecheck/mse_parser.py` | reads `.mse-set` files |
| `msecheck/state.py` | shared app state |
| `msecheck/context.py` | per-set context used by the checks |
| `msecheck/scryfall_data.py` | optional Scryfall data and similarity |
| `msecheck/card_checks.py` | per-card checks |
| `msecheck/design_risk.py` | loop / balance / design-risk checks |
| `msecheck/set_checks.py` | set-wide checks |
| `msecheck/scryfall_links.py` | builds Scryfall search links |
| `msecheck/analysis.py` | runs everything, applies fixes, builds corrected files |
| `msecheck/reports.py` | exports |
| `msecheck/web_ui.py` | the page and local web server |
| `msecheck/launcher.py` | start-up and window handling |

Run the tests with `python -m unittest discover tests`.
