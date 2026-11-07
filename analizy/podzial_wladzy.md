# Kto rządzi, kto blokuje: podział władzy w 188 konstytucjach

Stan danych: 2026-11-07. Wersja interaktywna (każde państwo, każda decyzja): https://maxqmaxx.github.io/konstytucja/wladza/index.html. Dane: dane/wladza_kraje.csv i dane/wladza_decyzje.csv; metoda: docs/metoda.md.

Raport opisuje, jak teksty obowiązujących konstytucji dzielą 11 kluczowych decyzji między parlament, głowę państwa, rząd, naród (referendum) i sądy. Każdą decyzję zapisano jako grę: które organy muszą się zgodzić i jaką większością. Z tego wynika udział siły każdego organu (indeks Shapleya-Shubika, w każdej decyzji suma 100%), kto ma weto i jaka mniejszość w parlamencie wystarczy do blokady.

## Najważniejsze wnioski

- **Prezydent RP ma 16,3% siły** (średnio w 11 decyzjach). To 128. miejsce z 178 od najsilniejszej głowy państwa (przy innych założeniach modelu 120.–144.) i 11. z 26 w UE. Mediana świata: 29,2%, średnia UE: 15,1%.
- **Sejm i Senat razem: 66,8%**, rząd 13,9%. Senat ma 4,5%: jego sprzeciw wobec ustaw Sejm odrzuca bezwzględną większością (art. 121 ust. 3), więc w modelu nie przesądza o wyniku zwykłej ustawy. Siłę Senatu daje zmiana konstytucji (art. 235).
- **Weto prezydenta RP** (art. 122 ust. 5) daje mu 10% siły przy ustawie: Sejm odrzuca je większością 3/5, więc zablokować może ponad 40% posłów popierających prezydenta. Na świecie częstszy jest próg 2/3 (53 państw, blokuje ponad 1/3) albo zwykła większość, przy której weto niczego nie przesądza (64). Próg 3/5: 3 państwa; weto nie do odrzucenia: 3.
- **Budżet**: wyłączna inicjatywa Rady Ministrów (art. 221) czyni rząd drugim, obok Sejmu, organem bez którego budżetu nie ma (po 50%). Prezydent nie może budżetu zawetować (art. 224), a gdy budżetu nie ma, rząd działa na podstawie projektu (art. 219 ust. 4).
- **Systemy prezydenckie** dają głowie państwa średnio 41,5% siły, parlamentarne 12,3%. Najsilniejsze głowy państwa: Brunei 64,3%, Gwinea Równikowa 63,6%, Arabia Saudyjska 62,5%, Katar 57,6%, Zambia 57,6%, Tunezja 57,4%, Malawi 55,6%, Zjednoczone Emiraty Arabskie 55,0%.
- **Najbardziej rozproszona władza** (najniższa koncentracja HHI): Włochy, Mali, Jordania, Demokratyczna Republika Konga, Madagaskar, Rwanda, Dominikana, Kongo. Polska: HHI 0,44, 100. miejsce z 178 od najbardziej skoncentrowanej.

## Polska: kto ile ma siły

- **Polska**: Izba pierwsza 62,2%, Druga izba 4,5%, Rząd 13,9%, Głowa państwa 16,3%, Sądy 3,0%
- **Unia Europejska (26)**: Izba pierwsza 61,1%, Druga izba 4,0%, Rząd 16,3%, Głowa państwa 15,1%, Naród 1,2%, Sąd konst. 1,0%, Sądy 1,2%
- **Świat (178)**: Izba pierwsza 56,9%, Druga izba 4,7%, Rząd 9,0%, Głowa państwa 26,9%, Naród 1,0%, Sąd konst. 0,3%, Sądy 1,2%

Udział w decyzjach (Shapley-Shubik), weto i mniejszość blokująca w Sejmie. „Gdy Prezydent przeciw”: ile posłów wystarczy, by utrzymać jego sprzeciw.

