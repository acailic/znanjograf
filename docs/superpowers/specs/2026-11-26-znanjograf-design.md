# Znanjograf — specifikacija dizajna

**Datum:** 2026-11-26 · **Status:** dizajn odobren u razgovoru; ovo je upisani oblik · **Licenca:** kod MIT, podaci CC BY 4.0

## 1. Svrha i merilo uspeha

Znanjograf je otvoreni skup podataka i statičan sajt koji za matematiku osnovne škole u Republici Srbiji (1–8. razred) daje tri stvari:

1. **graf znanja** — teme i veze prethodnih uslova („ovo treba da znaš pre onoga“);
2. **banku proverenih zadataka** po temama;
3. **dijagnostiku** — od izabrane teme odlazi unazad dok ne nađe najverovatnije mesto gde je znanje puklo, pa ispiše put popravke po razredima.

**Merilo uspeha.** Roditelj ili nastavnik za deset minuta sazna u kom razredu dete ima rupu. Programer preuzme podatke u JSON-u na ćirilici i latinici. Svaki broj u README-u generiše alat; nijedan se ne kuca ručno.

**Podstrek.** Zamišljeno po uzoru na `xiaoyang111222/cn-math-taxonomy` (CC BY-NC 4.0, zatvoren sajt). Znanjograf je nezavisna implementacija: ne kopira njegove podatke, kod ni tekst. README navodi zahvalnicu za ideju, bez tvrdnje o bilo kakvoj povezanosti.

## 2. Fiksne odluke

| Tema | Odluka |
|---|---|
| Licenca | kod MIT; podaci (`data/`) CC BY 4.0 |
| Obim prve isporuke | matematika, 1–8. razred osnovne škole |
| Pisma | latinica je izvor istine; ćirilica se generiše. Oba su prvorazredna na sajtu, s prekidačem |
| Sajt | statičan, GitHub Pages, bez frejmvorka; izgradnja samo Python alatom |
| Privatnost | bez naloga, bez analitike, bez backenda; odgovori deteta ne napuštaju pregledač |
| Zavisnosti | Python standardna biblioteka; Node ugrađen test runner; KaTeX serviran lokalno; nijedan CDN |
| Imenovanje | identifikatori (fajlovi, ključeve, komande, kod) na engleskom; sav sadržaj i UI na srpskom |
| Repo | `ZCodeProject/znanjograf`; javni `acailic/znanjograf` kad temelji prođu |

## 3. Utvrđene činjenice o nastavnom programu

Izvor: `ZCodeProject/research/sr-math-curriculum/` (izveštaji agenata koji su čitali primarne PDF-ove i HTML tekstove, 2026-11-26).

