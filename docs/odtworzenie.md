# Odtworzenie

Wymagania: Python 3.10+, pakiety z `kod/requirements.txt`, narzędzia `pdfinfo` i `pdftotext` (Poppler). Uruchamiaj z katalogu `kod/`.

```bash
cd kod
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 1. Archiwum: odkrywanie i pobieranie (tworzy countries/, catalog.jsonl; kilka GB, godziny)
python3 collect.py discover
python3 sources.py wipo --workers 4 ; python3 sources.py mjp --workers 4 ; python3 sources.py sejm --workers 4
python3 seed_official.py && python3 maintain.py && python3 resolve_landings.py
python3 collect.py download --workers 4 && python3 collect.py verify

# 2. Kodowanie CCP i statystyki
python3 analysis/features/ccp_topics.py
python3 analysis/features/prevalence.py
python3 -m unittest discover -s analysis/features -p test_features.py

# 3. Serwis statyczny (atlas, Polska, mapa, państwa, Konstytucja RP, tematy, problemy, teczka)
python3 analysis/atlas.py normalize && python3 analysis/atlas.py screen && python3 analysis/atlas.py build
sh tools/build_site.sh   # wszystkie strony, potem wspólne menu i motyw (theme/apply.py)

# 4. (opcjonalnie) wyszukiwarka pełnotekstowa i przekłady (wymaga klucza API Anthropic, płatne)
python3 analysis/szukaj/index.py
python3 analysis/tlumaczenia/rich.py          # pilot; pełny przebieg: rich.py submit / status / collect
```

Pobieraj z umiarem: skrypty mają limity równoległości i odstępy między żądaniami. Szanuj warunki wydawców.

Warianty (`analysis/warianty/extract.py`) wymagają klucza API i przebiegu wsadowego (ok. 15 USD). Surowe odczyty z cytatami (`warianty.jsonl`) nie są publikowane, bo zawierają fragmenty tekstów; gotowe wartości są w `dane/warianty.csv`.
