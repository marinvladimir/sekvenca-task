"""Galerija runa: jedna HTML stranica u dizajnu aplikacije Kadar.

Prikazuje traku kadrova (stanje faza) i gotove objave sa slajdovima, opisom,
ciljem, formatom i obrazloženjem. Stranica je statična i koristi relativne
putanje, pa radi i iz ZIP-a i s GitHuba (preuzeto lokalno).
"""

from __future__ import annotations

import html
import os
from pathlib import Path

from ..config import settings
from ..state import PHASES, Run

LABELS = {"01_brif": "Brif", "02_analiza": "Analiza", "03_plan": "Plan", "04_izrada": "Izrada",
          "05_provjera": "Provjera", "06_isporuka": "Isporuka"}
GOALS = {"edukacija_spremanja": "Edukacija · spremanja", "predstavljanje_proizvoda": "Predstavljanje proizvoda",
         "interes_za_kupnju": "Interes za kupnju", "reakcije_komentari": "Reakcije i komentari"}


def build_gallery(run: Run) -> Path:
    out = run.dir / "galerija.html"
    assets = os.path.relpath(settings.root / "app" / "assets", run.dir)
    e = html.escape
    steps = []
    for p in PHASES:
        st = run.meta(p).get("status", "pending")
        steps.append(f'<li class="st-{st}"><span class="mono">{p[:2]}</span>{LABELS[p]}</li>')
    posts_html = []
    create = run.output("04_izrada") or {"posts": []}
    for post in create["posts"]:
        story = post["format"] == "story_niz"
        slides = "".join(
            f'<a href="{e(s)}" target="_blank"><img loading="lazy" src="{e(s)}" alt="slajd {i}"></a>'
            for i, s in enumerate(post["slajdovi"], 1))
        posts_html.append(f"""
<section class="post">
  <header>
    <span class="mono">OBJAVA {post['objava']}</span>
    <h2>{e(post['naslov'])}</h2>
    <div class="chips"><span class="chip">{e(post['format'].replace('_', ' '))}</span>
      <span class="chip chip--goal">{e(GOALS.get(post['cilj'], post['cilj']))}</span>
      <span class="chip">{len(post['slajdovi'])} slajdova</span></div>
  </header>
  <div class="strip {'strip--story' if story else ''}">{slides}</div>
  <div class="meta">
    <div><h3 class="mono">Opis objave</h3><p class="caption">{e(post['opis'])}</p></div>
    <div><h3 class="mono">Zašto ovako</h3><p>{e(post['obrazlozenje'])}</p>
      <h3 class="mono">KPI</h3><p>{e(post['kpi'])}</p></div>
  </div>
</section>""")
    if not posts_html:
        posts_html.append(f'<div class="empty"><img src="{assets}/empty-gallery.jpg" alt=""><p>Objave još nisu izrađene.</p></div>')

    info = run.info()
    page = f"""<!doctype html><html lang="hr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kadar · {e(info['brand'])}</title>
<link rel="icon" href="{assets}/favicon.svg">
<link rel="stylesheet" href="{assets}/theme.css">
<style>
body {{ margin:0; background:var(--bg); color:var(--text); font-family:var(--font-body); }}
.wrap {{ max-width:1280px; margin:0 auto; padding:32px 24px 80px; }}
.mono {{ font-family:var(--font-mono); font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--text-muted); }}
.top {{ display:flex; align-items:center; gap:14px; }} .top img {{ height:34px; }}
.top h1 {{ font-family:var(--font-head); font-size:26px; margin:0; }}
.top .brand {{ margin-left:auto; color:var(--text-muted); }}
ol.timeline {{ list-style:none; padding:0; margin:28px 0 36px; display:grid; grid-template-columns:repeat(6,1fr); gap:6px; }}
.timeline li {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px 14px; font-weight:600;
  display:flex; flex-direction:column; gap:4px; position:relative; }}
.timeline li::before, .timeline li::after {{ content:""; position:absolute; left:8px; right:8px; height:4px;
  background:radial-gradient(circle, var(--border) 1.5px, transparent 2px) 0 0/10px 4px; }}
.timeline li::before {{ top:3px; }} .timeline li::after {{ bottom:3px; }}
.st-approved {{ border-color:var(--accent)!important; }} .st-approved .mono {{ color:var(--accent); }}
.st-needs_review {{ border-color:var(--assumption)!important; }} .st-running .mono {{ color:var(--rec); }}
.post {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--r-card); padding:24px; margin-bottom:28px; }}
.post h2 {{ font-family:var(--font-head); font-size:28px; margin:6px 0 12px; }}
.chips {{ display:flex; gap:8px; flex-wrap:wrap; }}
.chip {{ color:var(--text-muted); }} .chip--goal {{ color:var(--accent); }}
.strip {{ display:flex; gap:12px; overflow-x:auto; padding:20px 0 12px; scroll-snap-type:x mandatory; }}
.strip a {{ flex:none; scroll-snap-align:start; }}
.strip img {{ height:420px; border-radius:8px; display:block; box-shadow:0 0 0 1px var(--border); }}
.strip--story img {{ height:520px; }}
.meta {{ display:grid; grid-template-columns:1fr 1fr; gap:28px; margin-top:8px; }}
.meta h3 {{ margin:14px 0 6px; }} .meta p {{ margin:0; line-height:1.55; color:var(--text); }}
.caption {{ white-space:pre-wrap; background:var(--surface-2); border-radius:8px; padding:14px 16px; }}
.empty {{ text-align:center; color:var(--text-muted); }} .empty img {{ max-width:280px; border-radius:10px; }}
@media (max-width:760px) {{ ol.timeline {{ grid-template-columns:repeat(3,1fr); }} .meta {{ grid-template-columns:1fr; }}
  .strip img {{ height:300px; }} .strip--story img {{ height:380px; }} }}
</style></head>
<body class="grain"><div class="wrap">
<div class="top"><img src="{assets}/logo.svg" alt=""><h1>Kadar</h1>
  <span class="brand">{e(info['brand'])} · {e(info.get('instagram', ''))}</span></div>
<ol class="timeline">{''.join(steps)}</ol>
{''.join(posts_html)}
</div></body></html>"""
    out.write_text(page, encoding="utf-8")
    return out
