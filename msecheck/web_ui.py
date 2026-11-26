"""MSECheck - web ui."""
import json, os, re, time, urllib.parse
from http.server import BaseHTTPRequestHandler
from .state import HEARTBEAT, LOCK, ST
from .scryfall_data import ORACLE, _strip_name, close_for_finding, find_close_oracle_matches, load_oracle
from .analysis import analyze, load_text, load_upload
from .reports import export
from . import shortcut, symbols_data
import base64
_SYMBOLS_PNG = base64.b64decode("".join(symbols_data.PNG_B64))


def _sets_dir():
    import os, sys
    here = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0] else os.getcwd()
    for d in (getattr(sys, "_MEIPASS", None), here, os.getcwd()):
        if d and os.path.isfile(os.path.join(d, "setsdata", "index.json")):
            return os.path.join(d, "setsdata")
    return None


def _cset_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "customsets")


def _cset_index():
    try:
        return json.load(open(os.path.join(_cset_dir(), "index.json"), encoding="utf-8"))
    except Exception:
        return []


def _sets_index():
    d = _sets_dir()
    try:
        return json.load(open(os.path.join(d, "index.json"), encoding="utf-8")) if d else []
    except Exception:
        return []


# ----------------------------------------------------------------------------------------
# Web UI
# ----------------------------------------------------------------------------------------
PAGE = r"""<!doctype html><html lang=en data-theme=dark><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=icon type=image/png href="data:image/png;base64,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">
<title>MSECheck</title>
<script>try{document.documentElement.dataset.theme=localStorage.getItem('msecheck-theme')==='light'?'light':'dark'}catch(e){}</script>
<style>
:root{--font:"Inter","Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,Roboto,"Helvetica Neue",Arial,sans-serif;
--brand:#a2d7f2;--brand2:#6fb8e0;--r:16px}
:root[data-theme=dark]{color-scheme:dark;--bg:#0a0a0c;--fg:#f4f4f6;--mut:#a3a3ad;--glass:rgba(255,255,255,.055);--glass2:rgba(255,255,255,.04);--inset:rgba(0,0,0,.28);
--bd:rgba(255,255,255,.11);--bd2:rgba(255,255,255,.2);--head:rgba(10,10,12,.72);--sh:0 10px 40px rgba(0,0,0,.35);
--lime:#c6e65a;--grad:linear-gradient(165deg,#8a4f9e 0%,#69598f 48%,#4d8c9f 100%);--err:#ff7a6e;--rev:#ffbe5c;--sug:#74b2ff;--ok:#5fd68a;--accent:#a2d7f2;
--mark:rgba(255,196,80,.28);--del:rgba(255,107,94,.3);--ins:rgba(84,210,128,.28);
--fade:linear-gradient(transparent,transparent)}
:root[data-theme=light]{color-scheme:light;--bg:#fbf8f7;--fg:#16161a;--mut:#62626d;--glass:rgba(255,255,255,.66);--glass2:rgba(255,255,255,.55);--inset:rgba(20,20,30,.045);
--bd:rgba(20,20,30,.1);--bd2:rgba(20,20,30,.2);--head:rgba(251,248,247,.78);--sh:0 10px 34px rgba(60,30,30,.1);
--lime:#5c8500;--grad:linear-gradient(165deg,#8a4f9e 0%,#69598f 48%,#4d8c9f 100%);--err:#c62828;--rev:#a85a00;--sug:#1559b8;--ok:#1f7a3d;--accent:#2b7fb0;
--mark:rgba(255,200,60,.45);--del:rgba(239,100,90,.3);--ins:rgba(80,190,110,.32);
--fade:linear-gradient(transparent,transparent)}
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;background:transparent;color:var(--fg);font:15px/1.55 var(--font);-webkit-font-smoothing:antialiased;min-height:100vh}
body::before{content:"";position:fixed;inset:0;z-index:-1;background:var(--fade),var(--bg)}
body.plain::before{background:var(--bg)}
body.plain #floaters{display:none}
body.lens .fsym{opacity:.3;transition:opacity .15s}body.lens .fsym.c{opacity:.55}.fsym.c{background-color:transparent;-webkit-mask:none;mask:none;opacity:.28}body.lens .fsym.hit{opacity:.95}
#herologo{cursor:grab;touch-action:none;-webkit-user-drag:none;user-select:none}#brandlogo{cursor:pointer}
.herologo.held{position:fixed!important;z-index:70;width:120px!important;max-width:none;animation:none!important;cursor:grabbing;transition:none;filter:drop-shadow(1.5px 0 0 #fff) drop-shadow(-1.5px 0 0 #fff) drop-shadow(0 1.5px 0 #fff) drop-shadow(0 -1.5px 0 #fff) drop-shadow(0 8px 14px rgba(0,0,0,.45))}
:root[data-theme=light] .herologo.held{filter:drop-shadow(0 8px 14px rgba(0,0,0,.35))}
.herologo{transition:width .35s ease}
#settip{position:fixed;z-index:80;pointer-events:none;padding:.45rem .7rem;border-radius:10px;background:var(--glass2);border:1px solid var(--bd2);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);font-size:13px;line-height:1.35;box-shadow:0 8px 24px rgba(0,0,0,.35);max-width:260px}
#settip b{display:block;font-weight:650}#settip span{color:var(--mut);font-size:12px}
#floaters{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:-1}
.fsym{position:absolute;left:0;top:0;width:var(--s);height:var(--s);background:var(--fg);opacity:.085;will-change:transform;-webkit-mask:url(/symbols.png) no-repeat;mask:url(/symbols.png) no-repeat;-webkit-mask-size:calc(var(--s)*12) calc(var(--s)*10);mask-size:calc(var(--s)*12) calc(var(--s)*10);-webkit-mask-position:calc(var(--s)*var(--cx)*-1) calc(var(--s)*var(--cy)*-1);mask-position:calc(var(--s)*var(--cx)*-1) calc(var(--s)*var(--cy)*-1)}
body,main,article,pre,.f,.tile{-webkit-user-select:text;user-select:text}
::selection{background:rgba(162,215,242,.35)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
small{color:var(--mut)}.mut{color:var(--mut)}
::-webkit-scrollbar{width:11px;height:11px}::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:9px;border:3px solid transparent;background-clip:content-box}
/* header */
header.top{position:sticky;top:0;z-index:50;background:var(--head);backdrop-filter:blur(18px) saturate(1.4);-webkit-backdrop-filter:blur(18px) saturate(1.4);border-bottom:1px solid var(--bd)}
.topin{max-width:1180px;margin:auto;padding:.6rem 1.2rem;display:flex;align-items:center;gap:.7rem;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:.6rem;color:var(--fg);font-weight:650;font-size:17px;letter-spacing:-.02em;text-decoration:none!important}
.brand img{height:32px;width:auto;display:block}
:root:not([data-theme=light]) .brand img,:root:not([data-theme=light]) #mlogo{filter:drop-shadow(1px 0 0 #fff) drop-shadow(-1px 0 0 #fff) drop-shadow(0 1px 0 #fff) drop-shadow(0 -1px 0 #fff)}
.pill{font-size:11px;font-weight:600;padding:2px 9px;border-radius:99px;border:1px solid var(--bd);color:var(--mut);background:var(--glass2)}
.filters{display:flex;gap:.3rem;flex-wrap:wrap;margin-left:.2rem}
.chip{white-space:nowrap;display:inline-flex;align-items:center;gap:.45rem;cursor:pointer;padding:.3rem .56rem;border-radius:99px;border:1px solid var(--bd);background:var(--glass2);font-size:12.5px;font-weight:550;transition:.15s;color:var(--mut)}
.chip input{display:none}.chip i{width:8px;height:8px;border-radius:50%;background:currentColor;opacity:.9}
.chip b{font-weight:650;font-variant-numeric:tabular-nums;color:var(--fg)}
.chip:hover{border-color:var(--bd2)}
.chip:has(input:checked){color:var(--c);border-color:color-mix(in srgb,var(--c) 55%,transparent);background:color-mix(in srgb,var(--c) 13%,transparent)}
.chip.e{--c:var(--err)}.chip.r{--c:var(--rev)}.chip.s{--c:var(--sug)}.chip.o{--c:var(--lime)}
.chip.g:has(input:checked){background:var(--grad);color:#fff;border-color:transparent;box-shadow:0 4px 18px rgba(105,89,143,.5)}.chip.g:has(input:checked) b{color:#fff}
.tools{margin-left:auto;display:flex;align-items:center;gap:.5rem}
input[type=search],input[type=text],select,textarea{background:var(--glass2);color:var(--fg);border:1px solid var(--bd);border-radius:11px;padding:.42rem .75rem;font:inherit;font-size:13.5px;outline:none;transition:.15s}
input[type=search]{width:min(270px,100%)}
.topin.loaded .tools{flex:1 1 100%;margin-left:0}.topin.loaded #q{flex:1 1 auto;width:auto;min-width:0}
input.bad{border-color:var(--err)!important;box-shadow:0 0 0 3px color-mix(in srgb,var(--err) 20%,transparent)!important}select{padding-right:.4rem;cursor:pointer}option{background:var(--bg);color:var(--fg)}
input:focus,select:focus,textarea:focus{border-color:var(--brand);box-shadow:0 0 0 3px rgba(162,215,242,.2)}
textarea{width:100%;resize:vertical}
.switch{position:relative;width:58px;height:30px;border-radius:99px;border:1px solid var(--bd);background:var(--glass);cursor:pointer;padding:0;flex:none}
.switch svg{position:absolute;top:7px;width:16px;height:16px;stroke:var(--mut);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.switch .sun{left:8px}.switch .moon{right:8px}
.switch .knob{position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:50%;background:linear-gradient(135deg,var(--brand),var(--brand2));box-shadow:0 2px 8px rgba(162,215,242,.5);transition:transform .22s cubic-bezier(.3,.8,.3,1)}
:root[data-theme=light] .switch .knob{transform:translateX(28px)}
/* buttons */
button,.btn{white-space:nowrap;font:inherit;font-size:13px;font-weight:550;color:var(--fg);background:var(--glass);border:1px solid var(--bd);border-radius:99px;padding:.38rem .9rem;cursor:pointer;transition:.15s;display:inline-flex;align-items:center;gap:.4rem;text-decoration:none!important}
button:hover,.btn:hover{border-color:var(--bd2);background:color-mix(in srgb,var(--fg) 8%,transparent)}
.pri{background:linear-gradient(135deg,var(--brand),var(--brand2))!important;border-color:transparent!important;color:#0c2433!important;box-shadow:0 6px 22px rgba(162,215,242,.35)}
.pri:hover{filter:brightness(1.08)}
.ghost{background:transparent}
.lg{padding:.8rem 1.7rem;font-size:15px}
button:disabled{opacity:.4;cursor:default}
button:focus,.btn:focus{outline:none}button:focus-visible,.btn:focus-visible{outline:2px solid color-mix(in srgb,var(--brand) 70%,transparent);outline-offset:2px}
.sep{width:1px;align-self:stretch;background:var(--bd);margin:0 .2rem}
main{max-width:1180px;margin:auto;padding:0 1.2rem 4rem}
.glass{background:var(--glass);border:1px solid var(--bd);border-radius:var(--r);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);box-shadow:var(--sh)}
/* hero */
.heroin{display:grid;grid-template-columns:1.2fr .8fr;gap:2rem;align-items:center;padding:4.2rem 0 2.6rem}
.eyebrow{display:inline-flex;align-items:center;gap:.5rem;padding:.35rem .85rem;border-radius:99px;border:1px solid var(--bd);background:var(--glass);font-size:12.5px;font-weight:550;color:var(--mut)}
.eyebrow i{width:8px;height:8px;border-radius:50%;background:var(--brand);box-shadow:0 0 10px var(--brand)}
h1{font-size:clamp(2.4rem,5.2vw,4.1rem);line-height:1.04;letter-spacing:-.045em;font-weight:720;margin:1.1rem 0 1rem}
h1 em{font-style:normal;background:linear-gradient(120deg,var(--fg) 20%,var(--accent));-webkit-background-clip:text;background-clip:text;color:transparent}
.lead{font-size:16.5px;color:var(--mut);max-width:34em;margin:0 0 1.6rem}
.cta{display:flex;gap:.8rem;flex-wrap:wrap}.hint{color:var(--mut);font-size:13px;margin:1rem 0 0}
.paste{padding:1rem;margin-top:1.2rem;max-width:34em}.paste p{margin:.4rem 0}.paste input{width:100%}
.heroart{position:relative;display:grid;place-items:center;min-height:300px}
.herologo{display:block;position:relative;width:min(100%,380px);height:auto;animation:fl 6s ease-in-out infinite;filter:drop-shadow(0 24px 40px rgba(0,0,0,.25))}
:root:not([data-theme=light]) .herologo{filter:drop-shadow(2.5px 0 0 #fff) drop-shadow(-2.5px 0 0 #fff) drop-shadow(0 2.5px 0 #fff) drop-shadow(0 -2.5px 0 #fff)}
.glow{position:absolute;width:75%;aspect-ratio:1;border-radius:50%;background:radial-gradient(circle,rgba(162,215,242,.55),transparent 68%);filter:blur(30px)}
@keyframes fl{50%{transform:translateY(-12px) rotate(-1deg)}}
@media(prefers-reduced-motion:reduce){.heroart img{animation:none}}
.stats3{display:grid;grid-template-columns:1fr 1fr 1.7fr;padding:1.6rem 1.8rem;gap:1.6rem}
.stats3>div+div{border-left:1px solid var(--bd);padding-left:1.6rem}
.stats3 h4{margin:0 0 .5rem;font-size:15px;font-weight:650;color:var(--accent);letter-spacing:-.01em}
.stats3 b{display:block;font-size:1.7rem;letter-spacing:-.03em;font-weight:700;line-height:1.2;margin-bottom:.2rem}
.stats3 span{color:var(--mut);font-size:12.5px}.stats3 .comm{font-size:14px;line-height:1.5;color:var(--fg);display:block}.stats3 .comm b{display:inline;font-size:inherit;margin:0;color:var(--accent)}
@media(max-width:860px){.heroin{grid-template-columns:1fr;padding-top:2rem}.heroart{display:none}.stats3{grid-template-columns:1fr}.stats3>div+div{border-left:0;padding-left:0;border-top:1px solid var(--bd);padding-top:1rem}}
/* dashboard */
#summary{padding:1.3rem 1.4rem;margin:1.4rem 0 1rem}
.sumhead{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;align-items:flex-start}
.eyebrow2{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--accent);font-weight:650}
#summary h2{margin:.15rem 0 0;font-size:1.6rem;letter-spacing:-.03em;font-weight:700;word-break:break-all}
.acts2{display:flex;gap:.45rem;flex-wrap:wrap;align-items:center}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:.7rem;margin-top:1.1rem}
.tile{background:var(--glass2);border:1px solid var(--bd);border-radius:14px;padding:.75rem .95rem}
.tile b{display:block;font-size:1.7rem;letter-spacing:-.03em;font-weight:700;line-height:1.15;font-variant-numeric:tabular-nums}
.tile span{font-size:12.5px;color:var(--mut)}
.tile.e b{color:var(--err)}.tile.r b{color:var(--rev)}.tile.s b{color:var(--sug)}.tile.o b{color:var(--ok)}
.ignbtn{margin-left:auto;font-size:15px;line-height:1;width:34px;height:30px;padding:0;border-radius:99px;display:inline-flex;align-items:center;justify-content:center}.acts2 button.on{background:var(--grad);color:#fff;border-color:transparent}.ignbtn.on{background:var(--grad);color:#fff;border-color:transparent}.igncard{opacity:.6}.igncard .rules{display:none}
.dets{margin-top:.9rem;color:var(--mut);font-size:13px}.dets summary{cursor:pointer;font-weight:550}.dgrid{display:grid;gap:1rem;margin-top:.9rem;padding:1rem 1.1rem;border-radius:14px;border:1px solid var(--bd);background:var(--glass2)}
.dgrid h5{margin:0 0 .4rem;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);font-weight:650}
.dchips{display:flex;flex-wrap:wrap;gap:.35rem}.dchips{gap:.25rem .65rem}.dchip{display:inline-flex;gap:.35rem;align-items:baseline;color:var(--fg);font-size:13.5px}
.dchip b{color:var(--mut);font-weight:550}.dchip:not(:last-child)::after{content:"·";margin-left:.65rem;color:var(--mut)}.dchip.kw{color:var(--mut)}
.drow{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem}.dval{color:var(--fg);font-size:13.5px;font-weight:550}
.warn{margin-top:.9rem;padding:.7rem 1rem;border-radius:12px;border:1px solid var(--err);color:var(--err);background:color-mix(in srgb,var(--err) 10%,transparent);font-weight:550}
article{background:var(--glass);border:1px solid var(--bd);border-radius:var(--r);padding:1.15rem 1.3rem;margin:.9rem 0;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
article header{display:flex;flex-wrap:wrap;gap:.3rem .8rem;align-items:baseline}
article h3{margin:0;font-size:1.12rem;letter-spacing:-.02em;font-weight:650}
.dots{margin-left:auto;display:flex;gap:.35rem}
.dot{font-size:12px;font-weight:650;padding:1px 9px;border-radius:99px;border:1px solid color-mix(in srgb,currentColor 45%,transparent);background:color-mix(in srgb,currentColor 12%,transparent)}
.dot.e{color:var(--err)}.dot.r{color:var(--rev)}.dot.s{color:var(--sug)}
pre.rules{white-space:pre-wrap;background:var(--inset);border-radius:12px;padding:.7rem .9rem;margin:.7rem 0;font:inherit;font-size:14.5px}
.ok{color:var(--ok);font-weight:600;margin:.4rem 0}
.f{border:1px solid var(--bd);border-left:3px solid var(--bd2);padding:.7rem 1rem;margin:.7rem 0;background:var(--glass2);border-radius:12px}
.f.likely{border-left-color:var(--err)}.f.review{border-left-color:var(--rev)}.f.suggestion{border-left-color:var(--sug)}
.badge{font-size:11.5px;font-weight:650;padding:1px 9px;border-radius:99px;border:1px solid currentColor;margin-right:.3rem}
.likely .badge{color:var(--err)}.review .badge{color:var(--rev)}.suggestion .badge{color:var(--sug)}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin-top:.65rem;font-weight:600}
blockquote{margin:.25rem 0;padding-left:.7rem;border-left:2px solid var(--bd2)}
mark{background:var(--mark);color:inherit;border-radius:2px;padding:0;margin:0}del{background:var(--del);text-decoration:none;border-radius:2px;padding:0;margin:0;white-space:pre-wrap}ins{background:var(--ins);text-decoration:none;border-radius:2px;padding:0;margin:0;white-space:pre-wrap}
.acts{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.7rem}
.matches{margin-top:12px;padding:12px 14px;border:1px solid var(--bd);border-radius:14px;background:var(--glass2)}.matches h4{margin:0 0 4px}
.match{padding:10px 0;border-top:1px solid var(--bd);display:flow-root}.match:first-of-type{border-top:0}.match img{float:right;width:96px;border-radius:7px;margin:0 0 4px 12px}
.match .rules{max-height:150px;overflow:auto;font-size:.9em}
.pager{display:flex;justify-content:space-between;align-items:center;margin:.8rem 0;gap:.6rem}
@media(max-width:700px){header.top{position:static}}
.empty{padding:2rem;text-align:center;display:grid;gap:.4rem;margin-top:1rem}.empty b{font-size:1.1rem}
.modal{position:fixed;inset:0;z-index:120;display:grid;place-items:center;padding:1rem;background:color-mix(in srgb,var(--bg) 55%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);animation:mfade .25s ease}
.mcard{width:min(420px,100%);padding:2rem 1.8rem 1.4rem;text-align:center;position:relative;overflow:hidden;animation:mpop .35s cubic-bezier(.2,.9,.3,1.2)}
.mcard::before{content:"";position:absolute;inset:-40% -20% auto -20%;height:80%;background:radial-gradient(closest-side,rgba(162,215,242,.5),transparent);filter:blur(24px);z-index:-1}
.mico{width:72px;height:72px;margin:0 auto 1rem;border-radius:20px;display:grid;place-items:center;background:var(--glass);border:1px solid var(--bd);box-shadow:0 10px 30px rgba(162,215,242,.35)}
.mico img{width:46px;height:auto;border-radius:6px}
.mcard h3{margin:0 0 .5rem;font-size:1.3rem;letter-spacing:-.025em;font-weight:700}.mcard p{margin:0 0 1.3rem;color:var(--mut);font-size:14px}
.mbtns{display:flex;gap:.6rem;justify-content:center;flex-wrap:wrap}
#mkshort{border-color:var(--bd2);background:var(--glass2)}
.short{display:flex;gap:.6rem;justify-content:center;flex-wrap:wrap;margin-top:1.2rem}.short .btn{margin:0}
.mlink{background:none;border:0;color:var(--mut);font-size:12.5px;margin-top:1rem;padding:.2rem .4rem;font-weight:500}.mlink:hover{color:var(--fg);background:none;text-decoration:underline}
.mcard.ok .mico{box-shadow:0 10px 30px rgba(95,214,138,.4)}
@keyframes mfade{from{opacity:0}}@keyframes mpop{from{opacity:0;transform:translateY(14px) scale(.96)}}
@media(prefers-reduced-motion:reduce){.modal,.mcard{animation:none}}
.cbtn{font-weight:550;color:var(--fg);border:1px solid var(--bd2);background:color-mix(in srgb,var(--fg) 10%,transparent);box-shadow:none}
.cbtn:hover{background:color-mix(in srgb,var(--fg) 16%,transparent)}
.sheet{overflow:hidden;margin:.8rem 0;padding:0}
.srow{display:grid;grid-template-columns:minmax(150px,1.3fr) minmax(160px,1.5fr) 150px;gap:1rem;padding:.5rem 1.1rem;align-items:center;font-size:14px;border-bottom:1px solid var(--bd)}
.shead{position:sticky;top:0;font-size:11.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);font-weight:650;background:var(--glass2)}
.sgroup{cursor:pointer;border-bottom:1px solid var(--bd)}.sgroup:nth-child(even){background:color-mix(in srgb,var(--fg) 3.5%,transparent)}.sgroup:hover{background:color-mix(in srgb,var(--brand) 9%,transparent)}
.sgroup .srow{border-bottom:0;padding-top:.32rem;padding-bottom:.32rem}.sgroup .srow:first-child{padding-top:.55rem}.sgroup .srow:last-child{padding-bottom:.55rem}
.sname{font-weight:650;letter-spacing:-.01em}.sgroup .none{color:var(--mut)}
@media(max-width:640px){.srow{grid-template-columns:1fr 1fr;gap:.3rem .8rem}.srow>:nth-child(3){grid-column:1/-1}.shead>:nth-child(3){display:none}}
.toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:110;width:min(460px,calc(100% - 24px));padding:1rem 1.2rem;animation:mpop .35s cubic-bezier(.2,.9,.3,1.2);border-color:rgba(60,190,110,.5)}
.toast b{display:block;font-size:15px;margin-bottom:.2rem}.toast p{margin:0 0 .8rem;color:var(--mut);font-size:13.5px}.toast .tb{display:flex;gap:.5rem;flex-wrap:wrap}
.sortwrap{position:relative;flex:1 1 140px;min-width:140px}.sortbtn{font-size:13px;width:100%;justify-content:center}.filters{margin-right:calc(-.7rem + .3rem)}.sortwrap.chartmode{flex:0 0 auto;min-width:0;margin-left:auto}.sortwrap.chartmode .sortbtn{width:auto}.sortbtn.act{border-color:#e8b93a;box-shadow:0 0 0 1px #e8b93a55}
.sortmenu{right:0;left:auto;top:calc(100% + 8px);width:min(660px,92vw);display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:.4rem .9rem;padding:.9rem 1rem .6rem}
.fsec h6{margin:0 0 .3rem;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);font-weight:650}
.fclr{grid-column:1/-1}.sortwrap.chartmode .sortsec{display:none}.sortmenu .raropt{padding:.35rem .4rem}.sortmenu .rarclr{margin-top:.4rem}
.rarn{background:#e8b93a;color:#2a1c00;border-radius:99px;font-size:11px;font-weight:750;padding:0 .4rem;line-height:1.5}
.rarmenu,.sortmenu{position:absolute;top:calc(100% + 8px);min-width:230px;padding:.4rem;z-index:80;background:color-mix(in srgb,var(--bg) 94%,var(--fg))!important;animation:mpop .2s ease}
.raropt{display:flex;align-items:center;gap:.6rem;padding:.45rem .6rem;border-radius:10px;cursor:pointer;font-size:13.5px;font-weight:550}.raropt:hover{background:color-mix(in srgb,var(--fg) 8%,transparent)}
.raropt input{accent-color:var(--brand);width:15px;height:15px;margin:0}
.raropt i{width:14px;height:14px;border-radius:50%;flex:none;border:1px solid color-mix(in srgb,var(--fg) 35%,transparent)}
.raropt b{margin-left:auto;color:var(--mut);font-weight:550;font-size:12px}
.rarclr{display:block;width:100%;text-align:center;margin-top:.2rem;padding:.4rem;font-size:12px;color:var(--mut);background:none;border:0;border-top:1px solid var(--bd);border-radius:0}
.extrasbtn{display:inline-flex;align-items:center;gap:.45rem;padding:.3rem .62rem;border-radius:99px;font-size:12.5px;font-weight:550;color:#fff;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.6);box-shadow:none;transition:.18s}
.extrasbtn:hover,.extrasbtn.open{border-color:#fff;background:rgba(255,255,255,.12)}.extrasbtn .car{display:inline-block;transition:transform .2s;font-size:10px}
:root[data-theme=light] .extrasbtn{color:#111;background:rgba(0,0,0,.04);border-color:rgba(0,0,0,.55)}
:root[data-theme=light] .extrasbtn:hover,:root[data-theme=light] .extrasbtn.open{border-color:#000;background:rgba(0,0,0,.09)}
.filters.chartmode .chip{display:none}
.extrabar{flex:1 1 100%;display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;padding:.55rem .7rem;border:1px solid var(--bd);border-radius:14px;background:var(--glass2);animation:mpop .2s ease}
.graphbtn{--c:#ee77b8;display:inline-flex;align-items:center;padding:.3rem .8rem;border-radius:99px;font-size:12.5px;font-weight:650;color:var(--c);border:1px solid color-mix(in srgb,var(--c) 58%,transparent);background:color-mix(in srgb,var(--c) 13%,transparent);box-shadow:none}
:root[data-theme=light] .graphbtn{--c:#b8327d}
.graphbtn:hover{border-color:var(--c);background:color-mix(in srgb,var(--c) 20%,transparent);filter:none}.graphbtn.on{color:var(--fg);border-color:var(--c);background:color-mix(in srgb,var(--c) 26%,transparent)}
.chartbox{padding:1.3rem 1.4rem;margin:.9rem 0}.charthead{display:flex;gap:1rem;align-items:center;flex-wrap:wrap;justify-content:space-between}
.chartsel{font-size:1.05rem;font-weight:650;padding:.55rem 1rem;border-radius:12px;min-width:min(380px,100%)}.chartsub{color:var(--mut);margin:.8rem 0 .4rem}
.chart{width:100%;height:auto;display:block}.chart .grid{stroke:var(--bd);stroke-width:1}.chart .tick,.chart .xl,.chart .xs,.chart .axl{fill:var(--mut);font-size:12.5px}.chart .xl{fill:var(--fg);font-size:13px;font-weight:550}.chart .axl{font-size:12px;letter-spacing:.04em}
.chart .tot{fill:var(--fg);font-size:12.5px;font-weight:650}.chart .seg{stroke:rgba(0,0,0,.28);stroke-width:.6}.chart .seg:hover,.chart .dot:hover{filter:brightness(1.18)}
.ctip{position:fixed;z-index:200;pointer-events:none;padding:.4rem .7rem;border-radius:10px;font-size:12.5px;line-height:1.35;background:color-mix(in srgb,var(--bg) 92%,var(--fg));border:1px solid var(--bd2);box-shadow:0 8px 24px rgba(0,0,0,.35);max-width:260px}.ctip b{display:block;font-size:13.5px}
.chart .seg.rr{stroke:color-mix(in srgb,var(--fg) 38%,transparent);stroke-width:1}
.chart .dot{cursor:pointer;transition:r .12s}.chart .dot:hover{r:9;stroke:var(--fg)}
.chart .dot{stroke:rgba(0,0,0,.4);stroke-width:1;opacity:.92}.chart .avg{stroke:var(--fg);stroke-width:2;stroke-dasharray:5 4}.chart .cell:hover{stroke:var(--fg);stroke-width:1.5}
.legend{display:flex;gap:.4rem 1.1rem;flex-wrap:wrap;margin:.4rem 0 0;font-size:13px;color:var(--mut)}.legend span{display:inline-flex;align-items:center;gap:.4rem}.legend i{width:12px;height:12px;border-radius:4px;display:inline-block;border:1px solid var(--bd2)}
.chartnote{color:var(--mut);font-size:13px;margin:.8rem 0 0}
#dropveil{position:fixed;inset:0;z-index:99;display:grid;place-items:center;font-size:1.5rem;font-weight:650;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(10px);border:3px dashed var(--brand);margin:12px;border-radius:24px}
#dropveil[hidden],[hidden]{display:none!important}
</style>
<body>
<div id=modal class=modal hidden role=dialog aria-modal=true aria-labelledby=mtitle><div class="glass mcard" id=mcard>
  <div class=mico><img id=mlogo alt=""></div><h3 id=mtitle>Add MSECheck to your Desktop?</h3>
  <p id=mtext>Get one-click access. A shortcut will appear on your Desktop so you can open MSECheck like any other app.</p>
  <div class=mbtns><button class="btn pri" id=madd type=button>Add shortcut</button><button class="btn ghost" id=mnot type=button>Not now</button></div>
  <button class=mlink id=mnever type=button>Don’t ask again</button></div></div>
<div id=toast class="glass toast" hidden role=status></div>
<div id=dropveil hidden>Drop your .mse-set file to check it</div>
<header class=top><div class=topin id=topin>
  <a class=brand href="#" id=home><img alt="" id=brandlogo><span>MSECheck</span><small id=ver class=pill>v5.2</small></a>
  <div id=filters class=filters hidden>
    <label class="chip e"><input type=checkbox data-sev="Likely error" checked><i></i>Errors <b id=cE>0</b></label>
    <label class="chip r"><input type=checkbox data-sev="Needs review" checked><i></i>Review <b id=cR>0</b></label>
    <label class="chip s"><input type=checkbox data-sev="Suggestion" checked><i></i>Suggestions <b id=cS>0</b></label>
    <label class="chip o"><input type=checkbox id=onlyissues checked title="Only show cards that have findings"><i></i>With findings</label>
    <label class="chip g" title="Show the closest-real-card panels and the Scryfall reference notes"><input type=checkbox id=noscry><i></i>Include Scryfall comparisons</label>
    <button id=extras class=extrasbtn type=button aria-expanded=false aria-controls=extrabar title="More tools">Extras <span class=car>▾</span></button>
  </div>
  <div id=sortwrap class=sortwrap hidden><button id=sortbtn class=sortbtn type=button aria-haspopup=true aria-expanded=false title="Sort the cards and filter them by rarity, colour and type">⇅ Sort &amp; filter <span id=sortn class=rarn hidden></span> ▾</button><div id=sortmenu class="glass sortmenu" hidden></div></div>
  <div class=tools>
    <input type=search id=q placeholder="Search cards for Magic cards… e.g. o:creature  t:elf  c:r  mv&lt;=2" hidden aria-label="Search cards for Magic cards" title="Scryfall-style search over the cards in your set.&#10;name  o:text  t:type  c:rg  m:{R}  mv>=3  pow>=3  tou  loy  r:rare  kw:flying  ft:flavor  a:artist  is:creature  has:findings&#10;sev:error  cat:credits  (red/blue/…)  -term  a or b  ( )  &quot;quoted phrase&quot;  /regex/  !&quot;exact name&quot;  ~ = card name">
    <button id=collapse class=cbtn type=button hidden title="Condense the results into a quick-look table">▤ Collapse all</button>
    <button id=theme class=switch role=switch aria-checked=false aria-label="Light mode" title="Light / dark mode">
      <svg class=sun viewBox="0 0 24 24"><circle cx=12 cy=12 r=4></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path></svg>
      <svg class=moon viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path></svg><i class=knob></i></button>
  </div>
  <div id=extrabar class=extrabar hidden>
    <button id=graphs class=graphbtn type=button title="Show graphs about your set instead of the cards">Graphs</button>
  </div>
</div></header>
<main>
<section id=hero>
  <div class=heroin>
    <div>
      <span class=eyebrow><i></i>The templating checker for Magic Set Editor</span>
      <h1>Find the mistakes in <em>your custom set.</em></h1>
      <p class=lead>Drop in a .mse-set file and MSECheck reviews every card for typos, rules-text templating, reminder text and design risks, with a Scryfall search for each card.</p>
      <div class=cta>
        <label class="btn pri lg" for=file>Choose a file</label><input type=file id=file accept=".mse-set,.zip,.txt" hidden>
        <button class="btn ghost lg" id=showpaste type=button>Individual card</button>
        <button class="btn ghost lg" id=backres type=button hidden>Back to results</button>
      </div>
      <p class=hint>or drop a <b>.mse-set</b> file anywhere in this window</p>
      <div id=pastebox class="glass paste" hidden>
        <p><input type=text id=cname placeholder="Card name (optional)"></p>
        <p><textarea id=ctext rows=5 placeholder="Paste the rules text here…"></textarea></p>
        <button class=pri id=checktext type=button>Check text</button>
      </div>
      <span id=oraclemsg hidden></span>
    </div>
    <div class=heroart><div class=glow></div>
      <img class=herologo id=herologo alt="MSECheck logo" src="data:image/png;base64,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">
    </div>
  </div>
  <div class="glass stats3">
    <div><h4>Privacy</h4><b>Local</b><span>Runs on your computer. Your file is never changed.</span></div>
    <div><h4>Scryfall data</h4><b id=heroNum>…</b><span id=heroOracle>unique cards for closest-match references</span></div>
    <div><h4>Community</h4><span class=comm>Looking for additional feedback and the potential for people to play your custom cards? Check out the <b>MSEM</b> and <b>Revolution</b> Discord communities and connect with other custom Magic designers!</span></div>
  </div>
  <p class=short><button id=mkshort class=btn type=button hidden>Add a Desktop shortcut</button></p>
</section>
<section id=dash hidden><div id=summary class=glass></div><div id=cards></div><div id=charts hidden></div></section>
</main>
<script>
setInterval(()=>{fetch('/api/ping').catch(()=>{})},4000);fetch('/api/ping').catch(()=>{});
const $=s=>document.querySelector(s);
$('#brandlogo').src=$('#herologo').src;
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const CL={'Likely error':'likely','Needs review':'review','Suggestion':'suggestion'};
const RANK={'Likely error':0,'Needs review':1,'Suggestion':2};
const on={'Likely error':true,'Needs review':true,'Suggestion':true};
let showDone=false,D=null,FM={},sortMode='sev',qtextv='',noScry=true,compact=false,chartMode=false;
/* Scryfall-style search over the cards in the set */
const QCOL={w:'W',white:'W',u:'U',blue:'U',b:'B',black:'B',r:'R',red:'R',g:'G',green:'G'};
const QRAR={c:0,common:0,u:1,uncommon:1,r:2,rare:2,m:3,mythic:3,s:4,special:4};
function qinfo(c){
  if(c._q)return c._q;
  const cost=(c.cost||'').replace(/[{}]/g,''),toks=[];let mv=0,cols=new Set();
  const re=/(\d+)|([WUBRG])\/([WUBRGP]|2)|([WUBRGCXS])/gi;let m;
  while((m=re.exec(cost))){
    if(m[1]){toks.push(m[1]);mv+=+m[1]}
    else if(m[2]){const a=m[2].toUpperCase(),b=m[3].toUpperCase();toks.push(a+'/'+b);cols.add(a);if('WUBRG'.includes(b))cols.add(b);mv+=b==='2'?2:1}
    else{const x=m[4].toUpperCase();toks.push(x);if('WUBRG'.includes(x))cols.add(x);if(x!=='X')mv+=1}}
  const rules=c.rules||'',nm=(c.name||'').toLowerCase(),low=rules.toLowerCase();
  const idc=new Set(cols);(rules.match(/\{([WUBRG])\}/g)||[]).forEach(x=>idc.add(x[1]));
  return c._q={toks,mv,cols,idc,low,tilde:nm?low.split(nm).join('~'):low,nm,type:(c.type||'').toLowerCase(),flavor:(c.flavor||'').toLowerCase(),artist:(c.artist||'').toLowerCase()}}
function qnum(v){const x=parseFloat(v);return isNaN(x)?null:x}
function qcmp(a,op,b){if(a==null||b==null)return false;
  switch(op){case':':case'=':return a===b;case'!=':return a!==b;case'<':return a<b;case'>':return a>b;case'<=':return a<=b;case'>=':return a>=b}return false}
function qtext(get,val,op){
  let rx=null;if(val.length>1&&val[0]==='/'&&val[val.length-1]==='/')rx=new RegExp(val.slice(1,-1),'i');
  const v=val.toLowerCase();
  if(op==='!=')return c=>rx?!rx.test(get(c)):!get(c).includes(v);
  return c=>rx?rx.test(get(c)):get(c).includes(v)}
function qcolors(op,val,getset){
  const v=val.toLowerCase();
  if(v==='c'||v==='colorless')return c=>getset(c).size===0;
  if(v==='m'||v==='multicolor')return c=>getset(c).size>1;
  const want=new Set();for(const ch of (QCOL[v]?[v]:v.split('')))if(QCOL[ch])want.add(QCOL[ch]);else throw new Error('Unknown color “'+val+'”');
  return c=>{const have=getset(c),all=[...want].every(x=>have.has(x)),eq=all&&have.size===want.size,sub=[...have].every(x=>want.has(x));
    switch(op){case':':case'>=':return all;case'=':return eq;case'!=':return !eq;case'>':return all&&have.size>want.size;case'<=':return sub;case'<':return sub&&have.size<want.size}return false}}
function qterm(key,op,val){
  const k=key.toLowerCase();
  switch(k){
  case'name':case'n':return qtext(c=>qinfo(c).nm,val,op);
  case'o':case'oracle':case'text':case'fo':{const t=qtext(c=>qinfo(c).low,val,op),t2=qtext(c=>qinfo(c).tilde,val,op);return val.includes('~')?t2:c=>t(c)||t2(c)}
  case't':case'type':case'type_line':return qtext(c=>qinfo(c).type,val,op);
  case'ft':case'flavor':return qtext(c=>qinfo(c).flavor,val,op);
  case'a':case'artist':case'art':return qtext(c=>qinfo(c).artist,val,op);
  case'kw':case'keyword':{const w=val.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),r=new RegExp('\\b'+w+'\\b');return c=>r.test(qinfo(c).low)}
  case'm':case'mana':{const want=val.replace(/[{}]/g,'').toUpperCase().match(/\d+|[WUBRG]\/[WUBRGP2]|[WUBRGCXS]/g)||[];
    return c=>{const have=qinfo(c).toks.slice();return want.every(t=>{const i=have.indexOf(t);if(i<0)return false;have.splice(i,1);return true})}}
  case'mv':case'cmc':case'manavalue':{const n=qnum(val);if(n==null)throw new Error('“'+key+'” needs a number');return c=>qcmp(qinfo(c).mv,op,n)}
  case'pow':case'power':case'tou':case'toughness':case'loy':case'loyalty':{
    const f=k.startsWith('p')?'power':k.startsWith('t')?'toughness':'loyalty',n=qnum(val);
    if(n==null){const o=({pow:'power',tou:'toughness',loy:'loyalty',power:'power',toughness:'toughness',loyalty:'loyalty'})[val.toLowerCase()];if(!o)throw new Error('“'+key+'” needs a number');return c=>qcmp(qnum(c[f]),op,qnum(c[o]))}
    return c=>qcmp(qnum(c[f]),op,n)}
  case'r':case'rarity':{const v=QRAR[val.toLowerCase()];if(v==null)throw new Error('Unknown rarity “'+val+'”');
    return c=>{const have=QRAR[(c.rarity||'').toLowerCase()];return have==null?false:qcmp(have,op,v)}}
  case'c':case'color':case'colors':return qcolors(op,val,c=>qinfo(c).cols);
  case'id':case'identity':case'ci':return qcolors(op,val,c=>qinfo(c).idc);
  case'is':{const v=val.toLowerCase();
    const m={creature:c=>/creature/.test(qinfo(c).type),artifact:c=>/artifact/.test(qinfo(c).type),enchantment:c=>/enchantment/.test(qinfo(c).type),land:c=>/land/.test(qinfo(c).type),
      planeswalker:c=>/planeswalker/.test(qinfo(c).type),instant:c=>/instant/.test(qinfo(c).type),sorcery:c=>/sorcery/.test(qinfo(c).type),legendary:c=>/legendary/.test(qinfo(c).type),
      permanent:c=>!/instant|sorcery/.test(qinfo(c).type),spell:c=>!/land/.test(qinfo(c).type),multicolor:c=>qinfo(c).cols.size>1,colorless:c=>qinfo(c).cols.size===0,
      vanilla:c=>!(c.rules||'').trim(),flagged:c=>c.findings.length>0,fixable:c=>c.findings.some(f=>f.can_apply),clean:c=>c.has_text&&!c.findings.length}[v];
    if(!m)throw new Error('Unknown “is:” value “'+val+'”');return m}
  case'has':{const v=val.toLowerCase();
    const m={findings:c=>c.findings.length>0,text:c=>!!(c.rules||'').trim(),artist:c=>!!c.artist,flavor:c=>!!c.flavor,pt:c=>!!(c.power||c.toughness)}[v];
    if(!m)throw new Error('Unknown “has:” value “'+val+'”');return m}
  case'sev':case'level':case'severity':{const v=val.toLowerCase(),want=/^err/.test(v)||/^like/.test(v)?'Likely error':/^rev|^need/.test(v)?'Needs review':/^sug/.test(v)?'Suggestion':null;
    if(!want)throw new Error('Use sev:error, sev:review or sev:suggestion');return c=>c.findings.some(f=>f.sev===want)}
  case'cat':case'category':case'issue':return c=>c.findings.some(f=>f.cat.toLowerCase().includes(val.toLowerCase())||f.rule.toLowerCase().includes(val.toLowerCase()));
  }
  throw new Error('Unknown search term “'+key+':”')}
function qtokens(s){const out=[];let i=0;const n=s.length;
  while(i<n){const ch=s[i];
    if(/\s/.test(ch)){i++;continue}
    if(ch==='('){out.push({p:'('});i++;continue}
    if(ch===')'){out.push({p:')'});i++;continue}
    let neg=false;
    if(ch==='-'&&i+1<n&&!/\s/.test(s[i+1])){neg=true;i++;if(s[i]==='('){out.push({p:'(',neg:true});i++;continue}}
    let w='',q=false,re=false;
    while(i<n){const c=s[i];
      if(!q&&!re&&(/\s/.test(c)||c===')'))break;
      if(c==='"'&&!re)q=!q;
      else if(c==='/'&&!q){if(re)re=false;else if(w===''||/[:=<>]$/.test(w))re=true}
      w+=c;i++}
    if(q)throw new Error('Missing closing quote');
    if(!neg&&/^or$/i.test(w))out.push({or:true});else if(/^and$/i.test(w)){}else out.push({w,neg})}
  return out}
function qcompile(src){
  const toks=qtokens(src);let p=0;
  const unq=v=>v.length>1&&v[0]==='"'&&v[v.length-1]==='"'?v.slice(1,-1):v;
  function term(t){let f;const w=t.w;
    if(w[0]==='!'){const v=unq(w.slice(1)).toLowerCase();f=c=>qinfo(c).nm===v}
    else{const m=w.match(/^([A-Za-z_]+)(!=|<=|>=|:|=|<|>)(.*)$/);
      if(m)f=qterm(m[1],m[2],unq(m[3]));
      else{const v=unq(w);f=qtext(c=>qinfo(c).nm,v,':')}}
    return t.neg?c=>!f(c):f}
  function orE(){let a=andE();while(toks[p]&&toks[p].or){p++;const x=a,b=andE();a=c=>x(c)||b(c)}return a}
  function andE(){const fs=[];
    while(p<toks.length&&!toks[p].or&&toks[p].p!==')'){const t=toks[p];
      if(t.p==='('){p++;const e=orE();if(!(toks[p]&&toks[p].p===')'))throw new Error('Missing closing )');p++;fs.push(t.neg?c=>!e(c):e)}
      else{fs.push(term(t));p++}}
    return fs.length?c=>fs.every(f=>f(c)):()=>true}
  const e=orE();if(p<toks.length)throw new Error('Unexpected )');return e}
let qfn=null,qerr='';
function setQuery(v){qtextv=v;qfn=null;qerr='';const q=$('#q');
  if(v.trim()){try{qfn=qcompile(v)}catch(e){qerr=e.message}}
  q.classList.toggle('bad',!!qerr)}


/* theme */
function setTheme(t){document.documentElement.dataset.theme=t;$('#theme').setAttribute('aria-checked',t==='light');try{localStorage.setItem('msecheck-theme',t)}catch(_){}}
$('#theme').setAttribute('aria-checked',document.documentElement.dataset.theme==='light');
$('#theme').onclick=()=>setTheme(document.documentElement.dataset.theme==='light'?'dark':'light');
async function post(path,body,raw){
  try{const r=await fetch(path,{method:'POST',headers:raw?{}:{'Content-Type':'application/json'},body:raw?body:JSON.stringify(body||{})});
  const j=await r.json();if(j.error){alert(j.error);return null}return j}catch(e){alert('Request failed: '+e);return null}}
function setCompact(v){compact=v;pg=0;const b=$('#collapse');b.textContent=v?'▦ Expand all':'▤ Collapse all';b.title=v?'Show the full cards again':'Condense the results into a quick-look table';if(D)draw()}
function setLoaded(v){$('#topin').classList.toggle('loaded',v);document.body.classList.toggle('plain',v)}
function showHero(){window.__lensOff&&window.__lensOff();$('#hero').hidden=false;$('#dash').hidden=true;$('#backres').hidden=!D;['#filters','#q','#sortwrap','#collapse','#extrabar'].forEach(s=>$(s).hidden=true);$('#extras').classList.remove('open');$('#extras').setAttribute('aria-expanded',false);setLoaded(false);window.scrollTo(0,0)}
function showDash(){window.__lensOff&&window.__lensOff();$('#hero').hidden=true;$('#dash').hidden=false;$('#filters').hidden=false;$('#q').hidden=false;$('#sortwrap').hidden=false;$('#collapse').hidden=false;setLoaded(true);if(chartMode)setChart(true)}
function render(d){
  if(!d)return;D=d;FM={};
  d.cards.forEach(c=>c.findings.forEach(f=>FM[f.id]=f));
  const s=d.summary,sv=s.severity;
  $('#ver').textContent='v'+d.version;showDash();
  $('#cE').textContent=sv['Likely error'];$('#cR').textContent=sv['Needs review'];$('#cS').textContent=sv['Suggestion'];
  const t=(cls,n,l)=>`<div class="tile ${cls}"><b>${n}</b><span>${l}</span></div>`;
  $('#summary').innerHTML=`<div class=sumhead><div><div class=eyebrow2>Analysis</div><h2>${esc(d.file)}</h2></div>
  <div class=acts2><button data-act=newcheck>＋ New check</button><button data-act=recheck>↻ Recheck</button><span class=sep></span>
    <button data-act=resetign>Reset ignores</button><button data-act=done id=donebtn></button></div></div>
  <div class=tiles>${t('',s.cards,'cards')}${t('e',sv['Likely error'],'likely errors')}${t('r',sv['Needs review'],'need review')}${t('s',sv['Suggestion'],'suggestions')}
  ${t('',s.with_findings,'cards with findings')}${t('o',s.clean,'checked, no findings')}${t('',s.no_text,'not checked (empty text)')}${t('',s.ignored,'ignored')}</div>
  ${s.game&&s.game!=='magic'?`<div class=warn>This file is for the game “${esc(s.game)}”, not Magic. Results may be meaningless.</div>`:''}
  <details class=dets><summary>Details</summary><div class=dgrid>
    <section><h5>Findings by category</h5><div class=dchips>${s.categories.map(c=>`<span class=dchip>${esc(c[0])} <b>${c[1]}</b></span>`).join('')||'<span class=mut>Nothing flagged.</span>'}</div></section>
    <section><h5>Rules-text fields read</h5><div class=dchips>${s.text_fields.map(x=>`<span class=dchip>${esc(String(x[0]).replace(/_/g,' '))} <b>${x[1]}</b></span>`).join('')||'<span class=mut>None found.</span>'}</div></section>
    <div class=drow><section><h5>Spell check</h5><span class=dval>${esc(s.spellcheck)}</span></section>
    <section><h5>Scryfall card data</h5><span class=dval>${d.oracle_cards?d.oracle_cards.toLocaleString()+' unique cards loaded':(d.oracle_state==='loading'?'Still loading…':'Not loaded')}</span></section></div>
    ${s.custom_keywords.length?`<section><h5>Custom keywords</h5><div class=dchips>${[...new Set(s.custom_keywords)].map(k=>`<span class="dchip kw">${esc(k)}</span>`).join('')}</div></section>`:''}
  </div></details>`;
  updDone();draw();
}
function findingHTML(f){
  let h=`<div class="f ${CL[f.sev]}"><span class=badge>${esc(f.sev)}</span> <b>${esc(f.cat)}</b>
  <div class=lbl>Detected text</div><blockquote>“${f.detected_html}”</blockquote><div class=lbl>Why it was flagged</div><div>${esc(f.why)}</div>`;
  if(f.after_html){h+=`<div class=lbl>Suggested wording (heuristic, not verified)</div>
   <div><small>Before:</small> ${f.before_html}</div><div><small>After:</small> ${f.after_html}</div>`}
  h+=`<div class=acts>`;
  if(f.after)h+=`<button data-act=copy data-id="${f.id}">Copy wording</button>`;
  h+=`<button data-act=ign data-scope=card data-id="${f.id}">Ignore on this card</button>
  <button data-act=ign data-scope=text data-id="${f.id}">Ignore this exact issue everywhere</button>
  <button data-act=ign data-scope=rule data-id="${f.id}">Ignore this type of issue everywhere</button></div>`;
  if(f.ref&&!noScry){const r=f.ref;
    h+=`<div class=lbl>Reference</div><div>${r.name?`Reference card “${esc(r.name)}” — ${esc(r.note)}. <a href="${r.url}" target=_blank rel=noopener>View card on Scryfall</a> · `:`${esc(r.note)}: `}
    <a href="${r.qurl}" target=_blank rel=noopener>Search similar wording on Scryfall</a><br>
    <small>A reference is a comparison, not proof that the custom card is incorrect.</small></div>`}
  return h+'</div>';
}
function closeHTML(cm,title,empty){
  if(!cm||!cm.items||!cm.items.length)return empty||'';
  return `<div class=matches><h4>${esc(title)}</h4>${cm.note?`<p class=mut><small>${esc(cm.note)}</small></p>`:''}${cm.items.map(m=>`<div class=match>${m.img?`<img src="${esc(m.img)}" loading=lazy alt="" onerror="this.remove()">`:''}<b><a href="${esc(m.url)}" target=_blank rel=noopener>${esc(m.name)}</a></b> <span class=mut>${esc(m.mana)} ${esc(m.type)}${m.of?' · '+m.score+'% similar · shares '+m.shared+' of '+m.of+' distinct words':' · closest type line'}</span><pre class=rules>${esc(m.text)||'(no rules text)'}</pre></div>`).join('')}<small>A close match is a wording comparison, not proof of an error or of copying.</small></div>`}
function cardHTML(v){
  const c=v.c,fs=v.fs,n=fs.length;
  const tf=c.text_fields&&c.text_fields.length?`<small>Text read from: ${c.text_fields.map(esc).join(', ')}</small>`:'';
  const dots=[['e','error','errors'],['r','review','review'],['s','suggestion','suggestions']].map((x,i)=>v.cnt[i]?`<span class="dot ${x[0]}">${v.cnt[i]} ${v.cnt[i]>1?x[2]:x[1]}</span>`:'').join('');
  return `<article data-idx="${c.idx}"${c.ign_whole?' class=igncard':''}><header><h3>${esc(c.name||'(unnamed card)')}</h3><span class=mut>${esc(c.cost)} ${esc(c.type)}</span>
  ${c.ignored&&!c.ign_whole?`<small>${c.ignored} ignored</small>`:''}<span class=dots>${dots}</span><button class="ignbtn${c.ign_whole?' on':''}" type=button data-act=igncard data-idx="${c.idx}" data-on="${c.ign_whole?0:1}" aria-label="${c.ign_whole?'Done. Click to check this card again':'Mark this card as done'}" title="${c.ign_whole?'Marked as done. Click to check this card again':'Mark this card as done (hides its issues)'}">✓</button></header>${c.ign_whole?'<p class=mut>This card is marked as done, so none of its issues are shown or counted.</p>':''}
  <pre class=rules>${esc(c.rules)||'(no rules text)'}</pre>${tf}
  ${!c.has_text?`<p class=mut>⚠ NOT CHECKED: this card has no non-empty rules-text field in the MSE data. The checker cannot verify text that is not stored in the file. Non-empty fields found: ${esc(c.filled.join(', ')||'none')}.</p>`:(c.findings.length?'':'<p class=ok>✓ No errors found</p>')}${fs.map(findingHTML).join('')}
  ${noScry?'':`<div class=lazy data-card="${c.idx}" data-title="Closest real cards to this card"><small class=mut>Finding the closest real cards…</small></div>`}
  <div class=acts>${c.scryfall&&!noScry?`🔎 <a href="${c.scryfall}" target=_blank rel=noopener>Search Scryfall for cards with similar key terms</a> <small>(${c.terms.map(esc).join(' · ')})</small>`:''}</div></article>`;
}
const lazyIO=new IntersectionObserver(es=>es.forEach(async e=>{
  if(!e.isIntersecting)return;const el=e.target;lazyIO.unobserve(el);
  try{const r=await (await fetch('/api/close?'+(el.dataset.f?'f='+encodeURIComponent(el.dataset.f):'card='+el.dataset.card))).json();
    el.innerHTML=r.empty?'<p class=mut><small>Found no rules text.</small></p>':closeHTML(r.close,el.dataset.title,el.dataset.f||D.oracle_cards?'':'<p class=mut><small>Scryfall card data isn’t loaded, so the closest real cards can’t be shown.</small></p>')}
  catch(_){el.innerHTML=''}}),{rootMargin:'600px'});
let fromList=false;
let pg=0;const PS=()=>compact?60:20;
function nav(total){const pages=Math.max(1,Math.ceil(total/PS())),a=pg*PS()+1,b=Math.min(total,(pg+1)*PS());
  return `<div class=pager><button data-act=prev ${pg<=0?'disabled':''}>← Previous ${PS()}</button><span class=mut>Cards ${total?a:0}–${b} of ${total} · page ${pg+1} of ${pages}</span><button data-act=next ${pg>=pages-1?'disabled':''}>Next ${PS()} →</button></div>`}
function view(c){const fs=c.findings.filter(f=>on[f.sev]),cnt=[0,0,0];fs.forEach(f=>cnt[RANK[f.sev]]++);
  return{c,fs,cnt,worst:fs.length?Math.min(...fs.map(f=>RANK[f.sev])):(c.has_text?3:4)}}
const CMP={sev:(a,b)=>a.worst-b.worst||b.cnt[0]-a.cnt[0]||b.cnt[1]-a.cnt[1]||b.cnt[2]-a.cnt[2]||a.c.idx-b.c.idx,
  set:(a,b)=>a.c.idx-b.c.idx,name:(a,b)=>(a.c.name||'').localeCompare(b.c.name||'')||a.c.idx-b.c.idx,
  count:(a,b)=>b.fs.length-a.fs.length||a.c.idx-b.c.idx};
function sheetHTML(list){
  const lv={'Likely error':'likely','Needs review':'review','Suggestion':'suggestion'};
  return '<div class="glass sheet"><div class="srow shead"><span>Card</span><span>Error type</span><span>Level</span></div>'+list.map(v=>{
    const c=v.c,nm=`<span class=sname>${esc(c.name||'(unnamed card)')}</span>`;
    if(!v.fs.length)return `<div class=sgroup data-act=openrow data-idx="${c.idx}"><div class=srow>${nm}<span class=none>${c.ign_whole?'✓ Marked as done':c.has_text?'No findings':'Not checked (no rules text)'}</span><span class=none>—</span></div></div>`;
    return `<div class=sgroup data-act=openrow data-idx="${c.idx}">`+v.fs.map((f,i)=>`<div class=srow>${i?'<span></span>':nm}<span>${esc(f.cat)}</span><span class="${lv[f.sev]}"><span class=badge>${esc(f.sev)}</span></span></div>`).join('')+'</div>'}).join('')+'</div>'}
function draw(){if(chartMode){drawCharts();return}
  const only=$('#onlyissues').checked;
  const list=D.cards.map(view).filter(v=>(showDone?v.c.ign_whole:!(only&&!v.fs.length))&&(!qfn||qfn(v.c))&&rfOk(v.c)).sort(CMP[sortMode]),
    pages=Math.max(1,Math.ceil(list.length/PS()));
  if(pg>=pages)pg=pages-1;if(pg<0)pg=0;
  const ebn=qerr?`<div class=warn>Search: ${esc(qerr)}. Showing all cards until it’s fixed.</div>`:'';
  let NV;
  $('#cards').innerHTML=ebn+(list.length?(NV=fromList&&!compact?'<div class=pager><button data-act=backlist>← Back to collapsed list</button></div>':nav(list.length))+(compact?sheetHTML(list.slice(pg*PS(),(pg+1)*PS())):list.slice(pg*PS(),(pg+1)*PS()).map(cardHTML).join(''))+NV
    :`<div class="glass empty"><b>No cards to show</b><span class=mut>${showDone?'No cards are marked as done yet. Use the ✓ button on a card to mark it done.':only?'“With findings” is on, so cards with nothing flagged are hidden. Turn it off to see all '+D.cards.length+' cards.':'No cards match your search.'}</span></div>`);
  document.querySelectorAll('.lazy').forEach(el=>lazyIO.observe(el))}
/* ---------- graphical analysis ---------- */
const CCOL={W:'#efe6c8',U:'#4a90d9',B:'#8b7d99',R:'#e3493b',G:'#4caf6b',M:'#e0b03a',C:'#9aa0a6'};
const CNAME={W:'White',U:'Blue',B:'Black',R:'Red',G:'Green',M:'Multicolour',C:'Colourless'};
const CORDER=['W','U','B','R','G','M','C'];
const ccol=c=>{const s=qinfo(c).cols;return s.size===0?'C':s.size>1?'M':[...s][0]};
const isBasic=c=>/basic/.test(qinfo(c).type)&&/land/.test(qinfo(c).type);
const isLand=c=>/land/.test(qinfo(c).type);
const ptype=c=>{const t=qinfo(c).type;return /land/.test(t)?'Land':/creature/.test(t)?'Creature':/planeswalker/.test(t)?'Planeswalker':/battle/.test(t)?'Battle':/instant/.test(t)?'Instant':/sorcery/.test(t)?'Sorcery':/artifact/.test(t)?'Artifact':/enchantment/.test(t)?'Enchantment':'Other'};
const prarity=c=>{const r=(c.rarity||'').toLowerCase();return /mythic/.test(r)?'Mythic':/uncommon/.test(r)?'Uncommon':/rare/.test(r)?'Rare':/special|bonus/.test(r)?'Special':r&&!/common/.test(r)?'Unknown':'Common'};
const RCOL={Common:'#2b2b2e',Uncommon:'#c4ccd6',Rare:'#e8b93a',Mythic:'#ee6a2c',Special:'#b483d8',Unknown:'#b483d8'},RNAME={Common:'Common',Uncommon:'Uncommon',Rare:'Rare',Mythic:'Mythic rare',Special:'Other',Unknown:'Other'};
const RAROD=['Common','Uncommon','Rare','Mythic','Special','Unknown'];
const noRem=c=>(qinfo(c).low||'').replace(/\([^)]*\)/g,' ');
const SW=900,SH=440,ML=58,MR=20,MT=30,MB=64;
function niceMax(v){if(v<=5)return 5;const p=Math.pow(10,Math.floor(Math.log10(v))),m=v/p;return(m<=1?1:m<=2?2:m<=5?5:10)*p}
function grid(top,fmt){let g='';const ph=SH-MT-MB;for(let i=0;i<=5;i++){const v=top/5*i,y=MT+ph*(1-v/top);g+=`<line class="grid" x1="${ML}" x2="${SW-MR}" y1="${y}" y2="${y}"/><text class="tick" x="${ML-8}" y="${y+4}" text-anchor="end">${fmt?fmt(v):Math.round(v*10)/10}</text>`}return g}
function legendHTML(keys,colors,names){return `<div class="legend">${keys.map(k=>`<span><i style="background:${colors[k]}"></i>${esc(names[k])}</span>`).join('')}</div>`}
function stacked(cats,keys,colors,names,opt){opt=opt||{};
  const tot=cats.map(c=>keys.reduce((a,k)=>a+(c.vals[k]||0),0)),top=niceMax(Math.max(1,...tot)),pw=SW-ML-MR,ph=SH-MT-MB,step=pw/cats.length,bw=Math.min(74,step*.66);
  let g=(opt.defs?'<defs>'+opt.defs+'</defs>':'')+grid(top);
  cats.forEach((c,i)=>{const x=ML+step*i+(step-bw)/2;let acc=0;
    keys.forEach(k=>{const n=c.vals[k]||0;if(!n)return;const h=ph*n/top,y=MT+ph*(1-(acc+n)/top);acc+=n;
      g+=`<rect class="seg${opt.outline?' rr':''}" x="${x}" y="${y}" width="${bw}" height="${h}" rx="3" fill="${c.fill||colors[k]}"${opt.op?` fill-opacity="${opt.op[k]}"`:''}><title>${esc(c.label)} · ${esc(names[k])}: ${n}</title></rect>`});
    g+=`<text class="tot" x="${x+bw/2}" y="${MT+ph*(1-tot[i]/top)-7}" text-anchor="middle">${tot[i]||''}</text><text class="xl" x="${x+bw/2}" y="${SH-MB+22}" text-anchor="middle">${esc(c.label)}</text>`;
    if(c.sub)g+=`<text class="xs" x="${x+bw/2}" y="${SH-MB+39}" text-anchor="middle">${esc(c.sub)}</text>`});
  if(opt.xlabel)g+=`<text class="axl" x="${ML+pw/2}" y="${SH-8}" text-anchor="middle">${esc(opt.xlabel)}</text>`;
  g+=`<text class="axl" transform="translate(14 ${MT+ph/2}) rotate(-90)" text-anchor="middle">Number of cards</text>`;
  return `<svg class="chart" viewBox="0 0 ${SW} ${SH}" role="img">${g}</svg>`+(opt.legend===false?'':legendHTML(keys,colors,names))}
function hbars(items,note){const rh=30,top=12,lw=170,w=SW-lw-70,h=top*2+rh*items.length,mx=Math.max(1,...items.map(i=>i.n));
  let g='';items.forEach((it,i)=>{const y=top+i*rh,bw=Math.max(2,w*it.n/mx);
    g+=`<text class="xl" x="${lw-10}" y="${y+rh/2+4}" text-anchor="end">${esc(it.label)}</text><rect class="seg" x="${lw}" y="${y+4}" width="${bw}" height="${rh-9}" rx="4" fill="${it.color||'var(--brand)'}"><title>${esc(it.label)}: ${it.n} card${it.n==1?'':'s'}</title></rect><text class="tot" x="${lw+bw+8}" y="${y+rh/2+4}">${it.n}</text>`});
  return `<svg class="chart" viewBox="0 0 ${SW} ${h}" role="img">${g}</svg>`+(note||'')}
const avg=a=>a.length?Math.round(a.reduce((x,y)=>x+y,0)/a.length*100)/100:0;
const note=t=>`<p class="chartnote">${t}</p>`;

function chMvCol(cs){const L=cs.filter(c=>!isLand(c)),B=['0','1','2','3','4','5','6','7+'],S=stackSpec(L);
  const cats=B.map(l=>({label:l,vals:{}}));L.forEach(c=>{const m=qinfo(c).mv,i=Math.min(7,Math.floor(m)),k=S.of(c);cats[i].vals[k]=(cats[i].vals[k]||0)+1});
  return stacked(cats,S.keys,S.colors,S.names,Object.assign({xlabel:'Mana value'},S.opt))+note(`${L.length} non-land cards · average mana value ${avg(L.map(c=>qinfo(c).mv))}`)}
function chTypeCol(cs){const T=['Creature','Instant','Sorcery','Artifact','Enchantment','Planeswalker','Battle','Land','Other'],m={};
  const S=stackSpec(cs);cs.forEach(c=>{const t=ptype(c),k=S.of(c);(m[t]=m[t]||{})[k]=((m[t]||{})[k]||0)+1});
  return stacked(T.filter(t=>m[t]).map(t=>({label:t,vals:m[t]})),S.keys,S.colors,S.names,S.opt)+note('Each card counts once, under its main type (an artifact creature counts as a creature).')}
function chMvRar(cs){const L=cs.filter(c=>!isLand(c)),K=['0–1','2','3','4','5','6+'],KC={'0–1':'#f6c5bf','2':'#f09a90','3':'#ea7466','4':'#e3493b','5':'#b8352b','6+':'#7d2019'},KN={};K.forEach(k=>KN[k]=k);
  const OP={'0–1':.38,'2':.5,'3':.62,'4':.74,'5':.87,'6+':1};K.forEach(k=>KC[k]='rgba(150,155,165,'+OP[k]+')');
  const bk=m=>m<=1?'0–1':m>=6?'6+':String(Math.floor(m)),by={};
  L.forEach(c=>{const r=prarity(c);(by[r]=by[r]||[]).push(c)});
  const cats=RAROD.filter(r=>by[r]).map(r=>{const v={};by[r].forEach(c=>{const k=bk(qinfo(c).mv);v[k]=(v[k]||0)+1});return{label:RNAME[r]||r,fill:RCOL[r],sub:'avg MV '+avg(by[r].map(c=>qinfo(c).mv)),vals:v}});
  return stacked(cats,K,KC,KN,{xlabel:'Rarity',op:OP,outline:true})+note('Each column uses its rarity’s colour; darker shades mean higher mana value. Lands are left out.')}
const PAIRS=[['W','U','Azorius'],['U','B','Dimir'],['B','R','Rakdos'],['R','G','Gruul'],['G','W','Selesnya'],['W','B','Orzhov'],['U','R','Izzet'],['B','G','Golgari'],['R','W','Boros'],['G','U','Simic']];
function chPairs(cs){const defs=PAIRS.map(p=>`<linearGradient id="gp-${p[0]}${p[1]}" x1="0" x2="1" y1="0" y2="0"><stop offset="50%" stop-color="${CCOL[p[0]]}"/><stop offset="50%" stop-color="${CCOL[p[1]]}"/></linearGradient>`).join('');
  const two=cs.filter(c=>qinfo(c).cols.size===2),cats=PAIRS.map(p=>({label:p[0]+p[1],sub:p[2],fill:`url(#gp-${p[0]}${p[1]})`,vals:{n:two.filter(c=>{const s=qinfo(c).cols;return s.has(p[0])&&s.has(p[1])}).length}}));
  const three=cs.filter(c=>qinfo(c).cols.size>2).length,mono=cs.filter(c=>qinfo(c).cols.size===1).length;
  return stacked(cats,['n'],{n:'#a2d7f2'},{n:'Cards'},{defs,legend:false,xlabel:'Colour pair'})+note(`Cards that are exactly two colours. Not shown: ${mono} one-colour cards and ${three} cards with three or more colours.`)}
function chSize(cs){const cr=cs.filter(c=>/creature/.test(qinfo(c).type)),N=8,cell={};let odd=0,n=0,mx=0;
  cr.forEach(c=>{const p=parseFloat(c.power),t=parseFloat(c.toughness);if(isNaN(p)||isNaN(t)){odd++;return}const a=Math.min(N-1,Math.max(0,Math.round(p))),b=Math.min(N-1,Math.max(0,Math.round(t))),k=a+','+b;cell[k]=(cell[k]||0)+1;mx=Math.max(mx,cell[k]);n++});
  const cw=64,ch=44,x0=110,y0=40,W=SW,H=y0+ch*N+70;let g='';
  for(let b=0;b<N;b++){g+=`<text class="xl" x="${x0-14}" y="${y0+ch*b+ch/2+4}" text-anchor="end">${b===N-1?N-1+'+':b}</text>`;
    for(let a=0;a<N;a++){const v=cell[a+','+b]||0,o=v?.18+.82*v/mx:.05;
      g+=`<rect class="cell" x="${x0+cw*a+2}" y="${y0+ch*b+2}" width="${cw-4}" height="${ch-4}" rx="6" fill="${(accent()||{col:'#a2d7f2'}).col}" fill-opacity="${o}"><title>${a===N-1?N-1+'+':a} power / ${b===N-1?N-1+'+':b} toughness: ${v}</title></rect>`+(v?`<text class="tot" x="${x0+cw*a+cw/2}" y="${y0+ch*b+ch/2+4}" text-anchor="middle">${v}</text>`:'')}}
  for(let a=0;a<N;a++)g+=`<text class="xl" x="${x0+cw*a+cw/2}" y="${y0-12}" text-anchor="middle">${a===N-1?N-1+'+':a}</text>`;
  g+=`<text class="axl" x="${x0+cw*N/2}" y="${H-24}" text-anchor="middle">Power →</text><text class="axl" transform="translate(24 ${y0+ch*N/2}) rotate(-90)" text-anchor="middle">Toughness ↓</text>`;
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img">${g}</svg>`+note(`${n} creatures with numbers for both power and toughness${odd?` · ${odd} more have * or no stats and aren’t shown`:''}. Darker squares mean more creatures.`)}
const MECH=['flying','first strike','double strike','deathtouch','haste','hexproof','indestructible','lifelink','menace','reach','trample','vigilance','defender','flash','ward','prowess','cycling','kicker','equip','scry','surveil','mill','landfall','convoke','delve','flashback','morph','megamorph','embalm','eternalize','escape','evolve','exploit','fabricate','fear','intimidate','infect','undying','persist','proliferate','populate','explore','investigate','amass','afflict','annihilator','bestow','cascade','changeling','crew','dash','disturb','enrage','fight','foretell','hideaway','madness','mentor','mutate','ninjutsu','offspring','overload','partner','plot','protection','rebound','renown','riot','saddle','shroud','skulk','spectacle','storm','suspend','toxic','training','transform','unearth','unleash','vanishing','wither','blitz','casualty','connive','craft','daybound','nightbound','disguise','squad','backup','bargain','treasure','food','clue','blood','incubate','adapt','learn','support','manifest','goad','venture','discover','cloak','impending','gift','valiant','menace'];
const rgba=(h,o)=>{h=h.replace('#','');return `rgba(${parseInt(h.slice(0,2),16)},${parseInt(h.slice(2,4),16)},${parseInt(h.slice(4,6),16)},${o})`};
const ROP={Common:.4,Uncommon:.58,Rare:.78,Mythic:.95,Special:.7,Unknown:.7};
/* when exactly one colour (or, failing that, one rarity) is filtered, graphs use that colour in different shades */
function accent(){const c=[...FILT.col.set].filter(k=>CCOL[k]);if(c.length===1)return{col:CCOL[c[0]],mode:'col'};
  const r=[...FILT.rar.set].map(k=>k==='Other'?'Special':k);if(r.length===1&&RCOL[r[0]])return{col:RCOL[r[0]],mode:'rar'};return null}
function stackSpec(cs){const a=accent();
  if(a&&a.mode==='col'){const keys=RAROD.filter(r=>cs.some(c=>prarity(c)===r)),colors={},names={};keys.forEach(k=>{colors[k]=rgba(a.col,ROP[k]);names[k]=RNAME[k]||k});
    return{keys,colors,names,of:prarity,opt:{outline:true}}}
  return{keys:CORDER,colors:CCOL,names:CNAME,of:ccol,opt:{}}}
function chMech(cs){const cust=(D.summary.custom_keywords||[]).map(x=>x.toLowerCase()),seen=new Set(),rows=[],S=stackSpec(cs);
  [...cust,...MECH].forEach(k=>{if(seen.has(k))return;seen.add(k);const r=new RegExp('\\b'+k.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\b');
    const hit=cs.filter(c=>r.test(noRem(c))),n=hit.length,vals={};hit.forEach(c=>{const q=S.of(c);vals[q]=(vals[q]||0)+1});
    if(n)rows.push({label:k.replace(/^./,x=>x.toUpperCase()),n,vals,sub:cust.includes(k)?'custom':''})});
  rows.sort((a,b)=>b.n-a.n||a.label.localeCompare(b.label));
  if(!rows.length)return '<div class="empty">No keywords found in the rules text.</div>';
  const top=rows.slice(0,12);
  return stacked(top,S.keys,S.colors,S.names,Object.assign({xlabel:'Keyword or mechanic'},S.opt))+note(`The ${top.length} most-used keywords and mechanics, split by card colour. Reminder text isn’t counted.${cust.length?' Keywords marked “custom” come from your set.':''}`)}
const REM=[['Destroy',/\bdestroy (?:up to \w+ )?(?:another )?target\b/],['Exile',/\bexile (?:up to \w+ )?(?:another )?target (?:\w+ )*?(?:creature|artifact|enchantment|permanent|planeswalker|battle|nonland)/],
  ['Damage',/\bdeals? (?:\d+|x|that much|twice x) damage to (?:any target|target (?:\w+ )*?(?:creature|planeswalker|battle|permanent)|up to)/],['−X/−X',/\bgets? -(?:\d+|x)\/-(?:\d+|x)/],
  ['Edict',/(?:target (?:player|opponent)|each opponent|defending player) sacrifices?/],['Bounce',/\breturn (?:up to \w+ )?target (?:\w+ )*?(?:creature|permanent|nonland permanent)s? to (?:its|their) owner/],
  ['Fight',/\bfights?\b/],['Sweeper',/\b(?:destroy|exile) all\b|damage to each creature|each creature gets -/]];
function chRemoval(cs){const m={},S=stackSpec(cs);let any=0;
  cs.forEach(c=>{const t=noRem(c),tt=t.split(qinfo(c).nm||'\u0000').join('~');let hit=false;REM.forEach(r=>{if(r[1].test(t)||r[1].test(tt)){hit=true;const k=S.of(c);(m[r[0]]=m[r[0]]||{})[k]=((m[r[0]]||{})[k]||0)+1}});if(hit)any++});
  const cats=REM.filter(r=>m[r[0]]).map(r=>({label:r[0],vals:m[r[0]]}));
  if(!cats.length)return '<div class="empty">No removal effects found in the rules text.</div>';
  return stacked(cats,S.keys,S.colors,S.names,Object.assign({xlabel:'Removal type'},S.opt))+note(`${any} card${any==1?'':'s'} with removal. A card that does more than one thing counts under each type. Found by matching common wording, so unusual templating can be missed.`)}
function chComplex(cs){const rar=RAROD.filter(r=>cs.some(c=>prarity(c)===r)),words=c=>noRem(c).trim().split(/\s+/).filter(Boolean).length,mx=Math.max(1,...cs.map(words)),top=niceMax(mx);
  const pw=SW-ML-MR,ph=SH-MT-MB,step=pw/rar.length;let g=grid(top);
  rar.forEach((r,i)=>{const L=cs.filter(c=>prarity(c)===r),cx=ML+step*i+step/2,a=avg(L.map(words)),ya=MT+ph*(1-a/top);
    L.forEach(c=>{const j=(((c.idx*47)%100)/100-.5)*Math.min(110,step*.7),y=MT+ph*(1-words(c)/top);
      g+=`<circle class="dot" cx="${cx+j}" cy="${y}" r="6" fill="${CCOL[ccol(c)]}" data-tip="${esc(c.name)}"></circle>`});
    g+=`<line class="avg" x1="${cx-step*.36}" x2="${cx+step*.36}" y1="${ya}" y2="${ya}"/><text class="tot" x="${cx+step*.36+6}" y="${ya+4}">avg ${a}</text><text class="xl" x="${cx}" y="${SH-MB+22}" text-anchor="middle">${r}</text><text class="xs" x="${cx}" y="${SH-MB+39}" text-anchor="middle">${L.length} cards</text>`});
  g+=`<text class="axl" transform="translate(14 ${MT+ph/2}) rotate(-90)" text-anchor="middle">Words of rules text</text><text class="axl" x="${ML+pw/2}" y="${SH-8}" text-anchor="middle">Rarity</text>`;
  return `<svg class="chart" viewBox="0 0 ${SW} ${SH}" role="img">${g}</svg>`+legendHTML(CORDER,CCOL,CNAME)+note('Each dot is a card; hover a dot to see its name. Complexity is measured as the number of words in the rules text, without reminder text. The line marks each rarity’s average.')}
const CHARTS=[{id:'mvcol',title:'Mana Value Distribution',sub:'How many cards cost each amount of mana.',draw:chMvCol},
  {id:'typecol',title:'Card Type Distribution',sub:'How many cards of each type there are.',draw:chTypeCol},
  {id:'mvrar',title:'Mana Value by Rarity',sub:'Each rarity’s cards grouped by mana value, with the average mana value underneath.',draw:chMvRar},
  {id:'pairs',title:'Colour Pair Distribution',sub:'How many cards belong to each two-colour combination.',draw:chPairs},
  {id:'size',title:'Creature Size Distribution',sub:'Creatures laid out by power and toughness.',draw:chSize},
  {id:'mech',title:'Mechanic Frequency',sub:'The keywords and mechanics your set uses most, split by colour.',draw:chMech},
  {id:'removal',title:'Removal Distribution',sub:'The kinds of removal in your set, split by colour.',draw:chRemoval},
  {id:'complex',title:'Complexity vs. Rarity',sub:'How much rules text cards have at each rarity.',draw:chComplex}];
let chartId='mvcol';
function drawCharts(){
  const cs=D.cards.filter(c=>(!showDone||c.ign_whole)&&(!qfn||qfn(c))&&rfOk(c)&&!isBasic(c)),ch=CHARTS.find(x=>x.id===chartId);
  $('#charts').innerHTML=`<div class="glass chartbox"><div class="charthead"><select id="chartsel" class="chartsel" aria-label="Choose a graph">${CHARTS.map(x=>`<option value="${x.id}"${x.id===chartId?' selected':''}>${esc(x.title)}</option>`).join('')}</select><span class="mut">${cs.length} card${cs.length==1?'':'s'}${showDone?' marked as done':qfn?' matching your search':' in your set'}</span></div><p class="chartsub">${esc(ch.sub)}</p>${cs.length?ch.draw(cs):'<div class="empty">No cards match your search.</div>'}</div>`;
  $('#chartsel').onchange=e=>{chartId=e.target.value;drawCharts()}}
function setChart(on){chartMode=on;$('#cards').hidden=on;$('#charts').hidden=!on;$('#summary').hidden=on;const b=$('#graphs');b.classList.toggle('on',on);b.textContent=on?'Back to cards':'Graphs';
  $('#filters').classList.toggle('chartmode',on);$('#collapse').hidden=on||!D;$('#sortwrap').classList.toggle('chartmode',on)
  if(D){if(on)drawCharts();else draw()}}
async function upload(f){if(!f)return;pg=0;showDone=false;Object.values(FILT).forEach(f=>f.set.clear());if(chartMode)setChart(false);render(await post('/api/upload?name='+encodeURIComponent(f.name),f,true))}
$('#file').onchange=e=>{upload(e.target.files[0]);e.target.value=''};
let dragN=0;
addEventListener('dragenter',e=>{e.preventDefault();dragN++;$('#dropveil').hidden=false});
addEventListener('dragleave',e=>{dragN=Math.max(0,dragN-1);if(!dragN)$('#dropveil').hidden=true});
addEventListener('dragover',e=>e.preventDefault());
addEventListener('drop',e=>{e.preventDefault();dragN=0;$('#dropveil').hidden=true;upload(e.dataTransfer.files[0])});
let orSeen=0;
async function pollOracle(){
  try{const r=await (await fetch('/api/status')).json();
    $('#oraclemsg').textContent=r.state==='ready'?('Loaded '+r.cards.toLocaleString()+' unique cards'):(r.message||'');
    $('#heroNum').textContent=r.state==='ready'?r.cards.toLocaleString():(r.state==='loading'?'…':'None');
    $('#heroOracle').textContent=r.state==='ready'?'unique Oracle cards for closest-match references':(r.state==='loading'?(r.message||'Loading card data…'):'No card data loaded. Closest-card matching is off.');
    if(r.state==='loading'){setTimeout(pollOracle,1500);return}
    if(r.state==='ready'&&r.cards!==orSeen){orSeen=r.cards;if(D)render(await post('/api/recheck'))}
  }catch(_){}}
pollOracle();
$('#showpaste').onclick=()=>{const b=$('#pastebox');b.hidden=!b.hidden;if(!b.hidden)$('#ctext').focus()};
$('#backres').onclick=showDash;$('#home').onclick=e=>{e.preventDefault();showHero()};
$('#checktext').onclick=async()=>{const r=await post('/api/text',{name:$('#cname').value,text:$('#ctext').value});if(r){pg=0;if(chartMode)setChart(false);render(r)}};
document.querySelectorAll('[data-sev]').forEach(cb=>cb.onchange=()=>{on[cb.dataset.sev]=cb.checked;pg=0;draw()});
$('#onlyissues').onchange=()=>{pg=0;draw()};

function toast(title,text,withDl){const t=$('#toast');
  t.innerHTML=`<b>${title}</b><p>${text}</p><div class=tb><button data-act=toastx>Got it</button></div>`;t.hidden=false}
$('#collapse').onclick=()=>{fromList=false;setCompact(!compact)};
$('#graphs').onclick=()=>setChart(!chartMode);


/* chart dot hover label */
(()=>{let tip=null;const hide=()=>{if(tip){tip.remove();tip=null}},place=e=>{if(!tip)return;const w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.min(innerWidth-w-8,e.clientX+14)+'px';tip.style.top=(e.clientY-h-12<4?e.clientY+18:e.clientY-h-12)+'px'};
  document.addEventListener('mouseover',e=>{const d=e.target.closest&&e.target.closest('.chart [data-tip]');if(!d){hide();return}
    hide();tip=document.createElement('div');tip.className='ctip';tip.innerHTML='<b>'+esc(d.dataset.tip)+'</b>';document.body.appendChild(tip);place(e)});
  document.addEventListener('mousemove',place);document.addEventListener('scroll',hide,true)})();

/* ---------- floating set symbols (home page background) ---------- */
(()=>{
  const COUNT=117,COLS=12;let last=-1,SETS=[],CUST=[],lens=false;const els=[];
  if(matchMedia('(prefers-reduced-motion: reduce)').matches||!Element.prototype.animate)return;
  const layer=document.createElement('div');layer.id='floaters';layer.setAttribute('aria-hidden','true');document.body.prepend(layer);
  const rnd=(a,b)=>a+Math.random()*(b-a);
  const MON=['January','February','March','April','May','June','July','August','September','October','November','December'];
  const fmtDate=r=>{const m=/^(\d{4})-(\d\d)-(\d\d)$/.exec(r||'');return m?(m[3]==='01'?'':(+m[3])+', ').replace(/^/,MON[+m[2]-1]+' ')+m[1]:(r||'')};
  const tip=document.createElement('div');tip.id='settip';tip.hidden=true;document.body.appendChild(tip);
  function spawn(el,initial){
    const W=innerWidth,H=innerHeight,s=rnd(46,76);
    /* odd slots: MSEM / Revolution sets (their own gold artwork); even slots: real MTG sets (Scryfall symbols, or the built-in symbol sheet when those aren't installed) */
    const useC=CUST.length&&el._slot%2===1;
    if(useC){let S;do{S=CUST[Math.floor(Math.random()*CUST.length)]}while(S===last&&CUST.length>1);last=S;el._set=S;el.classList.add('c');
      el.style.cssText=';background:url(/cset/'+S.id+'.png) center/contain no-repeat'}
    else if(SETS.length){let S;do{S=SETS[Math.floor(Math.random()*SETS.length)]}while(S===last&&SETS.length>1);last=S;el._set=S;el.classList.remove('c');
      const u='url(/set/'+S.c+'.svg)';el.style.cssText=';-webkit-mask:'+u+' center/contain no-repeat;mask:'+u+' center/contain no-repeat'}
    else{let i;do{i=Math.floor(Math.random()*COUNT)}while(i===last);last=i;el._set=null;el.classList.remove('c');el.style.cssText='';el.style.setProperty('--cx',i%COLS);el.style.setProperty('--cy',Math.floor(i/COLS))}
    el.style.setProperty('--s',s+'px');
    const side=Math.floor(Math.random()*4);let x0,y0,x1,y1;
    if(side===0){x0=-s;y0=rnd(0,H);x1=W+s;y1=rnd(0,H)}else if(side===1){x0=W+s;y0=rnd(0,H);x1=-s;y1=rnd(0,H)}
    else if(side===2){x0=rnd(0,W);y0=-s;x1=rnd(0,W);y1=H+s}else{x0=rnd(0,W);y0=H+s;x1=rnd(0,W);y1=-s}
    const dur=Math.hypot(x1-x0,y1-y0)/rnd(14,34)*1000,r0=rnd(0,360),r1=r0+rnd(-140,140);
    const a=el.animate([{transform:`translate(${x0}px,${y0}px) rotate(${r0}deg)`},{transform:`translate(${x1}px,${y1}px) rotate(${r1}deg)`}],{duration:dur,easing:'linear',fill:'forwards'});
    if(initial)a.currentTime=rnd(0,.95)*dur;
    el._a=a;a.onfinish=()=>spawn(el,false)}
  const n=Math.max(12,Math.min(25,Math.round(innerWidth*innerHeight/52000)));
  const start=()=>{for(let k=0;k<n;k++){const el=document.createElement('div');el.className='fsym';el._slot=k;layer.appendChild(el);els.push(el);spawn(el,true)}};
  /* the magnifier: grab it, drag it anywhere, and whatever set symbol is under the glass shows its name and year */
  const logo=$('#herologo');let held=false,off=[0,0],raf=0;
  const glass=()=>{const r=logo.getBoundingClientRect();return{x:r.left+r.width*.4,y:r.top+r.height*.39,r:r.width*.3}};
  function scan(){
    if(!held){raf=0;return}
    const g=glass();let best=null,bd=1e9;
    els.forEach(e=>{e.classList.remove('hit');if(!e._set)return;const r=e.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,d=Math.hypot(cx-g.x,cy-g.y);
      if(d<g.r+r.width*.2&&d<bd){bd=d;best=e}});
    if(best){best.classList.add('hit');tip.firstChild.textContent=best._set.n;tip.lastChild.textContent=best._set.id?('Designed by '+best._set.d+' \u00b7 Released '+fmtDate(best._set.r)):('Released '+best._set.y);tip.hidden=false;
      tip.style.left=Math.max(8,Math.min(innerWidth-270,g.x+g.r+10))+'px';tip.style.top=Math.max(8,Math.min(innerHeight-70,g.y-20))+'px'}else tip.hidden=true;
    raf=requestAnimationFrame(scan)}
  function setLens(on){lens=on;document.body.classList.toggle('lens',on);tip.hidden=true;
    els.forEach(e=>e.classList.remove('hit'));
    if(!on){held=false;logo.classList.remove('held');logo.style.left=logo.style.top='';}}
  window.__lensOff=()=>{if(lens)setLens(false)};
  tip.innerHTML='<b></b><span></span>';
  logo.addEventListener('pointerdown',e=>{
    if(!(SETS.length||CUST.length)||$('#hero').hidden)return;e.preventDefault();
    const r=logo.getBoundingClientRect(),w=120,h=w*r.height/r.width;
    if(!held){setLens(true);held=true;logo.classList.add('held');off=[w*.4,h*.39];
      logo.style.left=(e.clientX-off[0])+'px';logo.style.top=(e.clientY-off[1])+'px'}
    else off=[e.clientX-r.left,e.clientY-r.top];
    logo.setPointerCapture(e.pointerId);logo._drag=true;if(!raf)raf=requestAnimationFrame(scan)});
  logo.addEventListener('pointermove',e=>{if(!logo._drag)return;logo.style.left=(e.clientX-off[0])+'px';logo.style.top=(e.clientY-off[1])+'px'});
  logo.addEventListener('pointerup',()=>{logo._drag=false});
  logo.addEventListener('dblclick',()=>setLens(false));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&lens)setLens(false)});
  Promise.all([fetch('/sets.json').then(r=>r.json()).catch(()=>[]),fetch('/cset/index.json').then(r=>r.json()).catch(()=>[])]).then(([a,b])=>{SETS=Array.isArray(a)?a:[];CUST=Array.isArray(b)?b:[];start()})
})();
/* ---------- search filters: rarity / colour / type ---------- */
const rkey=c=>{const r=prarity(c);return r==='Special'||r==='Unknown'?'Other':r};
const FILT={
  rar:{label:'Rarity',opts:[['Common','Common',RCOL.Common],['Uncommon','Uncommon',RCOL.Uncommon],['Rare','Rare',RCOL.Rare],['Mythic','Mythic',RCOL.Mythic],['Other','Other',RCOL.Special]],has:(c,k)=>rkey(c)===k},
  col:{label:'Colour',opts:[['W','White','#f4efd2'],['U','Blue','#4a90d9'],['B','Black','#3d3646'],['R','Red','#e3493b'],['G','Green','#3da66a'],['M','Multicolour','#e8b93a'],['C','Colourless','#aeb4bd']],
    has:(c,k)=>{const s=qinfo(c).cols;return k==='M'?s.size>1:k==='C'?s.size===0:(s.size===1&&s.has(k))}},
  typ:{label:'Type',opts:['creature','instant','sorcery','artifact','enchantment','land','planeswalker'].map(t=>[t,t[0].toUpperCase()+t.slice(1),null]),has:(c,k)=>(qinfo(c).type||'').includes(k)}
};
Object.values(FILT).forEach(f=>f.set=new Set());
const rfOk=c=>Object.values(FILT).every(f=>!f.set.size||[...f.set].some(k=>f.has(c,k)));
const SORTS=[['sev','Errors first'],['set','Set order'],['name','Name A–Z'],['count','Most findings']];
function sortPanel(){
  const sec=([id,f])=>{const cnt={};if(D)D.cards.forEach(c=>f.opts.forEach(o=>{if(f.has(c,o[0]))cnt[o[0]]=(cnt[o[0]]||0)+1}));
    return `<div class="fsec" data-f="${id}"><h6>${f.label}</h6>${f.opts.map(o=>`<label class="raropt"><input type="checkbox" data-k="${o[0]}"${f.set.has(o[0])?' checked':''}>${o[2]?`<i style="background:${o[2]}"></i>`:''}${o[1]}<b>${cnt[o[0]]||0}</b></label>`).join('')}</div>`};
  $('#sortmenu').innerHTML=`<div class="fsec sortsec"><h6>Sort by</h6>${SORTS.map(([v,l])=>`<label class="raropt"><input type="radio" name="sortr" value="${v}"${sortMode===v?' checked':''}>${l}</label>`).join('')}</div>`
    +Object.entries(FILT).map(sec).join('')+'<div class="fclr"><button class="rarclr" type="button" data-clr="1">Clear all filters</button></div>';
  const n=Object.values(FILT).reduce((a,f)=>a+f.set.size,0),b=$('#sortn');b.hidden=!n;b.textContent=n;$('#sortbtn').classList.toggle('act',n>0)}
function sortOpen(on){$('#sortmenu').hidden=!on;$('#sortbtn').setAttribute('aria-expanded',on);if(on)sortPanel()}
$('#sortbtn').onclick=e=>{e.stopPropagation();sortOpen($('#sortmenu').hidden)};
$('#sortmenu').addEventListener('click',e=>{e.stopPropagation();if(e.target.dataset.clr){Object.values(FILT).forEach(f=>f.set.clear());pg=0;sortPanel();draw()}});
$('#sortmenu').addEventListener('change',e=>{const t=e.target;
  if(t.name==='sortr'){sortMode=t.value;pg=0;sortPanel();draw();return}
  const sec=t.closest('.fsec[data-f]');if(!sec||!t.dataset.k)return;const f=FILT[sec.dataset.f];t.checked?f.set.add(t.dataset.k):f.set.delete(t.dataset.k);pg=0;sortPanel();draw()});
document.addEventListener('click',()=>sortOpen(false));document.addEventListener('keydown',e=>{if(e.key==='Escape')sortOpen(false)});
$('#extras').onclick=e=>{e.stopPropagation();const bar=$('#extrabar'),on=bar.hidden;bar.hidden=!on;$('#extras').classList.toggle('open',on);$('#extras').setAttribute('aria-expanded',on)};


/* Ctrl + / Ctrl - / Ctrl 0 zoom, like Chrome */
(function(){
  const Z=[.25,.33,.5,.67,.75,.8,.9,1,1.1,1.25,1.5,1.75,2,2.5,3];let z=1;
  try{z=parseFloat(localStorage.getItem('msecheck-zoom'))||1}catch(_){}
  const tip=document.createElement('div');tip.style.cssText='position:fixed;right:16px;bottom:16px;z-index:99999;padding:.35rem .7rem;border-radius:99px;background:rgba(20,20,24,.92);color:#fff;font:600 13px system-ui;border:1px solid rgba(255,255,255,.25);opacity:0;transition:opacity .25s;pointer-events:none';document.body.appendChild(tip);let tt;
  const apply=(show)=>{document.documentElement.style.zoom=z===1?'':z;try{localStorage.setItem('msecheck-zoom',z)}catch(_){}
    if(show){tip.textContent=Math.round(z*100)+'%';tip.style.opacity=1;clearTimeout(tt);tt=setTimeout(()=>tip.style.opacity=0,900)}};
  apply(false);
  const step=d=>{let i=Z.findIndex(v=>v>=z-1e-6);if(i<0)i=Z.length-1;i=Math.max(0,Math.min(Z.length-1,i+d));z=Z[i];apply(true)};
  addEventListener('keydown',e=>{if(!(e.ctrlKey||e.metaKey)||e.altKey)return;
    if(e.key==='+'||e.key==='='||e.code==='NumpadAdd'){e.preventDefault();step(1)}
    else if(e.key==='-'||e.key==='_'||e.code==='NumpadSubtract'){e.preventDefault();step(-1)}
    else if(e.key==='0'||e.code==='Numpad0'){e.preventDefault();z=1;apply(true)}},true);
  addEventListener('wheel',e=>{if(!e.ctrlKey)return;e.preventDefault();step(e.deltaY<0?1:-1)},{passive:false});
})();
$('#noscry').onchange=e=>{noScry=!e.target.checked;draw()};
/* instant ignoring: update the page first, then tell the server (no re-analysis, no full redraw) */
function bg(path,body){fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({fast:true},body))}).catch(()=>{})}
function updDone(){const b=$('#donebtn');if(!b)return;const n=D.cards.filter(c=>c.ign_whole).length;b.classList.toggle('on',showDone);b.textContent=showDone?'Show all cards':'✓ See all completed ('+n+')'}
function recount(){
  const sv={'Likely error':0,'Needs review':0,'Suggestion':0};let clean=0,noT=0,ign=0,tot=0;
  D.cards.forEach(c=>{c.findings.forEach(f=>sv[f.sev]++);ign+=c.ignored||0;tot+=c.findings.length;if(!c.has_text)noT++;else if(!c.findings.length)clean++});
  const s=D.summary;s.severity=sv;s.clean=clean;s.no_text=noT;s.ignored=ign;s.total=tot;s.with_findings=D.cards.length-clean-noT;
  $('#cE').textContent=sv['Likely error'];$('#cR').textContent=sv['Needs review'];$('#cS').textContent=sv['Suggestion'];
  const v=[s.cards,sv['Likely error'],sv['Needs review'],sv['Suggestion'],s.with_findings,clean,noT,ign];
  updDone();document.querySelectorAll('#summary .tile b').forEach((el,i)=>{if(v[i]!==undefined)el.textContent=v[i]})}
function redrawCards(ids){
  ids.forEach(i=>{const el=document.querySelector('article[data-idx="'+i+'"]'),c=D.cards.find(x=>x.idx===i);
    if(!el||!c)return;const t=document.createElement('div');t.innerHTML=cardHTML(view(c));const n=t.firstElementChild;el.replaceWith(n);
    n.querySelectorAll('.lazy').forEach(l=>lazyIO.observe(l))})}
function ignFinding(f,scope){
  if(!f)return;const hit=new Set();
  D.cards.forEach(c=>{
    const gone=x=>scope==='rule'?x.rule===f.rule:x.key===f.key&&(scope==='text'||c.findings.includes(f)||(c._saved||[]).includes(f));
    const n=c.findings.filter(gone).length;
    if(scope==='card'&&!(c.findings.includes(f)||(c._saved||[]).includes(f)))return;
    if(n){c.findings=c.findings.filter(x=>!gone(x));c.ignored=(c.ignored||0)+n;hit.add(c.idx)}
    if(c._saved)c._saved=c._saved.filter(x=>!gone(x))});
  bg('/api/ignore',{id:f.id,scope});recount();if(chartMode)drawCharts();else redrawCards([...hit])}
function igncard(idx,on){
  const c=D.cards.find(x=>String(x.idx)===String(idx));if(!c)return;
  if(on){c._saved=c.findings;c.ignored=(c.ignored||0)+c.findings.length;c.findings=[];c.ign_whole=true}
  else{c.findings=c._saved||[];c.ignored=Math.max(0,(c.ignored||0)-c.findings.length);c._saved=null;c.ign_whole=false}
  bg('/api/ignorecard',{idx:c.idx,on});recount();if(showDone)draw();else redrawCards([c.idx])}
$('#q').oninput=e=>{fromList=false;setQuery(e.target.value);pg=0;draw()};
document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-act]');if(!b)return;const a=b.dataset.act,id=b.dataset.id,f=FM[id];
  if(a==='prev'||a==='next'){pg+=a==='next'?1:-1;draw();window.scrollTo({top:$('#cards').offsetTop-80});return}
  if(a==='toastx'){$('#toast').hidden=true;return}
  if(a==='igncard'){igncard(b.dataset.idx,b.dataset.on==='1');return}
  if(a==='done'){showDone=!showDone;pg=0;updDone();draw();return}
  if(a==='newcheck'){showHero();return}
  if(a==='backlist'){fromList=false;$('#q').value='';setQuery('');setCompact(true);window.scrollTo({top:0});return}
  if(a==='openrow'){const c=D.cards.find(x=>String(x.idx)===b.dataset.idx);if(c){$('#q').value='!"'+(c.name||'')+'"';setQuery($('#q').value);fromList=true;setCompact(false);window.scrollTo({top:$('#cards').offsetTop-$('header.top').offsetHeight-12})}return}
  if(a==='copy'){try{await navigator.clipboard.writeText(f.after);b.textContent='Copied ✓'}catch(_){prompt('Copy this wording:',f.after)}}
  else if(a==='ign')ignFinding(f,b.dataset.scope);
  else if(a==='recheck')render(await post('/api/recheck'));
  else if(a==='export')location.href='/api/export?fmt='+b.dataset.fmt;
  else if(a==='resetign')render(await post('/api/resetign'));
});

/* Desktop shortcut question (Windows app only) */
(async function(){
  let a;try{a=await (await fetch('/api/shortcut')).json()}catch(_){return}
  if(!a.ask&&!a.available)return;
  const m=$('#modal'),card=$('#mcard');$('#mlogo').src=$('#herologo').src;
  const close=()=>{m.hidden=true},open=()=>{m.hidden=false;$('#madd').focus()};
  $('#mkshort').hidden=false;$('#mkshort').onclick=()=>{$('#mtitle').textContent='Add MSECheck to your Desktop?';$('#mtext').textContent='Get one-click access. A shortcut will appear on your Desktop so you can open MSECheck like any other app.';document.querySelector('.mbtns').hidden=false;$('#mnever').hidden=false;card.classList.remove('ok');open()};
  if(a.ask)setTimeout(open,700);
  $('#mnot').onclick=close;
  $('#mnever').onclick=async()=>{close();try{await post('/api/shortcut',{action:'never'})}catch(_){}};
  $('#madd').onclick=async()=>{const b=$('#madd');b.disabled=true;b.textContent='Adding…';
    const r=await post('/api/shortcut',{action:'create'});b.disabled=false;b.textContent='Add shortcut';
    if(r&&r.ok){card.classList.add('ok');$('#mtitle').textContent='Shortcut added ✓';$('#mtext').textContent='Look for MSECheck on your Desktop.';
      document.querySelector('.mbtns').hidden=true;$('#mnever').hidden=true;setTimeout(close,1900)}
    else if(r){$('#mtitle').textContent='Couldn’t add the shortcut';$('#mtext').textContent=r.message||'Windows blocked it.';b.textContent='Try again'}};
})();
</script></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", code=200, name=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if name:
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
        self.end_headers()
        self.wfile.write(body)

    def js(self, obj, code=200):
        self.send(json.dumps(obj).encode("utf-8"), code=code)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/":
            return self.send(PAGE.encode("utf-8"), "text/html; charset=utf-8")
        if u.path == "/symbols.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(_SYMBOLS_PNG)))
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            return self.wfile.write(_SYMBOLS_PNG)
        if u.path == "/api/shortcut":
            return self.js({"ask": shortcut.should_ask(), "available": shortcut.available()})
        if u.path == "/sets.json":
            return self.js(_sets_index())
        if u.path == "/cset/index.json":
            return self.js(_cset_index())
        m = re.fullmatch(r"/cset/([a-z0-9\-]{2,80})\.png", u.path)
        if m:
            fp = os.path.join(_cset_dir(), m.group(1) + ".png")
            if os.path.isfile(fp):
                data = open(fp, "rb").read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                return self.wfile.write(data)
            self.send_error(404)
            return
        m = re.fullmatch(r"/set/([a-z0-9_]{2,8})\.svg", u.path)
        if m:
            d = _sets_dir()
            fp = os.path.join(d, m.group(1) + ".svg") if d else None
            if fp and os.path.isfile(fp):
                data = open(fp, "rb").read()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                return self.wfile.write(data)
            self.send_error(404)
            return
        if u.path == "/api/ping":
            HEARTBEAT["last"] = time.time()
            return self.js({"ok": True})
        if u.path == "/api/status":
            return self.js({"state": ORACLE["state"], "message": ORACLE["message"], "cards": ORACLE["doc_count"]})
        with LOCK:
            try:
                if u.path == "/api/close" and ST["last"]:
                    q = urllib.parse.parse_qs(u.query)
                    if "card" in q:
                        c = ST["last"]["cards"][int(q["card"][0])]
                        if not c["has_text"] or not (c["rules"] or "").strip():
                            return self.js({"close": None, "empty": True})
                        return self.js({"close": find_close_oracle_matches(_strip_name(c["rules"], c["name"]), 2, c["type"], c["name"])})
                    f = ST["findings"][q["f"][0]]
                    c = ST["last"]["cards"][f["card"]]
                    return self.js({"close": close_for_finding(f["detected"], c["rules"], c["name"], c["type"])})
                if u.path == "/api/export" and ST["last"]:
                    if ST.get("dirty"):      # ignores were applied without re-analysing; refresh the report data (finding ids stay as the page has them)
                        keep = ST["findings"]
                        analyze()
                        ST["findings"], ST["dirty"] = keep, False
                    b, t, n = export(urllib.parse.parse_qs(u.query).get("fmt", ["csv"])[0])
                    return self.send(b, t, name=n)
            except Exception as e:
                return self.js({"error": str(e)}, 400)
        self.send(b"Not found", "text/plain", 404)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        with LOCK:
            try:
                if u.path == "/api/upload":
                    name = urllib.parse.parse_qs(u.query).get("name", ["set.mse-set"])[0]
                    load_upload(name, raw)
                    return self.js(analyze())
                if u.path == "/api/oracle":
                    n = load_oracle(raw)
                    return self.js({"oracle": n, "result": analyze() if ST["kind"] else None})
                body = json.loads(raw or b"{}")
                if u.path == "/api/text":
                    if not body.get("text", "").strip():
                        raise ValueError("Paste some rules text first.")
                    load_text(body.get("name", ""), body["text"])
                    return self.js(analyze())
                if u.path == "/api/shortcut":
                    if body.get("action") == "create":
                        ok, msg = shortcut.create()
                        return self.js({"ok": ok, "message": msg})
                    shortcut.never()
                    return self.js({"ok": True})
                if ST["kind"] is None:
                    raise ValueError("Upload a file or paste a card first.")
                if u.path == "/api/recheck":
                    return self.js(analyze())
                if u.path == "/api/ignore":
                    f = ST["findings"][body["id"]]
                    {"card": lambda: ST["ign_card"].add((f["card"], f["key"])), "text": lambda: ST["ign_text"].add(f["key"]),
                     "rule": lambda: ST["ign_rule"].add(f["rule"])}[body["scope"]]()
                    if body.get("fast"):     # the page already updated itself; just remember the choice
                        ST["dirty"] = True
                        return self.js({"ok": True})
                    return self.js(analyze())
                if u.path == "/api/ignorecard":
                    w = ST.setdefault("ign_whole", set())
                    (w.add if body.get("on") else w.discard)(int(body["idx"]))
                    if body.get("fast"):
                        ST["dirty"] = True
                        return self.js({"ok": True})
                    return self.js(analyze())
                if u.path == "/api/resetign":
                    ST["ign_card"], ST["ign_text"], ST["ign_rule"], ST["ign_whole"] = set(), set(), set(), set()
                    return self.js(analyze())
                self.js({"error": "Unknown endpoint"}, 404)
            except Exception as e:
                self.js({"error": str(e)}, 400)
