# Autorski vodič — kako se pišu teme, grane i zadaci

Ovo je uputstvo za svoga ko dodaje ili ispravlja sadržaj u `data/`. Šema je opisana u [formatu podataka](format-podataka.md), a pravila provere u [specifikaciji](superpowers/specs/2026-11-26-znanjograf-design.md). Posle svake izmene pokreni:

```
python3 -m zg validate && python3 -m zg verify && python3 -m zg lint
```

Sve tri komande moraju završiti sa `OK`. Ne slabite proveru da bi sadržaj prošao; ispravite sadržaj.

## 1. Osnovna pravila

- Pišete **srpskom latinicom**. Ćirilica se generiše i nikad se ne piše ručno.
- Imena polja, fajlova i vrednosti koje mašina čita (`area`, `kind`, `level`, `type`, `strength`) su **engleski**. Sve što dete ili nastavnik čita je srpski.
- Formula ide u `$…$` kao LaTeX: `$3 + 4$`, `$\frac{3}{4}$`, `$x + 5 = 12$`.
- U formuli decimalni zarez piše se `{,}`: `$3{,}5$`. Množenje je `\cdot`, deljenje `:`, procenat `15\,\%`.
- Van formule: decimalni zarez (`3,5`), razmak kao separator hiljada (`1 000 000`), razmak ispred procenta (`15 %`), jedinice latiničkim slovima (`5 cm`, `3 kg`, `60 km/h`), novac rečima (`150 dinara`).
- Varijable su latinična slova u oba pisma (`$x$`, `$a$`, `$n$`). `\text{…}` služi samo za jedinice.
- Veznik „a“ ne pisati odmah posle broja, jer se tada čita kao jedinica (ari) i ostaje latiničan. Umesto „Ima $5$ a ne $3$.“ pišite „Ima $5$, a ne $3$.“

## 2. Tema

**Zrnatost.** Jedna tema je najmanje znanje koje dete može samo da savlada ili samo da promaši, veličine jezgra jednog časa.

- Dobro: „Sabiranje do 10“, „Prelaz preko desetice“, „Pisano sabiranje“, „Množenje razlomaka“.
- Loše (preveliko): „Brojevi do 100“, „Razlomci“.
- Loše (premalo): „Sabiranje 7 + 5“, „Zbir 8 i 3“.

Novi postupak (prelaz preko desetice, pisano deljenje) jeste nova tema. Proširenje istog postupka na veće brojeve je nova tema samo ako program za njega ima poseban ishod; inače su veći brojevi nivoi zadataka.

**Id** je nepromenljiv: `mat-` + kratke reči bez dijakritika, spojene crticom, najviše 48 znakova, bez razreda u imenu. Id nikad ne menjamo ni ne brišemo; ako se teme spajaju, koristi se `data/aliases.json`.

- Dobro: `mat-sabiranje-do-20`, `mat-prelaz-preko-desetice`, `mat-jednacine-sa-jednom-nepoznatom`.
- Loše: `mat-g5-t12`, `mat-Tema12`, `mat-razlomci1`.

**Naziv** je kratak i završen: „Sabiranje do 20“, „Poređenje razlomaka“, „Površina pravougaonika“.

**Vrsta:** `concept` (pojam), `procedure` (postupak), `problem` (rešavanje problema), `reasoning` (rezonovanje).

**Oblast:** `numbers` (brojevi i algebra), `geometry` (geometrija i merenje), `data` (obrada podataka i slučajnost).

**Kriterijumi savladanosti** su dva do tri uočljiva iskaza u infinitivu ili prezentu: „sabira dva broja sa zbirom do 20“, „prelazi preko desetice pri sabiranju“. Kriterijum mora da se može videti u jednom zadatku.

**Opis** je jednu do dve rečenice roditelju: šta ovo znanje omogućava i čemu služi.

**Mapiranje.** Svaka tema navodi bar jedan ishod programa (`curriculum`), sa `match`: `exact` ili `partial`.

Redosled tema u `topics.json` je redosled iz programa. On je ujedno redosled učenja unutar razreda, pa ga ne mešete.

## 3. Grane

Grana kaže da tema A zahteva temu B pre nego što se uči.

- `hard`: bez znanja teme B u meri u kojoj je B proverena, učenik ne može da reši standardne zadatke teme A. Primer: „Sabiranje do 20“ zahteva „Brojeve do 20“.
- `soft`: B pomaže, ali nije uslov. Primer: brzo usmeno računanje pomaže pri rešavanju tekstualnih zadataka, ali nije uslov.

**Protivnički test za `hard` grane.** Zamislite učenika koji nije savladao B, a zna sve ostale prethodne teme: ne ume da reši standardne zadatke teme B, a osnovne zadatke te teme može da zna. Može li da reši oba standardna zadatka teme A? Ako može, grana je `soft` ili je nema.

Test se čita tako strogo zato što tako radi dijagnostika: čim učenik tačno reši standardni zadatak teme A čiji se odgovor ne može pogoditi, ona izvodi da zna sve što toj temi čvrsto prethodi, i ne ispituje to. Zaključak je tačan samo ako taj zadatak zaista traži znanje iz B na nivou na kom se B proverava, a ne samo osnovni nivo. Zato u višim razredima čvrstih grana ima manje nego što se na prvi pogled čini: površina kvadrata koristi množenje, ali samo ono osnovno, pa je grana ka pismenom množenju meka.

