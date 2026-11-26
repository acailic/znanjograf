# Poznata ograničenja

Ovo je spisak onoga što Znanjograf jeste, a šta nije, bez uljepšavanja. Namenjen je pre svega nastavnicima. Kraći oblik ovih ograničenja stoji i na sajtu, na stranici „O projektu“.

U trenutku pisanja, 27. novembra 2026, pravi sadržaj je tek počeo da se upisuje. Postoje izdanja nastavnog programa za 1–6. razred (parafraze ishoda), a nema nijedne prave teme, grane ni zadatka: oni postoje samo u oglednom korpusu za testove. Zato nijedna od provera opisanih ovde nije još sprovedena na pravom materijalu.

Zato na svakoj stranici sajta, odmah ispod zaglavlja, stoji napomena o tome šta je upisano. Gradnja je ispisuje iz podataka i sama je sklanja kad svaki razred dobije teme s zadacima, pa ne može da ostane da stoji kad više ne važi.

## 1. Sadržaj pišu AI modeli, bez nastavnika

Teme, grane, zadatke i parafraze ishoda pišu AI modeli po [autorskom vodiču](autorski-vodic.md), a proveravaju ih programske kapije opisane na kraju ovog dokumenta. Nijednu temu do sada nije pregledao nastavnik, jer evidencija pregleda (`data/review/teachers.json`) nije ni napravljena. Dok se ne upiše prvi nastavnički pregled, svaki zadatak, grana i opis teme treba čitati kao nacrt.

Kako nastavnik može da pregleda sadržaj:

- **Na sajtu.** Stranica svake teme na mapi pokazuje opis teme, kriterijume savladanosti, ishode programa sa stranicom akta, prethodne teme i jedan probni zadatak s odgovorom. Ostali zadaci te teme tu nisu.
- **U repozitorijumu.** Svi zadaci jednog razreda stoje u `data/math/gN/questions.json`. To je običan tekst i može se čitati i bez znanja programiranja.
- **Prijavom greške.** Dugme „Prijavi grešku“ na stranici teme otvara na GitHubu obrazac za novu prijavu, s upisanom oznakom teme. Postoje i obrazci „Greška u zadatku“ i „Greška u temi ili grani“ (`.github/ISSUE_TEMPLATE/`).
- **Zapisom pregleda.** Kad nastavnik pregleda temu, pregled se upisuje u `data/review/teachers.json`: ime, uloga, datum i po želji napomena. Sajt tada na stranici teme prikazuje „Pregledao nastavnik: …“.

Ta oznaka je izjava osobe koja je upisana, i ništa više. Alat proverava samo oblik zapisa i to da tema postoji; ne proverava da je pregled obavljen, ni da je osoba nastavnik.

Danas ne postoji list za štampu sa svim zadacima jednog razreda: predviđen je planom, ali komanda koja ga pravi još nije napisana. Ne postoji ni automatska veza između prijave na GitHubu i provere; prijavljena greška se sama ne ubacuje u slepi prolaz.

## 2. „Slepi“ rešavač je iz iste porodice modela

Slepi prolaz je jedina provera da li je tekst zadatka dvosmislen. Rešavaču se daju samo tekstovi zadataka, bez odgovora, objašnjenja, nivoa i teme (`python3 -m zg blind sheet --grade <razred>`). On vraća svoj odgovor i svoj račun, da li je tačno jedan odgovor branjiv, sve što je morao da pretpostavi i ocenu svake pogrešne ponude; `python3 -m zg blind diff --grade <razred> --answers <fajl>` to poredi s bankom i svaka razlika ruši zadatak.

Taj rešavač je AI model, iz iste porodice modela koja je pisala i same zadatke. Zato „slep“ nije potpuno slep: model može da razume zadatak onako kako ga je pisac mislio, a ne onako kako bi ga razumelo dete. Slepi prolaz ne zamenjuje nezavisnu ljudsku proveru.

## 3. Nema kalibracije na stvarnoj deci

Niko nije merio kako deca odgovaraju na ove zadatke. Podela na osnovne i standardne zadatke i pravilo da je „jak“ onaj odgovor koji se ne može pogoditi su dogovori autora, a ne izmerene vrednosti.

Motor dijagnostike je proveren testovima na zamišljenim učenicima (onaj koji sve zna, onaj koji ništa ne zna, onaj koji pogađa) i na oglednom korpusu. To pokazuje da motor radi kako je zamišljeno, a ne da dobro meri znanje.

## 4. Jačina grana je pedagoška procena

Za svaku granu neko je procenio da li je prethodna tema obavezna (`hard`) ili samo od pomoći (`soft`). Alat proverava da graf nema ciklusa, da tema ne zahteva samu sebe, da prethodna tema nije iz višeg razreda i da nema suvišnih grana. Ne može da proveri da li je nešto zaista obavezno.

Od toga direktno zavisi rezultat, jer dijagnostika ide unazad samo po obaveznim granama. Greška u jednom smeru šalje dijagnostiku da traži rupu gde je nema; greška u drugom preskače pravi uzrok.

Predviđen je protivnički pregled svake obavezne grane, pri kome nezavisni pregledač pita da li učenik koji nema prethodnu temu može da reši oba standardna zadatka ove. Za taj pregled ne postoji komanda; obavljenost se može samo zapisati u `data/ledger.json`. Do sada nijedna grana nema takav zapis.

