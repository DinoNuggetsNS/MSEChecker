# MSECheck

Checks Magic Set Editor (`.mse-set`) custom Magic: The Gathering sets for rules-text, templating and design-risk problems.
It runs locally and opens in its own window.

## Run
    pip install -r requirements.txt     # optional extras
    python MSECheck.py                  # or: python -m msecheck

Options: `--browser` (use your normal browser), `--no-browser`, `--port N`, `--cards FILE` (Scryfall bulk data), `--no-design-risk`.

## Build the Windows app
Put `MSECheck.ico` next to `MSECheck.py`, then run `build.bat`. The result is `dist\MSECheck.exe`.

## Layout
| File | What it does |
|---|---|
| `msecheck/vocabulary.py` | word lists, keywords, spelling data |
| `msecheck/templating.py` | the rule engine and the templating rules |
| `msecheck/mse_parser.py` | reads `.mse-set` files |
| `msecheck/state.py` | shared app state (current file, lock, settings) |
| `msecheck/context.py` | per-set context used by the checks |
| `msecheck/scryfall_data.py` | optional Scryfall bulk data and similarity |
| `msecheck/card_checks.py` | per-card checks |
| `msecheck/design_risk.py` | loop / balance / design-risk checks |
| `msecheck/set_checks.py` | set-wide checks |
| `msecheck/scryfall_links.py` | builds Scryfall search links |
| `msecheck/analysis.py` | runs everything, applies fixes, builds corrected files |
| `msecheck/reports.py` | exports |
| `msecheck/web_ui.py` | the page and the local web server |
| `msecheck/launcher.py` | start-up: window, browser fallbacks |

Tests: `python -m unittest discover tests`
