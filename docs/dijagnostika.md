# Dijagnostika: kako radi

Dijagnostika je deo Znanjografa koji od izabrane teme odlazi unazad dok ne nađe najverovatnije mesto gde je znanje puklo, pa ispiše put popravke. Prvi deo ovog dokumenta je za roditelje, drugi za programere.

Kad se drugi deo ne slaže s kodom, važi kod: motor je u `site/js/engine/`, a stranicu koja ga pokreće piše `site/js/pages/diagnose.js`.

## Deo 1. Za roditelje

### Šta će dete da dobije

Dijagnostika polazi od onoga što izaberete: jedne teme s mape, svih tema jedne tematske celine, ključnih tema jednog razreda ili svih tema razreda.

Detetu se najpre postavi teži zadatak (standardni) iz prve teme na redu. Ako ga tačno reši, dijagnostika zaključuje da zna i sve što toj temi obavezno prethodi, i ide dalje. Ako ga ne reši, dete dobije lakši zadatak (osnovni) iz iste teme. Ako ni njega ne reši, dijagnostika odlazi unazad, ka temama koje ovoj prethode, i ponavlja isto: sve dok ne nađe prvu temu koju dete nije savladalo.

Odgovori ostaju u vašem pregledaču. Nema naloga, analitike ni servera koji pamti odgovore.

### Zašto postoji dugme „Ne znam“

Uz svako pitanje stoji dugme „Ne znam“. Ono je tu da dete ne bi pogađalo. Tačan pogodak prikazao bi da dete zna nešto što ne zna, pa bi rupa ostala sakrivena.

„Ne znam“ se računa kao pogrešan odgovor, ali bez druge posledice: na ekranu piše „U redu, idemo dalje.“, a ne „Netačno.“. Dijagnostika posle njega radi potpuno isto kao posle bilo kog pogrešnog odgovora.

Kod pitanja na koja se upisuje broj, sajt neće primiti prazan odgovor ni tekst koji nije broj. Kod pitanja s ponudama, redosled ponuda se meša pri svakom prikazu.

### Šta znače reči na rezultatu

Svaka tema posle provere dobija jedno od pet stanja.

| Na ekranu | Šta znači |
|---|---|
| savladano | Dete je tačno rešilo prvi standardni zadatak čiji se odgovor ne može pogoditi, ili je tačno rešilo oba standardna zadatka. |
| nesigurno | Dete je promašilo standardni zadatak, a onda tačno rešilo osnovni iz iste teme. Ili je rešilo prvi standardni zadatak čiji se odgovor mogao pogoditi, a drugi standardni promašilo. |
| nije savladano | Dete nije tačno rešilo ni osnovni zadatak iz te teme. |
| nije direktno provereno (izvedeno) | Ovoj temi nije postavljeno pitanje. Dijagnostika je izvela da je dete zna, jer je rešilo zadatak iz teme koja se bez nje ne može uraditi. |
| neprovereno | Do ove teme se nije stiglo, jer je dijagnostika zaustavljena. |

Odgovor se može pogoditi ako je ceo broj od −10 do 10. Zato se tačan takav odgovor uvek proverava još jednim zadatkom iz iste teme.

Rezultat ima još nekoliko delova. „Put popravke“ je spisak tema po redosledu, od najnižeg razreda naviše. „Teme koje treba učvrstiti“ su nesigurne teme. „Promašeni zadaci“ su zadaci koje dete nije rešilo u temi gde je puklo, s tačnim odgovorima i objašnjenjima.

### Šta znači „najverovatnije ovde je puklo“

Pod tim naslovom stoje teme za koje je dijagnostika našla da je u njima znanje najverovatnije nestalo. To su teme koje dete nije savladalo, a ispod kojih, u lancu obaveznih prethodnih znanja, nema druge nesavladane teme.

Uz svaku stoji jedna od dve oznake.

- **Potvrđeno** znači da su sve obavezne prethodne teme te teme proverene, pa se zna da rupa nije dublje od nje.
- **Nije potvrđeno do kraja** znači da neke prethodne teme nisu proverene, jer je dijagnostika zaustavljena. Rupa može biti i dublje.

