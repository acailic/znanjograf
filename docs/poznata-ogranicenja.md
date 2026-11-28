# Poznata ograničenja

Ovo je spisak onoga što Znanjograf jeste, a šta nije, bez uljepšavanja. Namenjen je pre svega nastavnicima. Kraći oblik ovih ograničenja stoji i na sajtu, na stranici „O projektu“.

U trenutku pisanja, 28. novembra 2026, pravi sadržaj je tek počeo da se upisuje. Postoje izdanja nastavnog programa za 1–8. razred (parafraze ishoda) i sadržaj za 1–4. razred: 112 tema, 203 grane i 448 zadataka. Za razrede 5–8 tema i zadataka još nema. Programske kapije i slepi prolaz sprovedeni su na sadržaju 1–4. razreda; nijedan nastavnik ga još nije pregledao.

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

Slepi prolaz sproveden je jednom, 27. novembra 2026, na zadacima 1. razreda. Tri rešavača su rešila svih 148 zadataka bez odgovora, objašnjenja i tema. Nijedan odgovor se nije razlikovao od banke i nijedna pogrešna ponuda nije ocenjena branjivom; jedan zadatak je imao dva branjiva odgovora, a trinaest ih je označeno zbog onoga što je rešavač morao da pretpostavi. Svi ti zadaci su dorađeni i ponovo su dati slepom rešavaču koji ih pre toga nije video, zajedno sa četiri zadatka koje je izmenio pregled grana (odeljak 4): svih sedamnaest odgovora slaže se s bankom, bez dvostrukog odgovora i bez branjive pogrešne ponude. Jedan zadatak je posle toga još jednom preformulisan, jer je reč u pitanju bila bliska pogrešnoj ponudi; i taj njegov oblik dat je novom rešavaču, pa `python3 -m zg status` pokazuje, za kapiju `blind-solve`, 148 proverenih i nijedan zastareo zadatak 1. razreda.

Za 2. razred slepi prolaz sproveden je 27. novembra 2026, na isti način: dva rešavača su rešila po 50 zadataka. Nijedan odgovor se nije razlikovao od banke i nijedna pogrešna ponuda nije ocenjena branjivom; jedan zadatak je imao dva branjiva odgovora, a sedam ih je označeno zbog onoga što je rešavač morao da pretpostavi (smer crtanja, razmera lenjira, položaji likova u opisu slike). Svi su dorađeni, a svaki zadatak čiji se tekst posle toga menjao dat je rešavaču koji ga pre toga nije video: devet, zatim tri, zatim osam koje je izmenio pregled grana (odeljak 4) i tri od njih. Svi odgovori slažu se s bankom, bez dvostrukog odgovora i bez branjive pogrešne ponude.

Ono što nije mana zadatka, a ipak se razlikuje od banke, prihvaćeno je uz zapisan razlog, ne tiho: jedanaest računa koje je rešavač napisao drugačije, a koji računaju istu vrednost; jedan odgovor kojem je rešavač dopisao jedinicu iza broja; i četiri „pretpostavke“ koje su znanje koje zadatak ispituje (koliko centimetara ima metar) ili odčitanje mere sa slike, a ne pretpostavka o tekstu. `python3 -m zg status` pokazuje, za kapiju `blind-solve`, 100 proverenih i nijedan zastareo zadatak 2. razreda.

Za 3. razred slepi prolaz sproveden je 27. novembra 2026: tri rešavača su rešila 38, 38 i 36 zadataka. Nijedan odgovor se nije razlikovao od banke i nijedan zadatak nije imao dva branjiva odgovora; jedna pogrešna ponuda ocenjena je branjivom (obrazloženje koje upoređuje samo jedan član nejednačine), pa je preformulisana, a ona i tri zadatka kojima je posle pregleda sređen tekst ili slika data su novom rešavaču. Svi odgovori slažu se s bankom, bez branjive pogrešne ponude. Uz zapisan razlog prihvaćeno je trideset pet računa drugačije napisanih: kod dva zadatka ponude su izraz i jednačina, pa je rešavač upisao njihovu vrednost, a kod jednog je rešavač prepisujući pogrešio jedno slovo. `python3 -m zg status` pokazuje, za kapiju `blind-solve`, 112 proverenih i nijedan zastareo zadatak 3. razreda.

