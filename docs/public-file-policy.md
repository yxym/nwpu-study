# 公开文件规则

本仓库面向公开归档，默认不把本地课程资料直接发布。所有文件必须经过白名单和人工确认后才能进入仓库。

## 核心原则

- 白名单制：只扫描 `public-whitelist.yml` 中列出的学期、课程和来源目录。
- 人工闸门：候选文件先进入复核清单，只有在 JSON 中设置 `approved: true` 后才会导入。
- 最小公开：只公开课程学习必要且适合共享的资料，不公开隐私、非课程事务和版权边界不清的内容。
- 可追踪：导入后由 manifest 和索引记录实际收录文件，便于复核和删除。

## 允许公开的资料

通常可以进入候选或收录范围的资料包括：

- 学生自愿公开的作业、实验报告、课程项目报告、展示材料、poster
- 实验原始数据、数据处理表格、代码、图表和复现材料
- 复习整理、课程笔记、知识点总结、错题整理
- worksheet、practice questions、评分标准、课程任务说明等非 lecture slides 类辅助文件
- 教材、电子书、老师答案、习题答案等在白名单中明确允许且适合公开的资料

这些资料仍需人工检查，确认没有隐私信息、版权风险或课程纪律问题。

## 排除的资料

以下内容不得公开导入：

- 课件、lecture slides、教师授课 PPT、课堂讲义、课程教学幻灯片
- 学长学姐资料、往年资料、历年整理、出售资料或来源不明的外部资料包
- 学生会、班级名单、报名表、简历、入党、出国、请假、花名册等非课程或隐私资料
- 未脱敏的个人信息，包括学号、手机号、身份证号、邮箱、住址、签名、成绩、分组名单等
- 系统垃圾文件和临时文件，如 `.DS_Store`、`Thumbs.db`、`desktop.ini`、`~$` 开头文件
- 明确违反学校规定、课程要求、考试纪律或版权协议的资料

脚本会根据关键词和课程排除规则自动标记一部分风险文件，但自动规则不能替代人工判断。

## 候选复核流程

1. 根据 `public-whitelist.yml` 扫描白名单来源，生成候选清单：

   ```bash
   python3 scripts/collect_candidates.py
   ```

   默认输出：

   - `docs/review/candidates.md`
   - `docs/review/candidates.json`

2. 阅读 `docs/review/candidates.md`，逐项检查分类、来源路径、目标路径和理由。
3. 只对确认可公开的条目，在 `docs/review/candidates.json` 中设置：

   ```json
   "approved": true
   ```

4. 不确定、需要删除、命中隐私或命中排除规则的条目保持 `approved: false`。

## 导入与检查命令

先预览将要复制的文件：

```bash
python3 scripts/sync_public_files.py --dry-run
```

确认无误后导入已批准文件：

```bash
python3 scripts/sync_public_files.py
```

导入后生成索引和仓库 manifest：

```bash
python3 scripts/build_manifest.py
```

提交前运行公开边界检查：

```bash
python3 scripts/build_manifest.py --check
```

如果 `--check` 报错，说明仓库当前已收录文件命中了排除规则。请按错误中的具体路径处理，不要手动绕过或隐藏错误。

## 删除与申诉

如果你发现仓库中存在不应公开的文件，请提供具体路径和原因。维护者应优先处理隐私、版权和学术诚信相关问题；必要时删除文件、更新 manifest，并补充白名单或排除规则。