**Šta to ne znači.** Ne znači da je temu potpuno zaboravilo: presuda se zasniva na jednom ili dva zadatka. Ne znači ni da je to mera njegovog znanja. Dijagnostika traži najverovatnije mesto pada; ne ocenjuje dete. Zato iznad rezultata piše da je rezultat trag, ne ocena, i na koliko se odgovora zasniva.

Ako nijedna tema nije pukla, umesto spiska piše: „Nema rupe: sve teme u opsegu su proverene i nijedna nije pukla.“ Ako se dijagnostika zaustavila pre kraja, a ništa dosad nije puklo, piše da su neke teme ostale neproverene.

### Zašto objašnjenje dolazi tek kad se tema završi

Posle svakog odgovora dete odmah vidi da li je bilo tačno. Objašnjenje zadatka vidi tek kad je presuda o temi doneta.

Razlog je u tome kako tema presuđuje: dok traje, iz iste teme može uslediti još jedan zadatak. Ako je prvi promašen, to je lakši zadatak iz iste teme; ako je tačan, a odgovor se mogao pogoditi, drugi teži. Objašnjenje prvog zadatka otkrilo bi odgovor na sledeći.

### Zašto ceo razred polazi od ključnih tema

Ako izaberete ključne teme razreda, dijagnostika ne polazi od prve teme u udžbeniku. Polazi od tema kojima se razred završava: onih koje nijedna druga tema istog razreda ne zahteva.

Ako ih dete reši, sve što im prethodi označava se kao izvedeno i preskače. Pitanja se troše samo tamo gde je nešto puklo.

### Zašto se dijagnostika može pauzirati

Jedan blok ima najviše 25 pitanja. Kad se blok napuni, dijagnostika staje i nudi „Nastavi“ ili „Vidi rezultat“.

Rezultat se može pogledati u svakom trenutku. Ako ga zaustavite na pauzi, dobijate rezultat do tada, s napomenom da se može dopuniti kad se nastavi. Započeta dijagnostika čuva se u pregledaču, pa se može nastaviti i posle zatvaranja lista.

### Rezultat je trag, ne ocena

Rezultat je znak gde da počnete, a ne slika onoga što dete zna. Zasniva se na jednom ili dva zadatka po temi, a nekad na samo jednom odgovoru.

Iz rezultata možete poneti vezu („Podeli vezu“), odštampati stranicu ili izvesti rezultat u JSON. Veza za deljenje nosi samo izbor odakle se krenulo i odgovore, bez imena i drugih podataka. Dugme „Obriši istoriju“ u zaglavlju briše započetu dijagnostiku, istoriju pitanja i izbor pisma iz pregledača.

## Deo 2. Za programere

Motor je skup čistih funkcija: bez DOM-a, bez skladišta, bez mreže. Stanje sesije je preklop (fold) njenog dnevnika, pa su vođenje, nastavak i deljenje sesije ista operacija.

### Moduli

| Modul | Izvozi |
|---|---|
| `engine/graph.js` | `buildIndex(topics, edges, aliases)` |
| `engine/verdict.js` | `STATUS`, `verdictOf(evidence)` |
| `engine/session.js` | `createSession`, `next`, `apply`, `extend`, `reduce`, `replay`, `summarise` |
| `engine/result.js` | `summarise(state)`, `statusesOf(state)` |
| `engine/answer.js` | `isStrongAnswer(question, correct)`, `isCorrect(question, response)` |
| `engine/rational.js` | `rat(num, den)`, `parseRat(text)` |
| `engine/encode.js` | `encodeSession({ scope, log })`, `decodeSession(text)` |

### Indeks grafa

`buildIndex(topics, edges, aliases)` prima oblik indeksnog paketa `podaci/index.*.json`: `topics` su `[{ id, grade, area, unit, kind, name }]`, `edges` su trojke `[topic, requires, strength]`, a `aliases` objekat „stari id“ → niz id-ova. Vraća objekat s ovim članovima:

- `topicIds`: svi id-jevi, u redosledu učenja;
- `gradeOf`, `unitOf`: mape id → razred, odnosno jedinica;
- `prereqsOf(id)`, `dependentsOf(id)`: `[{ id, strength }]`;
- `hardAncestorsOf(id)`, `ancestorsOf(id)`: skupovi bez samog `id`; prvi samo preko `hard` grana, drugi preko grana obe jačine;
- `learningOrder(ids)`: dati id-jevi u redosledu učenja; bez argumenta svi;
- `gradeExits(grade)`: izlazne teme razreda, u redosledu učenja;
- `resolveAlias(id)`: `[id]` za postojeću temu, niz ciljeva za stari id, `[]` inače.

