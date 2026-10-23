#!/usr/bin/env python3
"""Determine whether this run needs a refresh. No network calls or secrets.

Scheduled fallback checks skip news and AI if a recent successful refresh exists;
manual workflow_dispatch always refreshes. Fail-safe: invalid timestamps refresh.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path

NEWS = Path(__file__).resolve().parent.parent / 'data' / 'news.json'
MIN_AGE_HOURS = 16


def should_refresh(record: dict, *, event: str, now=None) -> bool:
    if event == 'workflow_dispatch':
        return True
    if event == 'push':
        return False
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        value = record.get('updated_at', '')
        timestamp = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            return True
        seconds = (now - timestamp.astimezone(dt.timezone.utc)).total_seconds()
        return seconds < -3600 or seconds >= MIN_AGE_HOURS * 3600
    except (ValueError, TypeError, AttributeError):
        return True


def main():
    try:
        record = json.loads(NEWS.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        record = {}
    refresh = should_refresh(record, event=os.getenv('GITHUB_EVENT_NAME', 'schedule'))
    print('refresh=' + ('true' if refresh else 'false'))
    print('reason=' + ('due_or_manual' if refresh else 'already_recent_or_push'))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
