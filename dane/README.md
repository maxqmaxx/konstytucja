# Dane

Pliki CSV są w UTF-8 z BOM, więc otwierają się poprawnie w Excelu. Liczności i oznaczenia generuje skrypt; nie edytuj ich ręcznie, zgłoś poprawkę ([CONTRIBUTING.md](../CONTRIBUTING.md)).

| Plik | Wiersz | Najważniejsze kolumny |
|---|---|---|
| `rozwiazania_swiat.csv` | rozwiązanie (temat CCP) | `rozwiazanie`, `liczba_konstytucji`, `udzial_swiat`, `udzial_od_2000`, `udzial_ue27`, `jak_czesto` (standard światowy ≥75%, częste 40–75%, rzadsze 15–40%, rzadkie <15%), `konstytucja_rp`, `artykuly_rp` |
| `konstytucja_rp_na_tle_swiata.csv` | artykuł Konstytucji RP × temat | `artykul`, `rozdzial`, `rozwiazanie`, `udzial_swiat`, `liczba_ue27`, `jak_czesto` |
| `konstytucja_rp_1997.txt` | — | tekst Konstytucji RP (odczyt roboczy tekstu ujednoliconego z ELI) |
| `luki_konstytucji_rp.csv` | temat bez tagu CCP w Konstytucji RP | `verdict` (`luka`, `luka_celowa`, `inna_technika`, `czesciowo`, `artefakt`, `nie_dotyczy`), `polish_basis`, `note` |
| `przepisy_tematy.csv` | przepis innego państwa × temat | `panstwo`, `artykul`, `rozwiazanie`, `sila_normy`, `problemy` (kody rozdzielone spacją), `streszczenie_pl`, `adres_przepisu` |
| `warianty.csv` | państwo × temat × pole | dokładne warianty dla 23 kluczowych tematów (np. rodzaj limitu kadencji, próg odrzucenia weta i zmiany konstytucji, maks. czas stanu nadzwyczajnego, kto wybiera i odwołuje sędziów): `temat`, `opis_pola`, `wartosc_opis`; `zrodlo_fragmentu` mówi, czy przepis oznaczył CCP, czy znaleziono go po słowach kluczowych; schemat pól: `warianty_schemat.json`. „nie_wynika” = tekst tego nie określa |
| `dlugosci_konstytucji.csv` | państwo | liczba słów angielskiego wydania w Constitute i liczba artykułów lub sekcji |
| `problemy_tematy.csv` | problem × temat | `problem`, `rozwiazanie`, `udzial_przepisow_tematu` (jaka część przepisów tematu dotyczy problemu), `liczba_przepisow` |
| `konstytucje_obowiazujace.csv` | państwo | `panstwo`, `wydanie_constitute`, `rok_uchwalenia`, `ue27`, `liczba_tematow_ccp`, `adres_constitute` |
| `propozycje_dla_polski.csv` / `.json` | propozycja P01–P24 | `title`, `verdict`, `poland` (stan dziś), `draft` (szkic), `benefit`, `risk`, `safeguards`, `inspirations` (id atlasu), `polish_articles` |
| `atlas_zapisy.csv` / `.json` | opis nietypowego przepisu (A001–A130) | `country`, `provision`, `title`, `meaning`, `why`, `caveat`, `categories`, `source_url` |
| `katalog_zrodel.csv` | pozycja archiwum | `panstwo`, `tytul`, `jezyk`, `zrodlo`, `status_wydawcy`, `rok_uchwalenia`, `adres_zrodla` |
| `slownik_*.csv` | kod | polskie nazwy tematów, siły normy i problemów |
| `LICZNOSCI.json` | — | liczba wierszy w każdym pliku (kontrola) |

## Przykładowe pytania do arkusza

- *Czego nie ma w Konstytucji RP, a ma większość państw UE?* W `rozwiazania_swiat.csv` ustaw `konstytucja_rp` = „brak tagu CCP”, posortuj malejąco po `udzial_ue27`, a potem sprawdź werdykt w `luki_konstytucji_rp.csv`.
- *Co rośnie w nowych konstytucjach?* Policz `udzial_od_2000` − `udzial_swiat` i posortuj.
- *Jak inni chronią sądy?* W `przepisy_tematy.csv` filtruj `problemy` zawierające `sady` i `sila_normy` = `zakaz` lub `obowiazek_wladzy`.