| Decyzja | Podział siły | Weto | Mniejszość blokująca w Sejmie | Założenia |
|---|---|---|---|---|
| Uchwalenie ustawy zwykłej | Sejm 90,0%, Prezydent 10,0% | Sejm | ponad 50%; gdy Prezydent przeciw: ponad 40% |  |
| Uchwalenie budżetu | Sejm 50,0%, Rada Ministrów 50,0% | Rada Ministrów, Sejm | ponad 50% | gdy parlament nie uchwali budżetu, władza wykonawcza działa na podstawie swojego projektu; nieuchwalenie budżetu pozwala rozwiązać parlament |
| Zmiana konstytucji | Sejm 50,0%, Senat 50,0% | Sejm, Senat | ponad 33,3% |  |
| Powołanie szefa rządu | Sejm 100,0% | Sejm | ponad 50% |  |
| Odwołanie rządu | Sejm 100,0% | Sejm | ponad 50% | konstruktywne wotum: ta sama większość musi wskazać następcę |
| Rozwiązanie parlamentu | Sejm 33,3%, Prezydent 66,7% | – | izba nie blokuje; gdy Prezydent przeciw: ponad 33,3% | samorozwiązanie: przyjęto próg 2/3, jeśli tekst nie podaje innego; tylko w określonych sytuacjach (np. nieuchwalenie budżetu, brak rządu) |
| Wybór sędziów sądu konstytucyjnego | Sejm 100,0% | Sejm | ponad 50% |  |
| Stan nadzwyczajny | Sejm 25,0%, Rada Ministrów 37,5%, Prezydent 37,5% | Rada Ministrów, Prezydent, Sejm | ponad 50%; gdy Prezydent przeciw: sprzeciwu nie da się odrzucić | parlament może tylko uchylić stan (słabsza kontrola niż zatwierdzenie) |
| Wojna i użycie wojska | Sejm 25,0%, Rada Ministrów 37,5%, Prezydent 37,5% | Rada Ministrów, Prezydent, Sejm | ponad 50%; gdy Prezydent przeciw: sprzeciwu nie da się odrzucić |  |
| Ratyfikacja umów | Sejm 44,4%, Rada Ministrów 27,8%, Prezydent 27,8% | Rada Ministrów, Prezydent, Sejm | ponad 33,3%; gdy Prezydent przeciw: sprzeciwu nie da się odrzucić | większość kwalifikowana (często tylko dla części umów, np. przekazania kompetencji); zgoda parlamentu tylko dla części umów: model pokazuje umowy wymagające zgody |
| Usunięcie głowy państwa | Sejm 66,7%, Trybunał Stanu / sądy 33,3% | Trybunał Stanu / sądy, Sejm | ponad 33,3% |  |

## Polska: kto kogo blokuje i kontroluje

- **Sejm** może zablokować: Prezydent (uchwalenie ustawy zwykłej, stan nadzwyczajny, wojna i użycie wojska, ratyfikacja umów); Rada Ministrów (uchwalenie budżetu, stan nadzwyczajny, wojna i użycie wojska, ratyfikacja umów); Senat (zmiana konstytucji); Trybunał Stanu / sądy (usunięcie głowy państwa)
- **Rada Ministrów** może zablokować: Sejm (uchwalenie budżetu, stan nadzwyczajny, wojna i użycie wojska, ratyfikacja umów); Prezydent (stan nadzwyczajny, wojna i użycie wojska, ratyfikacja umów)
- **Senat** może zablokować: Sejm (zmiana konstytucji)
- **Prezydent** może zablokować: Rada Ministrów (stan nadzwyczajny, wojna i użycie wojska, ratyfikacja umów); Sejm (stan nadzwyczajny, wojna i użycie wojska, ratyfikacja umów)
- **Trybunał Stanu / sądy** może zablokować: Sejm (usunięcie głowy państwa)
- Sejm: odwołuje rząd
- Prezydent: rozwiązuje Sejm
- Sejm: wybiera sędziów TK
- Trybunał Stanu / sądy, Sejm: usuwa Prezydenta

Ograniczenia hamujące: konstruktywne wotum nieufności (art. 158); 50 posłów lub 30 senatorów może zaskarżyć ustawę do TK (art. 191); skarga konstytucyjna (art. 79). Prezydent może skrócić kadencję Sejmu tylko w dwóch sytuacjach (art. 155 ust. 2 i art. 225).

