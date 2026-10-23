import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent

def load(name):
    path = ROOT/'scripts'/name
    spec = importlib.util.spec_from_file_location('v04_' + name.replace('.','_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

update = load('update_news.py')
ai = load('free_ai_editor.py')
audit = load('audit_news.py')

RDF = '''<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<item rdf:about="https://www.jpcert.or.jp/at/test.html">
<title>公式発表の技術的な注意喚起に関する速報</title>
<link>https://www.jpcert.or.jp/at/test.html</link>
<description><![CDATA[<p>発信元が公開するセキュリティ関連の概要です。関係機関の発表と対応状況を参照してください。</p>]]></description>
<dc:date>2026-10-23T12:20:00+09:00</dc:date>
</item>
</rdf:RDF>'''.encode('utf-8')

class V04Tests(unittest.TestCase):
    def test_official_rdf_excerpt_is_limited_and_attributed(self):
        a = update.parse_feed(RDF, 'テクノロジー', 'JPCERT/CC 公式RSS', official_excerpt=True)[0]
        self.assertEqual(a['excerpt_kind'], 'official_rss_excerpt')
        self.assertIn('セキュリティ関連', a['source_excerpt'])
        self.assertNotIn('<p>', a['source_excerpt'])
        self.assertEqual(a['published_at'], '2026-10-23T03:20:00+00:00')

    def test_generic_feed_can_never_publish_description(self):
        a = update.parse_feed(RDF,'テクノロジー','Example',official_excerpt=False)[0]
        self.assertNotIn('source_excerpt',a)
        xml = RDF.replace(b'www.jpcert.or.jp', b'example.com')
        b = update.parse_feed(xml,'テクノロジー','Example',official_excerpt=True)[0]
        self.assertNotIn('source_excerpt',b)

    def test_default_google_feed_description_not_copied(self):
        a = update.parse_feed((ROOT/'tests/fixtures/sample_feed.xml').read_bytes(), '国内', 'Test RSS')[0]
        self.assertNotIn('source_excerpt', a)

    def test_official_excerpt_has_fixed_max_length_and_strips_markup(self):
        long = '<script>STEAL</script><p>' + '情報です。'*110 + '</p>'
        txt = update.short_official_excerpt(long)
        self.assertNotIn('STEAL', txt)
        self.assertLessEqual(len(txt), 221)

    def test_budget_two_calls_per_jst_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'budget.json'
            self.assertEqual(ai.remaining_budget(path,'2026-10-23'),(2,0))
            count = ai.record_request(path,'2026-10-23',0)
            self.assertEqual(count,1)
            count = ai.record_request(path,'2026-10-23',count)
            self.assertEqual(ai.remaining_budget(path,'2026-10-23'),(0,2))
            with self.assertRaises(ai.QuotaExhausted):
                ai.record_request(path,'2026-10-23',count)
            self.assertEqual(ai.remaining_budget(path,'2026-10-24'),(2,0))

    def test_bad_quota_record_fails_closed_same_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'budget.json'
            path.write_text('{oops',encoding='utf-8')
            self.assertEqual(ai.remaining_budget(path,'2026-10-23'),(0,2))

    def test_jst_day_at_boundary(self):
        self.assertEqual(ai.jst_day(dt.datetime(2026,10,22,14,59,tzinfo=dt.timezone.utc)), '2026-10-22')
        self.assertEqual(ai.jst_day(dt.datetime(2026,10,22,15,0,tzinfo=dt.timezone.utc)), '2026-10-23')

    def test_ai_input_contains_only_allowlisted_excerpt(self):
        class Resp:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n): return json.dumps({'success':True,'result':{'response':'1. 具体的な発表の根拠は何でしょうか？\n2. 当事者の行動の背景は何でしょうか？\n3. 利用者にどんな影響がありますか？'}}).encode()
        seen=[]
        def opener(request, timeout): seen.append(request);return Resp()
        a = update.parse_feed(RDF,'テクノロジー','JPCERT/CC',official_excerpt=True)[0]
        self.assertEqual(len(ai.request_reading_guide('a'*32,'testsecret',a,opener=opener)),3)
        data=json.loads(seen[0].data)
        self.assertIn('publisher_rss_excerpt',data['messages'][1]['content'])
        self.assertNotIn('testsecret',seen[0].data.decode())
        a['excerpt_kind']='random'
        seen.clear()
        ai.request_reading_guide('a'*32,'testsecret',a,opener=opener)
        nested=json.loads(json.loads(seen[0].data)['messages'][1]['content'].split('\n',1)[1])
        self.assertEqual(nested['publisher_rss_excerpt'],'')

    def test_ai_attempt_is_charged_even_on_failure(self):
        now=dt.datetime(2026,10,23,12,tzinfo=dt.timezone.utc)
        items=[{'id':'1','title':'見出し','category':'国内','published_at':now.isoformat()}]
        spent=[]
        def bad(*args):raise RuntimeError('Workers AI HTTP status 401')
        n,_=ai.enrich(items,'a','b',now=now,before_request=lambda:spent.append(1),request_fn=bad)
        self.assertEqual(n,0)
        self.assertEqual(spent,[1])

    def test_audit_generates_review_only_improvement_report(self):
        now=dt.datetime(2026,10,23,12,tzinfo=dt.timezone.utc)
        r=audit.evaluate({'updated_at':now.isoformat(),'articles':[]},now=now)
        text=audit.improvement_plan(r)
        self.assertIn('未実施',text)
        self.assertIn('手動承認',text)
        self.assertIn('一次情報',text)
        self.assertEqual(r['official_excerpt_count'],0)

    def test_original_excerpt_is_only_displayed_as_sourced_data(self):
        app=(ROOT/'app.js').read_text(encoding='utf-8')
        self.assertIn('official_rss_excerpt',app)
        self.assertIn('独立した事実確認ではありません',app)
        self.assertIn('esc(a.source_excerpt)',app)

if __name__=='__main__': unittest.main()
