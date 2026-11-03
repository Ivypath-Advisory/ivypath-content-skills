#!/usr/bin/env python3
"""IvyPath 中文对外稿检查：句式限额、禁用词、隐私、查重、三层选校、金句结尾与标题。

用法：
  python3 scripts/zh_lint.py 稿件.md [--genre case|short|whitepaper|xhs|other]
                             [--src 参考文.txt ...] [--allow 校名项目名.txt] [--n 12]
                             [--protect 定稿句.txt] [--json]

- 支持 .md / .txt / .docx（docx 只读接受修订后的正文，不需要 python-docx）。
- 引号（“”「」""）里的文字、B体 `::: 原话` 与 `:::` 之间的原话区、以 > 开头的引用块按原话处理，
  不计入句式限额，但照查禁用词和隐私。
- 定稿保护句默认从 case-story-writer/references/learned-style.md 的「定稿保护句」一节读取，
  --protect 可再加一个文件（一行一句）。保护句不计入句式限额。
- 案例文与短页会检查标题行（第一个 `# ` 开头的行）：命题式、比喻和抽象词、「也能」，
  与 case-story-writer/references/titles-hooks.md 同口径。
- 有超限、禁用词、隐私命中、查重命中或标题禁用写法时退出码为 1。
"""
import argparse
import html
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNED = ROOT / 'case-story-writer' / 'references' / 'learned-style.md'

