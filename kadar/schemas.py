"""Pydantic sheme za strukturirani izlaz modela (faza 02).

Status svake tvrdnje je obavezan: PROVJERENO (ima izvor), PRETPOSTAVKA
(zaključak bez izravnog dokaza) ili NEDOSTUPNO (izvor nije bio dostupan).
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

Status = Literal["PROVJERENO", "PRETPOSTAVKA", "NEDOSTUPNO"]


# ---- klasifikacija slika proizvoda -------------------------------------------

class ImageRole(BaseModel):
    file: str = Field(description="naziv datoteke točno kao u oznaci slike")
    role: Literal["packshot", "promo_kompozicija", "lifestyle", "detalj_etikete", "ostalo"]
    background: Literal["bijela", "prozirna", "boja_brenda", "scena", "ostalo"]
    extra_items: List[str] = Field(description="predmeti na slici koji nisu sam proizvod (npr. poklon čarape)")
    visible_label_text: str = Field(description="tekst koji se jasno čita na etiketi, doslovno")
    usable_as_reference: bool = Field(description="smije li se koristiti kao referenca proizvoda za generiranje")
    reason: str


class ProductImages(BaseModel):
    images: List[ImageRole]
    best_reference: str = Field(description="datoteka najčišćeg packshota koji je usable_as_reference; prazno ako nijedna nije")
    packaging_description: str = Field(description="kratak opis pakiranja: oblik, boje, poklopac, raspored etikete")


# ---- tvrdnje o proizvodu --------------------------------------------------------

class Claim(BaseModel):
    text: str = Field(description="tvrdnja doslovno ili gotovo doslovno iz izvora, na hrvatskom")
    kind: Literal["nutritivna_vrijednost", "zdravstvena_tvrdnja", "sastav", "porijeklo_proizvodnja",
                  "upotreba", "upozorenje", "ocjena_kupaca", "ostalo"]
    source_field: str = Field(description="polje u product.json iz kojeg tvrdnja dolazi (npr. faq, properties.Energetska vrijednost)")
    exact_quote: str = Field(description="kratki doslovni citat iz izvora koji tvrdnju dokazuje")
    safe_for_post: bool = Field(description="smije li se koristiti u objavi bez dodatne pravne provjere")
    note: str = Field(description="npr. nedosljednost s drugim dijelom stranice, uvjeti uporabe, prazno ako nema")


class ProductClaims(BaseModel):
    product: str
    claims: List[Claim]
    inconsistencies: List[str] = Field(description="proturječja unutar izvora (npr. 22 g vs 22,5 g)")
    forbidden: List[str] = Field(description="što se ne smije tvrditi za ovaj proizvod, s razlogom")


# ---- analiza brenda ---------------------------------------------------------

class Finding(BaseModel):
    topic: Literal["ton", "publika", "teme", "stil", "boje", "prikaz_proizvoda", "prikaz_osoba",
                   "formati", "copy", "angažman"]
    statement: str
    status: Status
    evidence: List[str] = Field(description="ID-evi izvora (S1…) ili nazivi IG screenshotova; prazno ako NEDOSTUPNO")


class PaletteColor(BaseModel):
    hex: str
    role: str = Field(description="npr. primarna, pozadina, tekst, akcent")
    status: Status
    evidence: str


class Pillar(BaseModel):
    name: str
    description: str
    example_evidence: List[str]


class Voice(BaseModel):
    tone_words: List[str]
    address: Literal["ti", "vi", "mješovito", "nepoznato"]
    emoji_usage: str
    hashtags_seen: List[str]
    cta_patterns: List[str]
    do: List[str]
    dont: List[str]


class Visual(BaseModel):
    palette: List[PaletteColor]
    typography: str
    photo_style: str
    layout_patterns: List[str]
    product_presentation: str
    people_presentation: str


class Unavailable(BaseModel):
    source: str
    reason: str


class BrandAnalysis(BaseModel):
    summary: str
    audience: str
    findings: List[Finding]
    voice: Voice
    visual: Visual
    content_pillars: List[Pillar]
    opportunities: List[str] = Field(description="što brend radi rijetko, a moglo bi raditi bolje")
    unavailable_sources: List[Unavailable]


# ---- plan sadržaja (faza 03) ---------------------------------------------------
# Rasporedi odgovaraju HTML predlošcima u kadar/render/templates. Plan smije
# birati samo njih, pa svaki planirani slajd pipeline zna i izrenderirati.

Layout = Literal[
    "naslovnica",      # veliki naslov + opcionalno packshot (prvi slajd karusela / jedna slika)
    "cinjenica",       # velika brojka/podatak + kratko objašnjenje + izvor
    "savjet",          # numerirani savjet: naslov + tekst
    "mit_cinjenica",   # MIT vs ČINJENICA
    "proizvod",        # veliki packshot + 2–4 činjenice + naziv
    "poziv",           # završni slajd s pozivom na akciju (spremi, komentiraj, posjeti)
    "story_anketa",    # story: pitanje + 2 opcije (anketa)
    "story_kviz",      # story: pitanje + 3–4 opcije (kviz)
    "story_otkrivanje",  # story: odgovor/otkrivanje + proizvod
    "story_poveznica",   # story: poziv + oznaka poveznice na proizvod
]
Background = Literal["brand", "tamna", "svijetla", "bijela"]


class PlannedSlide(BaseModel):
    layout: Layout
    purpose: str = Field(description="što ovaj slajd postiže u nizu")
    kicker: str = Field(description="mali natpis iznad naslova, može biti prazan")
    headline: str = Field(description="naslov, kratko i udarno (najviše ~8 riječi)")
    body: str = Field(description="tekst slajda, najviše ~35 riječi; prazno ako nije potrebno")
    stat: str = Field(description="za 'cinjenica': brojka s jedinicom (npr. '22 g'); inače prazno")
    options: List[str] = Field(description="za ankete i kvizove: opcije; inače prazno")
    product: str = Field(description="naziv proizvoda ako se prikazuje packshot, inače prazno")
    background: Background
    claims_used: List[str] = Field(description="doslovni tekstovi tvrdnji s popisa dopuštenih koje slajd koristi")


class PlannedPost(BaseModel):
    number: int
    title: str
    goal: Literal["edukacija_spremanja", "predstavljanje_proizvoda", "interes_za_kupnju", "reakcije_komentari"]
    format: Literal["karusel", "slika", "story_niz"]
    product: str
    concept: str
    why_it_fits: str = Field(description="zašto pristup odgovara brendu, s pozivom na nalaze analize")
    evidence: List[str] = Field(description="ID-evi izvora ili oznake IG objava na koje se obrazloženje oslanja")
    kpi: str = Field(description="kako mjerimo uspjeh (npr. omjer spremanja/dosega)")
    slides: List[PlannedSlide]
    caption_brief: str = Field(description="o čemu govori opis objave i kojim tonom")
    cta: str
    hashtags: List[str]
    risks: List[str] = Field(description="rizici (tvrdnje, ton, točnost proizvoda) i kako ih izbjegavamo")


class RejectedIdea(BaseModel):
    idea: str
    reason: str


class ContentPlan(BaseModel):
    strategy_summary: str
    posts: List[PlannedPost]
    rejected_ideas: List[RejectedIdea]


# ---- završni tekstovi (faza 04) ----------------------------------------------
# Raspored, pozadina i proizvod preuzimaju se iz odobrenog plana (kod), a model
# smije mijenjati samo tekst — tako izrada ne može "odlutati" od plana.

class FinalSlide(BaseModel):
    kicker: str
    headline: str = Field(description="završni naslov; jednu ključnu riječ označi *zvjezdicama* (prikazuje se narančasto)")
    body: str = Field(description="najviše ~30 riječi; za raspored 'proizvod' stavke odvoji znakom •")
    stat: str
    options: List[str]
    footnote: str = Field(description="sitni obavezni tekst (upozorenja, izvor); prazno ako ne treba")


class FinalPost(BaseModel):
    number: int
    caption: str = Field(description="cijeli opis objave s hashtagovima na kraju; za story niz kratka napomena za objavu")
    alt_text: str = Field(description="alternativni tekst za pristupačnost, 1–2 rečenice")
    slides: List[FinalSlide]


class FinalCopy(BaseModel):
    posts: List[FinalPost]
    editor_notes: List[str] = Field(description="što je urednik promijenio u odnosu na plan i zašto")


# ---- provjera (faza 05) -------------------------------------------------------

VisionCheck = Literal["proizvod_tocan", "logo_tocan", "citljivost", "hijerarhija", "jezik_pravopis",
                      "prirodnost_hr", "ton_brenda", "vizualni_identitet", "tvrdnje_dopustene", "cta_jasan"]


class VisionFinding(BaseModel):
    check: VisionCheck
    status: Literal["pass", "warn", "fail"]
    slide: int = Field(description="broj slajda na koji se nalaz odnosi; 0 ako se odnosi na cijelu objavu")
    detail: str


class LanguageFix(BaseModel):
    slide: int = Field(description="broj slajda; 0 za opis objave")
    original: str
    suggestion: str
    reason: str


class VisionReview(BaseModel):
    findings: List[VisionFinding] = Field(description="točno jedan nalaz za svaku od 10 provjera")
    language_fixes: List[LanguageFix]
    overall: str