## Typy ustroju na świecie

| Typ (z tekstu) | Państw | Głowa państwa | Rząd | Parlament | Naród i sądy |
|---|---|---|---|---|---|
| Prezydencki: głowa państwa kieruje rządem | 52 | 41,5% | 0,0% | 56,2% | 2,3% |
| Parlamentarny (głowa państwa wybierana pośrednio) | 34 | 12,3% | 13,3% | 72,5% | 1,9% |
| Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 23 | 17,0% | 9,3% | 70,0% | 3,8% |
| Półprezydencki: rząd odpowiada przed parlamentem i prezydentem | 19 | 30,2% | 14,1% | 52,0% | 3,7% |
| Monarchia parlamentarna | 18 | 17,8% | 19,0% | 61,3% | 1,9% |
| Rząd odpowiada przed parlamentem i głową państwa (głowa wybierana pośrednio) | 15 | 28,1% | 10,8% | 60,5% | 0,7% |
| Rząd zależny tylko od głowy państwa | 10 | 36,6% | 5,6% | 55,7% | 2,0% |
| Nie wynika z tekstu | 5 | 15,6% | 22,2% | 57,1% | 5,1% |
| Prezydent kieruje rządem, ale wybiera go parlament | 2 | 31,2% | 0,0% | 66,7% | 2,1% |

## Ranking: najsilniejsza i najsłabsza głowa państwa

| Państwo | Typ | Głowa państwa | Rząd | Parlament | HHI |
|---|---|---|---|---|---|
| Brunei | Prezydencki: głowa państwa kieruje rządem | 64,3% | 0,0% | 35,7% | 0,54 |
| Gwinea Równikowa | Prezydencki: głowa państwa kieruje rządem | 63,6% | 0,0% | 36,4% | 0,50 |
| Arabia Saudyjska | Rząd zależny tylko od głowy państwa | 62,5% | 0,0% | 37,5% | 0,53 |
| Katar | Rząd zależny tylko od głowy państwa | 57,6% | 4,3% | 38,1% | 0,48 |
| Zambia | Prezydencki: głowa państwa kieruje rządem | 57,6% | 0,0% | 42,4% | 0,51 |
| Tunezja | Rząd odpowiada przed parlamentem i głową państwa (głowa wybierana pośrednio) | 57,4% | 0,0% | 42,6% | 0,45 |
| Malawi | Prezydencki: głowa państwa kieruje rządem | 55,6% | 0,0% | 44,4% | 0,43 |
| Zjednoczone Emiraty Arabskie | Rząd zależny tylko od głowy państwa | 55,0% | 5,0% | 40,0% | 0,47 |
| Cypr | Prezydencki: głowa państwa kieruje rządem | 54,5% | 0,0% | 45,5% | 0,50 |
| Nigeria | Prezydencki: głowa państwa kieruje rządem | 53,7% | 0,0% | 46,3% | 0,40 |
| Kuwejt | Monarchia parlamentarna | 52,9% | 4,8% | 42,3% | 0,46 |
| Mozambik | Prezydencki: głowa państwa kieruje rządem | 50,4% | 0,0% | 43,2% | 0,44 |
| Surinam | Prezydencki: głowa państwa kieruje rządem | 50,0% | 0,0% | 50,0% | 0,50 |
| Angola | Prezydencki: głowa państwa kieruje rządem | 49,5% | 0,0% | 48,0% | 0,48 |
| Indonezja | Prezydencki: głowa państwa kieruje rządem | 48,8% | 0,0% | 47,5% | 0,42 |
| Zimbabwe | Prezydencki: głowa państwa kieruje rządem | 48,5% | 0,0% | 51,5% | 0,39 |
| Algieria | Półprezydencki: rząd odpowiada przed parlamentem i prezydentem | 48,2% | 3,9% | 36,9% | 0,35 |
| Ekwador | Prezydencki: głowa państwa kieruje rządem | 48,1% | 0,0% | 51,8% | 0,50 |
| Afganistan | Prezydencki: głowa państwa kieruje rządem | 46,3% | 0,0% | 50,0% | 0,42 |
| Meksyk | Prezydencki: głowa państwa kieruje rządem | 46,3% | 0,0% | 53,7% | 0,36 |

