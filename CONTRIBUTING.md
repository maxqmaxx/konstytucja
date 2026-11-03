# Jak współtworzyć

Dziękujemy, że chcesz pomóc. Repozytorium ma służyć rzetelnej rozmowie, więc kilka zasad:

1. **Fakt osobno, ocena osobno.** Liczby i cytaty muszą mieć źródło. Oceny, propozycje i pytania oznaczamy jako redakcyjne.
2. **Źródło przy każdym twierdzeniu.** Przepis: państwo, wydanie, artykuł, link. Badanie: autor, rok, link.
3. **Bez cudzych tekstów w całości.** Krótkie cytaty z podaniem źródła tak; wklejanie całych przepisów chronionych przekładów nie (zob. [docs/czego-nie-ma.md](docs/czego-nie-ma.md)).
4. **Neutralność wobec stron sporu.** Pokazujemy argumenty i ryzyka po obu stronach.

## Co możesz zrobić

- **Błąd w danych** (zły temat, przeoczony przepis Konstytucji RP, złe streszczenie albo siła normy): załóż zgłoszenie z szablonu „Błąd w danych”. Najcenniejsze są poprawki do [`dane/luki_konstytucji_rp.csv`](dane/luki_konstytucji_rp.csv).
- **Nowy przykład analizy:** szablon „Nowy przykład”. Przykłady powstają w `tools/examples.py` w repozytorium roboczym, więc wystarczy opis: pytanie, tematy CCP, wstęp, pytania do dyskusji.
- **Komentarz do propozycji dla Polski:** szablon „Propozycja lub komentarz”.
- **Publiczne projekty nowej polskiej konstytucji** (partii, organizacji, ekspertów): podaj link do oficjalnej publikacji; chcemy dodać je jako punkty porównania.

## Pull requesty

Zmiany w `dane/` i `przyklady/` są generowane, więc w PR opisz poprawkę i jej źródło, a włączymy ją do generatora. Dokumentację (`docs/`, README) można poprawiać bezpośrednio.
