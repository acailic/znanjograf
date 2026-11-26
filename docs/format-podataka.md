# Format podataka

Ovo je referenca oblika svega što stoji u `data/`. Kako se piše sadržaj (zrnatost tema, jezik zadataka, slike) objašnjava [autorski vodič](autorski-vodic.md), a odakle dolaze tekstovi nastavnog programa — [program](program.md).

Kad se ovaj dokument ne slaže s kodom, važi kod. Zato svako pravilo ovde nosi kod kojim ga alat prijavljuje; kodovi su uzeti iz `zg/`.

Za sve fajlove važe dva pravila:

- **Sve je srpska latinica**, osim imena polja, fajlova i vrednosti koje mašina čita. Ćirilica se nikad ne piše ručno; nastaje pri izgradnji sajta.
- **Nepoznato polje je greška.** Zapis sme da ima samo polja koja su ovde navedena; svako drugo prijavljuje `V2-unknown-field`.

Primeri su uzeti iz oglednog korpusa za testove (`tests/fixtures/raw.py`) ili su sastavljeni po istim pravilima. Id-jevi ishoda u tim primerima pripadaju oglednom korpusu i ne odgovaraju ishodima pravog izdanja `g1-2026`.

U `data/` su u trenutku pisanja upisani `data/math/meta.json`, izdanje za 1. razred (`data/curriculum/math/g1-2026.json`), `data/curriculum/sources.json`, `data/curriculum/unmapped.json` i pravila u `data/lint/`; tema i zadataka još nema.

## 1. Pregled fajlova

| Putanja | Šta sadrži | Čime se proverava |
|---|---|---|
| `data/math/meta.json` | oznaku predmeta, spisak razreda, oblasti | samo da je valjan JSON |
| `data/math/gN/topics.json` | teme jednog razreda, redom iz programa | `validate` |
| `data/math/gN/edges.json` | grane čija je zavisna tema u tom razredu | `validate` |
| `data/math/gN/questions.json` | zadaci tema tog razreda | `validate`, `verify`, `lint` |
| `data/curriculum/sources.json` | odluku o tekstu ishoda i spisak akata | ništa osim valjanog JSON-a |
| `data/curriculum/math/<izdanje>.json` | teme i ishode programa jednog razreda u jednom izdanju | `validate`, `lint` |
| `data/curriculum/unmapped.json` | ishode bez teme, s razlogom | `validate` |
| `data/registry.json` | svaki id teme ikad objavljen | `validate` |
| `data/aliases.json` | stari idove i njihove današnje ciljeve | `validate` |
| `data/review/teachers.json` | ljudske preglede po temi | `validate`, `lint` |
| `data/ledger.json` | hešove zapisa po kapiji | oblik pri čitanju (`python3 -m zg status`) |
| `data/lint/notation.json` | pravila notacije po razredu | `lint` |
| `data/lint/digraphs.json` | rečnik reči s `lj`, `nj` ili `dž` | `lint` |

### Kako se pokreće provera

Iz korena repozitorijuma, posle svake izmene:

```
python3 -m zg validate
python3 -m zg verify
python3 -m zg lint
```

Svaka komanda ispisuje po jednu liniju po grešci, u obliku `putanja: mesto: kod: poruka`, zatim `OK` ili broj grešaka, i završava se kodom 1 kad ima grešaka. `python3 -m zg all` pokreće sve tri kapije, a onda proverava da su brojevi u README-u i izgrađeni sajt ažurni.

Opcije `--root` i `--subject` stoje ispred komande, na primer `python3 -m zg --root <fascikla> validate`.

### Kako alat čita `data/`

- `grades` iz `meta.json` određuje koje se fascikle `data/math/gN/` čitaju. Fascikla razreda koja postoji, a u `meta.json` nije navedena, ipak se čita i prijavljuje se s `V1-json`.
- Fajl koji nedostaje čita se kao prazan. Fajl koji postoji, a ne može se pročitati (nevaljan JSON, nije UTF-8, tri fajla razreda nisu niz zapisa), prijavljuje se s `V1-json`, a dupliran ključ s `V1-duplicate-key`; tada padaju sve tri kapije.
- Svaki `*.json` u `data/curriculum/math/` je jedno izdanje, a ime fajla je id izdanja.
- Kad se isti id teme ili zadatka ponovi, važi prvi zapis, a ponovljeni se prijavljuje s `V3-id-duplicate`.

## 2. `math/meta.json`

```json
{
  "subject": "math",
  "name": "Matematika",
  "grades": [1, 2, 3, 4, 5, 6, 7, 8],
  "areas": ["numbers", "geometry", "data"]
}
```

| Polje | Tip | Značenje |
|---|---|---|
| `subject` | tekst | oznaka predmeta; danas samo `math` |
| `name` | tekst | naziv predmeta koji se prikazuje |
| `grades` | niz celih brojeva | razredi za koje postoje fascikle `gN/` |
| `areas` | niz tekstova | oblasti, u redu za prikaz |

Nijedno pravilo ne proverava polja ovog fajla. Alat čita samo `grades`, i to samo cele brojeve; ako nema nijednog, traži svaku fasciklu čije ime počinje slovom `g` iza koga idu cifre.

## 3. `math/gN/topics.json`

Niz tema. Redosled u fajlu je redosled iz programa i ujedno redosled učenja unutar razreda, pa se ne sme mesati.

```json
{
  "id": "mat-brojevi-do-10",
  "grade": 1,
  "area": "numbers",
  "unit": "Brojevi",
  "kind": "concept",
  "name": "Brojevi do 10",
  "summary": "Prepoznavanje, čitanje i pisanje brojeva od 1 do 10 i njihov redosled.",
  "mastery": [
    "redom nabroji brojeve od 1 do 10",
    "imenuje broj koji dolazi pre i posle datog broja"
  ],
  "curriculum": [
    {"edition": "g1-2026", "outcome": "g1-2026-001", "match": "exact"},
    {"edition": "g1-2026", "outcome": "g1-2026-005", "match": "exact"}
  ],
  "root_reason": "Ovo je pojam od koga polaze svi ostali: bez brojeva do 10 nema sabiranja."
}
```