Baca `Error("ZG_BAD_GRAPH: …")` ako grana pokazuje na nepostojeću temu ili graf ima ciklus.

**Redosled učenja** je topološki: svaka prethodna tema stoji pre teme koja je zahteva. Među temama kojima su sve prethodne već izlistane bira se ona s najmanjim ključem `(razred, mesto u fajlu, id)`. Isto pravilo važi i u `zg/corpus.py`.

**Izlazne teme** razreda su teme tog razreda koje nijedna druga tema istog razreda ne zahteva, ni `hard` ni `soft` granom.

### Stanje i dnevnik

`createSession({ scope, index, bank, budget = 25, history = {}, curriculum = {} })` vraća zamrznuto stanje s poljima `scope`, `index`, `bank`, `budget`, `history`, `curriculum`, `extensions` (na početku 0) i `log` (na početku prazan niz).

- `bank` je `{ topicId: [question, …] }`, gde svaki zadatak nosi `id` i `topic` (to im dodaje `bankOf` iz `site/js/data.js`).
- `history` je `{ questionId: broj prikazivanja }`.
- `curriculum` je `{ topicId: [{ edition, outcome, match }, …] }`.
- `log` je niz događaja `{ questionId, correct }`, redom kako su se desili.

Baca `TypeError("ZG_BAD_SCOPE: …")` za nepoznatu vrstu opsega i `TypeError("ZG_BAD_BUDGET: …")` za budžet koji nije pozitivan ceo broj.

- `next(state)` vraća `{ kind: "question", topicId, question, role }`, `{ kind: "paused", asked }` ili `{ kind: "done" }`. `role` je `"scope"` za temu iz opsega ili `"prerequisite"` za prethodnu temu.
- `apply(state, { questionId, correct })` vraća stanje s jednim događajem više. Za bilo koji drugi id pitanja, ili kad sesija ne postavlja pitanje, baca `Error("ZG_OUT_OF_SYNC")`.
- `extend(state)` dozvoljava još jedan blok (`extensions + 1`).

### Opseg

| `scope.kind` | Polja | Teme u opsegu |
|---|---|---|
| `topic` | `id` | `resolveAlias(id)` |
| `unit` | `grade`, `unit` | teme tog razreda s tom vrednošću `unit` |
| `grade` | `grade` | `gradeExits(grade)` |
| `grade-full` | `grade` | sve teme razreda |

### Redosled tema

1. Teme opsega obilaze se od najteže, u obrnutom redosledu učenja. Tema koja već ima stanje se preskače.
2. Kad tema postane `weak`, staje u **frontu**.
3. Fronta se prazni po redosledu pristizanja. Za svaku `weak` temu `w` u njoj:
   - presuđuju se njeni čvrsti preci bez stanja, od najbližeg; svaka tema koja pri tome postane `weak` staje u frontu;
   - ako posle toga nijedan čvrst predak od `w` nije `weak`, isto se radi s njenim ostalim precima: onima do kojih se dolazi samo preko meke grane.

### Presuda za jednu temu

Jedna tema dobija najviše dva pitanja.

```
prvi slobodni standardni zadatak
  nema ga                         → weak
  tačan i jak                     → mastered
  tačan, a nije jak
      drugi slobodni standardni zadatak
        nema ga                   → weak
        tačan                     → mastered
        pogrešan                  → shaky
  pogrešan
      prvi slobodni osnovni zadatak
        nema ga                   → weak
        tačan                     → shaky
        pogrešan                  → weak
```

`verdictOf(evidence)` u `engine/verdict.js` odlučuje iz `evidence`, niza `[{ question, correct }]` u redosledu postavljanja, i vraća `{ status, done }`. Dok je presuda otvorena, status je `untested` i `done` je `false`, pa pozivalac zna da treba još jedno pitanje.

`STATUS` ima pet vrednosti: `untested`, `mastered`, `shaky`, `weak`, `inferred`. Tema bez unosa u `status` je `untested`.

Zadatak koji je jednom postavljen ne bira se ponovo u istoj sesiji.

