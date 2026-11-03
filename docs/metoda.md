# Metoda i ograniczenia

## Źródła

Archiwum zbiera konstytucje i akty ustrojowe z publicznych katalogów: Constitute (Comparative Constitutions Project), WIPO Lex, Digithèque MJP (Université de Perpignan), Biblioteka Sejmowa „Konstytucje świata” oraz źródła urzędowe. Katalog wszystkich pozycji, ze statusem wydawcy i adresem źródła, jest w [`dane/katalog_zrodel.csv`](../dane/katalog_zrodel.csv). Jedna pozycja to dokument w danym języku z danego źródła, a nie odrębna konstytucja.

## Próba porównawcza

Statystyki liczymy na 188 konstytucjach oznaczonych przez Constitute jako obowiązujące, po jednej na państwo, w wydaniu angielskim. Dwie podgrupy: konstytucje uchwalone od 2000 r. (sygnał, czy rozwiązanie zyskuje na popularności) i UE-27 (najbliższy kontekst prawny Polski).

## Kodowanie tematów (CCP)

Constitute oznacza fragmenty tekstów tematami Comparative Constitutions Project, np. „Unamendable provisions” czy „Head of state term limits”. Odczytujemy te oznaczenia z zapisanych stron Constitute. Daje to 331 tematów przypisanych do konkretnych przepisów, a z tego udział każdego tematu w próbie.

**Ograniczenie:** brak tagu oznacza, że koderzy nie przypisali tematu, a nie że konstytucja milczy. Dla Konstytucji RP przejrzeliśmy ręcznie tematy, których CCP nie oznaczył, a które pokazujemy jako luki. Werdykty („luka”, „ujęte ogólną klauzulą”, „jest, choć CCP nie oznaczył” itd.) są w [`dane/luki_konstytucji_rp.csv`](../dane/luki_konstytucji_rp.csv).

## Streszczenia, siła normy i problemy

Każdy oznaczony fragment obowiązujących konstytucji (poza Polską) przetworzył model Claude Opus 5.5. Model otrzymał instrukcję wiernego tłumaczenia i zwrócił w ustalonym formacie:
- **streszczenie**: jedno zdanie prostym językiem, najwyżej 25 słów, bez ocen;
- **siłę normy**: jedną wartość z zamkniętej listy ([`dane/slownik_sila_normy.csv`](../dane/slownik_sila_normy.csv)) z opcją „niejasne”;
- **problemy**: od 0 do 3 kodów z zamkniętej listy 23 problemów polskiej debaty ([`dane/slownik_problemow.csv`](../dane/slownik_problemow.csv)).

Kontrole w kodzie:
- każda liczba z oryginału musi pojawić się w przekładzie;
- długość przekładu musi być rozsądna, a angielskich pozostałości nie może być;
- streszczenie ma 3–32 słowa;
- oznaczenia muszą pochodzić z listy.

Fragmenty z błędami przetłumaczono ponownie. Kontroli nie przechodzi 0,07% fragmentów, głównie z powodu liczb zapisanych słownie.

Pilot porównał Claude Opus 5.5, DeepSeek V4 Pro i DeepSeek V4.1 Flash na tych samych 60 fragmentach. Wybraliśmy Opus ze względu na polski styl prawniczy.

**Ograniczenia:** to oznaczenia do nawigacji, nie ocena prawna. Model czasem nazywa obce instytucje polskimi odpowiednikami (np. „Trybunał Konstytucyjny” zamiast „Sąd Konstytucyjny”). Wszystko to sprawdzaj w przepisie źródłowym.

## Atlas i propozycje

130 opisów nietypowych przepisów i 24 propozycje dla Polski to opracowania redakcyjne: wybór, parafrazy, oceny ryzyka. Nie są pomiarem ani projektem ustawy. Każdy opis wskazuje wydanie i przepis źródłowy.

## Czego te dane nie mówią

- Czy rozwiązanie działa w praktyce (potrzebne dane o skutkach, np. V-Dem, i orzecznictwo).
- Jak przepis jest stosowany i interpretowany przez sądy.
- Czy wydanie zawiera najnowsze zmiany; część wydań Constitute ma oznaczenie „wymaga aktualizacji”.
