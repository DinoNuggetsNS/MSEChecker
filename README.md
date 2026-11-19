<p align="center"><img src="assets/logo.png" alt="MSECheck logo" width="160"></p>

# MSECheck

MSECheck checks custom Magic: The Gathering sets made in **Magic Set Editor** (`.mse-set` files). It looks for typos, templating mistakes, rules problems and design risks, and builds a Scryfall search link for every card.

It runs entirely on your computer. Your original file is never changed.

---

## Get it running (Windows, 64-bit)

1. Go to the **[Releases page](../../releases/latest)** of this repository.
2. Under **Assets**, download **`MSECheck.exe`**.
3. Double-click it. The first time, it asks if you want a shortcut on your Desktop. MSECheck then opens in its own window.

That's it. Nothing else to install. The app already includes Scryfall's **Oracle Cards** data, so "closest real card" matching works straight away.

> Windows may show a blue "Windows protected your PC" box because the app isn't signed. Click **More info**, then **Run anyway**.

---

## How to use it

1. Open MSECheck.
2. Drag your **`.mse-set`** file onto the page, or click **Choose File**. You can also open *Or check a single card's rules text* and paste text in.
3. Read the findings for each card:
   - **Likely error** - probably wrong.
   - **Needs review** - worth a look.
   - **Suggestion** - optional polish.
4. Use **Copy wording** on a finding and make the change in MSE yourself, or **Ignore** to hide it. MSECheck only reads your set; it never edits or saves it.

### Card data (Scryfall)

The release includes Scryfall's Oracle Cards as of the day it was built. To use newer data, download **Oracle Cards** from <https://scryfall.com/docs/api/bulk-data> and put the file next to `MSECheck.exe`. MSECheck prefers a file you put there over the bundled one.

---

## Build it yourself (developers)

Releases are built automatically by GitHub (`.github/workflows/release.yml`) on a 64-bit Windows machine. To publish a new one, open the **Actions** tab, choose **Build Windows app and publish release**, and click **Run workflow**. To run from source instead: `pip install -r requirements.txt` then `python MSECheck.py` (options: `--browser`, `--no-browser`, `--port N`, `--cards FILE`, `--no-design-risk`).

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