Najsłabsza głowa państwa (udział bliski zera: działa na wniosek rządu albo nie uczestniczy w kluczowych decyzjach): Antigua i Barbuda, Armenia, Barbados, Bahamy, Dania, Etiopia, Finlandia, Izrael, Japonia, Saint Kitts i Nevis, Saint Lucia, Holandia, Norwegia, Nepal, Wyspy Salomona, Szwecja, Saint Vincent i Grenadyny.

## Unia Europejska

| Państwo | Typ | Głowa państwa | Rząd | Parlament | Inne | HHI |
|---|---|---|---|---|---|---|
| Cypr | Prezydencki: głowa państwa kieruje rządem | 54,5% | 0,0% | 45,5% | 0,0% | 0,50 |
| Malta | Rząd odpowiada przed parlamentem i głową państwa (głowa wybierana pośrednio) | 31,2% | 12,5% | 56,2% | 0,0% | 0,43 |
| Słowacja | Półprezydencki: rząd odpowiada przed parlamentem i prezydentem | 28,8% | 13,6% | 53,9% | 3,6% | 0,39 |
| Francja | Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 25,2% | 16,2% | 58,6% | 0,0% | 0,34 |
| Czechy | Rząd odpowiada przed parlamentem i głową państwa (głowa wybierana pośrednio) | 23,1% | 12,5% | 60,8% | 3,6% | 0,39 |
| Portugalia | Półprezydencki: rząd odpowiada przed parlamentem i prezydentem | 23,0% | 18,4% | 51,0% | 7,6% | 0,35 |
| Grecja | Parlamentarny (głowa państwa wybierana pośrednio) | 20,0% | 10,0% | 66,7% | 3,3% | 0,50 |
| Austria | Półprezydencki: rząd odpowiada przed parlamentem i prezydentem | 18,8% | 18,8% | 59,2% | 3,3% | 0,37 |
| Litwa | Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 18,6% | 4,5% | 73,5% | 3,4% | 0,58 |
| Włochy | Parlamentarny (głowa państwa wybierana pośrednio) | 18,2% | 23,9% | 50,0% | 8,0% | 0,23 |
| Polska | Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 16,3% | 13,9% | 66,8% | 3,0% | 0,44 |
| Rumunia | Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 15,9% | 15,9% | 60,6% | 7,6% | 0,32 |
| Chorwacja | Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 15,2% | 4,5% | 77,3% | 3,0% | 0,62 |
| Łotwa | Parlamentarny (głowa państwa wybierana pośrednio) | 13,6% | 13,6% | 63,6% | 9,1% | 0,45 |
| Słowenia | Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 13,6% | 0,0% | 83,3% | 3,0% | 0,64 |
| Niemcy | Parlamentarny (głowa państwa wybierana pośrednio) | 12,8% | 7,8% | 76,1% | 3,3% | 0,53 |
| Bułgaria | Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 12,5% | 4,5% | 76,5% | 6,4% | 0,61 |
| Estonia | Parlamentarny (głowa państwa wybierana pośrednio) | 10,0% | 10,0% | 80,0% | 0,0% | 0,66 |
| Węgry | Parlamentarny (głowa państwa wybierana pośrednio) | 8,0% | 12,5% | 76,5% | 3,0% | 0,61 |
| Irlandia | Nie wynika z tekstu | 6,2% | 12,5% | 77,1% | 4,2% | 0,48 |
| Luksemburg | Nie wynika z tekstu | 5,6% | 40,7% | 48,1% | 5,6% | 0,40 |
| Hiszpania | Monarchia parlamentarna | 2,1% | 29,4% | 66,3% | 2,1% | 0,42 |
| Dania | Monarchia parlamentarna | 0,0% | 37,5% | 56,2% | 6,2% | 0,46 |
| Finlandia | Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem | 0,0% | 25,0% | 75,0% | 0,0% | 0,62 |
| Holandia | Nie wynika z tekstu | 0,0% | 38,9% | 61,1% | 0,0% | 0,34 |
| Szwecja | Monarchia parlamentarna | 0,0% | 27,8% | 72,2% | 0,0% | 0,60 |