| Polje | Tip | Obavezno | Pravilo |
|---|---|---|---|
| `id` | tekst | da | `mat-`, pa mala slova, cifre i crtice, do 48 znakova, bez razreda u imenu (`V3-id-format`); jedinstven (`V3-id-duplicate`); upisan u `data/registry.json` (`V3-id-unregistered`) |
| `grade` | ceo broj | da | od 1 do 8 (`V4-grade`) |
| `area` | tekst | da | `numbers`, `geometry` ili `data` (`V4-enum`) |
| `unit` | tekst | da | naziv tematske celine onako kako se zove u važećem izdanju |
| `kind` | tekst | da | `concept`, `procedure`, `problem` ili `reasoning` (`V4-enum`) |
| `name` | tekst | da | kratak naziv; ne sme biti isti kao ili skoro isti kao naziv druge teme (`L6-near-duplicate`) |
| `summary` | tekst | da | jednu do dve rečenice roditelju |
| `mastery` | niz od 2 do 3 neprazna teksta | da | kriterijumi savladanosti (`V2-type`) |
| `curriculum` | niz stavaka `{edition, outcome, match}` | da | bar jedan ishod (`V7-topic-without-outcome`) |
| `root_reason` | tekst | ne | samo za temu bez prethodnih tema |

- Id teme se nikad ne preimenuje i ne briše. Ako se teme spajaju, stari id ostaje u `data/aliases.json`.
- Tema kojoj nijedna grana ne stoji u polju `topic` mora imati `root_reason` (`V6-root-reason-missing`); tema koja ima prethodne teme ne sme da ga ima (`V6-root-reason-unneeded`).
- Polje koje nedostaje prijavljuje `V2-missing-field`; vrednost pogrešnog tipa ili oblika prijavljuje `V2-type`.
- U svakom tekstu zapisa znakovi `$` idu u parovima i nijedna formula `$…$` nije prazna (`V10-dollar`).

### Stavka `curriculum`

| Polje | Tip | Pravilo |
|---|---|---|
| `edition` | tekst | id izdanja, oblik `gN-YYYY` (`V3-id-format`) |
| `outcome` | tekst | id ishoda, oblik `gN-YYYY-NNN` (`V3-id-format`); izdanje ga mora imati (`V7-outcome-missing`) |
| `match` | tekst | `exact` (pokriva ceo ishod) ili `partial` (pokriva deo ishoda) (`V4-enum`) |

Sva tri polja su obavezna.

## 4. `math/gN/edges.json`

Niz grana. Grana stoji u fajlu razreda **zavisne** teme, one u polju `topic`.

```json
[
  {
    "topic": "mat-sabiranje-do-100",
    "requires": "mat-sabiranje-do-20",
    "strength": "hard",
    "reason": "Pisano sabiranje dvocifrenih brojeva koristi usmeno sabiranje do 20."
  },
  {
    "topic": "mat-poredjenje-do-100",
    "requires": "mat-sabiranje-do-10",
    "strength": "soft",
    "reason": "Računanje zbirova pomaže pri proceni koji je broj veći, ali nije uslov."
  }
]
```

| Polje | Tip | Obavezno | Pravilo |
|---|---|---|---|
| `topic` | tekst | da | id zavisne teme; obe teme moraju postojati (`V5-edge-endpoint`) |
| `requires` | tekst | da | id prethodne teme |
| `strength` | tekst | da | `hard` ili `soft` (`V4-enum`) |
| `reason` | tekst | da | jednom rečenicom, ljudski |

- `hard` znači da se bez prethodne teme ne može uraditi nijedan zadatak ove teme; `soft` da pomaže, a nije uslov.
- Ista grana ne sme biti navedena dvaput (`V5-duplicate`), tema ne zahteva samu sebe (`V5-self-loop`), i ne sme postojati par `A → B` i `B → A` (`V5-reverse-pair`).
- Razred teme u `requires` nije veći od razreda teme u `topic` (`V5-grade-order`).
- Suvišna grana je greška (`V5-redundant`): čvrsta je suvišna ako do `requires` već vodi drugi put samo preko čvrstih grana, a meka ako vodi bilo koji drugi put. Alat je ne odbacuje sam; sadržaj se mora ispraviti.
- Graf mora biti bez ciklusa (`V6-cycle`).

## 5. `math/gN/questions.json`

Niz zadataka. Svaka tema ima najmanje dva osnovna i dva standardna zadatka (`V8-bank-count`).

### 5.1 Polja

```json
{
  "id": "mat-sabiranje-do-20-q3",
  "topic": "mat-sabiranje-do-20",
  "level": "standard",
  "type": "numeric",
  "prompt": "Mila ima $8$ kuvanica i kupi još $7$. Koliko kuvanica sada ima?",
  "answer": "15",
  "check": "(+ 8 7)",
  "explanation": "8 + 2 = 10, pa još 5: 15."
}
```

| Polje | Tip | Obavezno | Pravilo |
|---|---|---|---|
| `id` | tekst | da | `<id teme>-q<n>`, npr. `mat-sabiranje-do-20-q3` (`V3-qid-format`); jedinstven (`V3-id-duplicate`); zadaci jedne teme nose `q1`, `q2`… bez preskakanja (`V3-qid-format`) |
| `topic` | tekst | da | id postojeće teme (`V3-id-unknown`) |
| `level` | tekst | da | `basic` ili `standard` (`V4-enum`) |
| `type` | tekst | da | `numeric` ili `choice` (`V4-enum`) |
| `prompt` | tekst | da | tekst zadatka; dužina je ograničena po razredu (`L5-length`) |
| `answer` | tekst | da | za `numeric` broj (odeljak 7, `V8-numeric-answer`); za `choice` id tačne ponude (`V8-choice-ids`) |
| `check` | tekst | da | izraz provere (odeljak 6) |
| `explanation` | tekst | da | objašnjenje jezikom razreda, najviše 400 znakova (`L5-length`) |
| `choices` | niz stavaka `{id, text}` | uz `type: "choice"` | tri ili četiri ponude (`V8-choice-count`); id-jevi ponuda neprazni i različiti (`V8-choice-ids`); tekstovi ponuda različiti (`V8-choice-text`) |
| `points_to` | objekat „id pogrešne ponude“ → id teme | ne | ključ je id pogrešne ponude, a cilj je čvrst predak teme zadatka (`V8-points-to`) |
| `figure` | objekat | ne | slika (odeljak 5.5) |
| `round_to` | ceo broj | ne | obavezan kad tačan odgovor nije racionalan broj (odeljak 5.4) |

