# DESIGN — aplikacija "Kadar"

> Radni naziv: **Kadar**. Sekvenca je filmska kuća, a "sekvenca" se sastoji od kadrova. Zato je svaka faza recepta jedan **kadar** (01 Brif → 02 Analiza → 03 Plan → 04 Izrada → 05 Provjera → 06 Isporuka), a sučelje izgleda kao montažni stol ili clapperboard.
> Slogan: *Od brenda do objave, kadar po kadar.*

## 1. Načela

1. **Sučelje je neutralno, a sadržaj je u boji.** Aplikacija je tamni "montažni stol". Jedine jake boje na ekranu dolaze od brenda koji se obrađuje (npr. GymBeam narančasta). Tako alat radi za svaki brend.
2. **Faze su vidljive cijelo vrijeme.** Gornja traka je timeline s 6 kadrova; svaki ima status (čeka / radi / gotovo / treba pregled).
3. **Dokaz uz svaku tvrdnju.** Oznake `PROVJERENO`, `PRETPOSTAVKA` i `NEDOSTUPNO` su vizualni elementi (chipovi), ne samo tekst.
4. **Čovjek odobrava.** Na kraju svake faze je jasan gumb "Odobri kadar" ili "Ponovi".

## 2. Paleta

Paleta posuđuje teal i tamnoplavu iz PDF-a zadatka (tihi naklon ocjenjivačima) i dodaje "REC" crvenu kao filmski akcent.

| Token | Tamna tema (zadana) | Svijetla tema | Upotreba |
|---|---|---|---|
| `--bg` | `#0E1116` | `#F5F3EE` | pozadina (tamna = montažna soba, svijetla = papir) |
| `--surface` | `#161B22` | `#FFFFFF` | kartice, paneli |
| `--surface-2` | `#1F2630` | `#ECE9E2` | ugniježđeni paneli, inputi |
| `--border` | `#2A323D` | `#D9D4CA` | rubovi, razdjelnici |
| `--text` | `#E8E6E1` | `#14202E` | glavni tekst |
| `--text-muted` | `#8B95A1` | `#5C6670` | sekundarni tekst, timecodeovi |
| `--accent` | `#2BA89A` | `#1A7A70` | primarna akcija, aktivni kadar (teal iz PDF-a) |
| `--rec` | `#FF4D3D` | `#E0382A` | "REC" točka dok AI generira, kritične greške |
| `--verified` | `#3FB97F` | `#23874F` | chip PROVJERENO |
| `--assumption` | `#E8B23A` | `#A87A10` | chip PRETPOSTAVKA |
| `--missing` | `#8B95A1` | `#6B7580` | chip NEDOSTUPNO (iscrtkani rub) |
| `--ink` | `#12233A` | `#12233A` | tamnoplava iz PDF-a: naslovi u svijetloj temi, PDF izvještaj |

Kontrast: `--text` na `--bg` i `--accent` na `--bg` prolaze WCAG AA. Kad je teal na tamnom gumbu, tekst na gumbu je `#0E1116`.

## 3. Tipografija (Google Fonts)

- **Naslovi:** `Space Grotesk` 600/700 — tehnički, a ipak topao
- **Tekst:** `Inter` 400/500, 15px, line-height 1.55 (dobro podržava hrvatske dijakritike)
- **Oznake kadrova, timecode, statusi:** `JetBrains Mono` 500, UPPERCASE, letter-spacing 0.08em → npr. `KADAR 03 · PLAN · 00:42`

Skala: 12 / 13 / 15 / 18 / 24 / 32 / 44.

## 4. Raspored i komponente

```
┌──────────────────────────────────────────────────────────────┐
│ ● KADAR   [01 Brif]─[02 Analiza]─[03 Plan]─[04]─[05]─[06]   │  ← timeline traka
├───────────────┬──────────────────────────────────────────────┤
│ Projekt       │  KADAR 02 · ANALIZA BRENDA          ● REC    │
│  GymBeam HR   │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  Ulazi (14)   │  │ Ton     │ │ Boje    │ │ Publika │        │
│  Izvori (22)  │  └─────────┘ └─────────┘ └─────────┘        │
│  Povijest     │  Tvrdnja … [PROVJERENO ↗ gymbeam.hr/...]    │
│               │                                             │
│               │        [ Ponovi ]   [ Odobri kadar → ]       │
└───────────────┴──────────────────────────────────────────────┘
```

