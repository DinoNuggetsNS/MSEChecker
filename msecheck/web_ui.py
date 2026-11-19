"""MSECheck - web ui."""
import json, time, urllib.parse
from http.server import BaseHTTPRequestHandler
from .state import HEARTBEAT, LOCK, ST
from .scryfall_data import ORACLE, _strip_name, close_for_finding, find_close_oracle_matches, load_oracle
from .analysis import analyze, load_text, load_upload
from .reports import export
from . import shortcut, symbols_data
import base64
_SYMBOLS_PNG = base64.b64decode("".join(symbols_data.PNG_B64))


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
.ignbtn{margin-left:auto;font-size:12px;padding:.2rem .65rem}.igncard{opacity:.6}.igncard .rules{display:none}
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
mark{background:var(--mark);color:inherit;border-radius:4px;padding:0 2px}del{background:var(--del);text-decoration:none;border-radius:4px;padding:0 2px}ins{background:var(--ins);text-decoration:none;border-radius:4px;padding:0 2px}
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
.extrasbtn{display:inline-flex;align-items:center;gap:.45rem;padding:.3rem .62rem;border-radius:99px;font-size:12.5px;font-weight:550;color:var(--mut);background:var(--glass2);border:1px solid var(--bd);box-shadow:none;transition:.18s}
.extrasbtn:hover{border-color:var(--bd2);background:var(--glass2)}.extrasbtn .car{display:inline-block;transition:transform .2s;font-size:10px}
.extrasbtn.open{color:#fff;border-color:rgba(255,255,255,.75);background:rgba(255,255,255,.12);box-shadow:0 0 0 1px rgba(255,255,255,.3),0 0 16px rgba(255,255,255,.42),inset 0 0 12px rgba(255,255,255,.12)}.extrasbtn.open .car{transform:rotate(180deg)}
:root[data-theme=light] .extrasbtn.open{color:#111;border-color:#111;background:rgba(0,0,0,.06);box-shadow:0 0 0 1px rgba(0,0,0,.3),0 0 14px rgba(0,0,0,.28),inset 0 0 10px rgba(0,0,0,.06)}
.filters.chartmode .chip{display:none}
.extrabar{flex:1 1 100%;display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;padding:.55rem .7rem;border:1px solid var(--bd);border-radius:14px;background:var(--glass2);animation:mpop .2s ease}
.graphbtn{border-color:transparent;color:#fff;font-weight:650;background:linear-gradient(135deg,#3b6fd4,#7c4fd0);box-shadow:0 4px 16px rgba(92,80,208,.35)}
.graphbtn:hover{filter:brightness(1.08);background:linear-gradient(135deg,#3b6fd4,#7c4fd0);border-color:transparent}.graphbtn.on{background:var(--glass);color:var(--fg);border-color:var(--bd2);box-shadow:none}
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
    <label class="chip g" title="Hide the closest-real-card panels and the Scryfall reference notes"><input type=checkbox id=noscry><i></i>Remove Scryfall comparisons</label>
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
  <p class=short><button id=mkshort class=mlink type=button hidden>Add a Desktop shortcut</button></p>
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
let D=null,FM={},sortMode='sev',qtextv='',noScry=false,compact=false,chartMode=false;
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
function showHero(){$('#hero').hidden=false;$('#dash').hidden=true;$('#backres').hidden=!D;['#filters','#q','#sortwrap','#collapse','#extrabar'].forEach(s=>$(s).hidden=true);$('#extras').classList.remove('open');$('#extras').setAttribute('aria-expanded',false);setLoaded(false);window.scrollTo(0,0)}
function showDash(){$('#hero').hidden=true;$('#dash').hidden=false;$('#filters').hidden=false;$('#q').hidden=false;$('#sortwrap').hidden=false;$('#collapse').hidden=false;setLoaded(true);if(chartMode)setChart(true)}
function render(d){
  if(!d)return;D=d;FM={};
  d.cards.forEach(c=>c.findings.forEach(f=>FM[f.id]=f));
  const s=d.summary,sv=s.severity;
  $('#ver').textContent='v'+d.version;showDash();
  $('#cE').textContent=sv['Likely error'];$('#cR').textContent=sv['Needs review'];$('#cS').textContent=sv['Suggestion'];
  const t=(cls,n,l)=>`<div class="tile ${cls}"><b>${n}</b><span>${l}</span></div>`;
  $('#summary').innerHTML=`<div class=sumhead><div><div class=eyebrow2>Analysis</div><h2>${esc(d.file)}</h2></div>
  <div class=acts2><button data-act=newcheck>＋ New check</button><button data-act=recheck>↻ Recheck</button><span class=sep></span>
    <button data-act=resetign>Reset ignores</button></div></div>
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
  draw();
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
  return `<article${c.ign_whole?' class=igncard':''}><header><h3>${esc(c.name||'(unnamed card)')}</h3><span class=mut>${esc(c.cost)} ${esc(c.type)}</span>
  ${c.ignored&&!c.ign_whole?`<small>${c.ignored} ignored</small>`:''}<span class=dots>${dots}</span><button class=ignbtn type=button data-act=igncard data-idx="${c.idx}" data-on="${c.ign_whole?0:1}" title="${c.ign_whole?'Check this card again':'Skip every check for this card, for example a reminder token'}">${c.ign_whole?'Stop ignoring':'Ignore this card'}</button></header>${c.ign_whole?'<p class=mut>This card is being ignored, so none of its issues are shown or counted.</p>':''}
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
    if(!v.fs.length)return `<div class=sgroup data-act=openrow data-idx="${c.idx}"><div class=srow>${nm}<span class=none>${c.has_text?'No findings':'Not checked (no rules text)'}</span><span class=none>—</span></div></div>`;
    return `<div class=sgroup data-act=openrow data-idx="${c.idx}">`+v.fs.map((f,i)=>`<div class=srow>${i?'<span></span>':nm}<span>${esc(f.cat)}</span><span class="${lv[f.sev]}"><span class=badge>${esc(f.sev)}</span></span></div>`).join('')+'</div>'}).join('')+'</div>'}
function draw(){if(chartMode){drawCharts();return}
  const only=$('#onlyissues').checked;
  const list=D.cards.map(view).filter(v=>!(only&&!v.fs.length)&&(!qfn||qfn(v.c))&&rfOk(v.c)).sort(CMP[sortMode]),
    pages=Math.max(1,Math.ceil(list.length/PS()));
  if(pg>=pages)pg=pages-1;if(pg<0)pg=0;
  const ebn=qerr?`<div class=warn>Search: ${esc(qerr)}. Showing all cards until it’s fixed.</div>`:'';
  let NV;
  $('#cards').innerHTML=ebn+(list.length?(NV=fromList&&!compact?'<div class=pager><button data-act=backlist>← Back to collapsed list</button></div>':nav(list.length))+(compact?sheetHTML(list.slice(pg*PS(),(pg+1)*PS())):list.slice(pg*PS(),(pg+1)*PS()).map(cardHTML).join(''))+NV
    :`<div class="glass empty"><b>No cards to show</b><span class=mut>${only?'“With findings” is on, so cards with nothing flagged are hidden. Turn it off to see all '+D.cards.length+' cards.':'No cards match your search.'}</span></div>`);
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

function chMvCol(cs){const L=cs.filter(c=>!isLand(c)),B=['0','1','2','3','4','5','6','7+'];
  const cats=B.map(l=>({label:l,vals:{}}));L.forEach(c=>{const m=qinfo(c).mv,i=Math.min(7,Math.floor(m)),k=ccol(c);cats[i].vals[k]=(cats[i].vals[k]||0)+1});
  return stacked(cats,CORDER,CCOL,CNAME,{xlabel:'Mana value'})+note(`${L.length} non-land cards · average mana value ${avg(L.map(c=>qinfo(c).mv))}`)}
function chTypeCol(cs){const T=['Creature','Instant','Sorcery','Artifact','Enchantment','Planeswalker','Battle','Land','Other'],m={};
  cs.forEach(c=>{const t=ptype(c),k=ccol(c);(m[t]=m[t]||{})[k]=((m[t]||{})[k]||0)+1});
  return stacked(T.filter(t=>m[t]).map(t=>({label:t,vals:m[t]})),CORDER,CCOL,CNAME)+note('Each card counts once, under its main type (an artifact creature counts as a creature).')}
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
      g+=`<rect class="cell" x="${x0+cw*a+2}" y="${y0+ch*b+2}" width="${cw-4}" height="${ch-4}" rx="6" fill="#a2d7f2" fill-opacity="${o}"><title>${a===N-1?N-1+'+':a} power / ${b===N-1?N-1+'+':b} toughness: ${v}</title></rect>`+(v?`<text class="tot" x="${x0+cw*a+cw/2}" y="${y0+ch*b+ch/2+4}" text-anchor="middle">${v}</text>`:'')}}
  for(let a=0;a<N;a++)g+=`<text class="xl" x="${x0+cw*a+cw/2}" y="${y0-12}" text-anchor="middle">${a===N-1?N-1+'+':a}</text>`;
  g+=`<text class="axl" x="${x0+cw*N/2}" y="${H-24}" text-anchor="middle">Power →</text><text class="axl" transform="translate(24 ${y0+ch*N/2}) rotate(-90)" text-anchor="middle">Toughness ↓</text>`;
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img">${g}</svg>`+note(`${n} creatures with numbers for both power and toughness${odd?` · ${odd} more have * or no stats and aren’t shown`:''}. Darker squares mean more creatures.`)}
const MECH=['flying','first strike','double strike','deathtouch','haste','hexproof','indestructible','lifelink','menace','reach','trample','vigilance','defender','flash','ward','prowess','cycling','kicker','equip','scry','surveil','mill','landfall','convoke','delve','flashback','morph','megamorph','embalm','eternalize','escape','evolve','exploit','fabricate','fear','intimidate','infect','undying','persist','proliferate','populate','explore','investigate','amass','afflict','annihilator','bestow','cascade','changeling','crew','dash','disturb','enrage','fight','foretell','hideaway','madness','mentor','mutate','ninjutsu','offspring','overload','partner','plot','protection','rebound','renown','riot','saddle','shroud','skulk','spectacle','storm','suspend','toxic','training','transform','unearth','unleash','vanishing','wither','blitz','casualty','connive','craft','daybound','nightbound','disguise','squad','backup','bargain','treasure','food','clue','blood','incubate','adapt','learn','support','manifest','goad','venture','discover','cloak','impending','gift','valiant','menace'];
function chMech(cs){const cust=(D.summary.custom_keywords||[]).map(x=>x.toLowerCase()),seen=new Set(),rows=[];
  [...cust,...MECH].forEach(k=>{if(seen.has(k))return;seen.add(k);const r=new RegExp('\\b'+k.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\b');const n=cs.filter(c=>r.test(noRem(c))).length;if(n)rows.push({label:k.replace(/^./,x=>x.toUpperCase()),n,color:cust.includes(k)?'#4a90d9':null})});
  rows.sort((a,b)=>b.n-a.n||a.label.localeCompare(b.label));
  if(!rows.length)return '<div class="empty">No keywords found in the rules text.</div>';
  return hbars(rows.slice(0,18),note(`Number of cards using each keyword or mechanic (top ${Math.min(18,rows.length)}). Reminder text isn’t counted.${cust.length?' <span class="legend"><span><i style="background:#4a90d9"></i>Custom keyword from your set</span></span>':''}`))}
const REM=[['Destroy',/\bdestroy (?:up to \w+ )?(?:another )?target\b/],['Exile',/\bexile (?:up to \w+ )?(?:another )?target (?:\w+ )*?(?:creature|artifact|enchantment|permanent|planeswalker|battle|nonland)/],
  ['Damage',/\bdeals? (?:\d+|x|that much|twice x) damage to (?:any target|target (?:\w+ )*?(?:creature|planeswalker|battle|permanent)|up to)/],['−X/−X',/\bgets? -(?:\d+|x)\/-(?:\d+|x)/],
  ['Edict',/(?:target (?:player|opponent)|each opponent|defending player) sacrifices?/],['Bounce',/\breturn (?:up to \w+ )?target (?:\w+ )*?(?:creature|permanent|nonland permanent)s? to (?:its|their) owner/],
  ['Fight',/\bfights?\b/],['Sweeper',/\b(?:destroy|exile) all\b|damage to each creature|each creature gets -/]];
function chRemoval(cs){const m={};let any=0;
  cs.forEach(c=>{const t=noRem(c),tt=t.split(qinfo(c).nm||'\u0000').join('~');let hit=false;REM.forEach(r=>{if(r[1].test(t)||r[1].test(tt)){hit=true;const k=ccol(c);(m[r[0]]=m[r[0]]||{})[k]=((m[r[0]]||{})[k]||0)+1}});if(hit)any++});
  const cats=REM.filter(r=>m[r[0]]).map(r=>({label:r[0],vals:m[r[0]]}));
  if(!cats.length)return '<div class="empty">No removal effects found in the rules text.</div>';
  return stacked(cats,CORDER,CCOL,CNAME,{xlabel:'Removal type'})+note(`${any} card${any==1?'':'s'} with removal. A card that does more than one thing counts under each type. Found by matching common wording, so unusual templating can be missed.`)}
function chComplex(cs){const rar=RAROD.filter(r=>cs.some(c=>prarity(c)===r)),words=c=>noRem(c).trim().split(/\s+/).filter(Boolean).length,mx=Math.max(1,...cs.map(words)),top=niceMax(mx);
  const pw=SW-ML-MR,ph=SH-MT-MB,step=pw/rar.length;let g=grid(top);
  rar.forEach((r,i)=>{const L=cs.filter(c=>prarity(c)===r),cx=ML+step*i+step/2,a=avg(L.map(words)),ya=MT+ph*(1-a/top);
    L.forEach(c=>{const j=(((c.idx*47)%100)/100-.5)*Math.min(110,step*.7),y=MT+ph*(1-words(c)/top);
      g+=`<circle class="dot" cx="${cx+j}" cy="${y}" r="6" fill="${CCOL[ccol(c)]}" data-tip="${esc(c.name)}"></circle>`});
    g+=`<line class="avg" x1="${cx-step*.36}" x2="${cx+step*.36}" y1="${ya}" y2="${ya}"/><text class="tot" x="${cx+step*.36+6}" y="${ya+4}">avg ${a}</text><text class="xl" x="${cx}" y="${SH-MB+22}" text-anchor="middle">${r}</text><text class="xs" x="${cx}" y="${SH-MB+39}" text-anchor="middle">${L.length} cards</text>`});
  g+=`<text class="axl" transform="translate(14 ${MT+ph/2}) rotate(-90)" text-anchor="middle">Words of rules text</text><text class="axl" x="${ML+pw/2}" y="${SH-8}" text-anchor="middle">Rarity</text>`;
  return `<svg class="chart" viewBox="0 0 ${SW} ${SH}" role="img">${g}</svg>`+legendHTML(CORDER,CCOL,CNAME)+note('Each dot is a card; hover a dot to see its name. Complexity is measured as the number of words in the rules text, without reminder text. The line marks each rarity’s average.')}
const CHARTS=[{id:'mvcol',title:'Mana Value Distribution by Colour',sub:'How many cards cost each amount of mana, split by colour.',draw:chMvCol},
  {id:'typecol',title:'Card Type Distribution by Colour',sub:'How many cards of each type there are, split by colour.',draw:chTypeCol},
  {id:'mvrar',title:'Mana Value by Rarity',sub:'Each rarity’s cards grouped by mana value, with the average mana value underneath.',draw:chMvRar},
  {id:'pairs',title:'Colour Pair Distribution',sub:'How many cards belong to each two-colour combination.',draw:chPairs},
  {id:'size',title:'Creature Size Distribution',sub:'Creatures laid out by power and toughness.',draw:chSize},
  {id:'mech',title:'Mechanic Frequency',sub:'The keywords and mechanics your set uses most.',draw:chMech},
  {id:'removal',title:'Removal Distribution',sub:'The kinds of removal in your set, split by colour.',draw:chRemoval},
  {id:'complex',title:'Complexity vs. Rarity',sub:'How much rules text cards have at each rarity.',draw:chComplex}];
let chartId='mvcol';
function drawCharts(){
  const cs=D.cards.filter(c=>(!qfn||qfn(c))&&rfOk(c)&&!isBasic(c)),ch=CHARTS.find(x=>x.id===chartId);
  $('#charts').innerHTML=`<div class="glass chartbox"><div class="charthead"><select id="chartsel" class="chartsel" aria-label="Choose a graph">${CHARTS.map(x=>`<option value="${x.id}"${x.id===chartId?' selected':''}>${esc(x.title)}</option>`).join('')}</select><span class="mut">${cs.length} card${cs.length==1?'':'s'}${qfn?' matching your search':' in your set'}</span></div><p class="chartsub">${esc(ch.sub)}</p>${cs.length?ch.draw(cs):'<div class="empty">No cards match your search.</div>'}</div>`;
  $('#chartsel').onchange=e=>{chartId=e.target.value;drawCharts()}}
function setChart(on){chartMode=on;$('#cards').hidden=on;$('#charts').hidden=!on;$('#summary').hidden=on;const b=$('#graphs');b.classList.toggle('on',on);b.textContent=on?'Back to cards':'Graphs';
  $('#filters').classList.toggle('chartmode',on);$('#collapse').hidden=on||!D;$('#sortwrap').classList.toggle('chartmode',on)
  if(D){if(on)drawCharts();else draw()}}
async function upload(f){if(!f)return;pg=0;Object.values(FILT).forEach(f=>f.set.clear());if(chartMode)setChart(false);render(await post('/api/upload?name='+encodeURIComponent(f.name),f,true))}
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
  const COUNT=117,COLS=12;let last=-1;
  if(matchMedia('(prefers-reduced-motion: reduce)').matches||!Element.prototype.animate)return;
  const layer=document.createElement('div');layer.id='floaters';layer.setAttribute('aria-hidden','true');document.body.prepend(layer);
  const rnd=(a,b)=>a+Math.random()*(b-a);
  function spawn(el,initial){
    const W=innerWidth,H=innerHeight,s=rnd(46,76);let i;do{i=Math.floor(Math.random()*COUNT)}while(i===last);last=i;
    el.style.setProperty('--s',s+'px');el.style.setProperty('--cx',i%COLS);el.style.setProperty('--cy',Math.floor(i/COLS));
    const side=Math.floor(Math.random()*4);let x0,y0,x1,y1;
    if(side===0){x0=-s;y0=rnd(0,H);x1=W+s;y1=rnd(0,H)}else if(side===1){x0=W+s;y0=rnd(0,H);x1=-s;y1=rnd(0,H)}
    else if(side===2){x0=rnd(0,W);y0=-s;x1=rnd(0,W);y1=H+s}else{x0=rnd(0,W);y0=H+s;x1=rnd(0,W);y1=-s}
    const dur=Math.hypot(x1-x0,y1-y0)/rnd(14,34)*1000,r0=rnd(0,360),r1=r0+rnd(-140,140);
    const a=el.animate([{transform:`translate(${x0}px,${y0}px) rotate(${r0}deg)`},{transform:`translate(${x1}px,${y1}px) rotate(${r1}deg)`}],{duration:dur,easing:'linear',fill:'forwards'});
    if(initial)a.currentTime=rnd(0,.95)*dur;
    a.onfinish=()=>spawn(el,false)}
  const n=Math.max(10,Math.min(22,Math.round(innerWidth*innerHeight/60000)));
  for(let k=0;k<n;k++){const el=document.createElement('div');el.className='fsym';layer.appendChild(el);spawn(el,true)}
})();
/* ---------- search filters: rarity / colour / type ---------- */
const rkey=c=>{const r=prarity(c);return r==='Special'||r==='Unknown'?'Other':r};
const FILT={
  rar:{label:'Rarity',opts:[['Common','Common',RCOL.Common],['Uncommon','Uncommon',RCOL.Uncommon],['Rare','Rare',RCOL.Rare],['Mythic','Mythic',RCOL.Mythic],['Other','Other',RCOL.Special]],has:(c,k)=>rkey(c)===k},
  col:{label:'Colour',opts:[['W','White','#f4efd2'],['U','Blue','#4a90d9'],['B','Black','#3d3646'],['R','Red','#e3493b'],['G','Green','#3da66a'],['M','Multicolour','#e8b93a'],['C','Colourless','#aeb4bd']],
    has:(c,k)=>{const s=qinfo(c).cols;return k==='M'?s.size>1:k==='C'?s.size===0:s.has(k)}},
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


$('#noscry').onchange=e=>{noScry=e.target.checked;draw()};
$('#q').oninput=e=>{fromList=false;setQuery(e.target.value);pg=0;draw()};
document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-act]');if(!b)return;const a=b.dataset.act,id=b.dataset.id,f=FM[id];
  if(a==='prev'||a==='next'){pg+=a==='next'?1:-1;draw();window.scrollTo({top:$('#cards').offsetTop-80});return}
  if(a==='toastx'){$('#toast').hidden=true;return}
  if(a==='igncard'){render(await post('/api/ignorecard',{idx:b.dataset.idx,on:b.dataset.on==='1'}));return}
  if(a==='newcheck'){showHero();return}
  if(a==='backlist'){fromList=false;$('#q').value='';setQuery('');setCompact(true);window.scrollTo({top:0});return}
  if(a==='openrow'){const c=D.cards.find(x=>String(x.idx)===b.dataset.idx);if(c){$('#q').value='!"'+(c.name||'')+'"';setQuery($('#q').value);fromList=true;setCompact(false);window.scrollTo({top:$('#cards').offsetTop-$('header.top').offsetHeight-12})}return}
  if(a==='copy'){try{await navigator.clipboard.writeText(f.after);b.textContent='Copied ✓'}catch(_){prompt('Copy this wording:',f.after)}}
  else if(a==='ign')render(await post('/api/ignore',{id,scope:b.dataset.scope}));
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
                    return self.js(analyze())
                if u.path == "/api/ignorecard":
                    w = ST.setdefault("ign_whole", set())
                    (w.add if body.get("on") else w.discard)(int(body["idx"]))
                    return self.js(analyze())
                if u.path == "/api/resetign":
                    ST["ign_card"], ST["ign_text"], ST["ign_rule"], ST["ign_whole"] = set(), set(), set(), set()
                    return self.js(analyze())
                self.js({"error": "Unknown endpoint"}, 404)
            except Exception as e:
                self.js({"error": str(e)}, 400)
