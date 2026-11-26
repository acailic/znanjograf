# Kako doprineti

Hvala što želite da pomognete. Znanjograf je otvoren: kod je pod [MIT licencom](LICENSE), a podaci pod [CC BY 4.0](LICENSE-DATA).

## Prijavite grešku

Najkorisniji doprinos nastavnika i roditelja je prijava greške. Na svakoj temi na sajtu ima dugme „Prijavi grešku“ koje samo otvori obrazac s popunjenom oznakom. Obrazci: [greška u zadatku](https://github.com/acailic/znanjograf/issues/new?template=pogresan-zadatak.yml), [greška u temi ili grani](https://github.com/acailic/znanjograf/issues/new?template=pogresna-tema.yml).

Prijava greške u zadatku znači da zadatak pada na slepom prolazu dok se ne ispravi.

## Dodajte ili ispravite sadržaj

1. Pročitajte [autorski vodič](docs/autorski-vodic.md) i [format podataka](docs/format-podataka.md).
2. Napravite granu i izmenite fajlove u `data/`.
3. Pokrenite proveru:

```
python3 -m zg validate
python3 -m zg verify
python3 -m zg lint
```

Sve tri komande moraju završiti sa `OK`. Ne slabite proveru da bi sadržaj prošao; ispravite sadržaj.

4. Otvorite povlačenje (`pull request`). Automatska provera pokreće sve kapije.

## Razvijajte alat ili sajt

Potrebni su Python 3.12 ili noviji i Node 22 ili noviji. Bez pip zavisnosti i bez build-a za JavaScript.

```
python3 -m zg all        # sve kapije
node --test "tests/node/**/*.test.js"  # motor, slike, raspored, formule
python3 -m zg serve      # sajt na http://127.0.0.1:8765/
```

Pravila za rad u repozitorijumu su u [AGENTS.md](AGENTS.md).

## Licenca doprinosa

Slanjem izmene pristajete da vaš kod bude pod MIT licencom, a podaci koje ste napisali pod CC BY 4.0.

## Šta ne možemo da primimo

- Sadržaj preuzet iz udžbenika, zbirki zadataka ili tuđih baza. Pišite svoje zadatke.
- Tekst programa koji nije prošao pravilo zabeleženo u `data/curriculum/sources.json`.