Za 4. razred slepi prolaz sproveden je 28. novembra 2026: tri rešavača su rešila 30, 30 i 28 zadataka. Nijedan odgovor se nije razlikovao od banke i nijedan zadatak nije imao dva branjiva odgovora; jedna pogrešna ponuda ocenjena je branjivom (broj koji se može čitati i kao zaokružen na deseticu i na stotinu), a šest zadataka nisu rekla sve što treba (da su dve kocke jednake i poravnate, odakle se gleda, kakvog je oblika parka, kako je zapisana duža stranica, da je u nizu računanja vidno udruživanje činilaca, da se opis slike slaže s oblikom na njoj), pa je sedam zadataka preformulisano i dato novom rešavaču; jedan od njih je posle toga još jednom dopunjen i ponovo dat. Svi odgovori slažu se s bankom, bez branjive pogrešne ponude. Uz zapisan razlog prihvaćeno je četrdeset dva računa drugačije napisanih: kod triju su ponude izraz, razlomak i rečenica s dve vrednosti, pa je rešavač upisao vrednost. Jedna primedba rešavača na opis slike bila je pogrešna (prebrojao je polja), pa opis nije menjan. `python3 -m zg status` pokazuje, za kapiju `blind-solve`, 88 proverenih i nijedan zastareo zadatak 4. razreda.

## 3. Nema kalibracije na stvarnoj deci

Niko nije merio kako deca odgovaraju na ove zadatke. Podela na osnovne i standardne zadatke i pravilo da je „jak“ onaj odgovor koji se ne može pogoditi su dogovori autora, a ne izmerene vrednosti.

Motor dijagnostike je proveren testovima na zamišljenim učenicima (onaj koji sve zna, onaj koji ništa ne zna, onaj koji pogađa) i na oglednom korpusu. To pokazuje da motor radi kako je zamišljeno, a ne da dobro meri znanje.

## 4. Jačina grana je pedagoška procena

Za svaku granu neko je procenio da li je prethodna tema obavezna (`hard`) ili samo od pomoći (`soft`). Alat proverava da graf nema ciklusa, da tema ne zahteva samu sebe, da prethodna tema nije iz višeg razreda i da nema suvišnih grana. Ne može da proveri da li je nešto zaista obavezno.

Od toga direktno zavisi rezultat, jer dijagnostika ide unazad samo po obaveznim granama. Greška u jednom smeru šalje dijagnostiku da traži rupu gde je nema; greška u drugom preskače pravi uzrok.

Predviđen je protivnički pregled svake obavezne grane, pri kome nezavisni pregledač pita da li učenik koji nema prethodnu temu može da reši oba standardna zadatka ove. Za taj pregled ne postoji komanda; obavljenost se može samo zapisati u `data/ledger.json`. Protivnički pregled grana 1. razreda učinjen je jednom, 27. novembra 2026: čitalac koji nije pisao ni grane ni zadatke primenio je protivni test na svih tadašnjih 72 grane. Šezdeset sedam ih je prošlo. Devet primedbi razrešeno je istog dana: jedna grana je uklonjena, jedna od meke postala čvrsta, dve čvrste grane su dodate, jedan razlog je ispravljen, a četiri zadatka su preoblikovana da bi njihove grane opravdale. Te četiri nove ili izmenjene grane niko posle toga nije pregledao, pa u evidenciji stoje kao zastarele (`python3 -m zg status`: 69 važećih i 4 zastarele za kapiju `edges`).

Protivnički pregled grana 2. razreda učinjen je 27. novembra 2026: dva čitača koja nisu pisala ni grane ni zadatke primenila su protivni test na svih tadašnjih 46 grana. Dvadeset osam ih je prošlo. Osamnaest primedbi razrešeno je istog dana: devet grana je uklonjeno, četiri su od čvrstih postale meke, pet ih je dodato, a osam zadataka je preoblikovano; među njima jedan koji je tražio više nego „obim bez formula“ i dva čiji je odgovor prevazilazio brojeve do 100. Devetnaest grana koje su tada nove ili pripadaju temi s preoblikovanim zadacima data su trećem čitaču: šesnaest ih je prošlo, a tri primedbe su razrešene (jedna grana je uklonjena jer do iste teme već vodi put, a jedna meka grana zamenjena je onom koju je čitač tražio). Dve grane nastale tim razrešavanjem date su četvrtom čitaču: nova meka grana prošla je, a za čvrstu granu čitač je predložio tačniji razlog, koji je upisan. Pet grana kojima je posle toga sređen tekst razloga dato je petom čitaču i prošle su. `python3 -m zg status` pokazuje, za kapiju `edges`, 42 važeće i nijednu zastarelu granu 2. razreda.

