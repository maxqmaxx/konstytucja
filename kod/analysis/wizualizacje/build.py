#!/usr/bin/env python3
"""Build an offline gallery and reproducible lexical analysis of archived constitutions."""

from collections import Counter
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

# Keep BLAS work bounded and independent of host thread defaults.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
import scipy
from scipy import sparse
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from atlas import CATEGORIES, TOPICS, normalized

PARAMETERS = {
    "corpus": "provider=constitute, language=en",
    "min_document_frequency": 3,
    "max_document_frequency_ratio": 0.85,
    "features": "unigrams and adjacent bigrams; English stopwords removed",
    "tf": "1 + log(count)",
    "idf": "log((1 + N) / (1 + document_frequency)) + 1",
    "similarity": "cosine of L2-normalized TF-IDF vectors",
    "projection": "classical MDS of sqrt(2 * (1 - cosine)); two largest eigenvectors",
    "clustering": "average linkage of cosine distances; at most six clusters",
    "groups": 6,
    "topics": "seven existing atlas dictionaries; non-overlapping regex matches per cleaned paragraph",
    "normalization": "matches * 10000 / all alphabetic word tokens",
    "deduplication": "SHA-256 of cleaned text; keep every source record as alias",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")


def clean_lines(lines):
    """Keep original line numbers while excluding publisher furniture and contents."""
    result = []
    for line, text in enumerate(lines, 1):
        if re.search(r"constituteproject\.org|PDF generated:|Table of contents|repository of the Comparative|distributed on constituteproject", text, re.I):
            continue
        if re.search(r"(?:\.\s*){4,}|\bPage\s+\d+|^\s*\d+\s*/\s*\d+\s*$", text, re.I):
            continue
        value = " ".join(unicodedata.normalize("NFKC", text).split())
        if value and not value.isdigit():
            result.append((line, value))
    return result


def tokens(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", unicodedata.normalize("NFKC", text).lower())


def term_counts(text, stopwords):
    words = tokens(text)
    counts = Counter(w for w in words if len(w) > 2 and w not in stopwords)
    counts.update(a + " " + b for a, b in zip(words, words[1:])
                  if len(a) > 2 and len(b) > 2 and a not in stopwords and b not in stopwords)
    return counts


def tfidf(counts):
    frequency = Counter(term for row in counts for term in row)
    n = len(counts)
    vocabulary = sorted(term for term, df in frequency.items()
                        if PARAMETERS["min_document_frequency"] <= df <= n * PARAMETERS["max_document_frequency_ratio"])
    columns = {term: i for i, term in enumerate(vocabulary)}
    data, row_indices, col_indices = [], [], []
    for row, values in enumerate(counts):
        for term, count in values.items():
            if term in columns:
                row_indices.append(row)
                col_indices.append(columns[term])
                data.append((1 + np.log(count)) * (np.log((1 + n) / (1 + frequency[term])) + 1))
    matrix = sparse.csr_matrix((data, (row_indices, col_indices)), shape=(n, len(vocabulary)))
    norms = np.sqrt(matrix.multiply(matrix).sum(axis=1)).A1
    if np.any(norms == 0):
        raise ValueError("A document has no eligible lexical features")
    return sparse.diags(1 / norms) @ matrix, vocabulary


def coordinates_and_clusters(similarity):
    n = len(similarity)
    # Double-centering the Gram matrix equals classical MDS on normalized vectors.
    centered = similarity - similarity.mean(axis=0)[None, :] - similarity.mean(axis=1)[:, None] + similarity.mean()
    eigenvalues, eigenvectors = np.linalg.eigh(centered)
    axes = np.argsort(eigenvalues)[-2:][::-1]
    coords = eigenvectors[:, axes] * np.sqrt(np.maximum(eigenvalues[axes], 0))
    for axis in range(2):
        if coords[np.argmax(np.abs(coords[:, axis])), axis] < 0:
            coords[:, axis] *= -1
    distance = np.clip(1 - similarity, 0, 2)
    np.fill_diagonal(distance, 0)
    groups = fcluster(linkage(squareform(distance, checks=False), method="average"),
                      t=min(PARAMETERS["groups"], n), criterion="maxclust")
    # Stable group IDs follow the sorted document IDs, not linkage implementation labels.
    ordered = sorted(set(groups), key=lambda group: np.flatnonzero(groups == group)[0])
    groups = np.array([ordered.index(group) + 1 for group in groups])
    explained = float(eigenvalues[axes].sum() / np.maximum(eigenvalues, 0).sum())
    return coords, groups, explained


def topic_profile(lines, word_count):
    out = {}
    for key, (label, pattern) in TOPICS.items():
        hits = []
        for line, text in lines:
            matches = list(re.finditer(pattern, normalized(text), re.I))
            if matches:
                hits.append({"line": line, "count": len(matches), "text": text})
        count = sum(hit["count"] for hit in hits)
        out[key] = {"count": count, "rate": round(10000 * count / word_count, 4), "hits": hits}
    return out


def extract_html(path):
    soup = BeautifulSoup(path.read_bytes(), "lxml")
    body = soup.select_one(".constitution-content__copy")
    if body is None:
        raise ValueError("Constitution text container missing: " + str(path))
    for node in body.select("script,style,.section-topic"):
        node.decompose()
    lines, seen = [], set()
    for node in body.strings:
        value = node.strip()
        if not value:
            continue
        heading = node.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"])
        if heading is not None:
            if id(heading) in seen:
                continue
            seen.add(id(heading))
            value = heading.get_text(" ", strip=True)
        lines.append(value)
    return "\n".join(lines) + "\n"


def source_page(slug, record, lines):
    href = "../../../" + record["input_path"]
    content = "".join(f'<p id="l{line}"><a class="ln" href="#l{line}">{line}</a>{escape(text)}</p>' for line, text in lines)
    (HERE / "texts" / (slug + ".html")).write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{escape(record["title"])}</title><link rel="stylesheet" href="../source.css">'
        '<nav><a href="../index.html#sasiedztwo">← Galeria analiz</a></nav>'
        f'<h1>{escape(record["title"])}</h1><p>Odczyt do analizy słownictwa. Wiersze odnoszą się do wejściowego tekstu roboczego. '
        'Status i data opisują wydanie archiwalne.</p>'
        f'<p><a href="{escape(href, quote=True)}">Wejście w archiwum</a> · '
        f'<a href="{escape(record["source_url"], quote=True)}">Źródło u wydawcy</a></p>{content}</html>')


def corpus_analysis(catalog, normalized_sources):
    (HERE / "texts").mkdir(exist_ok=True)
    stopwords = set((HERE / "stopwords.txt").read_text().split())
    documents, exclusions, by_hash, counts, cleaned = [], [], {}, [], []
    records = sorted((r for r in catalog if r["provider"] == "constitute" and r["language"] == "en"), key=lambda r: r["id"])
    input_hashes = {}
    for record in records:
        source = normalized_sources.get(record["id"])
        generated_text = None
        if source:
            path = ROOT / source["path"]
            if digest(path) != source["sha256"]:
                raise ValueError("Normalized source hash differs: " + record["id"])
            raw = path.read_text()
        else:
            asset = next((a for a in record.get("assets", []) if a["format"] == "html"), None)
            if asset:
                source = {"path": asset["path"], "sha256": asset["sha256"]}
                path = ROOT / asset["path"]
                if digest(path) != asset["sha256"]:
                    raise ValueError("Archive source hash differs: " + record["id"])
                generated_text = extract_html(path)
                raw = generated_text
            else:
                exclusions.append({"id": record["id"], "reason": "no usable HTML or normalized source"})
                continue
        slug = record["id"].replace(":", "-")
        lines = clean_lines(raw.splitlines())
        text = "\n".join(value for _, value in lines)
        word_count = len(tokens(text))
        if word_count < 100:
            exclusions.append({"id": record["id"], "reason": "fewer than 100 word tokens"})
            continue
        sha = hashlib.sha256(text.encode()).hexdigest()
        alias = {"id": record["id"], "title": record["title"], "source_url": record["source_url"],
                 "input_path": source["path"], "sha256": source["sha256"]}
        input_hashes[source["path"]] = source["sha256"]
        if sha in by_hash:
            documents[by_hash[sha]]["aliases"].append(alias)
            continue
        if generated_text is not None:
            normalized_path = HERE / "texts" / (slug + ".txt")
            normalized_path.write_text(generated_text)
            alias["input_path"] = str(normalized_path.relative_to(ROOT))
            alias["sha256"] = digest(normalized_path)
        source_page(slug, alias, lines)
        item = {"id": record["id"], "title": record["title"], "country": record["country"], "country_code": record["country_code"],
                "status": record["status"], "year": record.get("year_enacted"), "revised": record.get("year_revised"),
                "source_url": record["source_url"], "text_url": "texts/" + slug + ".html", "input_path": alias["input_path"],
                "input_sha256": alias["sha256"], "clean_sha256": sha, "words": word_count, "aliases": [alias],
                "topics": topic_profile(lines, word_count)}
        by_hash[sha] = len(documents)
        documents.append(item)
        counts.append(term_counts(text, stopwords))
        cleaned.append(lines)
    print(f"Prepared {len(documents)} unique texts from {len(records)} records", flush=True)
    matrix, vocabulary = tfidf(counts)
    similarity = np.clip((matrix @ matrix.T).toarray(), 0, 1)
    coords, groups, explained = coordinates_and_clusters(similarity)
    group_labels = {}
    for group in sorted(set(groups)):
        members = np.flatnonzero(groups == group)
        centroid = np.asarray(matrix[members].mean(axis=0)).ravel()
        top = sorted(range(len(vocabulary)), key=lambda k: (-centroid[k], vocabulary[k]))[:5]
        group_labels[int(group)] = [vocabulary[k] for k in top]
    for i, item in enumerate(documents):
        row = matrix.getrow(i)
        top = sorted(zip(row.indices, row.data), key=lambda pair: (-pair[1], vocabulary[pair[0]]))[:8]
        item.update(x=round(float(coords[i, 0]), 7), y=round(float(coords[i, 1]), 7), group=int(groups[i]),
                    terms=[vocabulary[k] for k, _ in top])
        neighbors = sorted((j for j in range(len(documents)) if j != i), key=lambda j: (-similarity[i, j], documents[j]["id"]))[:5]
        item["neighbors"] = []
        for j in neighbors:
            shared = row.multiply(matrix.getrow(j))
            best = sorted(zip(shared.indices, shared.data), key=lambda pair: (-pair[1], vocabulary[pair[0]]))[:5]
            terms = [vocabulary[k] for k, _ in best]
            snippets = []
            for k in [i, j]:
                ranked = sorted(cleaned[k], key=lambda pair: (-sum(bool(re.search(r"\b" + re.escape(term) + r"\b", pair[1], re.I)) for term in terms), pair[0]))
                line, value = ranked[0]
                snippets.append({"id": documents[k]["id"], "line": line, "text": value,
                                 "url": documents[k]["text_url"] + f"#l{line}"})
            item["neighbors"].append({"id": documents[j]["id"], "similarity": round(float(similarity[i, j]), 7), "terms": terms, "snippets": snippets})
    return {"records": len(records), "documents": documents, "excluded": exclusions, "groups": group_labels,
            "projection_explained": round(explained, 5), "features": len(vocabulary),
            "similarities": np.round(similarity, 7).tolist(), "inputs": input_hashes}


def build():
    catalog = [json.loads(line) for line in (ROOT / "catalog.jsonl").read_text().splitlines()]
    clauses = json.loads((HERE.parent / "zapisy.json").read_text())
    proposals = json.loads((HERE.parent / "polska/propozycje.json").read_text())
    records = {r["id"]: r for r in catalog}
    for item in clauses:
        row = records[item["document_id"]]
        item.update(year=row.get("year_enacted"), revised=row.get("year_revised"))
    corpus = corpus_analysis(catalog, json.loads((HERE.parent / "normalized-sources.json").read_text()))
    inputs = {str(p.relative_to(ROOT)): digest(p) for p in [ROOT / "catalog.jsonl", HERE.parent / "zapisy.json",
              HERE.parent / "polska/propozycje.json", HERE.parent / "normalized-sources.json", HERE / "stopwords.txt", HERE / "build.py"]}
    inputs.update(corpus.pop("inputs"))
    data = {"clauses": clauses, "categories": CATEGORIES, "proposals": proposals["proposals"], "labels": proposals["labels"],
            "corpus": corpus, "topics": {key: value[0] for key, value in TOPICS.items()},
            "summary": json.loads((ROOT / "reports/summary.json").read_text()),
            "screening": json.loads((HERE.parent / "screening-summary.json").read_text()), "parameters": PARAMETERS}
    for relative in ["reports/summary.json", "analysis/screening-summary.json", "analysis/atlas.py"]:
        inputs[relative] = digest(ROOT / relative)
    write_json(HERE / "data.json", data)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    template = (HERE / "template.html").read_text()
    if template.count("@@DATA@@") != 1:
        raise ValueError("Exactly one gallery data marker is required")
    (HERE / "index.html").write_text(template.replace("@@DATA@@", payload))
    manifest = {"schema_version": 1, "inputs": inputs, "parameters": PARAMETERS,
                "versions": {"numpy": np.__version__, "scipy": scipy.__version__},
                "corpus_records": corpus["records"], "unique_clean_texts": len(corpus["documents"]),
                "excluded": corpus["excluded"], "features": corpus["features"],
                "outputs": {name: digest(HERE / name) for name in ["data.json", "index.html", "app.js", "style.css", "source.css"]}}
    write_json(HERE / "manifest.json", manifest)
    print(json.dumps({k: manifest[k] for k in ["corpus_records", "unique_clean_texts", "features", "excluded"]}), flush=True)


if __name__ == "__main__":
    build()
