#!/usr/bin/env python3
"""生成 Claude 账号版 SKILL.md（运行时加载说明 + 完整版正文 + 读不到仓库时的核心规则）。

Claude 账号的 skill 更新卡片每个 skill 只能保存一个 SKILL.md，所以账号版只放：
加载说明（开工先读本仓库完整版）+ 本仓库 SKILL.md 正文 + parts/ 里的离线核心规则。
运行：python3 claude-account/build.py   → 写到 claude-account/<skill>/SKILL.md
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
PARTS = OUT / 'parts'
REPO = 'Ivypath-Advisory/ivypath-content-skills'
VERSION = '2026-11-03'


def split_front(text):
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    return text[:m.end()], text[m.end():]


def loader(directory, read_first):
    return f"""> **Claude 账号版 · 运行时加载**（{VERSION} 版）
>
> 完整规则只在私有仓库 `{REPO}`（main 分支）的 `{directory}/` 目录维护。下文的路径都是仓库路径：没写 skill 名的 `references/…` 指 `{directory}/references/`，写了 `case-story-writer` 的指 `case-story-writer/references/`，`scripts/zh_lint.py` 指仓库根目录的检查脚本。Dropbox 市场库里的旧 `.skill` 包（2026-07 至 08 月版）已停止维护，不要读取。
>
> **开工先加载完整版**：用当前会话可用的方式读 {read_first}，再只读其中引用、本次任务需要的文件。Claude Code 会话：add_repo 挂上 `{REPO}` 后读本地克隆；有 gh 时：`gh api repos/{REPO}/contents/<路径> --jq .content | base64 -d`；有 GitHub 连接器时用连接器。同一会话读过就不重读。仓库版与本文件不一致时以仓库版为准。
>
> **读不到仓库时**：用一句话告诉用户「没读到 GitHub 上的完整规则，这次按 Claude 账号里的核心规则执行」，然后按下文执行（文末「离线核心规则」补足读不到的文件），不凭记忆补规则。改规则一律先改 GitHub（见仓库 AGENTS.md），再重新生成本文件。
"""


def build(name, read_first, extra=None):
    front, body = split_front((ROOT / name / 'SKILL.md').read_text(encoding='utf-8'))
    text = front + '\n' + loader(name, read_first) + '\n' + body.strip() + '\n'
    if extra:
        text += '\n---\n\n' + (PARTS / extra).read_text(encoding='utf-8').strip() + '\n'
    (OUT / name).mkdir(exist_ok=True)
    (OUT / name / 'SKILL.md').write_text(text, encoding='utf-8')
    return text


SKILLS = [
    ('case-story-writer', '`case-story-writer/SKILL.md` 与 `references/house-style.md`', 'case-story-offline.md'),
    ('ivypath-humanize-zh', '`ivypath-humanize-zh/SKILL.md`', 'humanize-offline.md'),
    ('ivypath-case-imitation-training',
     '`ivypath-case-imitation-training/SKILL.md` 与 `case-story-writer/references/reference-cases.md`',
     'training-offline.md'),
]

if __name__ == '__main__':
    for name, read_first, extra in SKILLS:
        t = build(name, read_first, extra)
        print(name, len(t.splitlines()), 'lines', len(t), 'chars')