„Ne znam“ za motor je običan pogrešan odgovor (`correct: false`); dugme samo ne prolazi kroz proveru odgovora.

### Jak odgovor

`isStrongAnswer(question, correct)` je `true` samo za numerički zadatak (`type` je `numeric`) koji je tačan i čija očekivana vrednost nije ceo broj između −10 i 10. Jak je dakle svaki odgovor koji nije ceo broj, i svaki ceo broj van tog raspona. Odgovor s ponudama nikad nije jak. Jakost se gleda samo kod prvog standardnog zadatka.

Očekivana vrednost je `answerRational` (niz od dva decimalna niza), a ako ga zadatak nema, `answer` pročitan kroz `parseRat`.

`isCorrect(question, response)` za `choice` poredi `response.choiceId` s `question.answer`; za `numeric` poredi razlomak unosa s očekivanim, tačno, po brojaocu i imeniocu.

### Orezivanje: `inferred`

Kad tema postane `mastered`, svaki njen čvrst predak bez stanja dobija `inferred`. Stanje se dodeljuje jednom: tema koja ima stanje više se u toj sesiji ne ispituje, pa tema označena kao `inferred` ne dobija svoje pitanje.

### Budžet i pauza

`questionLimit(state)` je `budget × (1 + extensions)`. `next()` vraća `paused` kad je broj preuzetih događaja iz dnevnika dostigao tu granicu, a skripta još nije gotova; `asked` je tada ukupan broj pitanja u sesiji. Ako se skripta završi upravo na granici, vraća se `done`. Stranica koristi `BUDGET = 25`.

U nizu od 13 tema u kome dete na sve odgovori pogrešno treba 26 pitanja. Posle 25. `next()` vraća `{ "kind": "paused", "asked": 25 }`, a koren koji rezultat tada pokazuje ima `confirmed: false`, jer mu prethodna tema još nema stanje.

### Koreni, `confirmed` i put

`summarise(state)` se može pozvati u svakom trenutku sesije. Vraća:

- `roots`: `weak` teme kojima nijedan čvrst predak nije `weak`, u redosledu učenja. Svaka nosi `id`, `confirmed` i `missed`.
- `confirmed`: `true` ako svaki čvrst predak korena ima stanje, bilo koje, uključujući `inferred`. Koren bez čvrstih predaka je uvek potvrđen.
- `missed`: id-jevi zadataka promašenih dok se tema presuđivala, redom.
- `path`: sve `weak` teme koje leže na putu od nekog korena do teme iz opsega, po čvrstim granama, i `shaky` teme na tim putevima; u redosledu učenja, svaka s `id` i `status`. Za koren koji do opsega dolazi samo preko mekih grana, put samo tog korena sme i preko njih.
- `shaky`: `id` svake `shaky` teme, u redosledu učenja.
- `counts`: `{ mastered, shaky, weak, inferred, untested }`.
- `untested`: `id` svake teme iz opsega bez stanja, u redosledu učenja. Samo iz opsega: neprovereni preci ovde ne ulaze.
- `outcomes`: `{ edition, id }` za svaki ishod korena i puta, svaki jednom; polje `match` se ne prenosi.

`statusesOf(state)` vraća mapu id → status svake teme koja ima stanje.

### Izbor zadatka, rotacija i istorija

Izbor je određen: za isti opseg, dnevnik i istoriju motor uvek traži isto pitanje.

- Od nekorišćenih zadataka traženog nivoa bira se onaj s najmanjim brojačem u `history`; ako su brojači jednaki, onaj koji u fajlu stoji prvi.
- Stranica posle svakog odgovora poziva `pushHistory([question.id])`, pa ponovna dijagnostika iste teme prvo traži zadatke koji su najduže nekorišćeni.

### Ponovno preslikavanje

Ništa se ne pamti osim dnevnika i broja produžetaka: svako pitanje motor izračunava tako što ponovo provodi skriptu kroz dnevnik.

