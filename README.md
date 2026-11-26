# Kadar — od Instagram brenda do tri gotove objave

**Kadar** je ponovljiv AI recept (lokalna web aplikacija + naredbeni redak + paket promptova za Claude Code) koji iz brifa i službenih izvora brenda izradi **tri gotove Instagram objave**: slajdove u PNG-u, opise, obrazloženja i izvještaj provjere.

Postupak je razložen na **6 kadrova**. Svaki kadar sprema svoj izlaz na disk, a čovjek ga pregleda i odobri prije sljedećeg. Rad se zato može nastaviti od bilo koje spremljene faze.

**Demonstracija:** GymBeam Hrvatska ([@gymbeamhr](https://www.instagram.com/gymbeamhr/)). Gotove objave, izvori i međurezultati nalaze se u [`isporuka/gymbeam-hr/`](isporuka/gymbeam-hr/README.md).

---

## Brzi start (≈ 5 min)

```bash
./setup.sh      # Python okruženje, paketi, Chromium za render, provjera Claude Code CLI-ja
./run.sh        # otvara aplikaciju na http://127.0.0.1:8770
```

**Jedina ručna radnja** je pristup AI modelu, na jedan od dva načina:

| Način | Što treba | Postavka u `.env` |
|---|---|---|
| **Claude Code** (zadano) | instaliran [Claude Code](https://claude.ai/install.sh) i prijava `claude auth login` (Claude pretplata) | `KADAR_LLM_BACKEND=claude-code` |
| **Claude API** | vlastiti API ključ | `KADAR_LLM_BACKEND=api`, `ANTHROPIC_API_KEY=…` |

**Windows** (PowerShell, u mapi projekta):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Preduvjeti: Python ≥ 3.9 (Windows: s python.org, uz opciju "Add python.exe to PATH") i internet za dohvat stranice brenda. Claude Code na Windowsu se instalira naredbom `irm https://claude.ai/install.ps1 | iex`. U repou nema ključeva; `.env.example` je primjer konfiguracije bez ključeva.

### Što radi bez AI pristupa

Bez Claude Codea i bez API ključa rade: aplikacija i pregled GymBeam demo runa, kadar 01 (dohvat proizvoda, loga i IG objava), render slajdova iz postojećih tekstova (`create`), provjera u kodu (`qa --no-vision`) i isporuka (`deliver`). AI je potreban za analizu (02), plan (03), nove tekstove (04) i provjeru s AI vizijom (05).

---

## Tri načina pokretanja

**1. Web aplikacija** (preporučeno): `./run.sh`. Ispuni brif ("+ Novi brend") ili otvori GymBeam demo, pa svaki kadar pokreni gumbom **Pokreni**, pregledaj ga i klikni **Odobri kadar →**.

**2. Naredbeni redak**, isti koraci kao u aplikaciji:

```bash
P=.venv/bin/python
$P -m kadar brief --from inputs/brief_gymbeam-hr.json   # 01 brif i ulazi
$P -m kadar approve gymbeam-hr 01_brif
$P -m kadar analyze gymbeam-hr                           # 02 analiza brenda
$P -m kadar approve gymbeam-hr 02_analiza
$P -m kadar plan gymbeam-hr                              # 03 plan triju objava
$P -m kadar approve gymbeam-hr 03_plan
$P -m kadar create gymbeam-hr                            # 04 tekstovi + render slajdova
$P -m kadar approve gymbeam-hr 04_izrada
$P -m kadar qa gymbeam-hr                                # 05 provjera (kod + AI vizija)
$P -m kadar fix gymbeam-hr                               #    petlja dorade: ispravci → novi render
$P -m kadar approve gymbeam-hr 05_provjera
$P -m kadar deliver gymbeam-hr                           # 06 paket za predaju
$P -m kadar status gymbeam-hr                            # gdje smo / od čega nastaviti
```

**3. Claude Code** (bez pisanja naredbi): u mapi projekta pokreni `claude` i upiši `/kadar gymbeam-hr`. Paket promptova u [`.claude/commands/kadar.md`](.claude/commands/kadar.md) vodi agenta kroz istih 6 kadrova i nakon svakog stane za ljudski pregled. Opis recepta je u [`RECEPT.md`](RECEPT.md).

---

## Kadrovi (faze)

| Kadar | Ulaz | Što radi | Izlaz |
|---|---|---|---|
| **01 Brif** | brif (obrazac ili JSON), poveznice proizvoda i IG objava, opcionalno logo i screenshotovi | dohvaća činjenice i slike proizvoda (schema.org), službeni logo (SVG) te javne podatke IG objava (opis, datum, lajkovi, slika) | `01_brif/output.json` |
| **02 Analiza** | izlaz 01 | bira čisti packshot (odbacuje promo kompozicije), izvlači **dopuštene tvrdnje s doslovnim citatima**, mjeri paletu kodom, analizira ton, publiku, teme, stil i prikaz proizvoda i osoba uz oznake **PROVJERENO / PRETPOSTAVKA / NEDOSTUPNO** | `analiza.md` |
| **03 Plan** | odobrena analiza + ljudske smjernice | tri objave (cilj, format, koncept, slajdovi iz skupa predložaka, KPI, rizici) i odbačene ideje; kod provjerava da su sve tvrdnje s popisa dopuštenih | `plan.md` |
| **04 Izrada** | odobreni plan | završni tekstovi i opisi (lektura, dosljedno „ti”), zatim **render u pregledniku**: HTML/CSS predložak → PNG 1080×1350 / 1080×1920 | `objava_N/slajd_XX.png`, `opis.txt` |
| **05 Provjera** | gotove objave | **~140 provjera**: kod (dimenzije, preljev teksta, sigurna zona storyja, zabranjene tvrdnje, brojke prisutne u izvoru, obavezna upozorenja, obraćanje…) i AI vizija (proizvod vs referenca, logo, čitljivost, jezik, ton, CTA). Petlja dorade primjenjuje ispravke. | `provjera.md` |
| **06 Isporuka** | odobreni kadrovi | slaže objave, izvore, ulaze i dokumente za predaju | `isporuka/<brend>/` |

Sve međurezultate sprema `runs/<brend>/<kadar>/` (`output.json`, `meta.json`, `calls.jsonl` s modelom, tokenima i trajanjem svakog AI poziva). Promptovi su zasebne datoteke u [`prompts/`](prompts/), da bi bili vidljiv i izmjenjiv dio recepta.

---

## Ključne odluke

- **Proizvod se ne generira.** Logo, pakiranje i etiketa moraju ostati točni, a modeli za slike ih redovito izobliče. Zato se koriste stvarni packshotovi sa službene stranice i službeni logo (SVG), a dizajn se renderira HTML/CSS-om. Tekst na slikama također renderira preglednik, ne model, pa su č, ć, ž, š i đ uvijek ispravni.
- **Činjenice samo iz izvora.** Svaka tvrdnja ima doslovni citat i oznaku smije li u objavu (EU Uredba 1924/2006 za zdravstvene tvrdnje). Cijene, akcije i ocjene se ne koriste jer su promjenjive.
- **Model bira samo iz zadanih okvira.** Plan bira između 10 rasporeda koje renderer zna nacrtati, a izrada mijenja samo tekst, dok raspored, pozadinu i proizvod preuzima iz plana.
- **Čovjek odlučuje na svakom kadru.** Ljudske odluke (boje, obraćanje, smjernice, ispravci) spremaju se u `inputs/` i ulaze u prompt. Evidencija je u [`HUMAN_EDITS.md`](HUMAN_EDITS.md).

## Što može varirati pri ponavljanju

Formulacije tekstova, koncepti objava i redoslijed slajdova razlikuju se od pokretanja do pokretanja jer je izlaz modela nedeterministički. Stabilni su: izvori i činjenice, izbor packshota, boje i logo, raspored i dimenzije slajdova te pravila provjere. Instagram se mijenja, pa analiza ovisi o objavama dostupnima u trenutku dohvata. Webshop može promijeniti strukturu stranice; scraper koristi standardni schema.org, uz rezervu na ručne ulaze.

## Ograničenja

- Instagram feed profila nije dostupan bez prijave, pa se koriste poveznice objava (javni podaci) i opcionalni screenshotovi. Metrike (spremanja, doseg) nisu dostupne.
- Ankete, kvizovi i poveznice u storyju su grafički prikaz. Pri objavi se preko njih postavljaju nativni Instagram stikeri; upute su uz svaku objavu.
- Nema AI generiranih fotografija scena: objave su grafičke, s pravim packshotom.

## Struktura

```
kadar/            kod recepta (faze, scraperi, LLM sloj, renderer, web aplikacija)
prompts/          svi promptovi (po fazama)
inputs/           ulazi i ljudske odluke za demonstraciju (brif, IG poveznice, screenshotovi, boje, smjernice, ispravci)
isporuka/         gotove objave za predaju (GymBeam demo)
app/assets/       dizajn aplikacije (logo, ilustracije, teme) — vidi DESIGN.md
runs/             radni direktorij pokretanja (stvara se automatski)
```
