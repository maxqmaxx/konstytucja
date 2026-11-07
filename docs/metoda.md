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

Dla 49 tematów model odczytał dokładne warianty z zamkniętych list ([`dane/warianty_schemat.json`](../dane/warianty_schemat.json)):
- **głowa państwa:** limit i długość kadencji, weto i jego odrzucenie, dekrety, usunięcie z urzędu;
- **parlament i rząd:** ordynacja, uchwalanie ustaw (izby, weto drugiej izby, rola głowy państwa), inicjatywa ustawodawcza, powołanie i odwołanie rządu, kontrasygnata, rozwiązanie parlamentu, konstruktywne wotum, immunitet;
- **sądy:** wybór, kadencja i ponowny wybór sędziów sądu konstytucyjnego, dostęp do sądu konstytucyjnego i skutki wyroków, rada sądownictwa, odwołanie sędziów, prokurator generalny;
- **zmiana konstytucji:** procedura i klauzula wieczysta;
- **obywatele:** referendum, inicjatywa obywatelska, rzecznik praw, dostęp do informacji publicznej, utrata obywatelstwa;
- **wybory, partie, przejrzystość:** organ wyborczy, zakazane partie, finansowanie partii i kampanii, jawność majątku osób publicznych;
- **prawa i wartości:** ochrona zdrowia, prawo do wody, ochrona środowiska, prywatność i ochrona danych, religia państwowa i świeckość;
- **państwo w świecie i obronność:** przekazanie kompetencji organizacjom międzynarodowym, status umów i prawa międzynarodowego, ratyfikacja, wypowiedzenie wojny i użycie wojska, ograniczenia sił zbrojnych, pobór;
- **kryzys, finanse, majątek:** stany nadzwyczajne, budżet (kto przygotowuje, co gdy nie zostanie uchwalony), reguły fiskalne i limity zadłużenia, bank centralny, ograniczenia sprzedaży i własności ziemi, zakaz zbywania zasobów naturalnych i kluczowych aktywów.

Jak to działa:
- **Wejście:** pełne artykuły zawierające przepisy oznaczone przez CCP (także nieoznaczone punkty wyliczeń) oraz artykuły, do których tekst odsyła („zasady z art. 1 i 20”). Gdy CCP nie oznaczył tematu w danej konstytucji, model dostaje do trzech artykułów znalezionych po słowach kluczowych (kolumna `zrodlo_fragmentu` = „słowa kluczowe”).
- **Wejście w 27 nowszych tematach** (pole `ccp_tags` w schemacie, np. ziemia, dług, ratyfikacja, prawa): artykuły oznaczone kilkoma pokrewnymi tematami CCP, a w każdej konstytucji także do pięciu artykułów znalezionych po słowach kluczowych. Z artykułów dłuższych niż 2500 znaków zostaje pierwszy akapit i akapity najlepiej pasujące do słów kluczowych. Dzięki temu przepisy w innym miejscu konstytucji (np. art. 216 ust. 5 Konstytucji RP o długu) nie są pomijane.
- **Tylko tekst:** model nie korzysta z wiedzy spoza tekstu, a gdy tekst czegoś nie określa, wpisuje „nie_wynika”.
- **Cytat:** każda odpowiedź ma dosłowny cytat, a kod sprawdza, że cytat występuje w źródle. Odpowiedzi bez zgodnego cytatu pomijamy. Z 7610 odczytów zostało 7028; odpadły głównie artykuły znalezione po słowach kluczowych, które okazały się nie na temat.
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

## Kto rządzi, kto blokuje (podział władzy)