- `replay(state)` je jedino mesto gde se skripta pokreće. Vraća `{ scopeIds, world, pending }`; `world` nosi mape `status` i `missed`, skup `used` i frontu `queue`.
- `reduce(log, ctx)` gradi stanje iz dnevnika. Događaj koji ne odgovara pitanju koje motor u tom trenutku traži prekida preslikavanje na tom mestu, i sve posle njega se odbacuje. Ako dnevnik nastavlja posle pauze, blok se produžuje.
- Kad nastavlja sačuvanu sesiju ili otvara deljeni link, stranica motoru daje istoriju u kojoj svaki zadatak iz dnevnika ima brojač manji od svakog stvarnog (`replayHistory` u `diagnose.js`: prvo pitanje najmanji, poslednje najveći). Tako motor ponovo bira upravo one zadatke.

### Šta radi stranica

Stranica ne drži svoje stanje: posle svakog odgovora upisuje sesiju u skladište i crta ekran nanovo iz onoga što skladište drži.

- Sačuvana sesija je `{ v: 1, scope, log, history, extensions, finished, updated }` pod `zg.session.v1`.
- `plan()` odlučuje šta je sa sačuvanom sesijom kad se stranica otvori. Adresa koja imenuje drugi opseg započinje novu dijagnostiku, s vezom „Nastavi započetu dijagnostiku“ nazad na sačuvenu. Sačuvana završena sesija pokazuje svoj rezultat, a nezavršena se nastavlja.
- Sačuvana sesija čiji opseg nema više nijednu temu, ili čiji dnevnik motor ne može da preslika, odbacuje se, a stranica to kaže.
- Posle odgovora stranica prikazuje samo „Tačno.“, „Netačno.“ ili „U redu, idemo dalje.“. Objašnjenje zadatka ulazi u poruku (`feedbackMarkup` u `site/js/ui/question.js`) tek kad je tema presuđena (`settled` u `diagnose.js`).
- Traka napretka pokazuje „Teme: … od …“ (teme opsega) i „Pitanja: …“.
- Kad `next(state).kind` jeste `paused`, rezultat nudi „Nastavi dijagnostiku“, koje produžava blok.
- `storage` događaj iz drugog lista, kojim se menja sesija ili istorija, ponovo crta stranicu.
- „Izvezi u JSON“ preuzima datoteku `znanjograf-rezultat.json` s `{ format, version, exported, script, scope, log, summary }`.

### Deljeni link

`encodeSession({ scope, log })` vraća `"v1."` i base64url UTF-8 JSON-a `{"scope", "log"}`, bez dopune. `scope` nosi samo ključeve svoje vrste (`kind`, `id`; ili `kind`, `grade`, `unit`; ili `kind`, `grade`), a `log` samo `questionId` i `correct`. `decodeSession(text)` vraća `{ scope, log }` ili `null`.

- Link je `dijagnostika/#rezultat=<kod>`; fragment adrese ne odlazi serveru.
- Odbijaju se više od 1000 događaja, tekst duži od 200 000 znakova i naziv celine ili id pitanja duži od 200 znakova.
- Rezultat iz linka je samo za čitanje i računa se s praznom istorijom.

### localStorage

| Ključ | Šta drži |
|---|---|
| `zg.session.v1` | započetu ili završenu sesiju |
| `zg.history.v1` | `{ questionId: broj prikazivanja }` |
| `zg.prefs.v1` | podešavanja; danas samo `script` (`"lat"` ili `"cyr"`) |

Svaki pristup skladištu je obavijen u `try/catch`, pa sajt radi i kad je skladište zabranjeno. Dugme „Obriši istoriju“ briše sva tri ključa (`clearAll` u `site/js/storage.js`).

### Primer

Ovaj primer drži test `tests/node/documented-example.test.js`: ako se motor promeni, test pada i primer se mora prepraviti; primer se ne sme menjati bez puštanja kroz motor.

Pet tema u jednom nizu i jedna sa strane. A, B i C su u 1. razredu, D, P i E u 2. razredu; A je koren. Svaka tema niza čvrsto zahteva prethodnu. E ima još jednu prethodnu temu, P, do koje dolazi mekom granom, a P čvrsto zahteva A. Meki predci dolaze na red tek kad se čvrsti ne pokažu kao rupa, pa se P u glavnom slučaju uopšte ne pita. Tekstovi zadataka i id-jevi ishoda su iz oglednog korpusa (`tests/fixtures/raw.py`) i ne odgovaraju ishodima pravog izdanja `g1-2026`; zadatak A-q3 je ovde numerički.

