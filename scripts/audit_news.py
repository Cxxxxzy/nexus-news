#!/usr/bin/env python3
"""Public-data-only audit; no credentials, body text, or external calls."""
from __future__ import annotations

from collections import Counter
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / 'data' / 'news.json'
REPORT = ROOT / 'reports' / 'latest-audit.md'
UTC = dt.timezone.utc


def parse_time(value):
    try:
        result = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result.astimezone(UTC) if result.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def evaluate(record: dict, now=None) -> dict:
    now = now or dt.datetime.now(UTC)
    articles = record.get('articles', [])
    if not isinstance(articles, list):
        raise ValueError('news articles must be a list')
    latest = parse_time(record.get('updated_at'))
    hours = round((now - latest).total_seconds()/3600, 1) if latest else None
    by_category = Counter(a.get('category', '') for a in articles if isinstance(a, dict))
    urls = [a.get('url', '') for a in articles if isinstance(a, dict)]
    bad_links = sum(urlparse(x).scheme not in ('http', 'https') or not urlparse(x).netloc for x in urls)
    ids = [a.get('id') for a in articles if isinstance(a, dict)]
    duplicates = len(ids) - len(set(ids))
    ai_count = sum(bool(a.get('ai_question') or a.get('ai_questions')) for a in articles if isinstance(a, dict))
    warnings = []
    if hours is None: warnings.append('更新時刻を取得できません')
    elif hours > 36: warnings.append('最終ニュース取得から36時間以上経過')
    if len(articles) < 20: warnings.append('ニュース記事が20件未満')
    if len(by_category) < 6: warnings.append('カテゴリが6種類未満')
    if bad_links: warnings.append(f'無効な記事URL: {bad_links}件')
    if duplicates: warnings.append(f'重複した記事ID: {duplicates}件')
    if record.get('demo'): warnings.append('デモ記事モード')
    return {
        'checked_at': now.isoformat(),
        'news_updated_at': record.get('updated_at'),
        'age_hours_at_check': hours,
        'article_count': len(articles),
        'category_counts': dict(sorted(by_category.items())),
        'ai_guide_count': ai_count,
        'warnings': warnings,
        'healthy_at_check': not warnings,
    }


def render_report(result: dict) -> str:
    lines = [
        '# NEXUS NEWS — 自動品質点検', '',
        f'点検日時（UTC）: {result["checked_at"]}',
        f'ニュース取得時刻（UTC）: {result["news_updated_at"]}',
        f'点検時の更新経過時間: {result["age_hours_at_check"]}時間',
        f'ニュース件数: {result["article_count"]}',
        f'AI読解ガイド付きの記事: {result["ai_guide_count"]}', '',
        '## カテゴリ内訳', '',
    ]
    lines += [f'- {key}: {val}件' for key, val in result['category_counts'].items()]
    lines += ['', '## 要確認', '']
    lines += [f'- {x}' for x in result['warnings']] if result['warnings'] else ['- 自動検査上の警告なし（事実確認済みという意味ではありません）']
    lines += ['', '※ メタデータの簡易検査です。記事本文・情報の真偽・著作権の適法性を判定していません。', '']
    return '\n'.join(lines)


def main():
    record = json.loads(NEWS.read_text(encoding='utf-8'))
    result = evaluate(record)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(result), encoding='utf-8')
    print('NEWS AUDIT: articles={article_count} ai={ai_guide_count} warnings={warnings}'.format(**result))
    return 0  # Warnings do not suppress valid news publication.

if __name__ == '__main__':
    raise SystemExit(main())