Alat ne traži polje `choices` po tipu, ali zadatak s ponudama bez `choices` pada na `V8-choice-count` jer tada ima nula ponuda. `points_to` se proverava i prelazi u paket sajta, ali ga sajt i motor dijagnostike danas ne koriste.

### 5.2 Numerički zadatak

Zadatak iznad (`type: "numeric"`) je potpun primer. Razlomak se piše kosom crtom:

```
"answer": "3/20",   "check": "(/ 3 4 5)"
```

### 5.3 Zadatak s ponudama

```json
{
  "id": "mat-poredjenje-do-100-q3",
  "topic": "mat-poredjenje-do-100",
  "level": "standard",
  "type": "choice",
  "prompt": "Koji znak treba upisati: $56$ ____ $65$?",
  "choices": [
    {"id": "a", "text": "$>$"},
    {"id": "b", "text": "$<$"},
    {"id": "c", "text": "$=$"}
  ],
  "answer": "b",
  "check": "<",
  "explanation": "56 je manje od 65.",
  "points_to": {"a": "mat-brojevi-do-10"}
}
```

- `answer` je id tačne ponude, a ne uvek `a`.
- Svaka pogrešna ponuda je uobičajena zabluda, ne slučajan broj. `points_to` za svaku pogrešnu ponudu sme da navede čvrstog pretka kog učenik verovatno nema; u primeru je to `mat-brojevi-do-10`, čvrsti predak teme `mat-poredjenje-do-100`.
- Ako su ponude brojevi (smeju stajati u `$…$`), `check` je izraz čija vrednost mora biti vrednost samo tačne ponude: tekst tačne ponude mora dati tu vrednost, a nijedna pogrešna ne sme; svaka pogrešna ponuda mora biti broj (`S-choice-value`).
- Ako nijedna ponuda nije broj (reči, znakovi), `check` je tekst tačne ponude bez `$`, a `{,}` se čita kao zarez.

### 5.4 Odgovor koji nije racionalan broj

Kad u `check` uđe `pi` ili koren broja koji nije kvadrat, vrednost nije tačan razlomak i pitanje mora da kaže na koliko decimala se odgovor zaokružuje.

```json
{
  "id": "mat-sabiranje-do-100-q1",
  "topic": "mat-sabiranje-do-100",
  "level": "basic",
  "type": "numeric",
  "prompt": "Koliko iznosi koren iz dvanaest, zaokruženo na dve decimale?",
  "answer": "3.46",
  "check": "(round (sqrt 12) 2)",
  "round_to": 2,
  "explanation": "Koren iz 12 je približno 3,46."
}
```

- `round_to` je ceo broj od 0 do 30. Bez njega `validate` prijavljuje `V8-round-to`, a `verify` `S-round-to`. Ako je veći od 30, `verify` ga računa kao da nedostaje.
- Vrednost se zaokružuje na `round_to` decimala, pri čemu polovina ide od nule, i `answer` mora biti jednak toj zaokruženoj vrednosti.

### 5.5 Slika

`figure` je objekat s obaveznim `kind` i `alt`.

```json
{
  "id": "mat-brojevi-do-10-q2",
  "topic": "mat-brojevi-do-10",
  "level": "basic",
  "type": "numeric",
  "prompt": "Koji broj je označen na brojevnoj pravoj?",
  "figure": {
    "kind": "numberline",
    "alt": "Brojevna prava od 0 do 10 sa tačkom iznad broja 7.",
    "min": 0,
    "max": 10,
    "marks": [7]
  },
  "answer": "7",
  "check": "7",
  "explanation": "Tačka stoji iznad broja $7$."
}
```

- `kind` je jedna od dvanaest vrsta (`V9-figure-kind`).
- `alt` je običan tekst od najmanje 20 znakova (`V9-figure-alt`) koji opisuje sliku dovoljno da se zadatak reši i bez nje. Sajt ga ispisuje i kad sliku ne može da nacrta, i čita ga čitaču ekrana. Prikaže se onakav kakav je, bez iscrtavanja formula: brojevi se u njemu pišu ciframa, a ne u `$…$`.
- Parametri koje vrsta nema, obavezni parametar koji nedostaje i vrednosti koje se ne slažu prijavljuju `V9-figure-param`.

Obavezni parametri su podebljani; ostali mogu da izostanu.

| `kind` | Parametri | Šta mora da se slaže |
|---|---|---|
| `numberline` | **`min`**, **`max`** (celi brojevi), `step` (pozitivan ceo broj, podrazumevano 1), `marks` (niz brojeva), `unit` (tekst) | `max` veći od `min`; najviše 60 oznaka na pravoj; svaka oznaka u `marks` između `min` i `max` |
| `fractionbar` | **`numerator`** (pozitivan ceo broj), **`denominator`** (ceo broj od 1 do 24), `shaded` (ceo broj) | `shaded` od 0 do `numerator` |
| `pie` | **`parts`** (ceo broj od 2 do 12), `shaded` (ceo broj) | `shaded` od 0 do `parts` |
| `dots` | **`rows`**, **`cols`** (celi brojevi od 1 do 12), `count` (ceo broj) | `count` od 0 do umnoška `rows` i `cols` |
| `bars` | `title` (tekst), **`categories`** (niz tekstova), **`values`** (niz pozitivnih brojeva) | od 2 do 8 natpisa; `values` ima onoliko vrednosti koliko `categories` |
| `pictogram` | **`symbol`** (neprazan tekst), **`items`** (niz stavaka `{label, count}`), `perSymbol` (pozitivan ceo broj, podrazumevano 1) | bar jedna stavka |
| `grid` | **`cols`**, **`rows`** (celi brojevi od 1 do 15), `cells` (niz parova `[red, kolona]`) | svako polje u mreži; red i kolona se broje od nule |
| `polygon` | **`vertices`** (niz parova `[x, y]`), `sides` (niz stavaka `{index, label}`), `labels` (niz stavaka `{text, x, y}`) | od 3 do 8 temena; `index` je redni broj temena; natpis strane s brojem mora odgovarati dužini te strane do 1 % (`V9-figure-geometry`) |
| `angle` | **`degrees`** (broj od 0 do 360), `label` (tekst), `vertex` (par `[x, y]`) | |
| `axes` | **`xmin`**, **`xmax`**, **`ymin`**, **`ymax`** (brojevi), `points` (niz stavaka `{x, y, label}`) | `xmax` veći od `xmin` i `ymax` veći od `ymin`; svaka tačka unutar osa |
| `clock` | **`hour`** (ceo broj od 1 do 12), **`minute`** (ceo broj od 0 do 59) | |
| `table` | **`columns`** (niz tekstova), **`rows`** (niz nizova tekstova) | bar jedna kolona; svaki red ima onoliko ćelija koliko `columns` |

