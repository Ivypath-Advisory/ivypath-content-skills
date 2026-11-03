# IvyPath 中文内容 skills

IvyPath 面向学生家长的中文内容写作规则，GitHub 是唯一维护来源。英文申请材料（文书、推荐信、简历）在另一个仓库 `Ivypath-Advisory/ivypath-writing-skills`。

## 三个 skill，三层分工

| 层 | skill | 管什么 | 不管什么 |
|---|---|---|---|
| 共享语言层 | `ivypath-humanize-zh` | 中文对外稿的语感与终审去 AI 味：通用规则、各体裁限额（白皮书 / 案例文 / 小红书 / 其他） | 文章结构、事实、选题 |
| 案例生产线 | `case-story-writer` | 案例文的口吻、体例（D / B / C）、选校与结尾写法、官网长页与四栏短页、配图与 offer 海报、改稿模式、学习记录 | 语言终审（调用 humanize-zh） |
| 培训外壳 | `ivypath-case-imitation-training` | 实习生训练：选案卡、训练包、练习任务、批改评分、素材包 | 写法规则（全部读 case-story-writer） |

共用检查脚本：`scripts/zh_lint.py`（句式限额、禁用词、隐私、12 字查重、三层选校与结尾金句检测）。

```
python3 scripts/zh_lint.py 成稿.md --genre case            # 公众号 / 官网长页
python3 scripts/zh_lint.py 短页.md --genre short           # 官网四栏短页
python3 scripts/zh_lint.py 回稿.docx --genre case --src 原文.txt   # 批改实习生回稿
```

## 目录

```
case-story-writer/                 案例生产线完整版（SKILL.md + references/）
ivypath-humanize-zh/               中文终审
ivypath-case-imitation-training/   实习生训练
scripts/zh_lint.py                 共用检查脚本
scripts/release.py                 生成 release.json（源文件与账号版哈希）
claude-account/                    Claude 账号版：build.py 生成，parts/ 是离线核心规则
tests/test_skills.py               离线回归测试
AUDIT.md                           规则决定记录
```

## Claude 账号版怎么来

Claude 账号的 skill 更新卡片每个 skill 只保存一个 SKILL.md，所以账号版 = 加载说明（开工先读本仓库完整版）+ 本仓库 SKILL.md 正文 + 读不到仓库时的离线核心规则。改规则的顺序：

1. 改本仓库对应 skill 目录里的文件；影响离线核心的，同时改 `claude-account/parts/`。
2. `python3 claude-account/build.py && python3 scripts/release.py && python3 -m unittest tests/test_skills.py`
3. 提交、推送 GitHub。
4. 把有变化的 `claude-account/<skill>/SKILL.md` 做成 skill 更新卡片，由 Daniel 保存后才生效。

## 和 Dropbox 市场库的关系

- 市场库 `/市场/Obsiden_市场/07_生产发布库/case-story-writer.skill` 等旧 `.skill` 包（2026-07 至 08 月版）停止维护。
- 市场库继续放素材、成稿、模板（案例卡模板、配图模板、OFFER捷报模板）和品牌资料。
- `01_品牌中枢/去AI味写作规范.md`（小红书 / 抖音版，2026-07-14）保留为阅读版；与本仓库冲突时以本仓库为准，它新增的禁用词补进 quality-check 和 zh_lint。