Strona [Władza](https://maxqmaxx.github.io/konstytucja/wladza/index.html) i pliki `dane/wladza_kraje.csv`, `dane/wladza_decyzje.csv` liczą, jak konstytucja dzieli 11 kluczowych decyzji: ustawę, budżet, zmianę konstytucji, powołanie i odwołanie rządu, rozwiązanie parlamentu, wybór sędziów sądu konstytucyjnego, stan nadzwyczajny, wojnę, ratyfikację umów i usunięcie głowy państwa. Kod: `kod/analysis/wladza/model.py`.

- **Gra decyzyjna.** Z wariantów (np. próg odrzucenia weta, siła drugiej izby, wyłączna inicjatywa budżetowa rządu, kontrasygnata, kto rozwiązuje parlament) powstaje lista „zwycięskich koalicji”: które organy muszą się zgodzić i jaki odsetek mandatów każdej izby jest potrzebny.
- **Udział siły** to indeks Shapleya-Shubika: jak często organ przesądza o wyniku, gdy organy dołączają w losowej kolejności. Organy jednoosobowe (głowa państwa, rząd, naród w referendum, sądy) są graczami, a izba to duża grupa równych posłów. Weto, które izba odrzuca większością 3/5, daje głowie państwa „okno” między 50% a 60% mandatów, czyli 10% siły w tej decyzji; przy 2/3 to 16,7%, przy wecie absolutnym 50%. Liczone dokładnie (całki wielomianów), bez losowania. Profil państwa to średnia z decyzji, a HHI to suma kwadratów udziałów (koncentracja).
- **Weto i mniejszość blokująca.** Weto ma organ niezbędny w każdej zwycięskiej koalicji. Mniejszość blokująca to najmniejszy odsetek mandatów pierwszej izby, który zatrzyma decyzję, gdy pozostałe organy są za, oraz ile mandatów wystarczy, by utrzymać sprzeciw głowy państwa.
- **Typ ustroju** wynika z tekstu: przed kim odpowiada rząd (parlament, głowa państwa, oba organy) i czy głowa państwa kieruje rządem. Gdy tekst nie mówi, kto kieruje rządem, a w całej konstytucji nie pada nazwa urzędu premiera ani monarchy, przyjmujemy, że rządem kieruje głowa państwa.
- **Uzupełnienia z CCP.** Liczbę izb i próg odrzucenia weta, gdy nie wynikały z naszego odczytu, oraz sposób wyboru głowy państwa (do typologii) bierzemy z ręcznego kodowania Comparative Constitutions Project (Elkins i Ginsburg, *Characteristics of National Constitutions* v5, 2025). Każde uzupełnienie jest zaznaczone przy decyzji. Wycinka danych CCP nie publikujemy (brak licencji na redystrybucję); `kod/analysis/wladza/ccp_ref.py` opisuje, jak go odtworzyć z plików pobranych ze strony CCP. Bez niego model działa, ale typologia nie odróżnia systemów półprezydenckich.
- **Typologia.** Prezydencki (głowa państwa kieruje rządem), półprezydencki premierowski (prezydent z wyborów powszechnych, rząd odpowiada tylko przed parlamentem; np. Polska, Francja), półprezydencki prezydencko-parlamentarny (rząd odpowiada też przed prezydentem; np. Rosja), parlamentarny, monarchia parlamentarna i typy pośrednie.
- **Odporność na przejęcie** (`dane/wladza_przejecie.csv`). Dla sądu konstytucyjnego, rady sądownictwa, rzecznika praw, banku centralnego, prokuratora generalnego, organu wyborczego i zmiany konstytucji: kto wybiera i jaką większością. Wynik to najsłabszy obóz, który sam obsadzi instytucję: zwykła większość w izbie (i rząd), większość z głową państwa, 3/5, 2/3 mandatów albo „poza zasięgiem samej polityki” (współdecydują sędziowie, naród lub opozycja). „Decyduje ustawa” oznacza, że konstytucja nie mówi, kto wybiera. Ograniczenia: druga izba i kadencje (rozłożenie w czasie) nie są uwzględnione.
- **Niezależność sądów w tekście** (`dane/wladza_sady.csv`): odsetek z 10 gwarancji (wybór TK przez kilka organów lub większością kwalifikowaną, kadencja co najmniej 9 lat, brak ponownego wyboru, rada sądownictwa z większością sędziów wybieranych przez sędziów, nieusuwalność, odwołanie przez organ sądowy i z przyczyn ustawowych, dostęp mniejszości lub obywateli do TK, moc wyroków). Gwarancje dotyczące instytucji, której konstytucja nie ma, nie są liczone.
- **Walidacja** (`dane/wladza_walidacja_pola.csv`). Nasze odczyty zgadzały się z kodowaniem CCP w 88,1% z 1641 porównań (liczba izb 97%, próg weta 99%, najsłabiej odwołanie rządu). Rozbieżności (188) rozstrzygnęliśmy osobno (`kod/analysis/wladza/rozstrzygniecia.py`): model dostaje pytanie w naszej definicji i szerszy fragment konstytucji, nie wie, która odpowiedź jest czyja, i musi podać dosłowny cytat. W 133 przypadkach tekst potwierdził nasz odczyt (różnica definicji CCP albo inna wersja konstytucji), w 42 poprawiliśmy dane (korekty z `"metoda": "rozstrzygniecie"` w `dane/warianty_korekty.json`, każda z cytatem), 12 zostało nierozstrzygniętych, 1 werdykt odrzuciliśmy po przeglądzie. Po poprawkach zgodność wynosi 90,5%; miarą jakości samej ekstrakcji pozostaje 88,1%. Typ ustroju zgadza się z klasyfikacją Cheibuba, Elkinsa i Ginsburga (2014) w 84% (106 konstytucji, kappa 0,76), a udział głowy państwa maleje zgodnie z ich typem (prezydenckie 39%, półprezydenckie 21%, parlamentarne 16%). Indeks sądów koreluje z indeksem Meltona i Ginsburga (2014) umiarkowanie (ρ = 0,32). Z indeksem władzy wykonawczej CCP (7 uprawnień) korelacja jest słaba (ρ = 0,19): tamten indeks liczy uprawnienia całej egzekutywy, także premiera, i prawie nie różnicuje typów ustroju.
- **Wrażliwość** (`dane/wladza_warianty.csv`). Ranking liczymy też z wagami decyzji, bez reguły dla monarchii, z łatwymi i nieosiągalnymi większościami kwalifikowanymi oraz tylko na decyzjach bez założeń. Korelacja rang z modelem bazowym: 0,87–0,99, ale pojedyncze miejsce przesuwa się typowo o 25 pozycji, więc podajemy przedział (Polska: 118.–144. z 178).
- **Symulator** (`wladza/symulator.html`) liczy te same gry dla Polski w przeglądarce po zmianie jednej reguły; test sprawdza, że ustawienie „obecnie” daje wyniki identyczne z modelem.
- **Ograniczenia.** Organy są jednolite: model nie zna partii, koalicji ani kohabitacji. Obie izby głosują tą samą większością. Kolejność (kto proponuje pierwszy) nie daje siły; liczy się tylko, czyja zgoda jest potrzebna. Gdy sędziów wybiera kilka organów, każdy dostaje równy udział. „Nie wynika z tekstu” prowadzi do założenia wypisanego przy decyzji. Do rankingów trafiają państwa z co najmniej 6 decyzjami bez niewiadomych w strukturze (178 ze 188).

## Atlas i propozycje

130 opisów nietypowych przepisów i 24 propozycje dla Polski to opracowania redakcyjne: wybór, parafrazy, oceny ryzyka. Nie są pomiarem ani projektem ustawy. Każdy opis wskazuje wydanie i przepis źródłowy.

## Czego te dane nie mówią

- Czy rozwiązanie działa w praktyce (potrzebne dane o skutkach, np. V-Dem, i orzecznictwo).
- Jak przepis jest stosowany i interpretowany przez sądy.
- Czy wydanie zawiera najnowsze zmiany; część wydań Constitute ma oznaczenie „wymaga aktualizacji”.