PATTERNS = {
    '不是…而是': (r'(?<!是)(?:不是|并非|并不是|不只是|不仅仅是|不仅是|不在于|与其说)[^。！？!?\n]{0,30}?(?:而是|更是|而在于|不如说)'
                 r'|(?:不只是|不仅仅是|不仅是)[^！？!?\n]{0,30}?。\s*而是'
                 r'|(?<!是)(?:不是|并非|不在于)[^。！？!?\n，,]{1,20}[，,]\s*(?:是|在于)'
                 r'|而不是'),
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

# 合规禁用语，与 case-story-writer/references/quality-check.md 第二节同口径
COMPLIANCE = (r'保录|包过|保证|100%\s*录取|包装背景|走捷径|内部资源|名校随便拿|低分也稳|最强'
              r'|(?:全美|全国|全球|行业|业内|同行|排名|口碑)第一|第一(?:名机构|品牌|机构)')
AI_WORDS = (r'赋能|抓手|闭环|打造|全方位|深耕|助力|保驾护航|至关重要|淋漓尽致|颠覆|重磅|干货满满|浓墨重彩'
            r'|大放异彩|圆梦名校|厚积薄发|未来可期|拭目以待|综上所述|总而言之|一言以蔽之|毋庸置疑|众所周知'
            r'|值得一提的是|不得不说|底层逻辑|一站式|多维度|无缝衔接|可圈可点|最后一块拼图|老规矩|重点来了'
            r'|更狠的是|更绝的是|更炸的是|更离谱的是')  # 后半来自市场库 01_品牌中枢/去AI味写作规范.md Tier 1
LIMITED_WORDS = {'脱颖而出': 1, '抛出橄榄枝': 1, '天花板': 1}
SELF_PRAISE = r'(?:非常|很|十分|特别)(?:专业|用心|贴心|高效|负责)|专业的(?:团队|老师|顾问|服务)|认真负责|用心负责'
URL = r'https?://\S+|www\.\S+'
PRIVACY = r'[\w.+-]+@[\w-]+\.[\w.]+|(?<!\d)1[3-9]\d{9}(?!\d)|(?<![\d.,$])(?!20\d{6}(?!\d))\d{8,}(?![\d.,])'
TIER_CARDS = r'(?:第[一二三]类|第[一二三]层|第[一二三]梯队)[^\n]{0,12}(?:冲刺|匹配|保底|稳妥|主申|组合补充|平台优先|综排优先)'
TIER_WORDS = r'冲刺|匹配(?!度)|保底|稳妥|主申|梦校|梯队'
APHORISM = (r'有些[^。\n]{0,12}的意义|的意义[^。\n]{0,12}(?:不只是|不是|在于)|的意义。|好的[^。\n]{0,8}(?:规划|申请|选校)[，,]\s*不是'
            r'|不代表[^。\n]{0,16}。?真正|真正要做的|愿每一个|被看见')
ENDING_START = r'整个申请过程中|我们看到的是一个|祝愿'
ENDING_STOP = r'预约|扫码|本文源自|查看更多案例'
# 标题禁用写法，与 titles-hooks.md「硬规则」同口径
TITLE_BAD = r'这一课|被看见|如何被|之路|破局|密码|答案|也能'
SECTION_LABEL = r'^(?:#{2,4}\s*(?:\d{2}\s*)?|\d{2}\s+)([\u4e00-\u9fff]{2,7})[：:]\s*\S.*$'  # 「01 起点：…」「## 文书：…」2026-11-03 起不用  # 「N申N中」与狂揽、斩获类动词 2026-11-03 起允许
QUOTE = r'“[^”\n]*”|「[^」\n]*」|"[^"\n]*"'
RAW_BLOCK = r'^:::\s*原话\s*$.*?^:::\s*$'          # B体原话区
BLOCKQUOTE = r'^>.*$'
BOLD = r'\*\*[^*\n]+\*\*'


def read_text(path):
    path = Path(path)
    if path.suffix.lower() == '.docx':
        with zipfile.ZipFile(path) as z:
            xml = z.read('word/document.xml').decode('utf-8')
        xml = re.sub(r'<w:del\b.*?</w:del>', '', xml, flags=re.S)       # 修订里删掉的文字不算
        xml = re.sub(r'<w:delText\b.*?</w:delText>', '', xml, flags=re.S)
        xml = re.sub(r'</w:p>', '\n', xml)
        return html.unescape(re.sub(r'<[^>]+>', '', xml))
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
    """定稿句照用，唯一允许变的是人称代词和全半角标点。"""
    removed = 0
    for s in protect:
        variants = set()
        for v in (s, norm_punct(s)):
            variants |= {v, v.replace('他', '她'), v.replace('她', '他')}
        for v in variants:
            n = text.count(v)
            if n:
                removed += n
                text = text.replace(v, '')
    return text, removed


def overlap(src, draft, n=12, allow=()):
    squash = lambda s: re.sub(r'\s+', '', s)
    a, b = squash(src), squash(draft)
    for name in sorted(allow, key=len, reverse=True):     # 校名、项目名不算重合
        a, b = a.replace(name, '⊙'), b.replace(name, '⊙')
    school = r'[一-鿿]{2,12}(?:大学|学院|分校)(?:[一-鿿]{0,12}(?:硕士|博士)?项目)?'
    a, b = re.sub(school, '⊙', a), re.sub(school, '⊙', b)
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
    # 只剩英文名、数字、符号的重合不算
    return [h for h in hits if re.search(r'[一-鿿]{6,}', h)]


def editorial_text(body):
    """去掉引号内原话、B体原话区、引用块；返回（编辑文字, 排除的字数）。"""
    excluded = 0
    for pat, flags in ((RAW_BLOCK, re.M | re.S), (BLOCKQUOTE, re.M), (QUOTE, 0)):
        for m in re.findall(pat, body, flags):
            excluded += len(m)
        body = re.sub(pat, '', body, flags=flags)
    return body, excluded


def count_dashes(text):
    t = re.sub(r'(?<=[\dA-Za-z])\s*[—–]\s*(?=[\dA-Za-z])', '-', text)   # 2023—2024、E6873—E6875、Rutgers—New Brunswick
    t = re.sub(r'(^|\n)\s*——?\s*\S{1,10}(?=\n|$)', r'\1', t)            # 另起一行的署名「——X同学」
    return re.findall(r'——|—', t)


def ending_zone(editorial):
    starts = [m.start() for m in re.finditer(ENDING_START, editorial) if m.start() >= len(editorial) * 0.6]
    start = min(starts) if starts else int(len(editorial) * 0.8)
    stop = re.search(ENDING_STOP, editorial[start:])
    return editorial[start:start + stop.start()] if stop else editorial[start:]


def three_tier(text):
    hits = re.findall(TIER_CARDS, text)
    for line in text.split('\n'):
        words = set(re.findall(TIER_WORDS, line))
        if len(words) >= 2:
            hits.append(line.strip()[:40])
    return hits


def title_line(text):
    m = re.search(r'^#\s+(.+)$', text, re.M)
    return m.group(1).strip() if m else ''


def title_check(title):
    issues = list(dict.fromkeys(re.findall(TITLE_BAD, title)))
    if re.search(PATTERNS['不是…而是'], title):
        issues.append('翻案句')
    if len(re.findall(r'[！!]', title)) > 1:
        issues.append('感叹号超过一个')
    return issues


def lint(text, genre='case', src_texts=(), protect=(), n=12, allow=()):
    body, n_protected = strip_protected(text, protect)
    body = re.sub(r'(?<=[”」"])\s*——?\s*[^\s，。！？“”「」]{1,10}(?=\n|。|$)', '', body)  # 引号后的署名「”——X同学」不算破折号
    editorial, excluded = editorial_text(body)
    length = max(1, len(re.sub(r'\s+', '', text)))
    caps = CAPS[genre]
    bold = ''.join(re.findall(BOLD, editorial))
    counts, over = {}, {}
    for k, pat in PATTERNS.items():
        hits = count_dashes(editorial) if k == '破折号' else re.findall(pat, editorial)
        counts[k] = {'count': len(hits), 'per_10k': round(len(hits) * 10000 / length, 1),
                     'cap': caps[k], 'ph_baseline_per_10k': PH_BASELINE[k], 'examples': hits[:5]}
        if k == '不是…而是':
            counts[k]['in_bold'] = len(re.findall(pat, bold))
        if caps[k] is not None and len(hits) > caps[k]:
            over[k] = len(hits)
    limited = {w: text.count(w) for w, cap in LIMITED_WORDS.items() if text.count(w) > cap}
    no_url = re.sub(URL, '', text)
    report = {
        'genre': genre,
        'chars': length,
        'protected_removed': n_protected,
        'quoted_chars_excluded': excluded,
        'patterns': counts,
        'over_cap': over,
        'compliance': sorted(set(re.findall(COMPLIANCE, text))),
        'ai_words': sorted(set(re.findall(AI_WORDS, editorial))),
        'limited_words_over': limited,
        'self_praise': sorted(set(re.findall(SELF_PRAISE, editorial))),
        'privacy': re.findall(PRIVACY, no_url),
        'you_in_editorial': editorial.count('你'),
    }
    if genre in ('case', 'short'):
        tail = ending_zone(editorial)
        report['three_tier_school_list'] = three_tier(text)
        report['aphorism_ending'] = re.findall(APHORISM, tail) + re.findall(PATTERNS['不是…而是'], tail)
        title = title_line(text)
        report['title'] = title
        report['title_issues'] = title_check(title)
        report['title_colon'] = bool(re.search(r'[：:]', title))
        report['section_labels'] = [m.group(0).lstrip('# ').strip() for m in re.finditer(SECTION_LABEL, text, re.M)]
    hits = []
    for s in src_texts:
        hits += overlap(s, text, n, allow)
    report['overlap'] = hits
    report['overlap_n'] = n
    report['fail'] = bool(over or report['compliance'] or report['privacy'] or hits or limited
                          or report.get('three_tier_school_list') or report.get('aphorism_ending')
                          or report.get('title_issues') or report.get('section_labels'))
    return report


def show(r):
    lines = [f"【zh_lint】体裁 {r['genre']} ｜ {r['chars']} 字 ｜ 跳过定稿句 {r['protected_removed']} 处 ｜ 引号内与原话区 {r['quoted_chars_excluded']} 字不计限额 ｜ 查重阈值 {r['overlap_n']} 字"]
    for k, v in r['patterns'].items():
        cap = '不设限' if v['cap'] is None else f"上限 {v['cap']}"
        flag = ' ← 超限' if k in r['over_cap'] else ''
        ex = ('；例：' + ' / '.join(v['examples'][:3])) if v['examples'] else ''
        bold = f"，其中加粗理念句里 {v['in_bold']} 次" if v.get('in_bold') is not None and v['count'] else ''
        lines.append(f"· {k}：{v['count']} 次{bold}（每万字 {v['per_10k']}，PH 基线 {v['ph_baseline_per_10k']}），{cap}{flag}{ex}")
    for key, label in (('title_issues', '标题禁用写法'), ('section_labels', '小标题写成「栏目名：」（house-style.md「小标题」）'), ('three_tier_school_list', '三层选校写法'), ('aphorism_ending', '结尾金句句式'),
                       ('compliance', '合规禁用语'), ('ai_words', 'AI 高频 / 空心词'), ('self_praise', '自夸形容词'),
                       ('privacy', '隐私（邮箱 / 手机 / 长数字）'), ('overlap', '与参考文连续重合')):
        if key in r and r[key]:
            lines.append(f"· {label}：{'；'.join(map(str, r[key][:8]))}")
    if r.get('title_colon'):
        lines.append(f"· 标题有冒号：{r['title']}。确认不是冒号前后对称的命题句（titles-hooks.md）")
    if r['limited_words_over']:
        lines.append('· 限次词超限：' + '；'.join(f'{k} {v} 次' for k, v in r['limited_words_over'].items()))
    if r['genre'] in ('case', 'short') and r['you_in_editorial']:
        lines.append(f"· 引号外的「你」{r['you_in_editorial']} 处：只允许在导语末句、IvyPath小贴士、建议、CTA、B体问句小标题和顾问寄语里，逐处人工确认")
    lines.append('结论：' + ('有必须处理的项' if r['fail'] else '通过（人工复核仍需做）'))
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('draft')
    ap.add_argument('--genre', default='case', choices=sorted(CAPS))
    ap.add_argument('--src', nargs='*', default=[], help='参考文 / 竞品原文，做 12 字查重')
    ap.add_argument('--allow', help='校名、项目名清单（一行一个），查重时不算')
    ap.add_argument('--n', type=int, default=12, help='查重的连续字数，改稿模式用 10')
    ap.add_argument('--protect', help='额外的定稿保护句文件，一行一句')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    allow = [x.strip() for x in read_text(a.allow).splitlines() if x.strip()] if a.allow else ()
    r = lint(read_text(a.draft), a.genre, [read_text(s) for s in a.src], protected_sentences(a.protect), a.n, allow)
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else show(r))
    return 1 if r['fail'] else 0


if __name__ == '__main__':
    sys.exit(main())
