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
PROPOSALS = ROOT / 'reports' / 'improvement-proposals.md'
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
    official_count = sum(a.get('excerpt_kind') == 'official_rss_excerpt' and bool(a.get('source_excerpt'))
                         for a in articles if isinstance(a, dict))
    newest = max((d for a in articles if isinstance(a, dict)
                  if (d := parse_time(a.get('published_at'))) is not None), default=None)
    headline_age = round((now-newest).total_seconds()/3600, 1) if newest else None
    warnings = []
    if hours is None: warnings.append('更新時刻を取得できません')
    elif hours > 36: warnings.append('最終ニュース取得から36時間以上経過')
    if len(articles) < 20: warnings.append('ニュース記事が20件未満')
    if len(by_category) < 6: warnings.append('カテゴリが6種類未満')
    if bad_links: warnings.append(f'無効な記事URL: {bad_links}件')
    if duplicates: warnings.append(f'重複した記事ID: {duplicates}件')
    if record.get('demo'): warnings.append('デモ記事モード')
    if headline_age is None: warnings.append('有効な記事公開日時がありません')
    elif headline_age > 36: warnings.append('最新記事の公開から36時間以上経過')
    return {
        'checked_at': now.isoformat(),
        'news_updated_at': record.get('updated_at'),
        'age_hours_at_check': hours,
        'article_count': len(articles),
        'category_counts': dict(sorted(by_category.items())),
        'ai_guide_count': ai_count,
        'official_excerpt_count': official_count,
        'newest_article_age_hours': headline_age,
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
        f'AI読解ガイド付きの記事: {result["ai_guide_count"]}',
        f'公式RSSの短い概要付き: {result["official_excerpt_count"]}',
        f'最新記事の経過時間: {result["newest_article_age_hours"]}時間', '',
        '## カテゴリ内訳', '',
    ]
    lines += [f'- {key}: {val}件' for key, val in result['category_counts'].items()]
    lines += ['', '## 要確認', '']
    lines += [f'- {x}' for x in result['warnings']] if result['warnings'] else ['- 自動検査上の警告なし（事実確認済みという意味ではありません）']
    lines += ['', '※ メタデータの簡易検査です。記事本文・情報の真偽・著作権の適法性を判定していません。', '']
    return '\n'.join(lines)


def improvement_plan(result: dict) -> str:
    """Deterministic, review-only; never directly changes deployed code."""
    next_steps = []
    if result['warnings']:
        next_steps.append('ニュース収集ログとRSS配信元を確認して、更新停止や件数不足を修復する')
    if result['official_excerpt_count'] == 0:
        next_steps.append('利用条件を確認できた一次情報RSSを増やす（本文の無断収集はしない）')
    if result['ai_guide_count'] < 5:
        next_steps.append('無料枠・AI実行ログを確認し、記事固有の読解ガイドを改善する')
    next_steps.append('スマホ・PCの表示速度と読みやすさを実機で確認する')
    next_steps.append('変更案は別ブランチでテストし、確認後に手動承認で公開する')
    lines = ['# NEXUS NEWS — 改善候補（自動生成・未実施）', '',
             'このレポートはメタデータに基づく提案です。サイト変更は自動実行しません。', '',
             '## 観測値', '',
             f'- ニュース: {result["article_count"]}件',
             f'- AI読解ガイド: {result["ai_guide_count"]}件',
             f'- 公式RSSの概要: {result["official_excerpt_count"]}件',
             f'- 警告: {len(result["warnings"])}件', '', '## 次の候補', '']
    lines += [f'{i}. {step}' for i, step in enumerate(next_steps, 1)]
    lines += ['', '※ 記事の正確性や法的な利用許可を検証した報告ではありません。', '']
    return '\n'.join(lines)


def main():
    record = json.loads(NEWS.read_text(encoding='utf-8'))
    result = evaluate(record)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(result), encoding='utf-8')
    PROPOSALS.write_text(improvement_plan(result), encoding='utf-8')
    import os
    step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if step_summary:
        with open(step_summary, 'a', encoding='utf-8') as out:
            out.write(render_report(result) + '\n')
    for warning in result['warnings']:
        # Controlled audit messages (not arbitrary RSS text).
        print('::warning::' + warning)
    print('NEWS AUDIT: articles={article_count} ai={ai_guide_count} warnings={warnings}'.format(**result))
    return 0  # Warnings do not suppress valid news publication.

if __name__ == '__main__':
    raise SystemExit(main())
