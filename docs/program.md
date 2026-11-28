# Program: odakle dolazi sadržaj

Znanjograf vezuje svaku temu za nastavni program iz matematike koji važi u osnovnoj školi u Republici Srbiji. Ovaj dokument objašnjava koji akt važi za koji razred, kako se to zapisuje u repozitorijumu i kako se proverava da li je sve pokriveno. Namenjen je nastavnicima i stručnjacima obrazovanja; tehnički detalji oblika zapisa stoje u [formatu podataka](format-podataka.md).

**Znanjograf nije zvaničan ni povezan sa Ministarstvom prosvete.** Programi su javni akti, ali su teme, grane i zadaci pisani za ovaj projekat i nisu deo tih akata.

## 1. Koji akt važi u školskoj 2026/27.

Nastavni program donosi ministar prosvete, i to pravilnikom koji se objavljuje u „Službenom glasniku Republike Srbije – Prosvetni glasnik“. Program je poseban pravilnik za svaki razred, a plan nastave (fond sati) je pravilnik po ciklusu: za 1–4. razred, za 5–6. razred i za 7–8. razred.

U školskoj 2026/27. godini svih osam razreda radi po programima donetim 2017–2019. godine, s kasnijim dopunama.

| Razred | Akt koji važi u 2026/27. | „Sl. glasnik RS – Prosvetni glasnik“ |
|---|---|---|
| 1. | „Pravilnik o planu nastave i učenja za prvi ciklus osnovnog obrazovanja i vaspitanja i programu nastave i učenja za prvi razred osnovnog obrazovanja i vaspitanja“ | 10/2017, 12/2018, 15/2018, 18/2018, 1/2019, 2/2020, 16/2022, 1/2023 – ispravka, 13/2023, 14/2023 i 11/2024 |
| 2. | „…o programu nastave i učenja za drugi razred…“ | 16/2018, 3/2019, 5/2021 i 13/2023 |
| 3. | „…za treći razred…“ | 5/2019, 1/2020, 6/2020, 7/2022 i 13/2023 |
| 4. | „…za četvrti razred…“ | 11/2019, 6/2020, 7/2021, 1/2023 i 13/2023 |
| 5. i 6. | „Pravilnik o planu nastave i učenja za peti i šesti razred osnovnog obrazovanja i vaspitanja i programu nastave i učenja za peti i šesti razred osnovnog obrazovanja i vaspitanja“ | 15/2018, 18/2018, 3/2019, 3/2020, 6/2020, 17/2021, 16/2022, 13/2023, 14/2023, 3/2024 i 6/2025 |
| 7. | plan za 7. i 8. razred, i „…o programu nastave i učenja za sedmi razred…“ | plan: 18/2018 i 13/2023; program: 5/2019, 1/2020, 6/2020, 8/2020, 5/2021, 17/2021, 16/2022, 13/2023, 14/2023 i 6/2025 |
| 8. | isti plan za 7. i 8. razred, i „…za osmi razred…“ | plan: 18/2018 i 13/2023; program: 11/2019, 2/2020, 6/2020, 5/2021, 17/2021, 16/2022, 13/2023, 14/2023, 4/2024 i 6/2025 |

Znak „…“ u tabeli znači da je naziv ili spisak brojeva glasnika ovde skraćen. Puni naziv svakog akta, s brojevima glasnika, adresom teksta i danom preuzimanja, čuva se u `data/curriculum/sources.json`; unosi za svih sedam akata su upisani.

## 2. Novi programi od 2027/28.

„Službeni glasnik RS – Prosvetni glasnik“ broj 1/2026 od 26.2.2026. donosi nove programe za 1. i 5. razred (matematika je među njima), novi plan za 7–8. razred i novi plan za 1–4. i 5–6. razred. Član 2 kaže da se sva tri primenjuju od školske 2027/2028. godine. Reč „pilot“ ne stoji ni u jednom od njih.

To znači da se u školskoj 2026/27. novi programi još ne primenjuju. Sadržaj Znanjografa prati programe koji važe u 2026/27.

## 3. Fond časova matematike

| Razred | Časova nedeljno | Časova godišnje |
|---|---|---|
| 1–4. | 5 | 180 |
| 5. i 6. | 4 | 144 |
| 7. | 4 | 144 |
| 8. | 4 | 136 |

U izdanju se fond sati zapisuje samo po temi programa (polje `hours`), i to kad ga dokument ima. Nedeljni i godišnji fond ovde su navedeni radi orijentacije; u repozitorijumu ne postoji zasebno polje za njih.

## 4. Tri oblasti

Sav sadržaj je raspoređen u tri oblasti: brojevi i algebra, geometrija i merenje, obrada podataka i slučajnost. Ta podela prati nove programe i pravilnik o standardima postignuća („Sl. glasnik RS“ 104/2024), a u repozitorijumu je zajednička za sve razrede.

## 5. Šta je „izdanje“ u repozitorijumu

Jedno **izdanje** (edition) jeste program nastave i učenja jednog razreda onakav kakav važi u jednoj školskoj godini. Id izdanja glasi `gN-YYYY`: `N` je razred, a `YYYY` je godina u kojoj ta školska godina počinje.

