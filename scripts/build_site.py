#!/usr/bin/env python3
"""Create minimal static output, never expose config/workflow/scripts in public site."""
from pathlib import Path
import json
import shutil
import importlib.util

spec = importlib.util.spec_from_file_location("nexus_audit", Path(__file__).resolve().parent / "audit_news.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
evaluate = audit.evaluate

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
PUBLIC_FILES = ['index.html', 'styles.css', 'app.js', 'policy.html', 'privacy.html', '.nojekyll']

def build():
    data = json.loads((ROOT/'data/news.json').read_text(encoding='utf-8'))
    if not isinstance(data.get('articles'), list):
        raise ValueError('news.json must contain articles list')
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    for name in PUBLIC_FILES:
        shutil.copy2(ROOT/name, DIST/name)
    shutil.copytree(ROOT/'assets', DIST/'assets')
    (DIST/'data').mkdir()
    shutil.copy2(ROOT/'data/news.json', DIST/'data/news.json')
    (DIST/'data/health.json').write_text(json.dumps(evaluate(data), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Built {DIST}, {len(data["articles"])} articles')

if __name__ == '__main__':
    build()
