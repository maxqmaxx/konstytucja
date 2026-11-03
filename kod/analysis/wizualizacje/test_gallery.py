"""Regression checks for evidence, counting units and reproducible lexical analysis."""
import hashlib
import json
from pathlib import Path
import unittest
from urllib.parse import urlparse, unquote

from bs4 import BeautifulSoup
import numpy as np

import build


class AnalysisTests(unittest.TestCase):
    def test_cleaning_preserves_line_numbers_and_legal_text(self):
        lines = ['PDF generated: 2026', 'Table of contents', 'Article 1 . . . . . 4',
                 'Page 3', 'Everyone has the right to judicial review.', '', 'The government shall publish its budget.']
        self.assertEqual(build.clean_lines(lines), [(5, lines[4]), (7, lines[6])])

    def test_html_extraction_excludes_publisher_topics(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'input.html'
            path.write_text('<div class="constitution-content__copy"><h2>Article <b>1</b></h2><p>Equal protection.</p><div class="section-topic">Publisher annotation</div></div>')
            self.assertEqual(build.extract_html(path), 'Article 1\nEqual protection.\n')

    def test_tfidf_cosine_and_projection_are_repeatable(self):
        rows = [build.Counter({'water': 3+i, 'rights': 2, 'budget': 2, 'onlyone': 1} if i == 0 else {'water': 3+i, 'rights': 2}) for i in range(6)]
        rows += [build.Counter({'budget': 5, 'tax': 3}) for _ in range(4)]
        matrix, vocabulary = build.tfidf(rows)
        self.assertNotIn('onlyone', vocabulary)
        similarity = (matrix @ matrix.T).toarray()
        np.testing.assert_allclose(similarity, similarity.T, atol=1e-12)
        np.testing.assert_allclose(np.diag(similarity), 1, atol=1e-12)
        self.assertGreater(similarity[1, 2], similarity[1, 8])
        a, ag, av = build.coordinates_and_clusters(similarity)
        b, bg, bv = build.coordinates_and_clusters(similarity)
        np.testing.assert_allclose(a, b)
        np.testing.assert_equal(ag, bg)
        self.assertEqual(av, bv)

    def test_topic_rates_count_multiple_hits_and_use_length(self):
        lines = [(7, 'Human rights and fundamental rights. Judicial review.')]
        profile = build.topic_profile(lines, 20)
        self.assertEqual(profile['rights']['count'], 2)
        self.assertEqual(profile['rights']['rate'], 1000)
        self.assertEqual(profile['rights']['hits'][0]['line'], 7)
        self.assertEqual(build.topic_profile(lines, 40)['rights']['rate'], 500)
        self.assertEqual(profile['capacity']['count'], 0)


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((build.HERE / 'data.json').read_text())
        cls.manifest = json.loads((build.HERE / 'manifest.json').read_text())

    def test_inputs_outputs_and_normalized_source_integrity(self):
        for path, sha in self.manifest['inputs'].items():
            self.assertEqual(build.digest(build.ROOT / path), sha, path)
        for path, sha in self.manifest['outputs'].items():
            self.assertEqual(build.digest(build.HERE / path), sha, path)
        for doc in self.data['corpus']['documents']:
            self.assertEqual(build.digest(build.ROOT / doc['input_path']), doc['input_sha256'])
            lines = build.clean_lines((build.ROOT / doc['input_path']).read_text().splitlines())
            self.assertEqual(hashlib.sha256('\n'.join(s for _, s in lines).encode()).hexdigest(), doc['clean_sha256'])

    def test_relationships_and_counting_units(self):
        entries = self.data['clauses']
        ids = {c['id'] for c in entries}
        self.assertEqual(len(ids), len(entries))
        self.assertEqual(len(entries), 130)
        self.assertEqual(len({c['document_id'] for c in entries}), 80)
        self.assertEqual(len({c['country_code'] for c in entries}), 67)
        for proposal in self.data['proposals']:
            self.assertTrue(set(proposal['inspirations']) <= ids)
            self.assertTrue(all(1 <= n <= 243 for n in proposal['polish_articles']))
        self.assertEqual(sum('panstwo' in c['categories'] and 'wladca' in c['categories'] for c in entries), 1)
        for a in self.data['categories']:
            for b in self.data['categories']:
                pair = sum(a in c['categories'] and b in c['categories'] for c in entries)
                self.assertLessEqual(pair, sum(a in c['categories'] for c in entries))

    def test_similarity_neighbors_and_evidence_resolve(self):
        corpus = self.data['corpus']
        docs = corpus['documents']
        by_id = {d['id']: d for d in docs}
        self.assertEqual(len({d['clean_sha256'] for d in docs}), len(docs))
        self.assertEqual(sum(len(d['aliases']) for d in docs) + len(corpus['excluded']), corpus['records'])
        similarity = np.asarray(corpus['similarities'])
        evidence_lines = {doc['id']: dict(build.clean_lines((build.ROOT / doc['input_path']).read_text().splitlines())) for doc in docs}
        source_html = {doc['id']: (build.HERE / doc['text_url']).read_text() for doc in docs}
        np.testing.assert_allclose(similarity, similarity.T)
        np.testing.assert_allclose(np.diag(similarity), 1)
        self.assertTrue(np.isfinite(similarity).all())
        self.assertTrue((similarity >= 0).all() and (similarity <= 1).all())
        for i, doc in enumerate(docs):
            self.assertEqual(len(doc['neighbors']), 5)
            self.assertNotIn(doc['id'], [n['id'] for n in doc['neighbors']])
            for neighbor in doc['neighbors']:
                self.assertIn(neighbor['id'], by_id)
                self.assertAlmostEqual(neighbor['similarity'], similarity[i, next(j for j, d in enumerate(docs) if d['id'] == neighbor['id'])])
                for snippet in neighbor['snippets']:
                    target = by_id[snippet['id']]
                    self.assertEqual(evidence_lines[target['id']][snippet['line']], snippet['text'])
                    self.assertIn(f'id="l{snippet["line"]}"', source_html[target['id']])
            for profile in doc['topics'].values():
                self.assertEqual(profile['count'], sum(hit['count'] for hit in profile['hits']))
                self.assertAlmostEqual(profile['rate'], profile['count'] * 10000 / doc['words'], places=3)

    def test_offline_page_matches_data_and_has_no_remote_dependencies(self):
        soup = BeautifulSoup((build.HERE / 'index.html').read_text(), 'lxml')
        self.assertEqual(json.loads(soup.select_one('#gallery-data').string), self.data)
        for node in soup.select('script[src], link[href], a[href]'):
            href = node.get('src', node.get('href'))
            target = urlparse(href)
            if target.scheme or not target.path:
                continue
            self.assertTrue((build.HERE / unquote(target.path)).resolve().is_file(), href)


if __name__ == '__main__':
    unittest.main()
