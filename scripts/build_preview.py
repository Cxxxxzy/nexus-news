#!/usr/bin/env python3
"""Single-file offline demo preview with embedded CSS/JS/data (no production API keys)."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parent.parent
html=(ROOT/'index.html').read_text(encoding='utf-8')
html=re.sub(r'<link[^>]*href="https?://[^>]+>', '', html)
html=html.replace('<link rel="stylesheet" href="./styles.css">', '<style>'+ (ROOT/'styles.css').read_text(encoding='utf-8') + '</style>')
data=json.loads((ROOT/'data/news.json').read_text(encoding='utf-8'))
# Controlled demo payload. Prevent closing script tags in future data.
payload=json.dumps(data, ensure_ascii=False).replace('<','\\u003c')
scripts='<script>window.fetch = async function(){return {ok:true, json:async function(){return '+payload+'}}};</script>'
scripts+='<script>'+(ROOT/'app.js').read_text(encoding='utf-8')+'</script>'
html=html.replace('<script src="./app.js" defer></script>', '')
html=html.replace('</body>',scripts+'</body>')
# Demo support pages are not embedded; show public policy documents in production.
html=html.replace('href="./policy.html"','href="#"').replace('href="./privacy.html"','href="#"')
html=html.replace('<title>NEXUS NEWS |', '<title>[オフラインプレビュー] NEXUS NEWS |')
(ROOT/'PREVIEW.html').write_text(html,encoding='utf-8')
print('Generated PREVIEW.html (offline demo)')