- **Timeline čip kadra:** pravokutnik s perforacijom filmske trake gore i dolje (CSS `radial-gradient` točkice); stanja: prazan obrub (čeka), teal ispuna (aktivan), kvačica (gotovo), žuta točka (treba pregled).
- **REC indikator:** crvena točka s pulsom + `GENERIRA · 00:37` (timecode = vrijeme čekanja, ujedno ulaz za timelog).
- **Chipovi izvora:** zaobljenost 999px, mono font, ikona strelice ↗ otvara izvor.
- **Kartice objava:** preview u pravom omjeru (4:5 / 9:16), ispod: cilj, format, tekst, QA status.
- **Paleta brenda:** uzorci boja izvučeni iz analize, s hex kodom; klik kopira.
- Zaobljenja: 10px kartice, 8px gumbi, 6px inputi. Razmaci na mreži od 4px. Sjene minimalne, u tamnoj temi umjesto sjena svjetliji rub.
- **Ikone:** [Lucide](https://lucide.dev) (stroke 1.75). Ikone **ne generiraj AI-jem**: knjižnica je dosljednija, oštrija i besplatna.
- Suptilna filmska zrnatost (noise PNG, opacity 0.03) preko `--bg` u tamnoj temi.

## 5. Promptovi za UI assete

Rade u svakom alatu za generiranje slika (Google Flow / Imagen, Midjourney, GPT-image, Nano Banana, Krea…). Na kraj svakog prompta lijepi **STYLE LOCK** da sve izgleda kao jedan set. Generiraj 4 varijante i biraj.

**STYLE LOCK** (dodaj na kraj svakog prompta):
```
Style: minimal editorial illustration, flat shapes with subtle film grain, limited palette of deep charcoal #0E1116, slate #1F2630, teal #2BA89A, warm off-white #E8E6E1, single small accent of red #FF4D3D. Clean geometry, generous negative space, no text, no letters, no logos, no watermarks, no gradients except very soft ones.
```

### 5.1 Logo / znak (1:1, PNG, kasnije vektoriziraj)
```
A minimal logo mark for a creative AI tool called "Kadar": a film clapperboard abstracted into simple geometric shapes, the striped top bar subtly forming a progress bar of six segments, the first three filled in teal. Centered on a plain dark charcoal background, crisp edges, works at 32px favicon size.
```
> Ako alat kvari oblik, logotip složimo sami u SVG-u: 6 pravokutnika, 10 minuta posla.

### 5.2 Hero / početni ekran (16:9)
```
Wide illustration of an abstract film editing table seen from above: a horizontal strip of six film frames running across the image, each frame containing a different simple abstract shape — a speech bubble, a magnifying glass, a grid, a paint brush, a checkmark, a paper plane — the frames progressively light up from left to right in teal. Dark charcoal background, lots of empty space on the left third for headline text.
```

### 5.3 Ilustracije praznih stanja (1:1, svaka zasebno)
Isti početak za svih šest: `Small spot illustration, single centered object on plain dark charcoal background,`
| Kadar | Nastavak prompta |
|---|---|
| 01 Brif | `a clipboard with a blank form and a small teal pencil, a polaroid photo of a product box tucked under the clip.` |
| 02 Analiza | `a magnifying glass hovering over a grid of nine small square social media thumbnails, three thumbnails highlighted in teal.` |
| 03 Plan | `three index cards pinned in a row on a dark board, connected by a thin teal thread, each card with simple abstract scribble lines.` |
| 04 Izrada | `a camera lens and a paint brush crossing each other, small teal sparkles around them.` |
| 05 Provjera | `a film strip with a magnifying loupe on one frame, a small green checkmark and a small red dot beside it.` |
| 06 Isporuka | `a neat stack of three phone-shaped cards tied with a teal ribbon, a small paper plane taking off from the top.` |

### 5.4 Stanje greške (1:1)
```
Small spot illustration of a tangled film strip forming a loose knot, one frame showing a small red dot, calm and slightly humorous mood, plain dark charcoal background.
```

### 5.5 Prazna galerija objava (4:5)
```
An empty smartphone screen outline in thin off-white lines showing a blank social media post placeholder, three faint dashed rectangles stacked like a carousel behind it, plain dark charcoal background.
```

### 5.6 Tekstura filmske zrnatosti (1:1, 1024px, bešavna)
```
Seamless tileable texture of fine analog film grain, neutral grey noise on pure mid-grey #808080 background, uniform, no vignette, no scratches, no objects.
```
> Bešavnu zrnatost možemo izgenerirati i kodom (SVG `feTurbulence`), što je pouzdanije. Ovaj prompt je samo ako želiš "pravi" analogni osjećaj.

### 5.7 OG slika / thumbnail za README (1200×630)
```
Social preview banner: the six-frame film strip from left to right across the lower half, frames glowing teal in sequence, large empty dark area in the upper half reserved for title text, cinematic, minimal.
```
> Naslov ("Kadar — od brenda do objave") dodajemo kodom, ne AI-jem.

## 6. Što NE radimo AI-jem (namjerno)

- **Ikone** → Lucide
- **Tekst na bilo kojoj slici** → HTML/CSS render (dijakritike, oštrina)
- **Proizvodi i logotipi brenda u objavama** → stvarne fotke s webshopa; AI radi samo scenu oko njih
- **Slike za objave** ne radiš ručno u ovom alatu, nego ih generira pipeline. Inače recept nije ponovljiv. Ovi promptovi služe **samo za UI aplikacije**.

## 7. Datoteke (stanje: assets obrađeni 26. 11.)

Originali iz generatora su u `app/assets/source/`; obrađene verzije:

| Datoteka | Izvor | Obrada |
|---|---|---|
| `logo.svg`, `favicon.svg` | ručno, po uzoru na generirani znak | vektorski, oštar i na 16–32 px |
| `logo-raster.png` | Kadar_AI_logo_mark (#7) | kvadratni izrez 512 px |
| `hero.jpg` | Abstract_film_editing_table (_9f5d) | bez promjene, lijeva trećina za naslov |
| `hero-glow.jpg` | Film_strip_glowing_teal | pozadina za landing/README |
| `empty-01-brif.jpg` … `empty-06-isporuka.jpg` | Six_steps_workflow (mreža 3×2) | izrezano u 6 kartica, 2× |
| `error.jpg` | Tangled_film_strip | kvadratni izrez |
| `empty-gallery.jpg` | Smartphone_screen_social_media_post | izrez 4:5 |
| `grain.png` | Analog_film_grain (_775b) | sivi tile 512 px, overlay 3,5 % |
| `og-base.jpg` | Social_preview_banner | 1200×630; naslov se dodaje kodom |
| `theme.css` | — | tokeni iz ove datoteke + chipovi, REC, zrnatost |

**Prilagodba dizajna:** generator je ilustracije praznih stanja napravio na svijetloj podlozi umjesto tamne. Ne regeneriramo ih, nego ih koristimo kao svijetle "kartice s ploče" na tamnom stolu (`.empty-card`). To se uklapa u filmsku metaforu (storyboard kartice) i ujedno odvaja ilustraciju od sučelja.