## 5. Rezultat dijagnostike je trag, ne ocena

Presuda o jednoj temi zasniva se na jednom ili dva zadatka. Dete koje jednom pogreši iz nepažnje dobiće „nesigurno“, a ako pogreši oba puta „nije savladano“; dete koje pogodi može dobiti „nesigurno“ ili „savladano“.

Oznaka „nije direktno provereno“ znači da je motor izveo znanje, a nije pitao. Oznaka „nije potvrđeno do kraja“ znači da rupa može biti dublje nego što rezultat pokazuje.

Rezultat se ne upisuje nigde: ostaje u pregledaču, osim ako ga ne podelite ili ne izvezete. Nije ocena i ne zamenjuje nastavnikov uvid; polazište je za razgovor s detetom.

## 6. Sadržaj prati programe koji važe u 2026/27.

Teme su vezane za ishode programa koji važe u školskoj 2026/27. Od 2027/28. menjaju se programi za 1. i 5. razred i planovi za sve razrede, pa će tada deo sadržaja morati da se pregleda i dopuni.

Tekstovi ishoda u repozitorijumu su parafraza, a ne bukvalan tekst akta. Za tačan tekst treba pogledati akt i stranu navedenu uz svaki ishod ([program](program.md)).

Planirano je i izdanje za 2027/28. za 1. i 5. razred. U trenutku pisanja ono nije upisano, a stranica „O projektu“ to i kaže.

## 7. Znanjograf nije zvaničan

Znanjograf nije zvaničan ni povezan sa Ministarstvom prosvete. Nastavni program je javni akt i čita se u izvorima navedenim u dokumentu [program](program.md), ali su teme, grane i zadaci delo projekta.

Zato se Znanjograf ne može citirati kao zvanično tumačenje programa. Ako se sadržaj sajta ne slaže s aktom, važi akt, a razlika je greška koju treba prijaviti.

## Šta mašina proverava, a šta ne može da vidi

Svaku izmenu u `data/` propuštaju tri programske kapije. One vide oblik i račun, a ne značenje.

### Tri kapije

| Kapija | Komanda | Šta proverava | Šta ne može da vidi |
|---|---|---|---|
| `validate` | `python3 -m zg validate` | oblik zapisa i dozvoljene vrednosti, id-jeve, graf (ciklusi, razredi, suvišne grane, koreni), pokrivenost ishoda, broj i oblik zadataka i ponuda, slike, da su oznake `$` formula uparene | da li je tema smislena celina, da li ishod zaista pripada temi, da li je grana zaista obavezna, da li je parafraza verna izvoru |
| `verify` | `python3 -m zg verify` | da li se izraz `check` tačno izračuna i poklopi s `answer`, i da li kod ponuda samo tačna daje odgovor | da li tekst zadatka vodi do tog odgovora (isti autor piše i odgovor i račun), da li je objašnjenje tačno, da li su pogrešne ponude zablude a ne slučajni brojevi |
| `lint` | `python3 -m zg lint` | notaciju po razredu, reči bez dijakritika, rečnik digrafa, decimalne tačke i razmake, dužinu teksta, skoro iste nazive tema, mešana pisma u ćiriličnom izlazu | da li je tekst razumljiv uzrastu, gramatiku i stil, i terminologiju koja nije u pravilima notacije |

`python3 -m zg all` pokreće sve tri. Pad bilo koje znači da sadržaj nije gotov; provera se ne sme slabiti da bi sadržaj prošao.

Pravila notacije u `data/lint/notation.json` navode ishode pravih izdanja, osim za stepen, kvadratni koren i broj pi: za njih još upućuju na mesto koje čeka izdanje 7. razreda (privremena oznaka `g7-2026-000`), pa se ta pravila ne mogu proveriti protiv programa. I uopšte, `lint` vidi samo ono što pravila navedu: ne vidi da li je tekst razumljiv, pa ni tačan zadatak ne mora biti razumljiv detetu.

### Ono što nijedna kapija ne vidi

- **Značenje.** Nijedna kapija ne zna da li zadatak zaista ispituje temu kojoj je dodeljen, ni da li mu je nivo dobro dodeljen.
- **Primerenost uzrastu.** Nijedna kapija ne procenjuje da li su reči, kontekst i način postavljanja razumljivi detetu tog uzrastu.
- **Dvosmislenost.** Jedina provera je slepi prolaz iz odeljka 2, a on ima svoje ograničenje: rešavač je iz iste porodice modela.

Predviđena su još dva pregleda: slepi klasifikator, koji vidi samo tekst zadatka i imenuje temu, nivo i najniži razred koji ga razume, i test ponuda, koji proverava da ponude ne odaju odgovor. Za oba još ne postoje komande; u evidenciji postoje samo mesta za njih (`classify` i `cueing`).

Slepi prolaz, protivnički pregled grana i oba planska pregleda nisu do sada sprovedeni ni jednom. U repozitorijumu nema pravih tema ni zadataka, a evidencija prolaza (`data/ledger.json`) ne postoji. `python3 -m zg all` ne proverava ni da je nešto od toga obavljeno: zapis o prolazu može biti i zastareo, a da sve kapije budu zelene.
