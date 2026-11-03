"""离线回归测试：检查脚本行为、规则一致性、加载器与发布清单。不访问网络。"""
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ['case-story-writer', 'ivypath-humanize-zh', 'ivypath-case-imitation-training']


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = load('zh_lint', 'scripts/zh_lint.py')


def skill_texts():
    for name in SKILLS:
        for p in sorted((ROOT / name).rglob('*.md')):
            yield p, p.read_text(encoding='utf-8')


class LintTests(unittest.TestCase):
    def test_reversal_family_is_counted(self):
        t = '他最核心的问题不是背景不够好，而是经历之间没有联系。这不只是一所学校 — 而是一条路。'
        r = lint.lint(t, 'case')
        self.assertEqual(r['patterns']['不是…而是']['count'], 2)
        self.assertIn('不是…而是', r['over_cap'])
        self.assertEqual(r['patterns']['破折号']['count'], 1)

    def test_quotes_are_not_counted(self):
        t = '她在问卷里写：“其实我真正担心的不是分数，而是方向。”我们先把课表过了一遍。'
        r = lint.lint(t, 'case')
        self.assertEqual(r['patterns']['不是…而是']['count'], 0)
        self.assertEqual(r['patterns']['真正']['count'], 0)
        self.assertGreater(r['quoted_chars_excluded'], 0)

    PROTECT = '列一份学校名单并不难,难的是让学生真正明白每所学校为什么适合自己。'

    def _protect_file(self, d):
        f = Path(d) / 'protect.txt'
        f.write_text(self.PROTECT, encoding='utf-8')
        return lint.protected_sentences(f)

    def test_protected_sentence_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            protect = self._protect_file(d)
        t = '以哥大为例。' + lint.norm_punct(protect[-1])
        r = lint.lint(t, 'case', protect=protect)
        self.assertEqual(r['patterns']['真正']['count'], 0)
        self.assertEqual(r['protected_removed'], 1)

    def test_three_tier_list_and_aphorism_ending(self):
        t = ('第一类 · 重点冲刺\n兴趣匹配度最高的项目。\n第二类 · 平台优先\n第三类 · 组合补充\n'
             + '放榜后他选择了哥大。\n' * 20
             + '有些申请的意义，不只是抵达一所学校，而是让热爱被看见。')
        r = lint.lint(t, 'case')
        self.assertEqual(len(r['three_tier_school_list']), 3)
        self.assertTrue(r['aphorism_ending'])
        self.assertTrue(r['fail'])

    def test_plain_ending_passes(self):
        t = ('以哥大为例，我们和他一门一门对过课号：ELEN E6873 统计信号处理与学习。\n'
             '看完这些课程，他发现，信号处理和机器学习都离不开统计推断。\n'
             '放榜季，他先后收到了五份录取，最后选择了哥大，因为纽约的产业资源离他想做的方向更近。\n'
             '整个申请过程中，我们看到的是一个愿意承认不足、肯追问的学生。\n'
             '我们也祝愿他在哥大的学习一切顺利，继续自己的 EE 探索之路。')
        r = lint.lint(t, 'case')
        self.assertFalse(r['fail'], lint.show(r))

    def test_overlap_ignores_proper_nouns(self):
        src = '她最后拿到了 Columbia University Master of Science 的录取，那一刻她在宿舍里哭了很久很久。'
        draft = '她拿到 Columbia University Master of Science 录取。那一刻她在宿舍里哭了很久很久。'
        hits = lint.overlap(src, draft)
        self.assertEqual(len(hits), 1)
        self.assertIn('宿舍里哭了很久', hits[0])

    def test_privacy_and_compliance(self):
        r = lint.lint('联系 test@example.com 或 13812345678。我们保录名校。', 'case')
        self.assertEqual(len(r['privacy']), 2)
        self.assertIn('保录', r['compliance'])

    def test_protected_sentence_with_she(self):
        with tempfile.TemporaryDirectory() as d:
            protect = self._protect_file(d)
        t = '以耶鲁为例。他说' + lint.norm_punct(protect[-1]).replace('他', '她')
        r = lint.lint(t, 'case', protect=protect)
        self.assertEqual(r['patterns']['真正']['count'], 0)

    def test_raw_block_and_blockquote_are_excluded(self):
        t = ('::: 原话\n其实我真正担心的不是分数，而是方向。\n:::\n'
             '> 我真正想去的是纽约。\n'
             '我们先把课表过了一遍。')
        r = lint.lint(t, 'case')
        self.assertEqual(r['patterns']['不是…而是']['count'], 0)
        self.assertEqual(r['patterns']['真正']['count'], 0)

    def test_dash_exclusions(self):
        t = '2023—2024 申请季，他在 Rutgers—New Brunswick 选了 E6873—E6875。\n“我想去纽约。”\n——Z同学\n他后来写：“先把课表看懂。”——Z同学'
        r = lint.lint(t, 'case')
        self.assertEqual(r['patterns']['破折号']['count'], 0)
        r = lint.lint('答案很简单——专注。', 'case')
        self.assertEqual(r['patterns']['破折号']['count'], 1)

    def test_more_reversal_forms(self):
        for s in ('他选了哥大，而不是宾大。', '这不是运气，是准备。', '关键不在于分数，在于主线。',
                  '有些申请的意义，不只是抵达一所学校。而是让热爱被看见。'):
            self.assertEqual(lint.lint(s, 'case')['patterns']['不是…而是']['count'], 1, s)
        self.assertEqual(lint.lint('他是不是该再考一次，是个问题。', 'case')['patterns']['不是…而是']['count'], 0)

    def test_tier_words_in_one_line(self):
        r = lint.lint('冲刺：哥大、康奈尔；匹配：NYU、BU；保底：雪城', 'case')
        self.assertTrue(r['three_tier_school_list'])
        r = lint.lint('兴趣匹配度最高的是哥大，我们建议他冲刺。', 'case')
        self.assertFalse(r['three_tier_school_list'])

    def test_ending_zone_starts_at_closing(self):
        body = '**招生官要的不是热情，而是证据。**\n' + '他补了一段实习。\n' * 30
        end = '整个申请过程中，我们看到的是一个真诚的学生。我们也祝愿他在哥大的学习一切顺利。\n预约一次评估'
        r = lint.lint(body + end, 'case')
        self.assertFalse(r['aphorism_ending'])
        self.assertEqual(r['patterns']['不是…而是']['in_bold'], 1)
        r = lint.lint(body + '整个申请过程中，我们看到的是一个真诚的学生。这就是申请的意义。愿每一个认真的你，都被看见。', 'case')
        self.assertTrue(r['aphorism_ending'])

    def test_student_quote_ending_passes(self):
        body = '他补了一段实习。\n' * 30
        end = ('整个申请过程中，我们看到的是一个真诚的学生。\n'
               '他后来在问卷里写：“申请不是比谁经历多，而是看你能不能把一件事讲清楚。”——Z同学\n预约一次评估')
        r = lint.lint(body + end, 'case')
        self.assertFalse(r['aphorism_ending'], r['aphorism_ending'])
        self.assertEqual(r['patterns']['破折号']['count'], 0)
        self.assertFalse(r['fail'], lint.show(r))

    def test_dates_and_urls_are_not_privacy(self):
        r = lint.lint('发布信息：20261103_案例文_Z同学；课号出处 https://bulletin.example.edu/courses/123456789', 'case')
        self.assertEqual(r['privacy'], [])

    def test_overlap_allow_list_and_school_names(self):
        src = '最后去了加州大学圣地亚哥分校数据科学硕士项目，那一刻她在宿舍里哭了很久很久。'
        draft = '她去了加州大学圣地亚哥分校数据科学硕士项目。'
        self.assertEqual(lint.overlap(src, draft), [])

    def test_docx_skips_deleted_text(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'r.docx'
            xml = ('<w:document><w:body><w:p><w:r><w:t>他先后收到了三份录取 &amp; 一封拒信。</w:t></w:r>'
                   '<w:del><w:r><w:delText>这不是终点，而是起点。</w:delText></w:r></w:del></w:p></w:body></w:document>')
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('word/document.xml', xml)
            text = lint.read_text(path)
            self.assertIn('& 一封拒信', text)
            self.assertNotIn('终点', text)

    def test_title_rules(self):
        bad = lint.lint('# 从一张成绩单到耶鲁：经济系学生如何被看见\n\n正文。', 'case')
        self.assertTrue(bad['title_issues'])
        self.assertTrue(bad['title_colon'])
        self.assertTrue(bad['fail'])
        hype = lint.lint('# 罗格斯学姐申8中8，斩获哥大！\n\n正文。', 'case')
        self.assertGreaterEqual(len(hype['title_issues']), 2)
        ok = lint.lint('# 7 个录取，耶鲁是最后到的\n\n他先后收到了七份录取。', 'case')
        self.assertEqual(ok['title_issues'], [])
        self.assertFalse(ok['title_colon'])
        self.assertFalse(ok['fail'])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            ok, bad = Path(d) / 'ok.md', Path(d) / 'bad.md'
            ok.write_text('他先后收到了三份录取，最后选择了 MIT。我们也祝愿他在 MIT 的学习一切顺利。', encoding='utf-8')
            bad.write_text('这不是结果，而是开始。这不是终点，而是起点。', encoding='utf-8')
            run = lambda p: subprocess.run([sys.executable, '-I', str(ROOT / 'scripts/zh_lint.py'), str(p)],
                                           capture_output=True, text=True).returncode
            self.assertEqual(run(ok), 0)
            self.assertEqual(run(bad), 1)


class ConsistencyTests(unittest.TestCase):
    """规则改动后不能留下互相打架的旧条目。"""

    STALE = [
        (r'选校逻辑三层', '三层选校已于 2026-08-21 废除'),
        (r'放宽到\s*≤?\s*3', '「不是…而是」限额已统一为每篇 ≤1'),
        (r'限额放宽到3次', '「不是…而是」限额已统一为每篇 ≤1'),
        (r'结尾金句回收', '结尾不再回收命题'),
        (r'意象只用于开头场景段和结尾金句', '结尾不写金句'),
        (r'冲刺/匹配/保底逻辑', 'B体选校问题已改为单校课号'),
        (r'面向读者用「你」', '人称规则已统一'),
        (r'05 三层选校', '长页 05 节已改为课号深挖'),
        (r'≤0\.5', '句式限额已从每万字改为每篇计数'),
        (r'答案不在于\{', '摘要公式已去掉翻案句'),
        (r'并不只是____', 'D体段2改为正面陈述'),
        (r'第一个offer详写', '放榜段按结尾四步，一句列完'),
        (r'八个标题公式|九个标题公式|标题公式\s*×\s*9', '标题改为 titles-hooks.md 的六种写法'),
        (r'公式\s?9', 'D体主标题不再用命题式'),
        (r'从\{起点意象\}', '标题与官网 H1 不再用从…到…命题式'),
        (r'让热情真正落地|找到最适合的空间|\{场景意象\}', '小标题改写事实短语'),
        (r'信息要密', '标题改为一个钩子，数字放副题'),
        (r'先问用户挖哪', '最好的 offer 不是最终去向时写录取后的项目权衡'),
        (r'列一份学校名单并不难', '选校收句每篇更换，固定句已撤下'),
    ]

    def test_no_stale_rules(self):
        for p, text in skill_texts():
            for pat, why in self.STALE:
                for line in text.splitlines():
                    if re.search(pat, line) and not re.search(r'作废|废除|取代|旧公式|不做|不写|删除|README|不再|撤下|没有沿用|\\bPROTECT\\b', line):
                        self.fail(f'{p.relative_to(ROOT)} 残留旧规则（{why}）：{line.strip()[:80]}')

    def test_reference_files_exist(self):
        refs = set(re.findall(r'references/([\w-]+\.md)', (ROOT / 'case-story-writer/SKILL.md').read_text()))
        for r in refs:
            self.assertTrue((ROOT / 'case-story-writer/references' / r).exists(), r)
        for p, text in skill_texts():
            for r in re.findall(r'case-story-writer/references/([\w-]+\.md)', text):
                self.assertTrue((ROOT / 'case-story-writer/references' / r).exists(), f'{p.name} → {r}')

    def test_frontmatter_names(self):
        for name in SKILLS:
            head = (ROOT / name / 'SKILL.md').read_text().split('---')[1]
            self.assertRegex(head, rf'name:\s*"?{re.escape(name)}"?')


class LoaderTests(unittest.TestCase):
    def test_loaders_are_current(self):
        before = {n: (ROOT / 'claude-account' / n / 'SKILL.md').read_text() for n in SKILLS}
        subprocess.run([sys.executable, str(ROOT / 'claude-account/build.py')], check=True, capture_output=True)
        for n in SKILLS:
            self.assertEqual(before[n], (ROOT / 'claude-account' / n / 'SKILL.md').read_text(),
                             f'{n} 的账号版不是最新，先运行 claude-account/build.py')

    def test_loader_points_to_repo(self):
        for n in SKILLS:
            t = (ROOT / 'claude-account' / n / 'SKILL.md').read_text()
            self.assertIn('Ivypath-Advisory/ivypath-content-skills', t)
            self.assertIn(f'`{n}/`', t)
            self.assertTrue(t.startswith('---\nname:'))

    def test_release_manifest_is_current(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/release.py'), '--check'])
        self.assertEqual(r.returncode, 0, 'release.json 不是最新，先运行 scripts/release.py')


if __name__ == '__main__':
    unittest.main()
