import datetime as dt
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('free_ai_editor', ROOT / 'scripts/free_ai_editor.py')
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)


class FakeResponse:
    def __init__(self, content):
        self.content = content
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n):
        return self.content


class FreeAIEditorTests(unittest.TestCase):
    def test_question_format_safety(self):
        self.assertEqual(ai.extract_question('なぜこの変更が必要とされているのでしょうか？'), 'なぜこの変更が必要とされているのでしょうか？')
        self.assertIsNone(ai.extract_question('確実に利益が増えます。'))
        self.assertIsNone(ai.extract_question('<script>alert(1)</script>？'))
        self.assertIsNone(ai.extract_question('https://example.org で確認して？'))
        self.assertIsNone(ai.extract_question('何が起きた？\n余計な説明'))

    def test_max_requests_cannot_exceed_three(self):
        self.assertEqual(ai.limit_from_env('9999'), 3)
        self.assertEqual(ai.limit_from_env('-10'), 0)
        self.assertEqual(ai.limit_from_env('abc'), 2)

    def test_picks_recent_distinct_categories_and_skips_existing(self):
        now = dt.datetime(2026,10,21,12,tzinfo=dt.timezone.utc)
        entries = [
            {'id':'1','title':'A', 'category':'国内','published_at':'2026-10-21T10:00:00+00:00'},
            {'id':'2','title':'B', 'category':'国内','published_at':'2026-10-21T09:00:00+00:00'},
            {'id':'3','title':'C', 'category':'経済','published_at':'2026-10-21T08:00:00+00:00'},
            {'id':'4','title':'D', 'category':'政治','published_at':'2026-10-21T07:00:00+00:00','ai_question':'何ですか？'},
            {'id':'5','title':'E', 'category':'国際','published_at':'2026-10-10T07:00:00+00:00'},
        ]
        result = ai.select_candidates(entries, now, 2)
        self.assertEqual([x['id'] for x in result],['1','3'])

    def test_cloudflare_request_schema_and_no_secret_in_payload(self):
        observed=[]
        def fake_open(req, timeout):
            observed.append((req, timeout))
            return FakeResponse(json.dumps({'success':True,'result':{'response':'どの点を元記事で確認すればよいでしょうか？'}}).encode())
        article={'category':'経済','source':'ニュース社','title':'架空のニュース見出し'}
        note=ai.request_question('a'*32,'fake-test-secret',article,opener=fake_open)
        self.assertTrue(note.endswith('？'))
        request,_ = observed[0]
        self.assertIn('/@cf/meta/llama-3.1-8b-instruct-fp8', request.full_url)
        self.assertNotIn('fake-test-secret', request.data.decode())
        self.assertEqual(len(json.loads(request.data)['messages']),2)
        self.assertEqual(request.get_method(),'POST')

    def test_enrich_does_not_replace_summary(self):
        now=dt.datetime(2026,10,21,12,tzinfo=dt.timezone.utc)
        a=[{'id':'x','title':'速報です','category':'科学','summary':'元の見出し説明','published_at':'2026-10-21T11:00:00Z'}]
        n, selected=ai.enrich(a, 'x','y', now=now, max_items=2,
                              request_fn=lambda acct,tok,article:'何を確認する必要があるのでしょうか？')
        self.assertEqual((n,selected),(1,1))
        self.assertEqual(a[0]['summary'],'元の見出し説明')
        self.assertIn('ai_question',a[0])

    def test_quota_error_stops_further_calls(self):
        now=dt.datetime(2026,10,21,12,tzinfo=dt.timezone.utc)
        a=[{'id':str(i),'title':'速報です','category':str(i),'published_at':'2026-10-21T11:00:00Z'} for i in range(3)]
        calls=[]
        def quota(*args):
            calls.append(1)
            raise ai.QuotaExhausted()
        n,_=ai.enrich(a, 'x','y',now=now,max_items=3,request_fn=quota)
        self.assertEqual(n,0)
        self.assertEqual(len(calls),1)


if __name__ == '__main__':
    unittest.main()