Protivnički pregled grana 3. razreda učinjen je 27. novembra 2026, u više krugova. Tri čitaoca primenila su protivni test na svih 52 grane i dvadeset sedam ih je prošlo; dvadeset pet primedbi razrešeno je tako što je dvadeset jedna grana pretvorena u meku (dve od njih ubrzo uklonjene, jer do iste teme već vodi put), jedna meka grana koja nije pomagala ni jednom zadatku uklonjena, tri razloga ispravljena, sedam čvrstih grana dodato i jedan zadatak preoblikovan. Drugi krug, dva čitaoca na dvadeset devet novih i izmenjenih grana, bio je stroži od prvog: osam čvrstih grana nije izdržalo strog test (učenik koji ne ume standardne zadatke prethodne teme ipak rešava oba standardna zadatka ove), pa su četiri uklonjene i četiri omekšane, a jedan zadatak preoblikovan da opravda granu vraćen je na prvobitni tekst; četiri su razloga ispravljena. Treći krug, jedan čitalac na četiri grane, vratio je jednu granu među čvrste (dva od tri čitaoca drže da mora biti čvrsta) i ispravio jedan razlog; četvrti krug, jedna grana čiji se zadatak posle prvog kruga menjao, prošao je. `python3 -m zg status` pokazuje, za kapiju `edges`, 52 važeće i nijednu zastarelu granu 3. razreda.

Protivnički pregled grana 4. razreda učinjen je 28. novembra 2026, u četiri kruga. Tri čitaoca primenila su protivni test na svih 38 grana i sedamnaest ih je prošlo; šesnaest grana ocenjeno je prejakim, a pet razloga netačnim. Razrešeno je tako što je dvanaest grana pretvoreno u meke, devetnaest razloga ispravljeno i šest veza zablude u četiri zadatka skinute; dve grane su posle omekšanja postale suvišne, pa su uklonjene. Drugi krug, dva čitaoca na devetnaest izmenjenih grana: petnaest ih je prošlo, tri su vraćene među čvrste i jedna je ocenjena prejakom. Treći čitalac presudio je u dve sporne grane iste teme (jedna čvrsta, jedna meka), a četvrti je pregledao dve grane vraćene među čvrste: obe su prošle. `python3 -m zg status` pokazuje, za kapiju `edges`, 36 važećih i nijednu zastarelu granu 4. razreda.

Od 3. razreda nadalje čitaoci primenjuju test strogo: učenik koji „nije savladao“ prethodnu temu ne ume njene standardne zadatke, a osnovne može da zna. Tako se test čita zato što dijagnostika, čim učenik tačno reši standardni zadatak čiji se odgovor ne može pogoditi, izvodi da zna sve što toj temi čvrsto prethodi, bez ispitivanja (autorski vodič, odeljak 3). U 3. razredu čvrsta je manje od polovine grana (25 od 52), a u 4. razredu nešto više od polovine (21 od 36). Standardni zadaci mnogih tema rešivi su i bez standardnog nivoa prethodne teme, pa dijagnostika iz tih tema ne izvodi znanje prethodne teme preko meke grane.

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

Pravila notacije u `data/lint/notation.json` navode ishode pravih izdanja za sve razrede. I uopšte, `lint` vidi samo ono što pravila navedu: ne vidi da li je tekst razumljiv, pa ni tačan zadatak ne mora biti razumljiv detetu.

### Ono što nijedna kapija ne vidi

- **Značenje.** Nijedna kapija ne zna da li zadatak zaista ispituje temu kojoj je dodeljen, ni da li mu je nivo dobro dodeljen.
- **Primerenost uzrastu.** Nijedna kapija ne procenjuje da li su reči, kontekst i način postavljanja razumljivi detetu tog uzrastu.
- **Dvosmislenost.** Jedina provera je slepi prolaz iz odeljka 2, a on ima svoje ograničenje: rešavač je iz iste porodice modela.

Predviđena su još dva pregleda: slepi klasifikator, koji vidi samo tekst zadatka i imenuje temu, nivo i najniži razred koji ga razume, i test ponuda, koji proverava da ponude ne odaju odgovor. Za oba još ne postoje komande; u evidenciji postoje samo mesta za njih (`classify` i `cueing`).

Slepi prolaz i protivnički pregled grana sprovedeni su po jedanput, za 1–4. razred (odeljci 2 i 4); četiri grane 1. razreda izmenjene posle pregleda u evidenciji stoje kao zastarele. Oba planska pregleda, slepi klasifikator i test ponuda, nisu sprovedeni ni jednom. Evidencija prolaza (`data/ledger.json`) postoji i pokazuje šta je koja kapija videla; `python3 -m zg status` ispisuje po razredu koliko je zapisa važeće, a koliko ih je zastarelo jer se sadržaj posle promenio. `python3 -m zg all` ne proverava ni da je nešto od toga obavljeno: zapis o prolazu može biti i zastareo, a da sve kapije budu zelene.
