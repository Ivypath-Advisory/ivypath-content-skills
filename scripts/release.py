#!/usr/bin/env python3
"""记录本版源文件与 Claude 账号版的哈希，写到 release.json。

用法：python3 scripts/release.py [--check]
--check 只比较不写入：release.json 与当前文件不一致时退出码为 1（测试用）。
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ['case-story-writer', 'ivypath-humanize-zh', 'ivypath-case-imitation-training']
VERSION = '2026-11-03-content-skills-github'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest():
    data = {'version': VERSION, 'repo': 'Ivypath-Advisory/ivypath-content-skills', 'skills': {}, 'claude_account': {},
            'shared': {}}
    for name in SKILLS:
        d = ROOT / name
        data['skills'][name] = {str(p.relative_to(d)): sha(p) for p in sorted(d.rglob('*')) if p.is_file()}
        acct = ROOT / 'claude-account' / name / 'SKILL.md'
        if acct.exists():
            data['claude_account'][name] = sha(acct)
    for p in sorted((ROOT / 'scripts').glob('*.py')):
        if p.name != 'release.py':
            data['shared'][f'scripts/{p.name}'] = sha(p)
    return data


if __name__ == '__main__':
    path = ROOT / 'release.json'
    new = manifest()
    if '--check' in sys.argv:
        old = json.loads(path.read_text()) if path.exists() else {}
        sys.exit(0 if old == new else 1)
    path.write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n')
    print('release.json updated:', sum(len(v) for v in new['skills'].values()), 'skill files')