- `g1-2026` je program 1. razreda koji važi u školskoj 2026/27.
- `g1-2027` biće program 1. razreda koji važi od 2027/28, po novom programu iz Prosvetnog glasnika 1/2026. Isto važi za 5. razred (`g5-2027`).

Za svako izdanje postoji jedan fajl, `data/curriculum/math/<id izdanja>.json`, s temama programa i ishodima. U njemu polje `applies_from` nosi školsku godinu od koje program važi, npr. `2026/27`.

Svaka tema navodi bar jedan ishod i izdanje kome on pripada. Id teme nema razred u sebi i ne menja se, pa ista tema može stajati u starom i u novom izdanju ako se njeno znanje nije promenilo. Plan je da se za 1. i 5. razred upišu oba izdanja i da se njihove teme mapiraju na oba, da skup ne zastari za godinu dana.

## 6. Kako se gradi id ishoda

Id ishoda ima tri dela, `gN-YYYY-NNN`: razred, izdanje i trocifreni broj koji razlikuje ishode unutar izdanja. Na primer, `g1-2026-012` je ishod 1. razreda u izdanju koje važi od 2026/27.

- Id nosi godinu izdanja, pa se isti ishod u novom izdanju upisuje pod novim id-om (`g1-2027-…`).
- Alat proverava oblik id-a i to da se u jednom izdanju ne ponovi (`V3-id-format`, `V3-id-duplicate`). Redosled brojeva ne proverava.
- Uz svaki ishod obavezno stoji `page`: broj štampane strane u aktu na kojoj ishod stoji.

## 7. Parafraza umesto bukvalnog teksta

Tekstovi ishoda u repozitorijumu nisu preneti bukvalno. Za svaki ishod stoji **parafraza**: isto značenje, sopstvene reči, uz broj štampane strane u aktu.

Zašto je to tako:

- ZUOV objavljuje sadržaj svog sajta, s koga se preuzimaju tekstovi pravilnika, pod licencom Creative Commons Autorstvo–Nekomercijalno–Bez prerada 3.0 Srbija (CC BY-NC-ND 3.0 RS).
- Sami pravilnici sastavni su deo akata.
- Kopija člana 6. Zakona o autorskom i srodnim pravima koja je pročitana kaže da zakoni i podzakonski akti nisu autorska dela. Ta kopija nije proverena prema važećem tekstu.

Zato repozitorijum čuva parafrazu svakog ishoda s uputom na akt i stranu, dok vlasnik prava ne odluči drugačije. Bukvalan tekst ne ulazi u repozitorijum.

Odluka je zapisana u `data/curriculum/sources.json` (`rule`, `evidence`, `acts`). Planirano je da svaku parafrazu sa značenjem izvora poredi neko ko je nije pisao. Nijedna komanda ne proverava kako je parafraza napisana; alat proverava samo da ishod postoji, da ima stranu i da je pokriven temom.

## 8. Kako se proverava pokrivenost

Pokrivenost se proverava u oba smera, komandom `python3 -m zg validate`:

- Svaka tema navodi bar jedan ishod koji stvarno postoji u izdanju (`V7-topic-without-outcome`, `V7-outcome-missing`).
- Tematska celina teme (`unit`) jeste tema bar jednog izdanja koje tema navodi (`V7-topic-unit`).
- Svaki ishod svakog izdanja ili pokriva bar jedna tema, ili je upisan u `data/curriculum/unmapped.json` s razlogom (`V7-outcome-unmapped`).
- Unos u `unmapped.json` koji više ne treba je greška (`V7-unmapped-stale`).
- Zaglavlje fajla izdanja mora odgovarati svom imenu (`V7-edition-grade`).

Koliko temu pokriva ishod kaže polje `match`: `exact` znači da tema pokriva ceo ishod, a `partial` da pokriva deo. To je procena autora teme; alat proverava samo da je vrednost jedna od te dve.

`python3 -m zg report` ispisuje po razredu koliko ima tema, grana, zadataka i ishoda. Na stranici teme na sajtu svaki ishod pokazuje svoj tekst, id i stranu, i da li ga tema pokriva celog ili delimično.

## 9. Zvanična mesta

- ZUOV: `https://zuov.gov.rs/`
- Pravno-informacioni sistem: `https://pravno-informacioni-sistem.rs/`
- Institut za vrednovanje: `https://ceo.edu.rs/`

## Šta još nije upisano

U trenutku pisanja, 27. novembra 2026, upisana su izdanja za svih osam razreda: u `data/curriculum/math/` stoji po jedan fajl za svaki razred, s temama programa i ishodima upisanim po pravilu parafraze, uz uputu na akt i stranu. U `data/curriculum/sources.json` stoje unosi za svih sedam akata (5. i 6. razred dele isti pravilnik).

Teme su upisane za 1–4. razred (112 tema s 448 zadataka), i svaki ishod izdanja `g1-2026` do `g4-2026` pokriva bar jedna tema. Za razrede 5–8 teme još nisu upisane, pa njihovi ishodi privremeno stoje u `data/curriculum/unmapped.json` s tom naznakom. Izdanja za 2027/28. za 1. i 5. razred planirana su, a nisu upisana.

Svaku parafrazu je alat uporedio s izvornikom i nije našao preuzete nizove reči, a čitalac koji nije pisao izdanje čita značenje naspram izvornika. To nije nastavnik.
