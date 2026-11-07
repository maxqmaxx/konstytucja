#!/bin/sh
# Rebuild every generated page, then apply the shared menu and light/dark theme (theme/apply.py must run last).
set -e
cd "$(dirname "$0")/.."
python3 analysis/features/prevalence.py
python3 analysis/polska/build.py
python3 analysis/mapa/build.py
python3 analysis/panstwa/build.py
python3 analysis/rp/build.py
python3 analysis/konstruktor/build.py
python3 analysis/statystyki/build.py
python3 analysis/wladza/model.py
python3 analysis/wladza/build.py
python3 analysis/theme/apply.py
