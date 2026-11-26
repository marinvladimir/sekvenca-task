# Ljudske dorade AI prijedloga

Evidencija svake ljudske odluke koja je promijenila ili nadjačala AI prijedlog (za PDF: "primjer vlastite dorade").

| # | Kadar | AI prijedlog | Ljudska odluka | Zašto |
|---|---|---|---|---|
| 1 | 02 analiza | Primarna boja brenda #DE7419 (izmjereno iz IG screenshotova) | #FF4500 (`inputs/brand/brand.json`) | Fotografije prigušuju boju; službena narančasta je u logu i na webshopu |
| 2 | 02 analiza | Brend u opisima koristi "vi"; brif traži "ti" (sukob) | Dosljedno "ti" (`inputs/plan_notes_gymbeam-hr.md`) | Edukacija za početnike je osobnija; brend "ti" već koristi na grafikama |
| 3 | 01 brif | Ručni index.csv: objava 04 = "MoiMüv pločica" | Analiza ispravila u "GymBeam 20g Protein Bar" | Primjer obrnute provjere: AI je uhvatio ljudsku grešku čitajući pakiranje |
| 4 | 03 plan | "pošalji **frendu**" (CTA objave 1 i slajd 7) | "pošalji **prijatelju**" | "Frend" nije uobičajen u lokalnom govoru publike; "prijatelj" je prirodniji |
| 5 | 03 plan | "Tek ulaziš u **svijet proteina**?" (opis objave 1) | "Tek ulaziš u **svijet gyma**?" | "Svijet proteina" zvuči neprirodno; publika se poistovjećuje s teretanom, ne s dodatkom |
| 6 | 04 izrada | Naslovi u Antonu s line-height .98 i velikim početnim veličinama | Veći razmak redova (1.08), manje maks. veličine naslova i brojki | Čovjek je pri pregledu uočio da se veliki naslovi preklapaju s redom ispod (kvačice Č/Š/Ž, brojka iznad naslova) |
| 7 | aplikacija | Generičko tamno sučelje; asseti vidljivi samo u praznim stanjima | Redizajn: hero s filmskom trakom, traka kadrova kao film s ilustracijama, ilustracija uz kadar | Čovjek: "izgleda kao AI slop, nije korišten moj dizajn" |
| 8 | 05 provjera | Provjera bez testa | Zahtjev za temeljitim testom (~50 rezultata) i analizom → 143 provjere u 2 kruga | Čovjek je tražio mjerljiv QA, ne samo vizualni dojam |
| 9 | 05 provjera | AI provjera: "uskladiti narančastu s #DE7419" | Odbačeno: zadržano #FF4500 (ljudska odluka #1); provjera sad dobiva ljudske odluke kao kontekst | Provjera ne smije poništavati svjesne ljudske odluke |
