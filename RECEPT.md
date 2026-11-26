# Recept (stvarno korišten za demonstraciju)

## Početna naredba
```bash
./setup.sh && ./run.sh            # aplikacija; ili u Claude Codeu: /kadar gymbeam-hr
```
Demonstracija je izvedena naredbama iz `README.md` (odjeljak "Naredbeni redak"), istim fazama koje koristi aplikacija.

## Alati i modeli
| Što | Alat / model | Postavka |
|---|---|---|
| Analiza, plan, tekstovi, provjera | Claude **Opus 5.5** (`claude-opus-5-5`) preko Claude Code CLI-ja (`claude -p`, strukturirani JSON izlaz validiran shemom) ili Claude API-ja | `KADAR_TEXT_MODEL`, `KADAR_LLM_BACKEND` |
| Effort po koraku | slike `low`, tvrdnje `medium`, analiza / plan / tekstovi `high`, provjera `medium` | u kodu faza |
| Dohvat podataka | httpx + BeautifulSoup (schema.org JSON-LD, Open Graph IG objava) | `KADAR_USER_AGENT`, `KADAR_REQUEST_DELAY_S` |
| Render slajdova | Jinja2 HTML/CSS predložak → Playwright Chromium → PNG | `kadar/render/templates/slide.html` |
| Fontovi | Anton, Inter (OFL, u repou) | `kadar/render/fonts/` |
| Modeli za slike | **ne koriste se** (proizvod i logo moraju ostati točni) | — |

## Promptovi (`prompts/`)
| Kadar | Datoteke |
|---|---|
| 02 | `02a_slike_*` (uloga slika, izbor packshota), `02b_tvrdnje_*` (dopuštene tvrdnje s citatima), `02c_brend_*` (analiza brenda) |
| 03 | `03_plan_*` |
| 04 | `04_tekst_*`, `04b_scene_*` (prompti za scene naslovnica i razigrani naslovi) |
| 05 | `05_provjera_*` |

Sheme strukturiranog izlaza su u `kadar/schemas.py`.

## Ljudske radnje (deklarirane)
1. Pristup modelu: `claude auth login` ili API ključ u `.env`.
2. Brif i poveznice IG objava (`inputs/brief_<brend>.json`, `inputs/…/posts.txt`); screenshotovi su opcionalni.
3. Pregled i odobrenje svakog kadra (`approve`, s napomenom što je pregledano).
4. Ljudske odluke koje nadjačavaju AI: boje i obraćanje (`inputs/brand/brand.json`), smjernice za plan (`inputs/plan_notes_<brend>.md`), ispravci teksta (`inputs/fixes_<brend>.json`: unosi s `"phase": "03_plan"` primjenjuju se na plan odmah nakon generiranja, ostali na tekstove izrade naredbom `fix`). Ručna referenca proizvoda, ako webshop nema čisti packshot: `inputs/brand/<slug-proizvoda>.png`.
5. Opcionalno, kreativni sloj: `kadar scenes <brend>` napiše prompte; čovjek generira scene u alatu po izboru (bez proizvoda i logotipa) i spremi ih u `inputs/scenes/objava_N_slajd_NN.jpg`, a izabrani naslov upiše u `inputs/fixes_<brend>.json`. Render umeće pravi packshot i logo preko scene.
6. Pri stvarnoj objavi: nativni stikeri u storyju (upute uz objavu).

Nema neobjašnjenih ručnih dorada: svaka ljudska promjena je u `inputs/` i evidentirana u `HUMAN_EDITS.md`.

## Međurezultati
`runs/<brend>/<kadar>/output.json` (izlaz), `meta.json` (status, vrijeme, napomena pregleda), `calls.jsonl` (svaki AI poziv: model, tokeni, trajanje), `steps/` (spremljeni koraci; ponovno pokretanje ih ne ponavlja). Ključni međurezultati demonstracije kopirani su u `isporuka/gymbeam-hr/dokumenti/`.

## Nastavak nakon prekida
`kadar status <brend>` pokazuje prvi neodobreni kadar. Ponovno pokretanje faze preskače spremljene korake (npr. već klasificirane slike i izvučene tvrdnje).