## 6. Jezik provere odgovora (`check`)

`check` je S-izraz: operator u zagradi, pa argumenti. `zg/dsl.py` ga čita rekurzivnim spuštanjem, a `verify` ga tačno izračunava u razlomcima (`zg/mathcheck.py`) i traži da vrednost bude jednaka `answer` (`S-answer-mismatch`).

**Atomi.** Ceo broj (`15`, `-3`), decimala s tačkom, tačna kao razlomak (`2.5` je 5/2), i `pi`.

**Operatori.**

| Operator | Broj argumenata | Šta računa | Primer |
|---|---|---|---|
| `+` | 2 ili više | zbir | `(+ 2 3 4)` → 9 |
| `-` | 1 ili više | jedan argument: suprotni broj; više: prvi minus ostali | `(- 5)` → -5; `(- 10 3 2)` → 5 |
| `*` | 2 ili više | proizvod | `(* 2 3 4)` → 24 |
| `/` | 2 ili više | prvi podeljen proizvodom ostalih | `(/ 3 4 5)` → 3/20 |
| `pow` | 2 | osnova na stepen; stepen je ceo broj i sme biti negativan | `(pow 2 10)` → 1024 |
| `sqrt` | 1 | kvadratni koren | `(sqrt 9)` → 3 |
| `abs` | 1 | apsolutna vrednost | `(abs -7)` → 7 |
| `min` | 2 ili više | najmanji argument | `(min 3 1 2)` → 1 |
| `max` | 2 ili više | najveći argument | `(max 3 1 2)` → 3 |
| `floor` | 1 | najveći ceo broj koji nije veći | `(floor -3.2)` → -4 |
| `ceil` | 1 | najmanji ceo broj koji nije manji | `(ceil -3.7)` → -3 |
| `round` | 1 ili 2 | zaokruženo na ceo broj, ili na dati broj decimala (od -30 do 30); polovina ide od nule | `(round 2.5)` → 3; `(round -2.5)` → -3 |
| `mean` | 2 ili više | aritmetička sredina | `(mean 2 4 6)` → 4 |
| `median` | 2 ili više | srednja vrednost; kod parnog broja argumenata sredina dve srednje vrednosti | `(median 1 3 2 4)` → 5/2 |
| `mode` | 2 ili više | najčešća vrednost; mora biti jedinstvena | `(mode 1 2 2 3)` → 2 |
| `gcd` | 2 ili više | najveći zajednički delilac celih brojeva | `(gcd 12 18)` → 6 |
| `lcm` | 2 ili više | najmanji zajednički sadržalac celih brojeva | `(lcm 4 6)` → 12 |
| `mod` | 2 | ostatak pri deljenju, nikad negativan; delilac mora biti pozitivan | `(mod 17 5)` → 2 |
| `percent` | 2 | prvi argument kao procenat drugog | `(percent 15 200)` → 30 |

**Pet primera.**

```
"answer": "15",    "check": "(+ 8 7)"                                → 8 + 7 = 15
"answer": "3/20",  "check": "(/ 3 4 5)"                              → 3 : (4 · 5) = 3/20
"answer": "30",    "check": "(percent 15 200)"                       → 15 % od 200 = 30
"answer": "4",     "check": "(- (* 2 5) 6)"                          → 2 · 5 − 6 = 4
"answer": "3.46",  "check": "(round (sqrt 12) 2)",   "round_to": 2   → koren iz 12, na dve decimale
```

**Granice.** Izraz sme da ima najviše 12 nivoa ugnježđivanja i 200 delova (`S-check-depth`). Nijedan međurezultat ne sme biti prevelik broj (`S-check-parse`). Vrednost koja nije racionalan broj računa se s 60 značajnih cifara i zahteva `round_to`.

**Šta `verify` prijavljuje na `check`.**

- `S-check-parse`: nepoznat operator, pogrešan broj argumenata, prazan izraz ili višak teksta posle njega, token koji nije broj ni `pi`, stepen koji nije ceo broj, koren negativnog broja, moda koja nije jedinstvena, `gcd` ili `lcm` nad brojem koji nije ceo, negativan delilac u `mod`, prevelik broj.
- `S-check-zero`: deljenje nulom.
- `S-check-depth`: izraz je predubok ili prevelik.

Autor piše i `answer` i `check`, pa `verify` ne vidi da li je tekst zadatka uopšte vodi do tog odgovora; to je posao slepog prolaza.

## 7. Kako se upisuje broj

`answer` numeričkog zadatka je tekst koji alat čita kao tačan razlomak. U fajlu važi:

- predznak `+` ili `-` sme stajati: `-7`;
- ceo broj: `15`; hiljade smeju biti odvojene jednim razmakom: `1 000 000`;
- decimala se piše s tačkom: `3.5`. Tačka je u fajlu uvek decimalni znak, pa je `0.125` jedna osmina, a `1.000` je jedan, ne hiljadu;
- razlomak: `3/4`; mešovit broj: `2 3/4`;
- najviše 100 znakova.

Nije broj: `1e3`, `3 4`, `.5`, `5.`, `1/0`, `abc`, `3,5 kg`.

Ono što učenik ukuca čita se drugim pravilom (`site/js/engine/rational.js`): tačka iza koje dolaze tačno tri cifre na kraju znači hiljade, pa je `1.000` hiljadu, a `1.5` jedan i po. Decimale se pišu zarezom.

## 8. `curriculum/sources.json`