1. **U školskoj 2026/27. svih osam razreda radi po programima donetim 2017–2019. s kasnijim dopunama.** Prosvetni glasnik 1/2026 od 26.2.2026 (tačke 5, 6 i 7: novi programi za 1. i 5. razred, novi plan za 7–8) primenjuje se od školske 2027/2028. po svom članu 2. Reč „pilot“ ne postoji ni u jednom od tih akata.
2. **Programi su zasebni pravilnici po razredu, a plan (fond časova) je pravilnik po ciklusu.** Prvi ciklus obuhvata 1–4. razred.
3. **Formati se razlikuju po generaciji programa.** Program za 1. razred (2017) ima „ISHODI — po završetku razreda učenik će biti u stanju da…“ kao nebrojanu listu, zatim oblasti, teme i sadržaje, ključne pojmove i uputstvo s predloženim fondom časova po temama. Program za 5. razred (2018) ima pet tema s fondom časova i 39 nerazvrstanih ishoda. Program za 7. razred (2019) ide tabelom „predmetni ishodi za kraj šestog razreda | oblasti i/ili teme | predmetni sadržaji“.
4. **Novi format** (od 2027/28, za 1. i 5. razred) donosi kodirane ishode po nivoima (`МАТ.А.ОО.О.1.1.`, tj. основни / средњи / напредни) u tri oblasti: brojevi i algebra, geometrija i merenje, obrada podataka i slučajnost.
5. **Službeni tekstovi su čitljivi:** API Pravno-informacionog sistema (`slgl.pravno-informacioni-sistem.rs/api/Prins/viewDoc?actId=…`), preuzimanja ZUOV-a (`zuov.gov.rs`) i ogledalo Paragrafa (`demo.paragraf.rs`).
6. **Tekstovi ishoda se čuvaju kao parafraza.** Sajt ZUOV-a, s koga se preuzimaju tekstovi pravilnika, objavljuje sadržaj pod Creative Commons Autorstvo-Nekomercijalno-Bez prerada 3.0 Srbija (CC BY-NC-ND 3.0 RS; https://zuov.gov.rs/uslovi-koriscenja-licenca/), a nije potvrđeno da Zakon o autorskom i srodnim pravima izuzima same akte. Zato `data/` sadrži parafrazu svakog ishoda (isto značenje, sopstvene reči) uz pokazivač na akt i štampanu stranu; bukvalan tekst ne ulazi u repozitorijum, a PDF-ovi se ne distribuiraju. `sources.json` beleži odluku i dokaz. Drugi agent poredi svaku parafrazu s izvornikom po značenju.

**Posledice za dizajn.** Prvih osam izdanja gradi se po važećim programima. Fond časova matematike: 1–4. razred 5 nedeljno / 180 godišnje; 5. i 6. 4 / 144; 7. 4 / 144; 8. 4 / 136 (isti i u novim planovima od 2027/28). Za 1. i 5. razred beleži se i izdanje 2027/28 (ishodi i teme), a teme se mapiraju na oba, da skup ne zastari za godinu dana. Tri oblasti novog formata jesu zajednička podela za sve razrede.

## 4. Raspored repozitorijuma

```
README.md  README.cir.md (generisan)  README.en.md  CHANGELOG.md  CONTRIBUTING.md  AGENTS.md
LICENSE (MIT)  LICENSE-DATA (CC BY 4.0)
docs/
  autorski-vodic.md        kako se pišu teme, grane i zadaci
  format-podataka.md       referenca šeme
  program.md               poreklo programa, izdanja, pokrivenost
  dijagnostika.md          algoritam i pravila presude
  poznata-ogranicenja.md   šta nije provereno i zašto
  superpowers/specs|plans/ procesni dokumenti
data/
  math/meta.json           predmet: oznaka, razredi, oblasti
  math/g1 … g8/            topics.json  edges.json  questions.json
  curriculum/sources.json  akti, brojevi glasnika, URL, pravilo teksta, dokaz
  curriculum/math/gN-YYYY.json   ishodi i teme po izdanju
  curriculum/unmapped.json ishodi bez teme, s razlogom
  registry.json            svaki id teme ikad objavljen (samo se dodaje)
  aliases.json             stari id → današnji id
  review/teachers.json     ljudski pregledi po temi
  lint/notation.json  lint/digraphs.json
zg/                        Python paket (§7)
site/                      izvor sajta (§12)
tests/                     Python i Node testovi, fixtures/
.github/workflows/ci.yml   ISSUE_TEMPLATE/
```

Izgrađeni sajt ide u `_site/` (ne verzionira se). Istražni izvodi i PDF-ovi ostaju van repozitorijuma.

## 5. Šema podataka

### 5.1 Tema (`topics.json`)

```json
{
  "id": "mat-sabiranje-do-20",
  "grade": 1,
  "area": "numbers",
  "unit": "Brojevi",
  "kind": "procedure",
  "name": "Sabiranje do 20",
  "summary": "…",
  "mastery": ["…", "…"],
  "curriculum": [
    {"edition": "g1-2026", "outcome": "g1-2026-012", "match": "exact"}
  ]
}
```

- `id` je nepromenljiv slug `^mat-[a-z0-9]+(-[a-z0-9]+)*$`, do 48 znakova, bez razreda u imenu. Premestanje teme u drugi razred ne menja id.
- `area` ∈ `numbers` (brojevi i algebra), `geometry` (geometrija i merenje), `data` (obrada podataka i slučajnost).
- `unit` je tema programa onako kako se zove u važećem izdanju.
- `kind` ∈ `concept`, `procedure`, `problem`, `reasoning`.
- `mastery` ima 2–3 uočljiva kriterijuma („Učenik može da…“).
- `curriculum` navodi bar jedan ishod; `match` ∈ `exact`, `partial`.
- `root_reason` (tekst) postoji samo ako tema nema nijednu granu.
- Redosled tema u fajlu je redosled iz programa; motor ga koristi kao redosled učenja unutar razreda.

**Pravilo zrnatosti.** Jedna tema je najmanje znanje koje dete može samo da savlada ili samo da promaši, veličine jezgra jednog časa. Novi postupak (prelaz preko desetice, pisano deljenje) je nova tema. Proširenje istog postupka na veće brojeve je nova tema samo ako program za njega ima poseban ishod; inače su veći brojevi nivoi zadataka.

### 5.2 Grana (`edges.json`, po razredu zavisne teme)

```json
{"topic": "mat-…", "requires": "mat-…", "strength": "hard", "reason": "…"}
```

`hard` znači da se bez prethodne teme ne može uraditi nijedan zadatak ove teme; `soft` da pomaže, a nije uslov. Važi `razred(requires) ≤ razred(topic)`. Alat odbacuje suvišne grane (čvrstu ako postoji drugi put od isključivo čvrstih grana; meku ako postoji bilo koji drugi put), pa se graf ne skraćuje ručno.

### 5.3 Ishod (`curriculum/math/gN-YYYY.json`)

```json
{
  "edition": "g1-2027",
  "grade": 1,
  "applies_from": "2027/28",
  "themes": [{"name": "…", "area": "numbers", "hours": 27, "content": ["…"], "page": 14}],
  "outcomes": [
    {"id": "g1-2027-012", "text": "…", "page": 15, "code": "МАТ.А.ОО.О.1.1", "level": "basic", "area": "numbers", "unit": "…"}
  ]
}
```

- Izdanje `gN-YYYY` znači „program koji važi u školskoj YYYY/(YYYY+1)“. `gN-2026` važi sada; `g1-2027` i `g5-2027` važe od 2027/28.
- `code`, `level`, `area`, `unit` su opcioni tamo gde dokument ih nema. `level` ∈ `basic`, `medium`, `advanced`.
- `page` je štampana stranica u izvoru.

### 5.4 Zadatak (`questions.json`)

```json
{
  "id": "mat-sabiranje-do-20-q1",
  "topic": "mat-sabiranje-do-20",
  "level": "standard",
  "type": "numeric",
  "prompt": "Mila ima $8$ kuvanica i kupi još $7$. Koliko kuvanica sada ima?",
  "answer": "15",
  "check": "(+ 8 7)",
  "explanation": "…"
}
```

- `id` je `<id teme>-q<n>`, uzastopno od 1.
- `level` ∈ `basic` (direktna primena), `standard`. Prvi standardni zadatak je direktan; drugi je višekorak ili prenos.
- `type` ∈ `numeric` (upis broja), `choice` (jedan tačan od 3–4).
- Za `choice`: `"choices": [{"id": "a", "text": "…"}, …]`, `answer` je id tačne ponude (ne uvek isti), a opciono `"points_to": {"b": "mat-…"}` za svaku pogrešnu ponudu koja ukazuje na nedostajućeg čvrstog pretka.
- Za `numeric`: `answer` je kanonski broj (tačka kao decimalni separator u podatku, razlomak `3/4`, mešovit `2 3/4`, predznak `-`); `"round_to": 2` je obavezno kad je tačan odgovor iracionalan.
- `figure` je opciona deklarativna slika (§12.3).
- `explanation` je uvek prisutno, jednostavnim jezikom razreda, i pokazuje se tek kad se tema završi.

**Banka.** Svaka tema ima najmanje 2 osnovna i 2 standardna zadatka. Procena za osam razreda: oko 480 tema, 1.000 grana, 1.900 zadataka.

### 5.5 Ostalo

- `aliases.json`: `{"stari-id": ["današnji-id", …]}`; bez lanaca.
- `review/teachers.json`: `{"mat-…": {"name": "…", "role": "…", "date": "YYYY-MM-DD", "note": "…"}}`.
- `lint/notation.json`: pravilo notacije po razredu; svako pravilo navodi ishod koji notaciju uvodi.
- `lint/digraphs.json`: klasifikacija svake reči s `lj`, `nj` ili `dž` (digraf ili granica morfeme).

## 6. Konvencije teksta

### 6.1 Matematika

- Formula ide u `$…$` kao LaTeX podskup koji KaTeX 0.19.1 podržava. Decimalni zarez u formuli piše se `{,}`. Množenje je `\cdot`, deljenje `:`, procenat `15\,\%`.
- `\text{…}` je dozvoljen samo za jedinice. Varijable su latinična kurzivna slova u oba pisma.
- CI parsira svaku formulu kopijom KaTeX-a iz repozitorijuma; pokvarena formula ruši build. U pregledaču greška pada na sirov LaTeX, nikad na prazno.

### 6.2 Brojevi i jedinice u tekstu

Decimalni zarez. Razmak kao separator hiljada (`1 000 000`). Razmak ispred `%` (`15 %`). Jedinice latiničkim slovima u oba pisma (`5 cm`, `3 kg`, `60 km/h`). Novac rečima (`150 dinara`).

### 6.3 Ćirilica

- Transliteracija je deterministička i povratna (latinica → ćirilica → latinica daje izvornik).
- Zaštićeni segmenti koje transliteracija ne dira: `$…$`, oznake jedinica, URL-ovi, kod, HTML oznake.
- Reč s `lj`, `nj` ili `dž` koja nije u `lint/digraphs.json` blokira validaciju dok se ne klasifikuje.
- Zabranjena je reč bez dijakritika koja odgovara reči s dijakritikom iz korpusa (`mnozenje` uz postojeće `množenje`).
- Zlatni korpus od najmanje 300 proverenih parova rečenica je test transliteracije.
- Pretraga na sajtu radi preko ključa bez dijakritika i pisma.
- Sve niske interfejsa, naslovi, opisi slika i README na ćirilici nastaju istom transliteracijom.

### 6.4 Jezik zadataka

Kratke rečenice. Naredbe u drugom licu jednine („Izračunaj.“, „Zaokruži.“). Bez termina iz viših razreda. Dužina teksta zadatka je najviše 200 znakova u 1–2. razredu, 300 u 3–4. i 400 u 5–8.

## 7. Alat `zg`

`python3 -m zg <komanda>` iz korena repozitorijuma. Samo standardna biblioteka.

| Modul | Odgovornost |
|---|---|
| `__main__.py` | argumenti i komande |
| `paths.py` | koren, putanje razreda, izvor i izlaz sajta |
| `jsonio.py` | učitavanje s odbijanjem duplikiranih ključeva, kanonski upis, `sha256` |
| `corpus.py` | učitavanje predmeta: `resolve(id)`, `ancestors(id)`, `descendants(id)`, `topo_rank()`, `bank(topic)` |
| `checks/schema.py` | polja po vrsti zapisa; nepoznato polje je greška |
| `checks/graph.py` | ciklusi, koreni, monotonost razreda, suvišne grane, izolovane teme |
| `checks/coverage.py` | tema ↔ ishod u oba smera |
| `checks/bank.py` | pravila banke, ponude, `points_to` |
| `checks/figure.py` | šema slike i geometrijska doslednost |
| `dsl.py` | parser izraza provere (§8) |
| `mathcheck.py` | tačno računanje i poređenje odgovora |
| `translit/protect.py`, `translit/rules.py` | zaštićeni segmenti; `to_cyrillic`, `to_latin`, `fold`, `collation_key` |
| `lint/notation.py`, `lint/text.py` | notacija po razredu; pravopis, dijakritike, dužina |
| `blind.py` | `make_sheet`, `diff` |
| `ledger.py` | heš sadržaja, prolaz kroz kapiju, zastarelost |
| `build.py` | izlaz sajta u oba pisma; `check_site` |
| `report.py` | statistika, blok za README, `status` |
| `review.py` | list za štampu po razredu; unos ljudskog pregleda |

Komande: `validate`, `verify`, `lint`, `blind sheet|diff`, `ledger`, `build [--check]`, `serve`, `report [--check]`, `review sheet|apply`, `status`, `all`. `all` pokreće sve kapije i jedina je komanda koju pokreće CI. Svaka komanda završava s kodom 1 i porukom `putanja: šta: zašto` za svaku grešku. Ni u jednom modulu nema `eval`.

## 8. Provera odgovora

`check` je S-izraz koji `dsl.py` parsira rekurzivnim spuštanjem s ograničenjem dubine i veličine, a `mathcheck.py` računa u `fractions.Fraction`.

- Atom: ceo broj (`-3`), decimalni zapis u izrazu tačan kao razlomak (`2.5`), `pi`.
- Operatori: `+ - * /` (n-arni), `pow`, `sqrt`, `abs`, `min`, `max`, `floor`, `ceil`, `round`, `mean`, `median`, `mode`, `gcd`, `lcm`, `mod`, `percent` (`(percent 15 200)` = 15 % od 200).
- `sqrt` nad iracionalnim rezultatom vraća broj s 50 cifara; odgovor se poredi zaokružen na `round_to`.

`verify` traži da izračunata vrednost bude jednaka `answer`. Za `choice` tekst tačne ponude daje istu vrednost, a tekst svake pogrešne ponude različitu. Autor piše i `answer` i `check`, pa grešna zamisao prolazi `verify`; zato slepi prolaz (§9) donosi svoj račun.

## 9. Kako sadržaj nastaje i kako se proverava

Sadržaj pišu agenti po `docs/autorski-vodic.md`. Svaka kapija je komanda. Pad bilo koje kapije znači da zadatak ili tema ostaju „neprovereni“.

1. **`validate`** — pravila V1–V11:
   - V1 JSON je valjan, bez duplikiranih ključeva.
   - V2 Nema nepoznatih polja; obavezna polja i tipovi su ispunjeni.
   - V3 Id-jevi odgovaraju šemi, jedinstveni su i upisani u `registry.json`.
   - V4 Razred je 1–8; `area`, `kind`, `level`, `type`, `strength` su iz dozvoljenih skupova.
   - V5 Grane: krajevi postoje; nema petlje, duplikata ni para u oba smera; razred prethodne nije veći; suvišna grana je greška.
   - V6 Graf je acikličan; tema bez grane ima `root_reason`; nema izolovanih tema.
   - V7 Pokrivenost u oba smera; ishod bez teme mora biti u `unmapped.json` s razlogom.
   - V8 Banka: 2 osnovna i 2 standardna; 3–4 ponude, jedan tačan id, ponude različite; `points_to` pokazuje na čvrstog pretka.
   - V9 Slika: vrsta iz zatvorenog skupa, `alt` od 20 znakova, geometrijska doslednost.
   - V10 Svaka formula parsira KaTeX.
   - V11 Aliasi bez lanaca, s ciljem koji postoji.
2. **`verify`** — odgovor je jednak računu iz `check`.
3. **`lint`** — L1 notacija po razredu s pozivom na ishod; L2 reči bez dijakritika; L3 rečnik digrafa; L4 pravopis i jedinice; L5 dužina teksta; L6 skoro-duplikati naziva tema; L7 mešana pisma u ćiriličnom izlazu.
4. **Protivnički pregled grana** — nezavisnom agentu se za svaku čvrstu granu A → B postavlja pitanje: „Može li učenik koji nije savladao B, a zna sve ostale prethodne teme, da reši oba standardna zadatka teme A?“ Ako može, grana postaje meka ili se briše. Isti agent, s spiskom tema nižih razreda, navodi očiglednog pretka koji A nema. Grana je prošla kad nezavisni pregledač potvrdi.
5. **Slepi prolaz na ćirilici** — `blind sheet` daje nezavisnom agentu samo tekstove ćirilicom. Za svaki zadatak on vraća: odgovor; svoj `check`; `unique` (da li je tačno jedan odgovor branjiv); `assumptions` (sve što je morao da pretpostavi); ocenu 0–3 branjivosti svake pogrešne ponude. `blind diff` pada ako se odgovor ili račun razlikuju, ako `unique` nije tačno, ako `assumptions` nije prazno ili ako je neka pogrešna ponuda ocenjena 2 ili 3. Nema adjudikacije: suma znači prepravku.
6. **Slepi klasifikator** — vidi samo tekst i ponude, bez etiketa, i imenuje temu, nivo i najniži razred koji razume rečnik. Pad ako označena tema nije tema zadatka, ako se nivo ne slaže ili ako je najniži razred viši od razreda teme.
7. **Test ponuda** — agent vidi samo ponude i pogađa tačnu. Ako je uspeh iznad slučaja (binomni test, `p < 0.05`), ponude odaju odgovor.
8. **`ledger`** — heš svakog zadatka i svake grane po kapiji. Izmena posle prolaza vraća zapis na „neproveren“; `all` pada na bilo čemu zastarelom.
9. **Ljudski pregled** — `review/teachers.json` napaja oznaku „Pregledao nastavnik“ po temi na sajtu. `review sheet` pravi stranicu za štampu po razredu. Svaka tema ima „Prijavi grešku“ s popunjenom oznakom.

## 10. Dijagnostički motor

Motor je skup čistih funkcija bez DOM-a, zajednički pregledaču i Node testovima.

### 10.1 Pojmovi

- **Dnevnik** je niz događaja `{q, correct}` redom kako su se desili. Stanje sesije je preklop (fold) nad dnevnikom; ne čuva se ništa osim dnevnika, opsega i verzija.
- **Redosled učenja** je topološki: razred rastuće, unutar razreda redosled iz `topics.json`.
- **Čvrsti preci** teme su svi predci preko `hard` grana.
- **Izlazne teme** razreda su teme koje nijedna druga tema istog razreda ne zahteva, ni čvrstom ni mekom granom.
- **Jak odgovor** je tačan upis broja čija vrednost nije ceo broj između −10 i 10, jer se ne može pogoditi.
- Stanja teme: `untested`, `mastered`, `shaky`, `weak`, `inferred`.

### 10.2 Presuda za jednu temu (1–2 pitanja)

1. Postavi prvi standardni zadatak. **Pogrešan** → postavi osnovni: pogrešan je `weak`, tačan je `shaky`.
2. **Tačan jak odgovor** → `mastered` odmah.
3. **Tačan odgovor koji nije jak** → postavi drugi standardni: tačan je `mastered`, pogrešan je `shaky`.

„Ne znam“ je pogrešan odgovor bez posebne posledice. Ponude se mešaju pri prikazu. Objašnjenje zadatka pokazuje se tek kad je tema presuđena.

### 10.3 Obilazak

1. Opseg je `topic` (jedna tema), `unit` (sve teme jednog razreda s istom vrednošću `unit`), `grade` (samo izlazne teme razreda) ili `grade-full` (sve teme razreda). Teme iz opsega obilaze se od najteže, suprotno od redosleda učenja; tema koja već ima stanje se preskače.
2. Kad tema postane `mastered`, svi njeni čvrsti preci bez stanja postaju `inferred` (na ekranu „nije direktno provereno“).
3. Kad tema postane `weak`, ulazi u red za obradu. Za svaku `weak` temu u redu pregledaju se njeni čvrsti pretci od najbližeg; svaki bez stanja se presuđuje, a svaki novi `weak` ulazi u red. Ako nijedan čvrsti predak nije `weak`, isto se radi s mekim pretcima.
4. Plafon je 25 pitanja po bloku. Kad se dosegne, sesija nudi „Nastavi“ ili „Vidi rezultat“.

### 10.4 Koreni i put

- **Koren** je `weak` tema kojoj nijedan čvrsti predak nije `weak`. Koren je `confirmed` samo ako su svi njegovi čvrsti pretci presuđeni ili izvedeni; inače je `confirmed: false`.
- **Put popravke** za koren je spisak svih `weak` tema na putevima od korena do cilja, bez ponavljanja, sortiran po razredima rastuće, s `shaky` temama na tim putevima kao koracima za učvršćivanje.
- Rezultat sadrži: korene („najverovatnije ovde je puklo“, s oznakama promašenih zadataka), put popravke, `shaky` teme, broj direktno proverenih i izvedenih, neproverene teme ako je sesija prekinuta, i ishode vezane za korene i put.

### 10.5 Nastavak, deljenje, čuvanje

- Nastavak je ponovno preslikavanje dnevnika. Događaj čije pitanje više ne postoji, ili ne odgovara temi i nivou koje motor traži, odbacuje se od tog mesta; sve pre toga ostaje.
- Deljenje rezultata ide u `#` fragment adrese, nikad u upit koji odlazi u logove servera. Sadržaj je verzionisan i nosi samo opseg i dnevnik.
- LocalStorage ključevi: `zg.session.v1`, `zg.history.v1` (rotacija zadataka), `zg.prefs.v1`. `setItem` je obavijen u `try/catch` (Safari privatni režim). `storage` događaj iz drugog jezička ponovo učitava sesiju. Postoji vidljivo „Obriši istoriju“.
- Izbor zadatka: prvi nekorišćen traženog nivoa; za ponovni test najduže nekorišćen iz istorije.

## 11. Testovi i CI

- **Python `unittest`:** parser i račun (tačni razlomci, iracionalni slučajevi, granice dubine), parser odgovora, transliteracija (zlatni korpus, digrafi, zaštićeni segmenti, povratnost), svako pravilo V i L na namerno pokvarenom primeru s tačnom porukom, izlaz građenja.
- **Node `node --test`:** motor na simuliranom učeniku koji zna sve, ne zna ništa i ne zna tačno jedan skup (motor mora vratiti očekivane korene); stopa lažnog savladavanja; dužina sesije; nastavak i deljenje; računanje odgovora; `figure.js` i `layout.js` kao čiste funkcije; KaTeX parsira svaku formulu iz izgrađenih paketa.
- **Krajem projekta:** jedan automatizovan prolaz kroz sajt u pravom pregledaču na oba pisma (početna → dijagnostika skriptovanog učenika → rezultat).

CI na svaki push i `pull_request` za `main`: `python3 -m zg all`, `node --test`, izgradnja sajta i `build --check`. Issue šabloni: „Greška u zadatku“, „Greška u temi ili grani“, „Predlog“.

## 12. Sajt

### 12.1 Stranice

`/` (početna), `/mapa/`, `/dijagnostika/`, `/o-projektu/` (izvori, licenca, ograničenja, privatnost) i `/pregled/gN.html` (list za štampu za nastavnike, generisan). Svi parametri idu u `#` fragment: `mapa/#mat-…`, `dijagnostika/#mat-…`, `dijagnostika/#razred=5`, `dijagnostika/#rezultat=…`, uz `pismo=cir|lat`.

### 12.2 Moduli (`site/js`)

| Modul | Izvozi |
|---|---|
| `engine/graph.js` | `buildIndex(topics, edges)` → `prereqsOf`, `hardAncestorsOf`, `topoRank`, `gradeExits` |
| `engine/verdict.js` | `verdictOf(evidence)` |
| `engine/session.js` | `create(scope, index, budget)`, `next(state)`, `apply(state, event)`, `reduce(log)` |
| `engine/result.js` | `summarise(state)` |
| `engine/answer.js` | `parseNumeric(text)`, `isCorrect(question, response)` |
| `engine/encode.js` | `encodeSession(events)`, `decodeSession(text)` |
| `figure.js` | `renderFigure(spec)` → SVG niska |
| `layout.js` | `layout(subgraph)` → položaji i veličina |
| `katex.js` | `renderInto(el, tex)` |
| `data.js` | `loadIndex()`, `loadGrades([...])`, `resolveAlias` |
| `graph-view.js` | `toSvg(layout, verdicts)`, `mount(el, onSelect)` |
| `storage.js` | čuvanje i čitanje sesije, istorije i podešavanja; `clearAll` |
| `common.js` | prekidač pisma, duboke veze, navigacija |
| `ui/question.js`, `ui/progress.js`, `ui/result.js` | prikaz jedinica interfejsa |
| `pages/home.js`, `pages/map.js`, `pages/diagnose.js`, `pages/about.js` | stranice |

### 12.3 Slike, graf, formule, pisma

- **Slike:** zatvoren skup vrsta `numberline`, `fractionbar`, `pie`, `dots`, `bars`, `pictogram`, `grid`, `polygon`, `angle`, `axes`, `clock`, `table`. Obavezan `alt`. Samo opis mora biti dovoljan za rešavanje. Geometrijska tela, konstrukcije i transformacije u prvoj isporoci nemaju slike.
- **Graf:** ručni SVG. `x` je sloj po najdužem lokalnom putu (+1 po grani). `y` je pojas razreda s onoliko redova koliko najšira ćelija pojasa traži, do osam redova, s viškom prikazanim kao „+N“. Mapa crta jedan nivo i širi se na klik; iznad 60 čvorova prikazuje samo spisak. Čvrste grane su pune, meke isprekidane.
- **Formule:** KaTeX 0.19.1 (MIT) u `site/vendor/katex/`. `throwOnError: true` u omotaču. MathML izlaz za čitače ekrana. Tri najčešća fonta predučitana. Licenca fontova uz paket.
- **Pisma:** `zg build` emituje latinično stablo i `cir/` ogledalo s paketima po razredu za svako pismo. Prekidač pamti izbor i prenosi ga u veze.

## 13. Postupak rada s agentima

- **Jedan fajl, jedan vlasnik.** Kad više agenata radi paralelno, svaki piše samo svoje fajlove. Zajedničke tačke spajanja (komande, indeks testova) povezuje koordinator.
- **Po fazama, s komitom posle svake.** Granice su u §14. Agent nikad ne dobija putanju referentnog repozitorijuma.
- **Katalozi tema u redosledu razreda**, prvo najniži. Agent za razred N vidi spisak tema nižih razreda (id, naziv, opis), da se jedna zamisao ne pojavi pod dva id-ja.
- **Zadaci u paketima** od 40–60, kroz komandu za unos koja pre upisa pokreće `validate` i `verify`.
- **Napredak je u repozitorijumu** (`ledger`, `zg status`), ne u kontekstu agenta. Jedan zadatak, jedna komanda, jedan komit.
- **Paralelno:** osam agenata po razredu i koordinacija. Pitanja za razred N mogu da se pišu dok se piše katalog razreda N+1.

## 14. Faze i kriterijumi „gotovo“

| Faza | Sadržaj | Gotovo kad |
|---|---|---|
| 0 | Repo, licence, `zg`, CI, šablon sajta | `python3 -m zg all` i `node --test` prolaze na oglednim primerima; CI zelen; Pages otvara stranicu |
| 1 | Ishodi za 1. razred | Svaka stranica matematičkog odeljka je parafrazirana ili označena da nema ishod; drugi agent uporedio parafrazu sa značenjem izvora; `sources.json` navodi dokaz za parafrazu |
| 2 | Prvi razred od kraja do kraja | Teme, grane, zadaci i sajt rade na oba pisma; motor na simuliranom učeniku vraća tačne korene; svaka kapija iz §9 zelena za 1. razred |
| 3 | Ishodi za razrede 2–8 | Isto što i faza 1, za svih sedam razreda |
| 4 | Mapa tema za razrede 2–8 | Nema skoro-duplikata; svaka tema mapirana na ishod; `validate` čist |
| 5 | Grane za razrede 2–8 | Svaka čvrsta grana prošla protivnički pregled; nema očiglednog nedostajućeg pretka |
| 6 | Zadaci za razrede 2–8 | Sve kapije iz §9 zelene za svih osam razreda |
| 7 | Sajt kompletan | Sve stranice, graf, slike, prekidač pisma, deljenje, štampa; provera na telefonu |
| 8 | Izdanje | README s generisanim brojevima; Pages uživo; arhiva oba pisma u `releases` |

Unutar razreda redosled je teme → grane → zadaci → slepi prolaz, s komitom posle svakog koraka. Izdanje 2027/28 za 1. i 5. razred upisuje se u fazama 1, 3 i 4 (ishodi i mapa), bez novih zadataka.

## 15. Namerno nije urađeno

Lekcije i vežbe. Nalozi, sinhronizacija i pregledi za nastavnike na mreži. Mobilna aplikacija. Gimnazija i drugi predmeti. Zadaci „naprednog“ nivoa. Slike geometrijskih tela, konstrukcija i transformacija. Service worker i rad bez interneta. Izvoz u CSV ili grafovske baze. Više jezika od srpskog. Analitika i A/B pokusi. Ocena ili sertifikat na kraju. Renderovanje formula na serveru. Pretraga po sadržaju zadataka. Backend bilo koje vrste.

## 16. Poznata ograničenja (stajaće na sajtu)

- Sadržaj pišu AI modeli bez nastavnika, dok ga neki nastavnik ne pregleda.
- „Slepi“ rešavač je ista porodica modela, pa slepoća nije potpuna.
- Nema kalibracije na stvarnoj deci; težina zadataka i jačina grana su pedagoške procene.
- Rezultat dijagnostike je trag, ne ocena.
- Sadržaj prati programe koji važe u 2026/27; za 1. i 5. razred postoji i izdanje 2027/28.
- Znanjograf nije zvaničan ni povezan sa Ministarstvom prosvete.

## 17. Rizici

| Rizik | Odgovor |
|---|---|
| Limit potrošnje obara agente usred posla | Komit posle svake faze; napredak u `ledger`-u; agenti pišu na disk kako napreduju |
| Jedna zamisao pod dva id-ja | Katalozi po redosledu razreda; lint skoro-duplikata |
| Zadatak meri pogrešnu stvar, a odgovor je tačan | Slepi klasifikator |
| Dvosmislen tekst dođe do deteta | Kapija sumnje u slepom prolazu, bez adjudikacije |
| Ćirilica sa greškom koju niko ne vidi | Rečnik digrafa; zlatni korpus; slepi prolaz na ćirilici |
| Zastarevanje podataka pri promeni programa | Id-jevi bez razreda; izdanja u id-jevima ishoda; mapa za 2027/28 |
| Sajt se pogrešno shvata kao zvaničan | Napomena u `o-projektu` i u README-u |