## Progi blokady

| Próg | Odrzucenie weta: państw | Zmiana konstytucji: państw |
|---|---|---|
| ponad 50% | 64 | 14 |
| ponad 40% | 3 | 9 |
| ponad 33,3% | 53 | 135 |
| ponad 25% | 1 | 20 |
| sprzeciwu nie da się odrzucić | 3 | 0 |
| – | 54 | 0 |

Odrzucenie weta: ile mandatów wystarczy, by utrzymać sprzeciw głowy państwa wobec ustawy („–”: głowa państwa nie ma weta lub tekst tego nie określa). Zmiana konstytucji: ile mandatów pierwszej izby blokuje zmianę, gdy pozostałe organy są za.

## Podstawa dla Polski

| Decyzja | Temat | Artykuły we fragmencie | Ręczna korekta |
|---|---|---|---|
| Uchwalenie ustawy zwykłej | legapp | Article 95, Article 121, Article 122, Article 123, Article 144, Article 235 |  |
| Uchwalenie ustawy zwykłej | override | Article 122 |  |
| Uchwalenie ustawy zwykłej | hospow | Article 133, Article 137, Article 138, Article 144 |  |
| Uchwalenie budżetu | budget | Article 146, Chapter VII. LOCAL SELF-GOVERNMENT, Article 167, Article 204, Article 219, Article 220 | art. 219 ust. 4: Rada Ministrów prowadzi gospodarkę na podstawie projektu; art. 225: Prezydent może zarządzić skrócenie kadencji Sejmu, jeśli ustawa budżetowa nie zostanie przedstawiona do podpisu w ciągu 4 miesięcy (artykułu nie było w fragmencie) |
| Uchwalenie budżetu | legini | Article 118, Article 122, Article 146, Article 219, Article 220, Article 221 | art. 220 ust. 1: zwiększenie wydatków lub ograniczenie dochodów planowanych przez Radę Ministrów nie może powodować ustalenia przez Sejm większego deficytu budżetowego niż przewidziany w projekcie |
| Uchwalenie budżetu | legapp | Article 95, Article 121, Article 122, Article 123, Article 144, Article 235 |  |
| Uchwalenie budżetu | override | Article 122 |  |
| Zmiana konstytucji | amend | Article 235 | art. 235 ust. 3 i 5: pierwsze czytanie najwcześniej 30. dnia od przedłożenia; dla rozdz. I, II, XII uchwalenie najwcześniej 60. dnia po pierwszym czytaniu |
| Powołanie szefa rządu | hogelect | Article 144, Article 147, Article 154, Article 155, Article 162, Chapter XIII. FINAL AND TRANSITIONAL PROVISIONS |  |
| Powołanie szefa rządu | hospow | Article 133, Article 137, Article 138, Article 144 |  |
| Odwołanie rządu | cabdiss | Article 154, Article 156, Article 157, Article 158, Article 159, Article 160 |  |
| Odwołanie rządu | hogdlim | Article 158 |  |
| Rozwiązanie parlamentu | legdiss | Article 98, Article 155, Article 225 |  |
| Rozwiązanie parlamentu | hospow | Article 133, Article 137, Article 138, Article 144 |  |
| Wybór sędziów sądu konstytucyjnego | consel | Article 194 |  |
| Stan nadzwyczajny | em | Chapter XI. EXTRAORDINARY MEASURES |  |
| Stan nadzwyczajny | hospow | Article 133, Article 137, Article 138, Article 144 |  |
| Wojna i użycie wojska | war | Article 116, Article 117, Article 136 | art. 116 ust. 2: jeżeli Sejm nie może zebrać się na posiedzenie, o stanie wojny postanawia Prezydent RP |
| Wojna i użycie wojska | hospow | Article 133, Article 137, Article 138, Article 144 |  |
| Ratyfikacja umów | treat | Article 55, Article 89, Article 90, Article 91, Article 133, Article 146 |  |
| Ratyfikacja umów | hospow | Article 133, Article 137, Article 138, Article 144 |  |
| Usunięcie głowy państwa | hosdiss | Article 131, Article 145 |  |

## Kto może sam przejąć instytucje

