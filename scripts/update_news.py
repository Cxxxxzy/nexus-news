#!/usr/bin/env python3
"""RSS -> validated headline index. Only metadata: never scrape/reproduce article bodies.

Usage:
  python scripts/update_news.py
  python scripts/update_news.py --fixture tests/fixtures/sample_feed.xml --category 国際
  python scripts/update_news.py --dry-run

Optional: OPENAI_API_KEY + AI_EDITOR_ENABLED=1 + pip install openai.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / 'data' / 'news.json'
SOURCES = ROOT / 'config' / 'sources.json'
ALLOWED = {'国内', '国際', '政治', '経済', 'テクノロジー', '科学', 'スポーツ', 'エンタメ'}
UTC = dt.timezone.utc
MAX_ARTICLES = 120
MAX_PER_FEED = 12
REQUEST_TIMEOUT = 18


def clean(s: str, limit: int = 180) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()[:limit]


def http_link(s: str) -> str | None:
    u = urlparse(s.strip())
    return s.strip() if u.scheme in ('https', 'http') and u.netloc else None


def date_iso(s: str) -> str:
    if not s:
        return dt.datetime.now(UTC).isoformat()
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(UTC).isoformat()
    except (TypeError, ValueError, OverflowError):
        try:
            return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(UTC).isoformat()
        except ValueError:
            return dt.datetime.now(UTC).isoformat()


def node_text(node, tag: str) -> str:
    n = node.find(tag)
    return ''.join(n.itertext()).strip() if n is not None else ''


def parse_feed(xml_bytes: bytes, category: str, name: str):
    """RSS 2.0 and Atom. Parse source title, title/link/pubDate only."""
    root = ET.fromstring(xml_bytes)
    entries = root.findall('./channel/item')
    atom = False
    if not entries:
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('./a:entry', ns)
        atom = True
    out = []
    for entry in entries[:MAX_PER_FEED * 3]:
        if atom:
            ns = '{http://www.w3.org/2005/Atom}'
            title = clean(node_text(entry, ns+'title'), 230)
            link = next((n.attrib.get('href') for n in entry.findall(ns+'link') if n.attrib.get('rel', 'alternate') == 'alternate'), '')
            published = node_text(entry, ns+'published') or node_text(entry, ns+'updated')
            source = name
        else:
            title = clean(node_text(entry, 'title'), 230)
            link = node_text(entry, 'link')
            published = node_text(entry, 'pubDate')
            source_node = entry.find('source')
            source = clean(source_node.text if source_node is not None else '', 80) or name
        link = http_link(link or '')
        if not title or not link:
            continue
        # Some Google News RSS headlines append ' - Publisher'. Prefer explicit RSS source.
        if not atom and source != name and title.endswith(' - ' + source):
            title = title[:-(len(source) + 3)].strip()
        if len(title) < 5:
            continue
        article_id = hashlib.sha256((link.split('#')[0]).encode('utf-8')).hexdigest()[:18]
        out.append({
            'id': article_id,
            'title': title,
            'summary': f'{source}によるニュースの見出しです。詳しい内容や事実関係は元記事をご確認ください。',
            'category': category,
            'source': source,
            'published_at': date_iso(published),
            'url': link,
            'demo': False,
        })
        if len(out) >= MAX_PER_FEED:
            break
    return out


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'NexusNewsStarter/1.0 (+news indexing example; contact site operator)',
        'Accept': 'application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.5'
    })
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read(1_800_000)


def make_note(client, title, category, source, model):
    """AI-generated reading question only; NOT a factual summary or a reported article."""
    response = client.responses.create(
        model=model,
        instructions=(
            'あなたはニュース見出しの読書ガイド編集者です。与えられるのは記事本文ではなく見出しだけです。'
            '見出しからは確認できない事実、人数、金額、因果関係を一切補わないでください。'
            '見出しを読む人にとって有益な確認ポイントを、日本語の疑問文1つ(75字以内)で返してください。'
            '質問だけを返し、回答・推測・引用は書かないでください。'
        ),
        input=f'カテゴリ: {category}\n媒体: {source}\n見出し: {title}',
        max_output_tokens=110,
    )
    question = clean(response.output_text, 75)
    if question and not any(c in question for c in '\n<>'):
        return 'AIによる確認ポイント（記事本文は未確認）：' + question
    return None


def enrich_with_ai(items):
    if os.getenv('AI_EDITOR_ENABLED') != '1' or not os.getenv('OPENAI_API_KEY'):
        return
    try:
        from openai import OpenAI
        client = OpenAI(timeout=25.0, max_retries=1)
        model = (os.getenv('OPENAI_MODEL') or 'gpt-5.5')
        limit = max(0, min(6, int(os.getenv('AI_MAX_ITEMS', '4'))))
        for a in items[:limit]:
            try:
                question = make_note(client, a['title'], a['category'], a['source'], model)
                if question:
                    a['summary'] = question
                    a['ai_note'] = True
            except Exception as exc:
                print(f'AI failed for {a["id"]}: {exc}', file=sys.stderr)
    except (ImportError, ValueError) as exc:
        print(f'AI disabled: {exc}', file=sys.stderr)


def merged_items(new_items, old_items):
    """Prefer fresh headline, preserve older records and ensure no demo leaks."""
    combined = new_items + [a for a in old_items if not a.get('demo')]
    unique = {}
    seen_title = set()
    for a in combined:
        if a.get('category') not in ALLOWED or not http_link(a.get('url') or ''):
            continue
        key = re.sub(r'\W+', '', a['title']).casefold()
        if a['id'] in unique or key in seen_title:
            continue
        unique[a['id']] = a
        seen_title.add(key)
    return sorted(unique.values(), key=lambda a:a['published_at'], reverse=True)[:MAX_ARTICLES]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixture', type=Path, help='offline RSS file, instead of live network')
    ap.add_argument('--category', default='国際')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    if args.category not in ALLOWED:
        ap.error('invalid category')
    feeds = json.loads(SOURCES.read_text(encoding='utf-8'))['feeds']
    old = json.loads(NEWS.read_text(encoding='utf-8'))
    new_items = []
    successes = 0
    if args.fixture:
        new_items = parse_feed(args.fixture.read_bytes(), args.category, 'Test RSS')
        successes = 1
    else:
        for feed in feeds:
            try:
                found = parse_feed(fetch_bytes(feed['url']), feed['category'], feed['name'])
                print(f'{feed["category"]}: {len(found)} headlines')
                if found:
                    new_items.extend(found)
                    successes += 1
            except (OSError, ET.ParseError, ValueError) as exc:
                print(f'WARN: {feed["category"]}: {exc}', file=sys.stderr)
    if not successes or not new_items:
        print('ERROR: no valid RSS items. Existing data not overwritten.', file=sys.stderr)
        return 1
    enrich_with_ai(new_items)
    articles = merged_items(new_items, old.get('articles', []))
    if not articles:
        print('ERROR: merge produced no valid articles.', file=sys.stderr)
        return 1
    record = {'updated_at': dt.datetime.now(UTC).isoformat(), 'demo': False, 'articles': articles}
    if not args.dry_run:
        temp = NEWS.with_suffix('.json.tmp')
        temp.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        temp.replace(NEWS)
    print(f'{"DRY RUN" if args.dry_run else "SAVED"}: {len(articles)} items from {successes} feed(s)')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
