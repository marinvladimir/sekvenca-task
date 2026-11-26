# TODO — Sekvenca zadatak (rok: ned 29. 11. 2026. do ponoći)

Legenda: **[TI]** = tvoj posao · **[JA]** = Claude · **[ZAJEDNO]** = ja pripremim, ti odlučiš/odobriš
⚠️ = zamka iz zadatka na koju ta stavka odgovara

---

## 0. Priprema (čet)

- [x] **[TI]** Potvrdi brend (prijedlog: GymBeam HR, @gymbeamhr) i proizvode koje promoviramo (2–3 komada)
- [x] **[TI]** Provjera pošiljatelja: Jure Pavlović (Gmail) = osnivač Sekvence, potvrđeno javnim izvorima; nema traženja osjetljivih podataka. Opcionalno: potvrda na info@sekvenca.hr
- [x] **[TI]** Pokreni `TIMELOG.md` odmah — bilježi **aktivni rad** odvojeno od **čekanja na generiranje** ⚠️ (traže to u PDF-u)
- [x] **[TI]** Prijava u Claude Code CLI (`claude auth login`) — LLM koraci idu preko pretplate, **bez API ključa i plaćanja**
- [x] **[TI]** GitHub repo napravljen (privatan): github.com/marinvladimir/sekvenca-task — lokalno `git init` + remote; **prvi commit/push još nije napravljen**
- [x] **[JA]** Kostur projekta: struktura mapa, `.env.example`, `.gitignore` (da `.env` i `runs/` s privatnim stvarima ne odu van) ⚠️
- [x] **[JA]** Dizajn sustav aplikacije → `DESIGN.md` ✅
- [x] **[TI]** Izgeneriraj UI assete prema promptovima iz `DESIGN.md` i spremi ih u `app/assets/`

## 1. Ulazi / brifing

- [x] **[TI]** Ručno spremi 12–15 screenshotova s @gymbeamhr (mješavina: proizvodi, ljudi, edukacija, reelsi, storyji) u `inputs/instagram/` — Instagram blokira scraping bez prijave, zato je ovo deklarirana ljudska radnja ⚠️
- [x] **[TI]** Zapiši datum spremanja i URL svake objave (`inputs/instagram/index.csv`) — da analiza ima konkretne poveznice ⚠️
- [x] **[JA]** Scraper za gymbeam.hr: naziv, opis, sastav, cijena, službene fotke proizvoda, logo → `inputs/products/` + `sources.json` s URL-om i datumom za svaku činjenicu ⚠️
- [x] **[TI]** Provjeri da su skinute fotke proizvoda čiste i trenutne (stvarno pakiranje, ne staro) ⚠️
- [x] **[JA]** Interaktivni brifing u aplikaciji (web, proizvodi, publika, ciljevi, uzori, upload slika/logotipa)
- [x] **[ZAJEDNO]** Ispunjeni demo brif (`runs/gymbeam/01_brief.json`) — ja predložim, ti potvrdiš ⚠️ ("sam pripremi i predaj odgovore i ulaze")

## 2. Analiza brenda

- [x] **[JA]** Prompt i faza analize: ton, publika, teme, stil, boje (izvučeni hex-ovi iz screenshotova), prikaz proizvoda i osoba
- [x] **[JA]** Svaka tvrdnja u analizi označena: `PROVJERENO (izvor)` / `PRETPOSTAVKA` / `NEDOSTUPNO` ⚠️
- [x] **[TI]** Pročitaj analizu i ispravi što ne štima. **Zapiši barem jednu konkretnu ispravku** (prije → poslije, zašto) za PDF ⚠️

## 3. Plan sadržaja

- [x] **[JA]** Faza plana: 3 objave × (cilj, format, koncept, obrazloženje, KPI) → `runs/gymbeam-hr/03_plan/plan.md`, sve tvrdnje s popisa dopuštenih
  - Objava 1: edukativni karusel (cilj: spremanja)
  - Objava 2: predstavljanje proizvoda, jedna slika (cilj: interes za kupnju)
  - Objava 3: niz od 3–4 storyja s anketom/kvizom (cilj: reakcije)
- [x] **[TI]** Pregled plana i dorade teksta

## 4. Izrada

- [x] **[JA]** Copywriting prompt: hrvatski, ton brenda, hashtagovi, CTA; **zabrana izmišljanja cijena i svojstava i zdravstvenih tvrdnji izvan izvora** (EU 1924/2006) ⚠️
- [x] **[JA]** ~~Model za slike~~ → odluka: bez plaćenog modela za slike; objave = stvarni packshotovi + službeni logo + HTML dizajn (točniji proizvod, nula troška) ⚠️
- [x] **[JA]** HTML/CSS predložak (10 rasporeda) + renderer → PNG preko Playwrighta; fontovi lokalno (Anton, Inter); testirano na svim rasporedima ⚠️
- [x] **[JA]** Izvoz: feed 1080×1350, story 1080×1920, slajdovi numerirani (01 / 06) ⚠️
- [x] **[JA]** Spremanje svake faze u `runs/<brend>/NN_*.json` + `--resume-from <faza>` ⚠️
- [x] **[TI]** Pokreni generiranje (čekanje ide u timelog kao "čekanje")

## 5. Provjera i dorada