```json
{
  "rule": "paraphrase",
  "evidence": "Sajt Zavoda za unapređivanje obrazovanja i vaspitanja (zuov.gov.rs), s koga se preuzimaju tekstovi pravilnika, objavljuje sadržaj svoje internet prezentacije pod licencom Creative Commons Autorstvo-Nekomercijalno-Bez prerada 3.0 Srbija (CC BY-NC-ND 3.0 RS; https://zuov.gov.rs/uslovi-koriscenja-licenca/), koja ne dozvoljava ni komercijalnu upotrebu ni preradu. Programi nastave čine sastavni deo pravilnika ministra prosvete, a kopija člana 6 Zakona o autorskom i srodnim pravima (sa sajta Paragraf, čije zaglavlje navodi izmene samo do 66/2019) kaže da se zakoni i podzakonski akti ne smatraju autorskim delom, ali taj tekst nije upoređen s važećim. Dok vlasnik repozitorijuma ne odluči drugačije, repozitorijum čuva parafrazu svakog ishoda, napisanu sopstvenim rečima uz pokazivač na akt i štampanu stranu, i ne distribuira nijedan PDF.",
  "acts": [
    {
      "title": "Pravilnik o planu nastave i učenja za prvi ciklus osnovnog obrazovanja i vaspitanja i programu nastave i učenja za prvi razred osnovnog obrazovanja i vaspitanja",
      "gazette": ["10/2017", "12/2018", "15/2018", "18/2018", "1/2019", "2/2020", "16/2022", "1/2023", "13/2023", "14/2023", "11/2024"],
      "url": "https://pravno-informacioni-sistem.rs/eli/rep/pg/ministarstva/pravilnik/2017/10/1/reg",
      "retrieved": "2026-11-26"
    }
  ]
}
```

Ovaj fajl zapisuje odluku o tekstu ishoda (zašto se čuvaju kao parafraza) i spisak akata od kojih potiču; o samoj odluci piše [program](program.md).

| Polje | Tip | Značenje |
|---|---|---|
| `rule` | tekst | `paraphrase` ili `verbatim` |
| `evidence` | tekst | dokaz za pravilo, slobodnim tekstom |
| `acts` | niz stavaka | jedan akt po stavci |
| `title` | tekst | pun naziv akta |
| `gazette` | niz tekstova | brojevi glasnika u kojima je akt objavljen i menjan |
| `url` | tekst | adresa teksta akta |
| `retrieved` | tekst `YYYY-MM-DD` | dan preuzimanja |

Nijedna komanda ne čita polja ovog fajla i nijedno pravilo ih ne proverava; dovoljno je da je valjan JSON. Oblik je dogovoren u planu (`docs/superpowers/plans/2026-11-26-faza-0-temelji.md`, odeljak C4) i tako je upisan unos za 1. razred, koji je ovde prikazan.

## 9. `curriculum/math/<izdanje>.json`

Jedan fajl po razredu i školskoj godini. Ime fajla je id izdanja, `gN-YYYY`: `N` je razred, a `YYYY` je prva godina školske godine u kojoj program važi. `g1-2026` je program 1. razreda koji važi u 2026/27.

```json
{
  "edition": "g2-2026",
  "grade": 2,
  "applies_from": "2026/27",
  "themes": [
    {
      "name": "Brojevi",
      "area": "numbers",
      "hours": 150,
      "content": [
        "Sabiranje i oduzimanje do 100",
        "Poređenje brojeva"
      ],
      "page": 20
    }
  ],
  "outcomes": [
    {"id": "g2-2026-001", "text": "sabira brojeve do 100", "page": 20, "area": "numbers", "unit": "Brojevi"},
    {"id": "g2-2026-002", "text": "poredi i uređuje brojeve do 100", "page": 20, "area": "numbers", "unit": "Brojevi"},
    {"id": "g2-2026-003", "text": "oduzima brojeve do 100", "page": 20, "area": "numbers", "unit": "Brojevi"},
    {"id": "g2-2026-004", "text": "rešava tekstualne zadatke sa jednom i dve računske operacije", "page": 21, "area": "numbers", "unit": "Brojevi"},
    {"id": "g2-2026-005", "text": "koristi znakove $<$ i $>$ za poređenje brojeva", "page": 20, "area": "numbers", "unit": "Brojevi"},
    {"id": "g2-2026-006", "text": "procenjuje rezultat sabiranja i oduzimanja do 100", "page": 21, "area": "numbers", "unit": "Brojevi"}
  ]
}
```

**Zaglavlje.**

| Polje | Tip | Obavezno | Pravilo |
|---|---|---|---|
| `edition` | tekst | da | jednako imenu fajla (`V7-edition-grade`) |
| `grade` | ceo broj | da | razred koji nosi id izdanja (`V7-edition-grade`) |
| `applies_from` | tekst | da | školska godina od koje program važi, npr. `"2026/27"` (`V2-missing-field`, `V2-type`) |
| `themes` | niz tema programa | ne | sme izostati |
| `outcomes` | niz ishoda | da | sme biti samo niz (`V2-missing-field`, `V2-type`) |
| `notes` | bilo šta | ne | ne proverava se i ne prelazi u sajt |

**Tema programa** (stavka niza `themes`).

| Polje | Tip | Obavezno | Značenje |
|---|---|---|---|
| `name` | tekst | da | naziv teme programa |
| `area` | tekst | ne | `numbers`, `geometry` ili `data` (`V4-enum`) |
| `hours` | broj koji nije negativan | ne | fond časova |
| `content` | niz nepraznih tekstova | ne | sadržaji |
| `page` | pozitivan ceo broj | ne | štampana stranica u izvoru (`V2-type`) |

**Ishod** (stavka niza `outcomes`).

| Polje | Tip | Obavezno | Značenje |
|---|---|---|---|
| `id` | tekst | da | `gN-YYYY-NNN` (`V3-id-format`); jedinstven u izdanju (`V3-id-duplicate`) |
| `text` | tekst | da | tekst ishoda |
| `page` | pozitivan ceo broj | da | štampana stranica akta na kojoj ishod stoji (`V2-type`) |
| `code` | tekst | ne | kod ishoda tamo gde ga dokument ima |
| `level` | tekst | ne | `basic`, `medium` ili `advanced` (`V4-enum`) |
| `area` | tekst | ne | `numbers`, `geometry` ili `data` (`V4-enum`) |
| `unit` | tekst | ne | tematska celina kojoj ishod pripada |

