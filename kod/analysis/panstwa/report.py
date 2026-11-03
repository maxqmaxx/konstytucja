"""Shared 'Zgłoś błąd' link. The prefilled GitHub issue URL is built on click by theme/theme.js from data-where /
data-current, so pages stay small; without JavaScript the link opens an empty issue form."""
from html import escape

REPO = "https://github.com/maxqmaxx/konstytucja"


def issue_link(where, current=""):
    cur = f' data-current="{escape(current[:300])}"' if current else ""
    return (f'<a class="report" href="{REPO}/issues/new?labels=dane" data-where="{escape(where)}"{cur} target="_blank" rel="noopener" '
            f'title="Otwiera zgłoszenie na GitHubie (wymaga konta)">Zgłoś błąd</a>')
