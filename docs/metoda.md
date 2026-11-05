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

## Warianty kluczowych rozwiązań

Dla 43 tematów model odczytał dokładne warianty z zamkniętych list ([`dane/warianty_schemat.json`](../dane/warianty_schemat.json)):
- **głowa państwa:** limit i długość kadencji, weto i jego odrzucenie, dekrety, usunięcie z urzędu;
- **parlament i rząd:** ordynacja, rozwiązanie parlamentu, konstruktywne wotum, immunitet;
- **sądy:** wybór, kadencja i ponowny wybór sędziów sądu konstytucyjnego, dostęp do sądu konstytucyjnego i skutki wyroków, rada sądownictwa, odwołanie sędziów, prokurator generalny;
- **zmiana konstytucji:** procedura i klauzula wieczysta;
- **obywatele:** referendum, inicjatywa obywatelska, rzecznik praw, dostęp do informacji publicznej, utrata obywatelstwa;
- **wybory, partie, przejrzystość:** organ wyborczy, zakazane partie, finansowanie partii i kampanii, jawność majątku osób publicznych;
- **prawa i wartości:** ochrona zdrowia, prawo do wody, ochrona środowiska, prywatność i ochrona danych, religia państwowa i świeckość;
- **państwo w świecie i obronność:** przekazanie kompetencji organizacjom międzynarodowym, status umów i prawa międzynarodowego, ratyfikacja, wypowiedzenie wojny i użycie wojska, ograniczenia sił zbrojnych, pobór;
- **kryzys, finanse, majątek:** stany nadzwyczajne, reguły fiskalne i limity zadłużenia, bank centralny, ograniczenia sprzedaży i własności ziemi, zakaz zbywania zasobów naturalnych i kluczowych aktywów.

Jak to działa:
- **Wejście:** pełne artykuły zawierające przepisy oznaczone przez CCP (także nieoznaczone punkty wyliczeń) oraz artykuły, do których tekst odsyła („zasady z art. 1 i 20”). Gdy CCP nie oznaczył tematu w danej konstytucji, model dostaje do trzech artykułów znalezionych po słowach kluczowych (kolumna `zrodlo_fragmentu` = „słowa kluczowe”).
- **Wejście w 21 nowszych tematach** (pole `ccp_tags` w schemacie, np. ziemia, dług, ratyfikacja, prawa): artykuły oznaczone kilkoma pokrewnymi tematami CCP, a w każdej konstytucji także do pięciu artykułów znalezionych po słowach kluczowych. Z artykułów dłuższych niż 2500 znaków zostaje pierwszy akapit i akapity najlepiej pasujące do słów kluczowych. Dzięki temu przepisy w innym miejscu konstytucji (np. art. 216 ust. 5 Konstytucji RP o długu) nie są pomijane.
- **Tylko tekst:** model nie korzysta z wiedzy spoza tekstu, a gdy tekst czegoś nie określa, wpisuje „nie_wynika”.
- **Cytat:** każda odpowiedź ma dosłowny cytat, a kod sprawdza, że cytat występuje w źródle. Odpowiedzi bez zgodnego cytatu pomijamy. Z 3168 odczytów zostało 2972; odpadły głównie artykuły znalezione po słowach kluczowych, które okazały się nie na temat.
- **Kontrola:** wyniki dla Polski sprawdzono ręcznie. Korekty z podstawą prawną zapisano jawnie w [`dane/warianty_korekty.json`](../dane/warianty_korekty.json). Przykład: zakaz finansowania deficytu przez NBP (art. 220 ust. 2) leży w innym temacie CCP, więc model go nie widział.

Ograniczenia:
- Słowa kluczowe są angielskie i proste, więc mogą pominąć przepis sformułowany inaczej. W tematach takich jak „ograniczenia odwołania szefa rządu” uwzględniają też zwykłe wotum nieufności (wtedy wartość „nie” dla wotum konstruktywnego).
- Odesłania są rozwijane do czterech artykułów i tylko w obrębie tej samej konstytucji. Odesłań do ustaw nie da się rozwinąć.
- Konstytucja może przewidywać kilka rodzajów stanów nadzwyczajnych; zapisano najczęściej opisywany.
- „Brak danych” w konstruktorze znaczy, że tekst tego nie określa (często odsyła do ustawy) albo nie został odczytany.

## Konstruktor i statystyki

- **Konstruktor** porównuje wybrany zestaw wariantów z konstytucjami, dla których dane pole ustalono. Kolejność: najpierw różnica między zgodnymi a niezgodnymi polami, potem liczba zgodnych. Napięcia „do przemyślenia” to krótka, ręcznie spisana lista typowych problemów z literatury porównawczej. Nie są oceną ani pełną analizą.
- **Długość konstytucji** to liczba słów angielskiego wydania w Constitute, co pozwala porównywać państwa niezależnie od języka. Przekład może być nieco dłuższy lub krótszy od oryginału. Wielka Brytania nie ma jednej konstytucji; Constitute zestawia jej ustawy ustrojowe.
- **Trend od 2000 r.** porównuje odsetek konstytucji z danym rozwiązaniem wśród uchwalonych od 2000 r. (49) i starszych (139). Uwzględnia tylko rozwiązania obecne w co najmniej 10 konstytucjach.

## Atlas i propozycje

130 opisów nietypowych przepisów i 24 propozycje dla Polski to opracowania redakcyjne: wybór, parafrazy, oceny ryzyka. Nie są pomiarem ani projektem ustawy. Każdy opis wskazuje wydanie i przepis źródłowy.

## Czego te dane nie mówią

- Czy rozwiązanie działa w praktyce (potrzebne dane o skutkach, np. V-Dem, i orzecznictwo).
- Jak przepis jest stosowany i interpretowany przez sądy.
- Czy wydanie zawiera najnowsze zmiany; część wydań Constitute ma oznaczenie „wymaga aktualizacji”.
