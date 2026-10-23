"""Offline regression suite for v0.5 safety and daily schedule."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(file):
    spec = importlib.util.spec_from_file_location('v05_' + file, ROOT/'scripts'/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

ai = load('free_ai_editor.py')
upd = load('update_news.py')
sched = load('should_update.py')
audit = load('audit_news.py')

NOW = dt.datetime(2026, 10, 23, 8, tzinfo=dt.timezone.utc)
TITLE = 'AXで国会審議充実政治制度改革本部にPTを新設し初会合'


class Response:
    def __init__(self, response):
        self.response = response
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self, limit):
        return json.dumps({'success': True, 'result': {'response': self.response}}, ensure_ascii=False).encode()


class V05Tests(unittest.TestCase):
    def test_anchor_rejects_invented_meaning(self):
        raw = json.dumps({'anchors': ['AXは新型システム', '国会審議']}, ensure_ascii=False)
        self.assertEqual(ai.parse_grounded_anchors(raw, TITLE), [])

    def test_anchor_accepts_only_literal_spans(self):
        anchors=['AX','国会審議','PT']
        raw=json.dumps({'anchors':anchors},ensure_ascii=False)
        self.assertEqual(ai.parse_grounded_anchors(raw,TITLE),anchors)

    def test_anchor_strict_json_and_duplicate_safety(self):
        self.assertEqual(ai.parse_grounded_anchors('返事は「AX」です',TITLE),[])
        self.assertEqual(ai.parse_grounded_anchors('{"anchors": ["事実", "PT"], "bad": 1}',TITLE),[])
        self.assertEqual(ai.parse_grounded_anchors('{"anchors": ["AX", "AX"]}',TITLE),['AX'])
        self.assertEqual(ai.parse_grounded_anchors('{"anchors": ["AX\\n国会"]}',TITLE),[])

    def test_anchor_question_does_not_expand_unknown_acronym(self):
        questions=ai.make_grounded_questions(['AX','国会審議','PT'])
        self.assertEqual(len(questions),3)
        self.assertIn('「AX」',questions[0])
        self.assertNotIn('システム', ' '.join(questions))
        self.assertTrue(all(q.endswith('？') for q in questions))

    def test_cloudflare_request_only_selects_title_anchors(self):
        seen=[]
        def fake(request, timeout):
            seen.append(request)
            return Response(json.dumps({'anchors':['AX','国会審議','PT']},ensure_ascii=False))
        questions, anchors = ai.request_grounded_guides('a'*32, 'secret', {'title':TITLE},opener=fake)
        self.assertEqual(len(questions),3)
        self.assertEqual(anchors,['AX','国会審議','PT'])
        payload=json.loads(seen[0].data)
        self.assertEqual(payload['max_tokens'],170)
        self.assertNotIn('secret', seen[0].data.decode('utf8'))

    def test_output_invalid_anchors_never_persist(self):
        article={'id':'x','title':TITLE,'category':'政治','published_at':NOW.isoformat(),'ai_question':'旧形式の質問ですか？'}
        calls=[]
        def invalid(*args):
            calls.append(1)
            return ['捏造した質問ですか？']*3, ['AX']
        count,selected=ai.enrich_grounded([article],'a','b',now=NOW,request_fn=invalid)
        self.assertEqual((count,selected),(0,1))
        self.assertNotIn('ai_grounding',article)
        self.assertEqual(len(calls),1)

    def test_replaces_legacy_guide_in_place(self):
        a={'id':'x','title':TITLE,'category':'政治','published_at':NOW.isoformat(),
           'ai_question':'旧形式の意味不明な質問？'}
        anchors=['AX','PT','国会審議']
        count,_=ai.enrich_grounded([a],'a','b',now=NOW,
             request_fn=lambda *_:(ai.make_grounded_questions(anchors), anchors))
        self.assertEqual(count,1)
        self.assertEqual(a['ai_grounding'],ai.GROUNDED_VERSION)
        self.assertNotIn('意味不明',a['ai_question'])
        self.assertEqual(ai.grounded_candidates([a],NOW,2),[])

    def test_refresh_preserves_new_provenance_and_guide(self):
        fresh={'id':'x','title':TITLE,'category':'政治','url':'https://example.com/a',
               'published_at':NOW.isoformat(),'demo':False,'origin_type':'news_aggregator'}
        prior={**fresh,'ai_grounding':ai.GROUNDED_VERSION,'ai_anchors':['AX'],
               'ai_question':'見出しの「AX」について、元記事に確認できる根拠はあるか？',
               'ai_questions':['A？','B？','C？']}
        result=upd.merged_items([fresh],[prior])[0]
        self.assertEqual(result['ai_grounding'],ai.GROUNDED_VERSION)
        self.assertEqual(result['ai_anchors'],['AX'])

    def test_schedule_morning_evening_gate(self):
        self.assertTrue(sched.should_refresh({'updated_at':(NOW-dt.timedelta(hours=24)).isoformat()},event='schedule',now=NOW))
        self.assertFalse(sched.should_refresh({'updated_at':(NOW-dt.timedelta(hours=12)).isoformat()},event='schedule',now=NOW))
        self.assertTrue(sched.should_refresh({'updated_at':(NOW-dt.timedelta(hours=12)).isoformat()},event='workflow_dispatch',now=NOW))
        self.assertFalse(sched.should_refresh({},event='push',now=NOW))
        self.assertTrue(sched.should_refresh({},event='schedule',now=NOW))
        self.assertTrue(sched.should_refresh({'updated_at':'not-a-date'},event='schedule',now=NOW))

    def test_trust_source_is_not_based_on_untrusted_publisher_name(self):
        xml=(ROOT/'tests/fixtures/sample_feed.xml').read_bytes()
        article=upd.parse_feed(xml,'国内','Official Bank of Japan',origin_type='news_aggregator')[0]
        self.assertEqual(article['origin_type'],'news_aggregator')

    def test_audit_tracks_grounded_separately(self):
        items=[{'id':'1','url':'https://example.com','category':'政治','origin_type':'news_aggregator',
                 'published_at':NOW.isoformat(),'ai_questions':['Legacy?']},
               {'id':'2','url':'https://jpcert.or.jp','category':'テクノロジー','origin_type':'official_rss',
                 'published_at':NOW.isoformat(),'ai_grounding':ai.GROUNDED_VERSION,'ai_questions':['Grounded?']}]
        result=audit.evaluate({'updated_at':NOW.isoformat(),'articles':items},now=NOW)
        self.assertEqual(result['grounded_ai_guide_count'],1)
        self.assertEqual(result['ai_guide_count'],2)
        self.assertEqual(result['official_origin_count'],1)
        self.assertEqual(result['news_aggregator_count'],1)

    def test_site_hides_legacy_question(self):
        js=(ROOT/'app.js').read_text(encoding='utf8')
        self.assertIn("if(!isGrounded(a))return ''",js)
        self.assertIn('RSS取得経路未確認',js)
        self.assertIn("a.ai_grounding==='headline_anchors_v1'",js)

    def test_timezone_explicit_and_secret_names_unchanged(self):
        w=(ROOT/'.github/workflows/publish.yml').read_text(encoding='utf8')
        self.assertIn("timezone: 'Asia/Tokyo'",w)
        self.assertIn("cron: '17 6 * * *'",w)
        self.assertIn("cron: '43 18 * * *'",w)
        self.assertIn("steps.refresh.outputs.refresh == 'true'",w)
        self.assertIn('secrets.CLOUDFLARE_API_TOKEN',w)

if __name__ == '__main__': unittest.main()
