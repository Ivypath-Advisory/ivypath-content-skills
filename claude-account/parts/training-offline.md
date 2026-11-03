## 离线核心规则（读不到仓库时按此执行）

写法规则按 case-story-writer 账号版（含它文末的「离线核心规则」），语言终审按 ivypath-humanize-zh。以下补足 reference-cases.md 与检查脚本。

### 选案

- 外部案例目录：Dropbox `/网站开发/6、网站项目库与案例库/竞品案例库/外部案例目录_PH清柚常青藤拓达_20261103.csv`（UTF-8 带 BOM，1,180 条；不在 Dropbox 时请用户附上）。优先院校参考表在同目录。PH 授权清单：`/网站开发/6、网站项目库与案例库/PH素材库/ph_authorized.tsv`。
- 授权：A 授权清单（第一次用前跟 Daniel 确认文字、图片分别能否用）；B 本团队经手（清柚数据表学员，按改稿模式，清柚原文和图片一张不用，上线前确认学生授权；数据表含真名，只在本地 Excel 用）；C 仅培训（其余全部）。
- 匹配层级：L1 同本科 + 同录取项目 → L2 同本科 + 同白皮书方向 → L3 同类院校（UC 系；罗格斯 / UConn / 石溪；布兰迪斯 / 雪城；NYU / NYU Shanghai）+ 同项目或方向 → L4 任意本科 + 同项目。
- 打分：最终去向在本方向 +3；录了白皮书 05 节项目 +2；2025 季及以后 +2，2023–2024 季 +1；PH 正文 ≥3,000 字 +1；有 GPA +1；本方向录取每个 +0.5（最多 +1.5）。

### 检查脚本（仓库脚本不可用时临时用）

```python
import re
PAT = {"不是…而是": r"(?:不是|并非|并不是|不只是|不仅是|不在于|与其说)[^。！？\n]{0,30}?(?:而是|更是|而在于|不如说)",
       "真正": r"真正", "破折号": r"——|—"}
CAP = {"不是…而是": 1, "真正": 1, "破折号": 1}  # 每篇；引号内原话不计
QUOTE = r"“[^”\n]*”|「[^」\n]*」"
BANNED = r"保证|包过|保录|100%录取|最强|包装背景|走捷径|内部资源|赋能|打造|全方位|深耕|助力|保驾护航|至关重要|闭环"

def counts(t):
    e = re.sub(QUOTE, "", t)
    return {k: len(re.findall(v, e)) for k, v in PAT.items()}

def overlap(src, draft, n=12):
    a, b = re.sub(r"\s+", "", src), re.sub(r"\s+", "", draft)
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
    return hits  # 只允许校名 / 项目名 / 数字类专有名词
```