| Oznaka | `id` | Naziv | Razred |
|---|---|---|---|
| A | `mat-brojevi-do-10` | Brojevi do 10 | 1 |
| B | `mat-sabiranje-do-10` | Sabiranje do 10 | 1 |
| C | `mat-sabiranje-do-20` | Sabiranje do 20 | 1 |
| D | `mat-sabiranje-do-100` | Sabiranje do 100 | 2 |
| E | `mat-zadaci-sa-sabiranjem` | Zadaci sa sabiranjem | 2 |
| P | `mat-poredjenje-do-100` | Poređenje brojeva do 100 | 2 |

Grane su sve `hard`: B zahteva A, C zahteva B, D zahteva C i E zahteva D. Redosled učenja je A, B, C, D, E. Izlazna tema 2. razreda je samo E.

| Zadatak | Nivo | Tekst | Odgovor |
|---|---|---|---|
| A-q1 | osnovni | Koji broj dolazi posle broja $6$? | 7 |
| A-q2 | osnovni | Koji broj dolazi pre broja $5$? | 4 |
| A-q3 | standardni | Koji je najveći broj: $6$, $9$, $3$ ili $8$? Upiši taj broj. | 9 |
| A-q4 | standardni | U nizu $4$, $5$, ____, $7$ koji broj nedostaje? | 6 |
| B-q1 | osnovni | Koliko je $3 + 4$? | 7 |
| B-q2 | osnovni | Koliko je $2 + 6$? | 8 |
| B-q3 | standardni | Mila ima $5$ kuvanica, a Pera $2$. Koliko kuvanica imaju zajedno? | 7 |
| B-q4 | standardni | Koliko je $2 + 3 + 4$? | 9 |
| C-q1 | osnovni | Koliko je $9 + 5$? | 14 |
| C-q2 | osnovni | Koliko je $7 + 6$? | 13 |
| C-q3 | standardni | Mila ima $8$ kuvanica i kupi još $7$. Koliko kuvanica sada ima? | 15 |
| C-q4 | standardni | Koliko je $6 + 5 + 4$? | 15 |
| D-q1 | osnovni | Koliko je $23 + 45$? | 68 |
| D-q2 | osnovni | Koliko je $40 + 37$? | 77 |
| D-q3 | standardni | Koliko je $36 + 28$? | 64 |
| D-q4 | standardni | U autobusu su $26$ putnika. Na sledećoj stanici ušlo je još $19$. Koliko putnika sada ima u autobusu? | 45 |
| E-q1 | osnovni | Mila ima $24$ sličice, a Pera $15$. Koliko sličica imaju zajedno? | 39 |
| E-q2 | osnovni | U kutiji su $33$ crvene i $26$ plavih kuglica. Koliko kuglica ima u kutiji? | 59 |
| E-q3 | standardni | Mila je pročitala $18$ stranica ujutru, $22$ posle podne i $10$ uveče. Koliko stranica je pročitala tog dana? | 50 |
| E-q4 | standardni | Pera je imao $35$ dinara. Dobio je $20$ dinara od bake i $15$ od dede. Koliko dinara sada ima? | 70 |
| P-q3 | standardni | Koji znak treba upisati: $56$ ____ $65$? Ponude su $>$, $<$ i $=$. | $<$ |
| P-q1 | osnovni | Koji je broj veći: $34$ ili $43$? Upiši taj broj. | 43 |

Teme od A do E imaju po četiri `numeric` zadatka, a prikazana su sva. Od P se u primeru pokušavaju samo P-q3 i P-q1. Odgovori tema A i B nisu jaki, jer su celi brojevi između −10 i 10. Odgovori tema C, D i E jaki su. P-q3 je zadatak s ponudama, pa njegov odgovor nikad nije jak.

**Dete na sve odgovori „Ne znam“.** Opseg je `{ "kind": "topic", "id": "mat-zadaci-sa-sabiranjem" }`, budžet je 25, istorija je prazna.