`reason` je jednom rečenicom, ljudski: „Pisano sabiranje dvocifrenih brojeva koristi usmeno sabiranje do 20.“ Kod meke grane rečenica kaže čime prethodna tema pomaže, a ne samo da nije potrebna.

Alat sam odbacuje suvišne grane. Čvrsta grana je suvišna ako postoji drugi put od A do B samo preko čvrstih grana; meka grana je suvišna ako postoji bilo koji put. Prethodna tema nikad nije iz višeg razreda od teme.

## 4. Zadaci

Svaka tema ima **najmanje dva osnovna i dva standardna** zadatka.

- `basic` je direktna primena: „Koliko je $9 + 5$?“
- Prvi `standardni` je direktan, gde god je moguće **upis broja**: „Mila ima $8$ kuvanica i kupi još $7$. Koliko kuvanica sada ima?“
- Drugi `standardni` je višekorak ili prenos: „Koliko je $6 + 5 + 4$?“

**Tipovi.** `numeric` (upis broja) je prvi izbor, jer se ne može pogoditi. `choice` služi tamo gde odgovor nije broj (naziv figure, znak poređenja) ili gde pojava pogrešnog odgovora govori o zabludi.

**Jezik.** Kratke rečenice. Naredbe u drugom licu jednine: „Izračunaj.“, „Zaokruži.“, „Upiši broj.“. Konteksti su iz života dece: kuvanice, sličice, dinari, autobus, igralište, školsko dvorište. Bez termina iz viših razreda. Dužina teksta: najviše 200 znakova u 1–2. razredu, 300 u 3–4. i 400 u 5–8.

**Odgovor (`answer`).** Za `numeric`: kanonski broj — ceo broj (`15`), decimala s tačkom u podatku (`3.5`), razlomak (`3/4`), mešovit (`2 3/4`), predznak (`-7`). U podatku decimala uvek ide s tačkom i bez separatora hiljada: `0.125` je jedna osmina, a ne sto dvadeset pet. (Za ono što učenik ukuca važi drugo pravilo: tačka i tačno tri cifre na kraju znače hiljade.) Ako je tačan odgovor iracionalan, obavezno je `"round_to": 2` (ili koliko zadatak traži). Za `choice`: id tačne ponude. Tačan odgovor nije uvek `a`.

**Ponude.** Tri do četiri. Svaka pogrešna ponuda je uobičajen pogrešan odgovor (zabluda), ne slučajan broj: prebrojana desetica, pogrešna računska operacija, sabran cifru umesto da se pomnoži. Opciono `points_to` za svaku pogrešnu ponudu navodi čvrstog pretka kog učenik verovatno nema.

**Provera (`check`).** S-izraz koji alat tačno izračuna. Rezultat mora biti jednak `answer`. Za izbor sa nenumeričkim ponudama, `check` je tekst tačne ponude.

```
"answer": "15",     "check": "(+ 8 7)"
"answer": "3/20",   "check": "(/ 3 4 5)"
"answer": "30",     "check": "(percent 15 200)"
"answer": "3.46",   "check": "(round (sqrt 12) 2)", "round_to": 2
"answer": "4",      "check": "(- (* 2 5) 6)"
"answer": "b",      "check": "<"          (za izbor)
```

Operatori: `+ - * /` (više argumenata), `pow`, `sqrt`, `abs`, `min`, `max`, `floor`, `ceil`, `round`, `mean`, `median`, `mode`, `gcd`, `lcm`, `mod`, `percent`.

**Objašnjenje (`explanation`).** Jedna do tri rečenice, korak po korak, jezikom razreda. Pokazuje se tek kad se tema presuđi.

## 5. Slike

Slika je deklarativna (`figure`) i ima `alt` od najmanje 20 znakova koji opisuje sliku dovoljno da se zadatak reši i bez nje. `alt` je običan tekst: sajt ga prikazuje bez iscrtavanja formula, pa se brojevi u njemu pišu ciframa, a ne u `$…$`. Vrste: `numberline` (brojevna prava), `fractionbar` (razlomačka traka), `pie` (kolač), `dots` (tačke), `bars` (stubičasti dijagram), `pictogram` (slikovni dijagram), `grid` (mreža), `polygon` (mnogougao), `angle` (ugao), `axes` (koordinate), `clock` (sat), `table` (tabela).

## 6. Kako posao teče

1. Napišete paket (40–60 zadataka ili teme jednog razreda).
2. `python3 -m zg validate` — šema, graf, pokrivenost.
3. `python3 -m zg verify` — da li se odgovor poklapa s računom.
4. `python3 -m zg lint` — notacija po razredu, pravopis, rečnik digrafa.
5. Slepi prolaz: nezavisnom agentu se daju samo tekstovi ćirilicom. Zadatak koji on reši pogrešno, ili za koji kaže da ima dva odgovora, vraća se na doradu.

Greška u bilo kom koraku znači da zadatak ili tema ostaju neprovereni. Ne zaobilazite kapiju; popravite sadržaj.
