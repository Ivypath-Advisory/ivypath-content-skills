## 离线核心规则（读不到仓库时按此执行）

写法规则按 case-story-writer 账号版（含它文末的「离线核心规则」），语言终审按 ivypath-humanize-zh。以下补足 reference-cases.md 与检查脚本。

### 选案

- 外部案例目录：Dropbox `/网站开发/6、网站项目库与案例库/竞品案例库/分析与汇总_20261103/竞品案例数据表_20261103/外部案例目录_PH清柚常青藤拓达_20261103.csv`（UTF-8 带 BOM，1,180 条；路径不对就按文件名搜，找不到请用户附上）。优先院校参考表在同目录。PH 授权清单：`/网站开发/6、网站项目库与案例库/竞品案例库/ph_authorized.tsv`。
- 授权：A 授权清单（第一次用前跟 Daniel 确认文字、图片分别能否用）；B 本团队经手（清柚数据表学员，按改稿模式，清柚原文和图片一张不用，上线前确认学生授权；数据表含真名，只在本地 Excel 用）；C 仅培训（其余全部）。
- 匹配层级：L1 同本科 + 同录取项目 → L2 同本科 + 同白皮书方向 → L3 同类院校（UC 系；罗格斯 / UConn / 石溪；布兰迪斯 / 雪城；NYU / NYU Shanghai）+ 同项目或方向 → L4 任意本科 + 同项目。
- 打分：最终去向在本方向 +3；录了白皮书 05 节项目 +2；2025 季及以后 +2，2023–2024 季 +1；PH 正文 ≥3,000 字 +1；有 GPA +1；本方向录取每个 +0.5（最多 +1.5）。

### 检查（仓库脚本不可用时）

读不到仓库里的 `scripts/zh_lint.py` 时不要临时拼一个简化脚本，按 case-story-writer 账号版「离线核心规则」的句式限额和禁用语人工计数，查重用下面这个函数（与仓库脚本同口径的最小版本），批改报告里写明「未跑 zh_lint，人工计数」。

```python
import re

def overlap(src, draft, n=12):
    squash = lambda s: re.sub(r"\s+", "", s)
    school = r"[\u4e00-\u9fff]{2,12}(?:大学|学院|分校)"
    a, b = re.sub(school, "⊙", squash(src)), re.sub(school, "⊙", squash(draft))
    grams = {a[i:i + n] for i in range(len(a) - n + 1)}
    hits, i = [], 0
    while i <= len(b) - n:
        if b[i:i + n] in grams:
            j = i + n
            while j < len(b) and b[i:j + 1] in a:
                j += 1
            hits.append(b[i:j]); i = j
        else:
            i += 1
    return [h for h in hits if re.search(r"[\u4e00-\u9fff]{6,}", h)]  # 只剩英文名和数字的重合不算
```
