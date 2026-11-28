# Znanjograf

Dijagnostički graf znanja iz matematike za osnovnu školu u Srbiji (1–8. razred): teme, veze koje kažu šta treba znati pre čega, banka zadataka i dijagnostika koja od izabrane teme odlazi unazad dok ne nađe najverovatnije mesto gde je znanje puklo.

Sajt: <https://acailic.github.io/znanjograf/>, na latinici i na ćirilici. Isti tekst na ćirilici: [README na ćirilici](README.cir.md).

> **Status: rana verzija, sadržaj se upisuje.** Alat, motor dijagnostike i sajt su napravljeni i provereni testovima. Sadržaj se upisuje razred po razred; tabela ispod pokazuje šta je upisano, a svaka stranica sajta nosi istu napomenu dok god neki razred nema teme s zadacima. Sadržaj pišu AI modeli i dok ga nastavnik ne pregleda, treba ga čitati kao nacrt.

## Kako radi

1. **Mapa znanja** pokazuje teme i veze među njima. Čvrsta veza znači „ovo treba da znaš pre onoga“; meka veza znači „ovo pomaže“.
2. **Dijagnostika** kreće od teme ili od celog razreda. Za svaku temu prvo pita teže pitanje, a ako ga dete promaši, lakše. Tema koju dete ne reši ni uz lakše pitanje smatra se rupom; tada dijagnostika ide unazad po čvrstim vezama i pita šta je pre nje, dok ne dođe do najdublje teme koju dete ne zna. Šta dete očito zna, ne pita se ponovo.
3. **Rezultat** je trag, a ne ocena: gde je znanje najverovatnije puklo, koje zadatke je dete promašilo i kojim redosledom popravljati, od najnižeg razreda naviše.

Detaljno, s računatim primerom: [Dijagnostika: kako radi](docs/dijagnostika.md).

## Šta je u repozitorijumu

- `data/` — sav sadržaj u običnom JSON-u: nastavni program po razredima, teme, veze, zadaci, pravila provere.
- `zg/` — alat koji čita `data/`, proverava ga, gradi sajt i održava evidenciju pregleda. Samo standardna biblioteka Pythona.
- `site/` — sajt bez frejmvorka: običan HTML, CSS i ES moduli, s KaTeX-om za formule; JavaScript se ne pakuje ni prevodi.
- `docs/` — dokumentacija za nastavnike, autore sadržaja i programere.
- `tests/` — testovi alata (Python) i motora dijagnostike (`node`).

## Stanje sadržaja

Ovu tabelu ispisuje alat (`python3 -m zg report --write`); brojevi u njoj su ono što stvarno stoji u `data/`.

<!-- zg:stats -->
| Razred | Ishodi programa | Teme | Grane | Zadaci |
|---|---|---|---|---|
| 1. razred | 22 | 37 | 73 | 148 |
| 2. razred | 24 | 25 | 42 | 100 |
| 3. razred | 27 | 28 | 52 | 112 |
| 4. razred | 23 | 22 | 36 | 88 |
| 5. razred | 31 | 0 | 0 | 0 |
| 6. razred | 17 | 0 | 0 | 0 |
| 7. razred | 19 | 0 | 0 | 0 |
| 8. razred | 11 | 0 | 0 | 0 |
| Ukupno | 174 | 112 | 203 | 448 |
<!-- /zg:stats -->

„Ishodi programa“ su ishodi nastavnog programa upisani u repozitorijum. Tema sme da stoji samo s bar dva osnovna i dva standardna zadatka, a odgovor svakog zadatka alat posebno izračuna i poredi s upisanim; ako se ne poklapa, provera pada.

## Kako se pokreće

Potrebni su Python 3.12 ili noviji i `node` 22 (samo za testove motora); ništa se ne instalira.

```sh
python3 -m zg build            # gradi sajt u _site/, u oba pisma
python3 -m zg serve            # služi ga na http://127.0.0.1:8765/ i gradi nanovo pri svakoj izmeni
python3 -m zg all              # sve provere: sadržaj, odgovore, notaciju, tabelu i ažurnost izgradnje

python3 -m unittest discover -s tests -q     # testovi alata
node --test "tests/node/**/*.test.js"         # testovi motora dijagnostike
```

## Dokumentacija

- [Program: odakle dolazi sadržaj](docs/program.md) — koji akt važi za koji razred i kako se to zapisuje.
- [Format podataka](docs/format-podataka.md) — oblik svakog fajla u `data/`, jezik za proveru odgovora i spisak svih pravila provere.
- [Dijagnostika: kako radi](docs/dijagnostika.md) — motor, redosled pitanja, presuda, rezultat.
- [Poznata ograničenja](docs/poznata-ogranicenja.md) — šta mašina proverava, a šta ne može da vidi.
- [Autorski vodič](docs/autorski-vodic.md) — kako se pišu teme, veze i zadaci.
- [Specifikacija dizajna](docs/superpowers/specs/2026-11-26-znanjograf-design.md).

## Šta Znanjograf nije

- **Nije zvaničan** ni povezan sa Ministarstvom prosvete. Ako se sadržaj ne slaže s aktom, važi akt.
- **Nije ocena.** Rezultat dijagnostike je trag za razgovor s detetom; ne zamenjuje nastavnikov uvid.
- **Nije kalibrisan na stvarnoj deci.** Niko nije merio kako deca odgovaraju na ove zadatke.

Ostalo, bez uljepšavanja, stoji u [Poznatim ograničenjima](docs/poznata-ogranicenja.md).

## Kako se učestvuje

Pogrešan zadatak, pogrešna tema ili veza, predlog: počinje se od [obrazaca za prijavu](https://github.com/acailic/znanjograf/issues/new/choose). Pravila za izmene su u [CONTRIBUTING.md](CONTRIBUTING.md).

## Licenca

- Kod (alat i sajt): [MIT](LICENSE).
- Podaci (teme, veze, zadaci, ishodi programa): [CC BY 4.0](LICENSE-DATA).
- Formule prikazuje [KaTeX](https://katex.org/), pod MIT licencom.

## Poreklo

Zamišljeno po uzoru na [`xiaoyang111222/cn-math-taxonomy`](https://github.com/xiaoyang111222/cn-math-taxonomy), kao nezavisna implementacija za nastavni program Republike Srbije; ništa iz tog repozitorijuma nije preneto.

Teme su vezane za nastavne programe koji važe u školskoj 2026/27. godini. Tekstovi ishoda u repozitorijumu su parafraza s uputom na akt i stranu, a ne bukvalan tekst akta; zašto, i odakle se tekstovi preuzimaju, objašnjava [Program](docs/program.md).