- [x] **[JA]** QA faza: Claude Vision uspoređuje proizvod na objavi s referencom (logo, etiketa, boja pakiranja) ⚠️
- [x] **[JA]** QA: svaka rečenica s tvrdnjom mapirana na `sources.json`; što nema izvor, ide van ⚠️
- [x] **[JA]** QA: jezik (srbizmi, kalkovi), dimenzije, sigurna zona za UI Instagrama
- [ ] **[TI]** Ljudski pregled svih slajdova; odbaci ili pokreni ponovno što ne valja. **Svaku ručnu doradu zapiši** (recept ne smije imati "neobjašnjene ručne dorade") ⚠️
- [x] ~~Osobe na slikama~~ — nije primjenjivo (objave nemaju osobe; namjerna odluka)

## 6. Isporuka (sub–ned)

- [x] **[JA]** `README.md`: instalacija, pokretanje, postavke, modeli, ljudske radnje, što varira pri ponavljanju ⚠️
- [x] **[JA]** Paket promptova za Claude Code (alternativa bez pokretanja aplikacije)
- [x] **[JA]** Nacrt PDF-a (1–2 str.): pokretanje, faze, ključne odluke, provjera, ograničenja, prijedlog unapređenja (učenje iz komentara, odobrenja i metrika objava + A/B evaluacija nove verzije)
- [x] **[JA]** Vrijeme iz TIMELOG-a i primjer dorade upisani u PDF → **[TI]** samo potvrdi pri čitanju
- [x] **[JA]** Svježa kopija bez .venv/runs/.env: setup.sh ✓ (Python 3.11), brif od nule ✓, render ✓, 113/113 provjera ✓, isporuka ✓, aplikacija ✓; uhvaćeno i ispravljeno: anthropic 2.x na novijem Pythonu → verzija zaključana
- [x] **[JA]** Provjera da u repou/ZIP-u nema ključeva (`git grep` za `sk-`, `AIza` i sl.) ⚠️
## 7. Završni QA (prije slanja) ⚠️

**Kvaliteta objava**
- [x] **[JA]** Svaki slajd pogledan na punoj veličini: nema rezanog ni preklopljenog teksta, naslovi stanu, kontrast čitljiv
- [x] **[JA]** Proizvod na svakoj objavi = stvarni packshot (bez poklona/promo elemenata), logo točan i neizobličen
- [x] **[JA]** Svaka tvrdnja na slajdovima i u opisima mapirana na izvor (S1–S3); nema cijena, kodova, superlativa ni "jača/liječi"
- [x] **[JA]** Lektura hrvatskog (dijakritike, srbizmi, tipfeleri), dosljedno "ti"
- [x] **[JA]** Dimenzije: feed 1080×1350, story 1080×1920; sigurna zona storyja (gore ~250 px, dolje ~340 px) bez ključnog teksta
- [x] **[JA]** Objave jasno označene 1, 2, 3; karusel slajdovi numerirani redom; uz svaku format, cilj, obrazloženje i opis
- [ ] **[TI]** Ljudski pregled svih slajdova na mobitelu ("bi li ovo GymBeam objavio?")

**Cijeli flow (ponovljivost)**
- [x] **[JA]** Čisti run od nule u novoj mapi (`runs/` obrisan) s istim ulazima: svih 6 kadrova prolazi bez ručnih intervencija osim deklariranih
- [x] **[JA]** Nastavak nakon prekida: prekinuti fazu usred rada, ponovno pokrenuti, provjeriti da se gotovi koraci ne ponavljaju
- [ ] **[JA]** Run u **novoj Claude Code sesiji** samo s receptom (bez ovog razgovora): dokaz da recept ne ovisi o nepredanom razgovoru
- [x] **[JA]** API backend (`KADAR_LLM_BACKEND=api`): barem provjera da se kod pokreće (dry-run), jer ga ocjenjivač može koristiti
- [x] **[JA]** `README` upute izvršene doslovno, korak po korak, na svježem klonu
- [x] **[JA]** Nema tajni u repou/ZIP-u; `.env.example` bez ključeva; `runs/` s privatnim stvarima isključen ili namjerno uključen kao primjer

**Predaja**
- [x] **[JA]** PDF (1–2 str.): vrijeme iz TIMELOG-a, ograničenja. **Ljudski doprinos opisati općenito: lektura i ton tekstova, vizualni QA, završni QA** (bez sitnih primjera); jedan konkretan primjer = vizualni (preklapanje naslova)
- [ ] **[TI]** Završno čitanje PDF-a i maila prije slanja
- [ ] **[TI]** Mail: odgovor Juri, **CC velimir@filmconnect.com**. Prilozi: 3 objave (mape + tekstovi), PDF, link na repo ili ZIP, link na aplikaciju ako je deployana

## 8. Web aplikacija (lokalna) i instalacija

- [x] **[JA]** Web aplikacija `python -m kadar app` (Flask): brif obrazac s uploadom, traka kadrova, pokretanje/odobravanje, ljudske odluke (boje, ti/vi), smjernice za plan, pregled objava
- [x] **[JA]** `setup.sh` + `run.sh`: automatska instalacija svih preduvjeta (Python okruženje, paketi, Chromium, provjera/instalacija Claude Code CLI-ja) + jasna poruka za jedinu ljudsku radnju (`claude auth login` ili API ključ)
- [x] **[JA]** Kadar 05 provjera: 143 provjere (kod + AI vizija), krug 1 → ispravci → krug 2; `kadar fix` petlja dorade
- [x] **[JA]** Kadar 06 isporuka (`isporuka/gymbeam-hr/`, README sa slikama) + u aplikaciji gumbi "Primijeni ispravke" i "Provjera bez AI"

## Opcionalno, ako ostane vremena

- [x] ~~Deploy online~~ → odluka: nije preduvjet zadatka; online bi tražio plaćeni API ključ na serveru. Lokalna aplikacija + setup.sh
- [ ] **[JA]** Kratki screen recording aplikacije u radu (gif u README-u)
