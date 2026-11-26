---
description: Kadar — od Instagram brenda do tri gotove objave (6 kadrova s ljudskim pregledom)
argument-hint: "[slug-brenda, npr. gymbeam-hr] ili prazno za novi brend"
allowed-tools: Bash(.venv/bin/python -m kadar:*), Bash(./setup.sh), Read, Write, Edit
---

Vodiš korisnika kroz recept **Kadar** u ovoj mapi. Sav posao rade naredbe `.venv/bin/python -m kadar …`; ti ih pokrećeš, sažimaš izlaz i čekaš odluku čovjeka. Ne izmišljaj sadržaj objava sam: tekstove, analizu i plan proizvode faze recepta.

Argument: `$ARGUMENTS` (slug brenda; ako je prazan, radi se novi brend).

## 0. Priprema
- Ako ne postoji `.venv/`, pokreni `./setup.sh` i javi korisniku ručnu radnju koju skripta ispiše (npr. `claude auth login`).
- Pokreni `.venv/bin/python -m kadar status <slug>` ako slug postoji i **nastavi od prvog neodobrenog kadra**.

## 1. Brif (kadar 01)
- Novi brend: postavi korisniku pitanja iz brifa (naziv, Instagram profil, web/webshop, poveznice proizvoda, publika, ciljevi, uzori, ton, ograničenja, jezik) i poveznice 5–15 IG objava. Spremi odgovore u `inputs/brief_<slug>.json` (oblik kao `inputs/brief_gymbeam-hr.json`, s `instagram_screenshots_dir` i `brand_dir` u `inputs/<slug>/…`), a poveznice objava u `inputs/<slug>/instagram/posts.txt`.
- Pokreni `.venv/bin/python -m kadar brief --from inputs/brief_<slug>.json`.
- Pokaži upozorenja i pitaj za odobrenje.

## 2–6. Za svaki sljedeći kadar
| Kadar | Naredba | Što pokazati korisniku |
|---|---|---|
| 02 Analiza | `analyze <slug>` | sažetak `runs/<slug>/02_analiza/analiza.md`: ton, boje, prilike, nedostupni izvori, nedosljednosti u izvoru. Pitaj za ljudske odluke (boje, „ti”/„vi”) i upiši ih u `<brand_dir>/brand.json` |
| 03 Plan | `plan <slug>` | tri objave (cilj, format, koncept) iz `plan.md` i provjeru tvrdnji. Smjernice korisnika upiši u `inputs/plan_notes_<slug>.md` i ponovi plan ako ih ima |
| 04 Izrada | `create <slug>` | putanje do slajdova `runs/<slug>/04_izrada/objava_N/` i opise; pozovi korisnika da ih pogleda |
| 05 Provjera | `qa <slug>`, zatim po potrebi `fix <slug>` i ponovno `qa <slug>` | broj provjera ✅/⚠️/❌ i popis upozorenja; ručne ispravke upiši u `inputs/fixes_<slug>.json` |
| 06 Isporuka | `deliver <slug>` | `isporuka/<slug>/README.md` |

Nakon svakog kadra **stani i pitaj**: odobriti, ponoviti ili promijeniti? Na odobrenje pokreni `.venv/bin/python -m kadar approve <slug> <kadar> --note "<što je čovjek pregledao ili promijenio>"`.

Pravila: nikad ne odobravaj kadar bez izričitog "da" korisnika; ne mijenjaj tvrdnje o proizvodu mimo popisa dopuštenih; ključeve i lozinke ne upisuj u datoteke.
