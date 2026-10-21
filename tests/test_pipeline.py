import importlib.util
import json
from pathlib import Path
import tempfile
import os
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('update_news', ROOT/'scripts/update_news.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class PipelineTests(unittest.TestCase):
    def test_parses_rss_metadata_without_body(self):
        data = (ROOT/'tests/fixtures/sample_feed.xml').read_bytes()
        articles = module.parse_feed(data, '国際', 'Test RSS')
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]['title'], '国際ニュースのタイトルをテストする')
        self.assertEqual(articles[0]['source'], 'Example News')
        self.assertNotIn('ARTICLE BODY', json.dumps(articles))
        self.assertNotIn('<script>', json.dumps(articles))

    def test_rejects_unsafe_urls(self):
        self.assertIsNone(module.http_link('javascript:alert(1)'))
        self.assertIsNone(module.http_link('file:///etc/passwd'))
        self.assertIsNotNone(module.http_link('https://example.org/news'))

    def test_merge_deduplicates_and_removes_demo(self):
        items = module.parse_feed((ROOT/'tests/fixtures/sample_feed.xml').read_bytes(), '国際', 'Test RSS')
        merged = module.merged_items(items + items, [dict(items[0], demo=True),{'id':'old-demo','demo':True}])
        self.assertEqual(len(merged), 2)
        self.assertTrue(all(not x['demo'] for x in merged))

    def test_ai_question_is_preserved_when_headline_is_refetched(self):
        items = module.parse_feed((ROOT/'tests/fixtures/sample_feed.xml').read_bytes(), '国際', 'Test RSS')
        old = [dict(items[0], ai_question='何を元記事で確認すべきでしょうか？', ai_provider='Cloudflare Workers AI', ai_label='見出しから考える確認ポイント（本文未確認）')]
        result = module.merged_items(items, old)
        same = next(a for a in result if a['id'] == items[0]['id'])
        self.assertEqual(same['ai_question'], '何を元記事で確認すべきでしょうか？')

    def test_atom(self):
        xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom news headline</title><link href="https://example.com/a" rel="alternate"/><updated>2026-10-21T12:00:00Z</updated></entry></feed>'''
        self.assertEqual(len(module.parse_feed(xml, '科学', 'Atom Source')), 1)

    def test_fixture_update_removes_demo_and_persists(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'news.json'
            target.write_text(json.dumps({'demo': True, 'articles': [{'id': 'demo1', 'demo': True}]}), encoding='utf-8')
            original = module.NEWS
            original_ai = os.environ.get('AI_EDITOR_ENABLED')
            try:
                module.NEWS = target
                os.environ['AI_EDITOR_ENABLED'] = '0'
                code = module.main(['--fixture', str(ROOT/'tests/fixtures/sample_feed.xml')])
                self.assertEqual(code, 0)
                result = json.loads(target.read_text(encoding='utf-8'))
                self.assertFalse(result['demo'])
                self.assertEqual(len(result['articles']), 2)
            finally:
                module.NEWS = original
                if original_ai is None:
                    os.environ.pop('AI_EDITOR_ENABLED', None)
                else:
                    os.environ['AI_EDITOR_ENABLED'] = original_ai

    def test_build_only_public_files(self):
        spec = importlib.util.spec_from_file_location('build_site', ROOT/'scripts/build_site.py')
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        build.build()
        self.assertTrue((ROOT/'dist'/'index.html').exists())
        self.assertTrue((ROOT/'dist'/'data/news.json').exists())
        self.assertFalse((ROOT/'dist'/'config/sources.json').exists())
        self.assertFalse((ROOT/'dist'/'scripts/update_news.py').exists())

if __name__ == '__main__':
    unittest.main()

