#!/usr/bin/env python3
"""IvyPath 中文对外稿检查：句式限额、禁用词、隐私、查重、三层选校与金句结尾。

用法：
  python3 scripts/zh_lint.py 稿件.md [--genre case|short|whitepaper|xhs|other]
                             [--src 参考文.txt ...] [--protect 定稿句.txt] [--json]

- 支持 .md / .txt / .docx（docx 只读正文文字，不需要 python-docx）。
- 引号（“”「」""）里的文字按原话处理，不计入句式限额，但照查禁用词和隐私。
- 定稿保护句默认从 case-story-writer/references/learned-style.md 的「定稿保护句」一节读取，
  --protect 可再加一个文件（一行一句）。保护句不计入句式限额。
- 有超限、禁用词、隐私命中或查重命中时退出码为 1。
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNED = ROOT / 'case-story-writer' / 'references' / 'learned-style.md'

PATTERNS = {
    '不是…而是': r'(?:不是|并非|并不是|不只是|不仅仅是|不仅是|不在于|与其说)[^。！？!?\n]{0,30}?(?:而是|更是|而在于|不如说)',
    '真正': r'真正',
    '破折号': r'——|—',
}
# 每篇上限；None = 只报告不设限
CAPS = {
    'case': {'不是…而是': 1, '真正': 1, '破折号': 1},
    'short': {'不是…而是': 0, '真正': 0, '破折号': 0},
    'whitepaper': {'不是…而是': 1, '真正': None, '破折号': None},
    'xhs': {'不是…而是': None, '真正': None, '破折号': None},
    'other': {'不是…而是': 1, '真正': None, '破折号': None},
}
# PH 2020–2024 案例文基线（每万字），只作参照
PH_BASELINE = {'不是…而是': '0.2–0.7', '真正': '0.3–1.7', '破折号': '0.1–0.3'}

COMPLIANCE = r'保录|包过|保证录取|100%\s*录取|包装背景|走捷径|内部资源|名校随便拿|低分也稳'
AI_WORDS = (r'赋能|抓手|闭环|打造|全方位|深耕|助力|保驾护航|至关重要|淋漓尽致|颠覆|重磅|干货满满|浓墨重彩'
            r'|大放异彩|圆梦名校|厚积薄发|未来可期|拭目以待|综上所述|总而言之|一言以蔽之|毋庸置疑|众所周知'
            r'|值得一提的是|不得不说|底层逻辑|一站式|多维度|无缝衔接|可圈可点|最后一块拼图|老规矩|重点来了'
            r'|更狠的是|更绝的是|更炸的是|更离谱的是')  # 后半来自市场库 01_品牌中枢/去AI味写作规范.md Tier 1
LIMITED_WORDS = {'脱颖而出': 1, '抛出橄榄枝': 1, '天花板': 1}
SELF_PRAISE = r'(?:非常|很|十分|特别)(?:专业|用心|贴心|高效|负责)|专业的(?:团队|老师|顾问|服务)|认真负责|用心负责'
PRIVACY = r'[\w.+-]+@[\w-]+\.[\w.]+|(?<!\d)1[3-9]\d{9}(?!\d)|(?<![\d.,$])\d{8,}(?![\d.,])'
TIERS = r'(?:第[一二三]类|第[一二三]层|第[一二三]梯队)[^\n]{0,12}(?:冲刺|匹配|保底|稳妥|组合补充|平台优先|综排优先)|(?:冲刺|匹配|保底)[^\n]{0,6}(?:冲刺|匹配|保底)[^\n]{0,6}(?:冲刺|匹配|保底)'
APHORISM = r'有些[^。\n]{0,12}的意义|的意义[^。\n]{0,12}(?:不只是|不是|在于)|好的[^。\n]{0,8}(?:规划|申请|选校)[，,]\s*不是|不代表[^。\n]{0,16}。?真正|真正要做的'
QUOTE = r'“[^”\n]*”|「[^」\n]*」|"[^"\n]*"'


def read_text(path):
    path = Path(path)
    if path.suffix.lower() == '.docx':
        with zipfile.ZipFile(path) as z:
            xml = z.read('word/document.xml').decode('utf-8')
        xml = re.sub(r'</w:p>', '\n', xml)
        return re.sub(r'<[^>]+>', '', xml)
    return path.read_text(encoding='utf-8-sig')


def protected_sentences(extra=None):
    out = []
    if LEARNED.exists():
        text = LEARNED.read_text(encoding='utf-8')
        m = re.search(r'## 定稿保护句[^\n]*\n(.*?)(?:\n## |\Z)', text, re.S)
        if m:
            out += [x[2:].strip() for x in m.group(1).splitlines() if x.startswith('- ')]
    if extra:
        out += [x.strip() for x in read_text(extra).splitlines() if x.strip()]
    return out


def norm_punct(s):
    return s.replace(',', '，').replace(':', '：').replace(';', '；').replace('?', '？').replace('!', '！')


def strip_protected(text, protect):
    removed = 0
    for s in protect:
        for variant in {s, norm_punct(s)}:
            n = text.count(variant)
            if n:
                removed += n
                text = text.replace(variant, '')
    return text, removed


def overlap(src, draft, n=12):
    squash = lambda s: re.sub(r'\s+', '', s)
    a, b = squash(src), squash(draft)
    grams = {a[i:i + n] for i in range(len(a) - n + 1)}
    hits, i = [], 0
    while i <= len(b) - n:
        if b[i:i + n] in grams:
            j = i + n
            while j < len(b) and b[i:j + 1] in a:
                j += 1
            hits.append(b[i:j])
            i = j
        else:
            i += 1
    # 只剩校名、项目名、数字这类专有名词的重合不算
    return [h for h in hits if re.search(r'[一-鿿]{6,}', h)]


def lint(text, genre='case', src_texts=(), protect=()):
    body, n_protected = strip_protected(text, protect)
    quotes = re.findall(QUOTE, body)
    editorial = re.sub(QUOTE, '', body)
    length = max(1, len(re.sub(r'\s+', '', text)))
    caps = CAPS[genre]
    counts, over = {}, {}
    for k, pat in PATTERNS.items():
        hits = re.findall(pat, editorial)
        counts[k] = {'count': len(hits), 'per_10k': round(len(hits) * 10000 / length, 1),
                     'cap': caps[k], 'ph_baseline_per_10k': PH_BASELINE[k], 'examples': hits[:5]}
        if caps[k] is not None and len(hits) > caps[k]:
            over[k] = len(hits)
    limited = {w: text.count(w) for w, cap in LIMITED_WORDS.items() if text.count(w) > cap}
    # 结尾区：正文最后 20%（金句一般出现在放榜段之后、CTA 之前）
    tail = editorial[int(len(editorial) * 0.8):]
    report = {
        'genre': genre,
        'chars': length,
        'protected_removed': n_protected,
        'quoted_chars_excluded': sum(len(q) for q in quotes),
        'patterns': counts,
        'over_cap': over,
        'compliance': sorted(set(re.findall(COMPLIANCE, text))),
        'ai_words': sorted(set(re.findall(AI_WORDS, editorial))),
        'limited_words_over': limited,
        'self_praise': sorted(set(re.findall(SELF_PRAISE, editorial))),
        'privacy': re.findall(PRIVACY, text),
        'you_in_editorial': editorial.count('你'),
    }
    if genre in ('case', 'short'):
        report['three_tier_school_list'] = re.findall(TIERS, text)
        report['aphorism_ending'] = re.findall(APHORISM, tail) + re.findall(PATTERNS['不是…而是'], tail)
    hits = []
    for s in src_texts:
        hits += overlap(s, text)
    report['overlap_12'] = hits
    report['fail'] = bool(over or report['compliance'] or report['privacy'] or hits or limited
                          or report.get('three_tier_school_list') or report.get('aphorism_ending'))
    return report


def show(r):
    lines = [f"【zh_lint】体裁 {r['genre']} ｜ {r['chars']} 字 ｜ 跳过定稿句 {r['protected_removed']} 处 ｜ 引号内原话 {r['quoted_chars_excluded']} 字不计限额"]
    for k, v in r['patterns'].items():
        cap = '不设限' if v['cap'] is None else f"上限 {v['cap']}"
        flag = ' ← 超限' if k in r['over_cap'] else ''
        ex = ('；例：' + ' / '.join(v['examples'][:3])) if v['examples'] else ''
        lines.append(f"· {k}：{v['count']} 次（每万字 {v['per_10k']}，PH 基线 {v['ph_baseline_per_10k']}），{cap}{flag}{ex}")
    for key, label in (('three_tier_school_list', '三层选校写法'), ('aphorism_ending', '结尾金句句式'),
                       ('compliance', '合规禁用语'), ('ai_words', 'AI 高频 / 空心词'), ('self_praise', '自夸形容词'),
                       ('privacy', '隐私（邮箱 / 手机 / 长数字）'), ('overlap_12', '12 字以上与参考文重合')):
        if key in r and r[key]:
            lines.append(f"· {label}：{'；'.join(map(str, r[key][:8]))}")
    if r['limited_words_over']:
        lines.append('· 限次词超限：' + '；'.join(f'{k} {v} 次' for k, v in r['limited_words_over'].items()))
    if r['genre'] in ('case', 'short') and r['you_in_editorial']:
        lines.append(f"· 引号外的「你」{r['you_in_editorial']} 处：只允许在导语末句、IvyPath小贴士、建议板块、CTA、B体顾问寄语里，逐处人工确认")
    lines.append('结论：' + ('有必须处理的项' if r['fail'] else '通过（人工复核仍需做）'))
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('draft')
    ap.add_argument('--genre', default='case', choices=sorted(CAPS))
    ap.add_argument('--src', nargs='*', default=[], help='参考文 / 竞品原文，做 12 字查重')
    ap.add_argument('--protect', help='额外的定稿保护句文件，一行一句')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    r = lint(read_text(a.draft), a.genre, [read_text(s) for s in a.src], protected_sentences(a.protect))
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else show(r))
    return 1 if r['fail'] else 0


if __name__ == '__main__':
    sys.exit(main())
