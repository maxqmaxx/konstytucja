# Konstytucje świata: warsztat do myślenia o lepszej konstytucji

Repozytorium dla osób, które chcą rozmawiać o przyszłej polskiej konstytucji na podstawie faktów, a nie haseł: ekspertów, studentów, dziennikarzy, aktywistów i ciekawych obywateli. Znajdziesz tu:

- **jak częste jest dane rozwiązanie** w 188 obowiązujących konstytucjach świata, w 331 tematach, z podziałem na świat, konstytucje uchwalone od 2000 r. i Unię Europejską;
- **jak wypada Konstytucja RP**, artykuł po artykule, z ręcznie sprawdzonymi lukami;
- **53 745 przepisów innych państw** z polskim streszczeniem, siłą normy (prawo, obowiązek, cel programowy…) i przypisaniem do problemów polskiej debaty, każdy z linkiem do pełnego tekstu;
- **dokładne warianty 15 kluczowych rozwiązań**, np. ile kadencji, jaki próg zmiany konstytucji, ile dni stanu nadzwyczajnego, kto wybiera sędziów, każdy z wartością dla Polski;
- **przykłady analiz** prowadzące od pytania do wniosków i pytań do dyskusji;
- **24 autorskie propozycje dla Polski** z ryzykami i zabezpieczeniami;
- **kod**, którym każdy może odtworzyć i rozwinąć całość.

> To materiał do debaty, nie projekt ustawy ani opinia prawna. Liczby mówią, co zapisano w konstytucjach, a nie czy to działa.

## Zacznij tutaj

| Masz | Zrób to |
|---|---|
| 5 minut | Otwórz jeden z [przykładów](przyklady/README.md), np. [Czy część konstytucji powinna być niezmienialna?](przyklady/01-klauzula-wieczysta.md) |
| 30 minut | Pobierz [`dane/rozwiazania_swiat.csv`](dane/rozwiazania_swiat.csv) i otwórz w Excelu albo Google Sheets. Posortuj po `udzial_ue27`, odfiltruj `konstytucja_rp` = „brak tagu CCP”. Opis kolumn: [`dane/README.md`](dane/README.md). |
| Własne pytanie | W [`dane/przepisy_tematy.csv`](dane/przepisy_tematy.csv) filtruj po `problemy` (np. `sady`, `stany_nadzwyczajne`) lub `kod_ccp` i czytaj streszczenia; link w `adres_przepisu` prowadzi do pełnego tekstu. |
| Warsztat kodu | [`kod/`](kod/) zawiera pobieranie archiwum, kodowanie, statystyki i generator serwisu. Zobacz [docs/odtworzenie.md](docs/odtworzenie.md). |

## Co jest w repozytorium

| Katalog | Zawartość |
|---|---|
| [`przyklady/`](przyklady/) | Analizy krok po kroku: klauzula wieczysta, limit kadencji, stany nadzwyczajne, niezależność sądów, demokracja bezpośrednia, środowisko i woda |
| [`dane/`](dane/) | CSV i JSON gotowe do arkusza: rozpowszechnienie rozwiązań, Konstytucja RP na tle świata, przepisy z oznaczeniami, luki, propozycje, atlas, katalog źródeł, słowniki |
| [`analizy/`](analizy/) | Pełne opracowania: atlas 130 nietypowych zapisów i 24 propozycje dla Polski |
| [`docs/`](docs/) | [Metoda i ograniczenia](docs/metoda.md), [czego tu nie ma i dlaczego](docs/czego-nie-ma.md), [odtworzenie](docs/odtworzenie.md) |
| [`kod/`](kod/) | Skrypty Pythona i strony statyczne |

## Najważniejsze zastrzeżenia

1. **Brak oznaczenia to nie brak przepisu.** Tematy nadali eksperci Comparative Constitutions Project; czasem pomijają przepis albo ujmują go inaczej. Przykład: barwy narodowe są w art. 28 Konstytucji RP, choć CCP ich nie oznaczył. Luki Polski pokazywane w przykładach sprawdzono ręcznie ([`dane/luki_konstytucji_rp.csv`](dane/luki_konstytucji_rp.csv)).
2. **Częstość nie jest skutecznością.** Popularne rozwiązanie może nie działać, rzadkie może być świetne.
3. **Streszczenia, siła normy i problemy nadał model językowy** (Claude Opus 5.5) z zamkniętych list, z kontrolami jakości. To narzędzie nawigacji, a nie ocena prawna; zawsze sprawdzaj przepis źródłowy.
4. **Status „obowiązująca”** odtwarza oznaczenie wydawcy (Constitute); część wydań może nie zawierać najnowszych zmian.

## Współtworzenie

Zgłaszaj błędy w danych, proponuj nowe przykłady i lepsze sformułowania, dodawaj publiczne projekty polskiej konstytucji jako punkty porównania. Zasady: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencje i cytowanie

- Kod: [MIT](LICENSE).
- Własne opracowania (przykłady, analizy, propozycje, atlas, słowniki, streszczenia, oznaczenia, statystyki): [CC BY 4.0](LICENSE-TRESCI.md).
- Kodowanie tematów: Comparative Constitutions Project (Elkins, Ginsburg, Melton), za pośrednictwem [Constitute](https://www.constituteproject.org/). Teksty konstytucji innych państw nie są tu publikowane; linkujemy do źródeł ([dlaczego](docs/czego-nie-ma.md)).
- Tekst Konstytucji RP nie jest przedmiotem prawa autorskiego (art. 4 pkt 1 ustawy o prawie autorskim i prawach pokrewnych).

Jak cytować: [CITATION.cff](CITATION.cff). Stan danych: 2026-11-03.

*English summary: [README.en.md](README.en.md).*