| # | Zadatak | Tema | `role` | Zašto baš taj |
|---|---|---|---|---|
| 1 | E-q3 | E | `scope` | prvi zadatak: najteža tema opsega i njen prvi standardni zadatak |
| 2 | E-q1 | E | `scope` | prvi je promašen, pa ide osnovni; i on je promašen, pa je E `weak` i staje u frontu |
| 3 | D-q3 | D | `prerequisite` | čvrsti preci od E, od najbližeg: D nema stanje |
| 4 | D-q1 | D | `prerequisite` | D je `weak` i staje u frontu |
| 5 | C-q3 | C | `prerequisite` | sledeći čvrsti predak |
| 6 | C-q1 | C | `prerequisite` | C je `weak` |
| 7 | B-q3 | B | `prerequisite` | sledeći čvrsti predak |
| 8 | B-q1 | B | `prerequisite` | B je `weak` |
| 9 | A-q3 | A | `prerequisite` | poslednji čvrsti predak |
| 10 | A-q1 | A | `prerequisite` | A je `weak` |

Posle desetog pitanja fronta je `[E, D, C, B, A]`. Za E, D, C i B svi čvrsti preci imaju stanje, a bar jedan je `weak`, pa se meki preci ne gledaju. A nema ni čvrste ni druge pretke. Skripta je gotova: `next()` vraća `{ "kind": "done" }`, bez pauze, jer je 10 manje od 25.

Svih pet tema su `weak`. `summarise(state)` vraća:

```json
{
  "roots": [
    {
      "id": "mat-brojevi-do-10",
      "confirmed": true,
      "missed": ["mat-brojevi-do-10-q3", "mat-brojevi-do-10-q1"]
    }
  ],
  "path": [
    {"id": "mat-brojevi-do-10", "status": "weak"},
    {"id": "mat-sabiranje-do-10", "status": "weak"},
    {"id": "mat-sabiranje-do-20", "status": "weak"},
    {"id": "mat-sabiranje-do-100", "status": "weak"},
    {"id": "mat-zadaci-sa-sabiranjem", "status": "weak"}
  ],
  "shaky": [],
  "counts": { "mastered": 0, "shaky": 0, "weak": 5, "inferred": 0, "untested": 0 },
  "untested": [],
  "outcomes": [
    {"edition": "g1-2026", "id": "g1-2026-001"},
    {"edition": "g1-2026", "id": "g1-2026-005"},
    {"edition": "g1-2026", "id": "g1-2026-002"},
    {"edition": "g1-2026", "id": "g1-2026-003"},
    {"edition": "g2-2026", "id": "g2-2026-001"},
    {"edition": "g2-2026", "id": "g2-2026-004"}
  ]
}
```

Koren je samo A: jedina je `weak` tema kojoj nijedan čvrst predak nije `weak`, a prethodnih tema uopšte nema, pa je potvrđen. Put obuhvata svih pet tema. Promašeni zadaci su oba zadatka iz A.

Roditelj tada na ekranu vidi odeljak „Najverovatnije ovde je puklo“ s temom Brojevi do 10, oznakom „potvrđeno“ i mestom „1. razred · Brojevi“; pod njim „Promašeni zadaci“ s A-q3 i A-q1. „Put popravke“ ima teme A, B i C pod „1. razred“ i D i E pod „2. razred“, sve sa statusom „nije savladano“. Odeljak „Teme koje treba učvrstiti“ pokazuje „Nema takvih tema.“

**Za poređenje, tri kraća slučaja na istom grafu.** Redosled brojeva u `counts` je `mastered`, `shaky`, `weak`, `inferred`, `untested`.

| Šta dete radi | Pitanja | Ishod |
|---|---|---|
| Na E-q3 tačno odgovori 50 | 1 | 50 je jak odgovor, pa je E `mastered`, a D, C, B i A `inferred`. `roots` i `path` su prazni; `counts` su 1, 0, 0, 4, 0. |
| „Ne znam“ na E-q3 i E-q1, a na D-q3 tačno odgovori 64; „Ne znam“ i na P-q3 i P-q1 | 5 | E je `weak`; D je `mastered`, pa su C, B i A `inferred`. Nijedan čvrst predak E nije `weak`, pa motor pita i njenu meku prethodnu temu P. I P je `weak`. Koreni su P i E, oba potvrđena, svaki s oba promašena zadatka u `missed`; `path` je P pa E; `counts` su 1, 0, 2, 3, 0. |
| „Ne znam“ na E-q3, a na E-q1 tačno odgovori 39 | 2 | E je `shaky` i ništa drugo se ne ispituje. `roots` i `path` su prazni, `shaky` je samo E, `counts` su 0, 1, 0, 0, 0. Stranica tada pokazuje da nema rupe. |