## 10. `curriculum/unmapped.json`

```json
{
  "<id ishoda>": "zašto ishod nema svoju temu"
}
```

Objekat „id ishoda“ → razlog. Svaki ishod iz svakog izdanja mora biti pokriven: ili ga navodi bar jedna tema, ili stoji ovde s razlogom.

- Ishod bez teme i bez unosa prijavljuje `V7-outcome-unmapped`.
- Unos koji više ne treba prijavljuje `V7-unmapped-stale`: ishod ne postoji ni u jednom izdanju, ili ga teme pokrivaju.

## 11. `registry.json`

```json
{
  "topics": [
    "mat-brojevi-do-10",
    "mat-sabiranje-do-10"
  ]
}
```

Registar sadrži svaki id teme ikad objavljen i samo se dodaje.

- Svaka tema mora biti upisana (`V3-id-unregistered`).
- Svaki upis mora odgovarati pravilu za id teme (`V3-id-format`).
- Upis za temu koja više nema zapis u `topics.json` nije greška.

## 12. `aliases.json`

```json
{
  "mat-brojevi": ["mat-brojevi-do-10"]
}
```

Objekat „stari id teme“ → niz današnjih id-ova. Stari id mora da odgovara pravilu za id teme (`V3-id-format`).

- Vrednost je neprazan niz postojećih tema; sve drugo prijavljuje `V11-alias-target`.
- Aliasi ne smeju da grade lance: ako je neki alias cilj drugog aliasa, prijavljuje se `V11-alias-chain`.

## 13. `review/teachers.json`

Fajl je izborn. Zapisuje pregled nastavnika po temi; sajt ga prikazuje na stranici teme.

```json
{
  "mat-brojevi-do-10": {
    "name": "Ime Prezime",
    "role": "nastavnik matematike",
    "date": "2026-11-26",
    "note": "Napomena o pregledu."
  }
}
```

| Polje | Tip | Obavezno | Pravilo |
|---|---|---|---|
| ključ | id teme | da | tema mora postojati (`V3-id-unknown`) |
| `name` | neprazan tekst | da | ko je pregledao (`V2-missing-field`, `V2-type`) |
| `role` | neprazan tekst | da | uloga, npr. nastavnik (`V2-missing-field`, `V2-type`) |
| `date` | tekst `YYYY-MM-DD` | da | dan pregleda (`V2-missing-field`, `V2-type`) |
| `note` | tekst | ne | napomena (`V2-type`) |

- Zapis mora biti objekat (`V2-type`), a polje koje nije navedeno prijavljuje `V2-unknown-field`.
- Oznaka je izjava onoga ko ju je upisao: nijedna kapija ne proverava da li je pregled zaista obavljen.
- `name`, `role` i `note` prolaze kroz `lint` kao i svaki drugi tekst. Reč s `lj`, `nj` ili `dž` u imenu ili ulozi mora biti u `data/lint/digraphs.json`, inače `lint` prijavljuje `L3-digraph`.

## 14. `ledger.json`

```json
{
  "edges": {
    "mat-sabiranje-do-10>mat-brojevi-do-10": "8fb01d1ff803666b94e00900f4c1c5423c49a45cb4841bc82607cdccfce0d7a9"
  },
  "verify": {
    "mat-brojevi-do-10-q1": "87554148fb8922320e034ecf430cb2b7baeadbb31e24e349461a7694a09d3076"
  }
}
```

Objekat „kapija“ → objekat „id zapisa“ → heš sadržaja zapisa. Kapije su `verify`, `blind-solve`, `classify`, `cueing` i `edges`; zapis je zadatak (ključ je id zadatka), a za `edges` grana (ključ je `topic>requires`).

- Fajl piše `python3 -m zg ledger mark --gate <kapija> --grade <razred>`. Za kapiju `verify` komanda prvo ponovo pokreće `verify` i ništa ne zapisuje ako za taj razred ima grešaka; za ostale kapije samo zapisuje.
- Fajl čita `python3 -m zg status`, koji po razredu pokazuje koliko zapisa je provereno, a koliko je zastarelo (izmenjeno posle beleženja). Kapija kojoj u fajlu nema sekcije nikad nije pokrenuta.
- Fajl čiji vrh nije objekat sekcija po kapiji je greška: `python3 -m zg status` je ispisuje i završava se kodom 1.
- Nijedna druga komanda ne čita ovaj fajl. `python3 -m zg all` ne pada na zastarelim zapisima; zastarelost se vidi samo kroz `status`.

## 15. `lint/notation.json`

```json
[
{
  "pattern": "\\\\times|\\\\cdot",
  "min_grade": 2,
  "outcome": "g2-2026-005",
  "note": "množenje"
},
{
  "pattern": "(?<!\\\\):",
  "min_grade": 2,
  "outcome": "g2-2026-005",
  "note": "deljenje"
}
]
```

Niz pravila. Svako pravilo ima ta četiri polja i nijedno drugo; loše oblikovano pravilo prijavljuje `L1-rule-invalid` i preskače se.

| Polje | Tip | Značenje |
|---|---|---|
| `pattern` | regularni izraz | šta se traži unutar formule `$…$` |
| `min_grade` | ceo broj od 1 do 8 | najraniji razred u kome se notacija uvodi |
| `outcome` | id ishoda | ishod koji notaciju uvodi |
| `note` | tekst | kratko ime notacije u poruci |

- Pravilo važi za zadatke čija je tema u razredu nižem od `min_grade`. Formula se traži u tekstu zadatka, u ponudama i u objašnjenju, i jedan zadatak se prijavljuje jednom po pravilu (`L1-notation`).
- LaTeX komanda u `pattern` piše se s dvokratnom obrnutom crtom (u JSON-u `\\\\times`), jer je uzorak regularni izraz. Napisana s jednom, postaje kontrolni znak koji ništa ne nalazi, pa je `lint` odbija.
- Poziv na ishod proverava se tek kad to izdanje bude u repozitorijumu: ako ga izdanje nema, prijavljuje se `L1-rule-outcome` i pravilo se preskače. Do tada pravilo važi i bez provere poziva.
- Segmenti `\text{…}` se pre traženja uklanjaju, da oznaka jedinice ne bi prošla kao promenljiva.
- Pragovi prate program: deljenje i razlomak ulaze u 2. razredu, decimalni zapis i znakovi „manje ili jednako“ i „veće ili jednako“ u 3., a stepen, kvadratni koren i broj pi u 7. Pravilo za stepen ne gleda `^` iza vitičaste zagrade ili razmaka (jedinice poput `\text{m}^2`) ni `^\circ` (stepen ugla), jer se to piše mnogo pre stepenovanja.