Dla każdej instytucji opisanej w konstytucji: najsłabszy obóz polityczny, który sam wybiera wszystkich jej członków. „Decyduje ustawa”: konstytucja nie mówi, kto wybiera. „Poza zasięgiem samej polityki”: współdecydują sędziowie, naród albo opozycja.

| Instytucja | Polska | Państw z tą instytucją | Zwykła większość lub ustawa | Potrzebna większość kwalifikowana lub sędziowie |
|---|---|---|---|---|
| Sąd konstytucyjny | zwykła większość w izbie | 88 | 53,4% | 46,6% |
| Rada sądownictwa | decyduje ustawa (zwykła większość) | 130 | 72,3% | 27,7% |
| Rzecznik praw (ombudsman) | zwykła większość w izbie | 89 | 100,0% | 0,0% |
| Bank centralny | większość i głowa państwa | 95 | 100,0% | 0,0% |
| Prokurator generalny | decyduje ustawa (zwykła większość) | 149 | 83,9% | 16,1% |
| Organ wyborczy | nie ma w konstytucji | 113 | 85,0% | 15,0% |
| Zmiana konstytucji | 2/3 mandatów | 178 | 4,5% | 95,5% |

W Polsce sędziów Trybunału wybiera Sejm bez większości kwalifikowanej (art. 194), a konstytucja nie mówi, kto wybiera sędziów-członków KRS (art. 187 ust. 4 odsyła do ustawy). Te dwie instytucje może więc obsadzić sama większość sejmowa. Prezesa NBP powołuje Sejm na wniosek Prezydenta (art. 227), więc potrzebna jest ich zgoda. Zmiana konstytucji wymaga 2/3 Sejmu i Senatu (art. 235).

## Niezależność sądów zapisana w konstytucji

Indeks: odsetek z 10 gwarancji obecnych w tekście (spośród tych, które dotyczą danej konstytucji). Polska: 80 na 100, mediana świata 30, średnia UE 54. Brakuje dwóch: sędziów TK wybiera jeden organ zwykłą większością, a konstytucja nie mówi, że sędziów-członków KRS wybierają sędziowie.

| Gwarancja | Polska | Odsetek konstytucji |
|---|---|---|
| Sędziów TK wybiera więcej niż jeden organ albo większość kwalifikowana | nie | 42,2% |
| Kadencja sędziów TK co najmniej 9 lat albo do wieku emerytalnego | tak | 26,6% |
| Sędzia TK nie może być wybrany ponownie | tak | 26,6% |
| Rada sądownictwa z większością sędziów | tak | 16,9% |
| Sędziowie-członkowie rady wybierani przez sędziów | nie | 23,8% |
| Nieusuwalność sędziów | tak | 26,2% |
| O odwołaniu sędziego decyduje organ sądowy | tak | 20,7% |
| Odwołanie tylko z przyczyn określonych w ustawie | tak | 65,9% |
| Mniejszość parlamentarna lub obywatel może zaskarżyć ustawę do TK | tak | 57,1% |
| Wyrok TK uchyla niekonstytucyjny przepis | tak | 51,3% |

| Państwo UE | Indeks |
|---|---|
| Włochy | 90 |
| Polska | 80 |
| Portugalia | 80 |
| Rumunia | 80 |
| Słowenia | 80 |
| Austria | 75 |
| Czechy | 75 |
| Bułgaria | 70 |
| Hiszpania | 70 |
| Chorwacja | 70 |
| Francja | 60 |
| Węgry | 60 |
| Litwa | 60 |
| Estonia | 50 |
| Luksemburg | 50 |
| Grecja | 40 |
| Cypr | 30 |
| Niemcy | 30 |
| Łotwa | 30 |
| Malta | 30 |
| Słowacja | 30 |
| Finlandia | 12 |
| Irlandia | 0 |

## Jak reformy zmieniłyby układ sił w Polsce

Wynik symulatora (strona Władza → Symulator) dla gotowych zestawów. „Instytucje”: ile z pięciu (TK, KRS, RPO, NBP, zmiana konstytucji) może obsadzić sama zwykła większość, z Prezydentem lub bez.

