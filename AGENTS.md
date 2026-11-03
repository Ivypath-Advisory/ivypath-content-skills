# IvyPath content skills · 维护说明

此仓库维护三个中文内容 skill：`case-story-writer`（案例文生产线）、`ivypath-humanize-zh`（中文终审去 AI 味）、`ivypath-case-imitation-training`（市场实习生训练）。分工见 README.md。修改前读 AUDIT.md 的决定表，不恢复已废除的规则（三层选校、结尾金句、D体「不是…而是」≤3、按每万字计的句式上限），也不擅自取消 Daniel / Shawn 定下的规则。

## 改规则

- 规则只在一处写：语言规则在 humanize-zh；案例文结构、口吻、体例在 case-story-writer；培训 skill 只引用，不复制写法规则。
- 新规则来自 Daniel、Shawn 的改稿或明确指示。实习生回稿、批改记录不进规则。改稿学习先记进 `case-story-writer/references/learned-style.md` 的候选，连续 3 篇没被推翻、Daniel 确认后转正。
- Daniel / Shawn 给的定稿文字照用。需要 lint 跳过的定稿句收进 learned-style.md「定稿保护句」。
- 改完运行：`python3 claude-account/build.py && python3 scripts/release.py && python3 -m unittest tests/test_skills.py`，全部通过再提交。离线核心规则（`claude-account/parts/`）要跟着改的一并改。
- 测试里的「残留旧规则」表（`tests/test_skills.py` ConsistencyTests.STALE）随规则变更维护：废除一条规则时把它加进去。

## 不进仓库的东西

学生全文初稿、学生真名、联系方式、清柚数据表、外部案例目录 CSV 与竞品原文全文、offer 原件、凭据、本机备份。参考资料只写 Dropbox 路径。已发表文章的短摘录可以作为写法例句。

## 同步

- 用户说「同步内容 skill」「和 GitHub 同步」（在本仓库语境下）：比较 GitHub、本地工作副本和 Claude 账号已安装版，只合并已授权的改动；语义冲突只问具体取舍，不覆盖任何一边；不强制推送。
- GitHub 推送成功不等于 Claude 账号已更新：账号版要用 skill 更新卡片由用户保存。两件事分别报告。
- 用 add_repo 挂仓库或 GitHub 连接器；遇到权限拒绝不绕过。