## 16. `lint/digraphs.json`

```json
{
  "sabiranje": "digraph",
  "injekcija": "split:n|j"
}
```

Objekat „reč malim slovima“ → `"digraph"` ili `"split:<levo>|<desno>"`.

- `digraph`: par `lj`, `nj` ili `dž` u toj reči je jedno slovo (većina reči).
- `split:n|j`: par je granica dva slova; prvo pojavljivanje tog para u reči se razdvaja.

Transliteracija bez rečnika čita svaki par kao jedno slovo, pa pogrešna klasifikacija daje pogrešnu ćirilicu.

- Reč s `lj`, `nj` ili `dž` koja nije u rečniku prijavljuje `L3-digraph` u svakom tekstu gde se pojavi, dok se ne klasifikuje. Zato `python3 -m zg lint` pada na novoj reči pre nego što se doda.
- Rečnik gleda male slova, pa ključ treba upisati malim slovima.
- `python3 tools/add-digraphs.py --root .` ispisuje reči iz korpusa kojih u rečniku još nema, po abecedi.

## 17. Tabela kodova pravila

### `validate`

| Kod | Značenje |
|---|---|
| `V1-json` | fajl se ne može pročitati: nevaljan JSON, nije UTF-8, nije niz zapisa, fascikla razreda nije u `meta.json`, `data/lint/notation.json` nije niz |
| `V1-duplicate-key` | isti ključ dvaput u jednom objektu |
| `V2-unknown-field` | zapis ima polje koje ne sme |
| `V2-missing-field` | obavezno polje nedostaje |
| `V2-type` | polje nije traženog tipa ili oblika; `page` nije pozitivan ceo broj |
| `V3-id-format` | id teme, zadatka, izdanja, ishoda, aliasa ili upis u registru ne odgovara pravilu |
| `V3-id-duplicate` | isti id teme ili zadatka dvaput; isti id ishoda dvaput u izdanju |
| `V3-id-unregistered` | tema nije upisana u `data/registry.json` |
| `V3-id-unknown` | zadatak ili `points_to` pokazuje na nepostojeću temu; pregled je upisan za nepostojeću temu |
| `V3-qid-format` | id zadatka nije `<id teme>-q<n>` ili se ne slaže s `topic`; zadaci teme nisu označeni redom |
| `V4-enum` | vrednost polja `area`, `kind`, `level`, `type`, `strength` ili `match` nije iz dozvoljenog skupa |
| `V4-grade` | `grade` teme nije od 1 do 8 |
| `V5-edge-endpoint` | grana pokazuje na nepostojeću temu |
| `V5-self-loop` | tema zahteva samu sebe |
| `V5-duplicate` | ista grana je navedena više puta |
| `V5-reverse-pair` | postoje grane `A → B` i `B → A` |
| `V5-grade-order` | tema zahteva temu iz višeg razreda |
| `V5-redundant` | suvišna grana: do prethodne teme već vodi drugi put |
| `V5-wrong-file` | grana stoji u `edges.json` drugog razreda |
| `V6-cycle` | ciklus zavisnosti |
| `V6-root-reason-missing` | tema bez prethodnih tema nema `root_reason` |
| `V6-root-reason-unneeded` | tema s prethodnim temama ima `root_reason` |
| `V6-isolated` | tema nema nijednu granu u oba smera ni `root_reason` |
| `V7-outcome-missing` | tema navodi ishod koji izdanje nema ili izdanje koje ne postoji |
| `V7-outcome-unmapped` | ishod nema nijednu temu, a nije u `data/curriculum/unmapped.json` |
| `V7-unmapped-stale` | unos u `unmapped.json` odnosi se na ishod koji ne postoji ili koji teme pokrivaju |
| `V7-topic-without-outcome` | tema ne navodi nijedan ishod |
| `V7-edition-grade` | polje `edition` ili `grade` u zaglavlju izdanja ne odgovara imenu fajla |
| `V8-bank-count` | tema ima manje od 2 osnovna ili 2 standardna zadatka |
| `V8-choice-count` | zadatak nema 3 ili 4 ponude |
| `V8-choice-ids` | id ponude nije neprazan tekst, ponavlja se, ili `answer` nije id nijedne ponude |
| `V8-choice-text` | više ponuda ima isti tekst |
| `V8-points-to` | `points_to` navodi ponudu koja nije pogrešna, ili cilj nije čvrst predak teme zadatka |
| `V8-numeric-answer` | `answer` numeričkog zadatka nije broj u prihvaćenom zapisu |
| `V8-round-to` | tačan odgovor nije racionalan broj, a `round_to` nedostaje |
| `V9-figure-kind` | `figure` nije objekat, nema `kind`, ili vrsta nije među dvanaest |
| `V9-figure-alt` | `alt` nedostaje, nije tekst, ili ima manje od 20 znakova |
| `V9-figure-param` | parametar slike je nepoznat, obavezan parametar nedostaje, ili se vrednosti ne slažu |
| `V9-figure-geometry` | natpis strane mnogougla s brojem ne odgovara dužini te strane do 1 % |
| `V10-dollar` | neparan broj znakova `$` u tekstu, ili prazna formula `$…$` |
| `V11-alias-chain` | alias je cilj drugog aliasa |
| `V11-alias-target` | vrednost aliasa nije neprazan niz postojećih tema |

### `verify`

| Kod | Značenje |
|---|---|
| `S-check-parse` | `check` nije valjan izraz, ili računanje nije uspelo |
| `S-check-depth` | `check` je ugnježđen dublje od 12 nivoa ili ima više od 200 delova |
| `S-check-zero` | `check` deli nulom |
| `S-answer-mismatch` | `answer` nije broj ili nije jednak vrednosti `check` |
| `S-choice-value` | kod zadatka s ponudama: nijedna ponuda nema id odgovora, tačna ponuda ne daje odgovor, pogrešna ponuda daje odgovor ili nije broj, ili tekst tačne ponude nije jednak `check` |
| `S-round-to` | vrednost nije racionalan broj, a `round_to` nedostaje ili nije ceo broj od 0 do 30 |