| Zestaw | Sejm | Senat | Rząd | Prezydent | Naród | Instytucje w zasięgu zwykłej większości |
|---|---|---|---|---|---|---|
| Obecna konstytucja | 62,2% | 4,5% | 13,9% | 16,3% | 0,0% | 4 z 5 |
| P04: ochrona sądów przed przejęciem | 62,2% | 4,5% | 13,9% | 16,3% | 0,0% | 2 z 5 |
| P20: obywatelskie referendum ustaw | 58,5% | 4,5% | 13,9% | 15,9% | 4,1% | 4 z 5 |
| P24: wariant parlamentarny | 71,7% | 4,5% | 18,7% | 2,0% | 0,0% | 4 z 5 |
| Kierunek prezydencki | 52,5% | 4,5% | 13,9% | 26,0% | 0,0% | 4 z 5 |

## Na ile ufać tym liczbom

- **Odczyty a eksperci.** W 1644 porównaniach z ręcznym kodowaniem Comparative Constitutions Project (wersja 5) zgodność wynosi 86,9%. Pola strukturalne: liczba izb 97%, próg odrzucenia weta 99%, rozwiązanie parlamentu 97%. Najsłabiej: kto odwołuje rząd (ok. 70%), bo CCP liczy też formalne odwołanie ministrów przez głowę państwa.
- **Typ ustroju.** Zgodność z klasyfikacją Cheibuba, Elkinsa i Ginsburga (2014): 83,0% (106 konstytucji, kappa 0,746). Udział głowy państwa w naszym modelu rośnie zgodnie z ich typem: parlamentarne 16,0%, półprezydenckie 21,4%, prezydenckie 39,2%.
- **Niezależność sądów.** Korelacja rang z indeksem Meltona i Ginsburga (2014): ρ = 0,317 (95%: 0,159–0,459). Umiarkowana: ich indeks dotyczy sądu najwyższego, nasz głównie TK i rady sądownictwa.
- **Indeks władzy wykonawczej CCP** (7 uprawnień) koreluje z naszym udziałem głowy państwa i rządu słabo (ρ = 0,183). Ten indeks liczy uprawnienia całej władzy wykonawczej, także premiera, i prawie nie różnicuje typów ustroju, więc mierzy co innego.
- **Założenia.** Przy innych założeniach (wagi decyzji, bez reguły dla monarchii, łatwe lub nieosiągalne większości kwalifikowane, tylko decyzje bez założeń) korelacja rang z modelem bazowym wynosi 0,857–0,993, ale pojedyncze miejsce przesuwa się typowo o 27 pozycji. Dlatego podajemy przedziały.

## Metoda i ograniczenia

- Dane: 49 tematów wariantów odczytanych modelem językowym (Claude) z angielskich wydań Constitute dla 188 obowiązujących konstytucji. Kod sprawdza, że cytat występuje w tekście; odpowiedzi bez zgodnego cytatu pominięto. Wartości dla Polski sprawdzono ręcznie (korekty z podstawą prawną w korekty.json).
- Indeks Shapleya-Shubika: organy jednoosobowe są graczami, izba to duża grupa równych posłów. Weto odrzucane większością q daje głowie państwa udział równy szerokości okna między 50% a q. Liczone dokładnie, bez losowania. Profil państwa to średnia z decyzji, które da się zbudować z tekstu.
- Organy są jednolite: model nie zna partii, koalicji, kohabitacji ani praktyki. Kolejność działania (kto proponuje pierwszy) nie daje siły, liczy się tylko, czyja zgoda jest potrzebna. Obie izby głosują tą samą większością.
- Liczbę izb i próg odrzucenia weta, gdy nie wynikały z odczytu, oraz sposób wyboru głowy państwa (do typologii) wzięto z kodowania CCP (Elkins i Ginsburg 2025).
- Gdy tekst czegoś nie określa, przyjęto założenie wypisane przy decyzji. Do rankingów trafiają państwa z co najmniej 6 decyzjami bez niewiadomych w strukturze (178 ze 188).
- Wydania Constitute mogą nie uwzględniać najnowszych zmian. Raport nie obejmuje ustaw, regulaminów ani orzecznictwa.