### `lint`

| Kod | Značenje |
|---|---|
| `L1-notation` | zadatak koristi notaciju koju njegov razred još nije upoznao |
| `L1-rule-outcome` | pravilo notacije navodi ishod koji izdanje nema; pravilo je preskočeno |
| `L1-rule-invalid` | pravilo notacije nije ispravno oblikovano; pravilo je preskočeno |
| `L2-folded` | reč bez dijakritika ima dvojnika s dijakritikom u korpusu |
| `L3-digraph` | reč s `lj`, `nj` ili `dž` nije u rečniku digrafa |
| `L4-orthography` | decimala s tačkom, `%` bez razmaka ispred, dva razmaka, razmak ispred znaka, ili ćirilično slovo u izvoru |
| `L5-length` | tekst zadatka ili objašnjenje je duže od dozvoljenog |
| `L6-near-duplicate` | naziv teme isti je kao ili skoro isti kao naziv druge teme |
| `L7-mixed-script` | reč meša ćirilicu i latinicu, ili je srpska reč ostala na latinici u ćiriličnom tekstu |

Pravila `lint` čitaju ove tekstove: kod teme `name`, `summary`, `unit`, `root_reason` i `mastery`; kod grane `reason`; kod zadatka `prompt`, `explanation`, tekst ponuda i `alt` slike; kod teme programa `name` i `content`; kod ishoda `text` i `unit`; kod pregleda `name`, `role` i `note`.

Dužina teksta zadatka: najviše 200 znakova u 1. i 2. razredu, 300 u 3. i 4. i 400 od 5. do 8. razreda; objašnjenje najviše 400 znakova u svim razredima.

`L7-mixed-script` se proverava na ćiriličnom tekstu koji nastaje transliteracijom izvora, a kad se `lint` pokrene iz korena repozitorijuma i `_site/cir/` postoji, i nad izgrađenim sajtom.

## 18. Kako se podaci pretvaraju u sajt

`python3 -m zg build` briše `_site/` i piše ga iznova, u oba pisma. `python3 -m zg build --check` gradi u privremenu fasciklu i ispisuje svaki fajl koji bi bio drugačiji; kod 1 ako ima razlika. `python3 -m zg serve` služi sajt na `http://127.0.0.1:8765/` i gradi ga nanovo kad se izvor promeni.

Pored stranica iz `site/`, izgradnja piše:

```
_site/
  manifest.json
  podaci/
    index.lat.json
    gN.lat.json
    ishodi/<izdanje>.lat.json
  cir/
    podaci/
      index.cyr.json
      gN.cyr.json
      ishodi/<izdanje>.cyr.json
```

- `gN` je po jedan paket za svaki razred iz `meta.json` (`g1.lat.json`, `g2.lat.json`…), a `ishodi/` nosi po jedan paket za svako izdanje.
- Latinični paketi imaju nastavak `.lat.json` i stoje u `_site/podaci/`; ćirilični imaju nastavak `.cyr.json` i stoje u `_site/cir/podaci/`.
- `_site/cir/` je celo stablo sajta na ćirilici; naslovi i tekstovi stranica i sve rečenice interfejsa su transliterovani, a veze unutar njega ostaju u `cir/`.
- `manifest.json` nosi `data` (heš latiničnog indeksnog paketa), `script` (heš izvornih fajlova sajta) i `built` (vreme izgradnje).

| Paket | Šta sadrži |
|---|---|
| `index.*.json` | `subject`, `name`, `grades`, `areas`; `topics` kao niz `{id, grade, area, unit, kind, name}`; `edges` kao niz trojki `[topic, requires, strength]`; `aliases`; `units` (razred → nazivi celina po redu); `counts` |
| `gN.*.json` | `topics`: po id-u teme `{summary, mastery, curriculum, review}`; `questions`: po id-u zadatka `{level, type, prompt, answer, explanation}`, uz `choices`, `figure`, `points_to` i `round_to` kad ih zadatak ima, i `answerRational` za numeričke zadatke |
| `ishodi/<izdanje>.*.json` | `edition`, `grade`, `applies_from`, `themes`, `outcomes` |

`review` je `null` kad tema nema evidenciju pregleda, a inače `{name, role, date, note}`.

**Šta programer koji samo čita JSON treba da zna.**

- **Id-jevi su stalni.** Id teme se nikad ne preimenuje i ne briše. Kad se tema spoji s drugom ili podeli, njen stari id ostaje u `aliases` indeksnog paketa kao „stari id“ → niz današnjih id-ova; lance nema.
- **Zadaci su označeni id-om i nemaju polje `topic`.** Tema zadatka se dobija odbacivanjem nastavka `-q<n>` (`topicOfQuestion` u `site/js/data.js`). Izraz `check` ne prelazi u paket; uz numerički zadatak stoji `answerRational`.
- **`answerRational` je `[numerator, denominator]` kao decimalni nizovi**, skraćen razlomak: `["15", "1"]`, `["3", "20"]`, `["-7", "1"]`. Kod odgovora koji se zaokružuje tu je zaokružena vrednost: uz `round_to: 2` za koren iz 12 to je `["173", "50"]`.
- **Tekstovi su transliterovani u `cyr` paketima**, celo stablo, osim vrednosti pod ključevima `id`, `outcome`, `area`, `level`, `kind`, `symbol`, `edition`, `match`, `hours`, `page`, `applies_from` i `strength`, a u slici i `unit`. Polja `answer`, `round_to` i `points_to` se prepisuju bez promene.
- **Vrednosti nabrajanja nikad se ne transliterišu.** `numeric`, `choice`, `basic`, `standard`, `hard`, `soft`, `exact`, `partial` i ostale iste su u oba paketa, pa se motor ponaša isto u oba pisma.
- Reč koja sadrži slovo koje srpski nema (`x`, `y`, `q`, `w`) ili veliko slovo usred reči (akronimi, `JavaScript`) ostaje na latinici.
- **U paketima nema** `root_reason`, `reason` grana, `check`, `data/curriculum/unmapped.json`, `data/curriculum/sources.json`, `notes` izdanja ni `data/ledger.json`.
