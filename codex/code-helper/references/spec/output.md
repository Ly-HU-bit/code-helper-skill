# 输出规范

输出格式由执行 profile 决定。用户明确指定的格式优先于本文件。

## Quick / Standard（默认）

```text
output/<task-name>/
├── code/                 # 可运行工作区：修改后源码、现有测试、必要配置
├── tests/                # 可选：便于单独查看的新增测试副本
├── report.md             # 精简结论、验证状态和教学性建议
├── verification.json     # 机器可读的检查结果与耗时
└── changes.patch         # 唯一的逐行代码差异
```

`report.md` 应包含：profile、处理范围、重要 bug/修改、测试与样式验证结果、
未完成或无法验证的事项。报告引用文件和行号即可；不要重复粘贴
`changes.patch` 中已经存在的完整 diff。

使用统一入口收尾：

```bash
python -m codehelper finalize input/<task> output/<task>/code output/<task> --profile quick
```

## Deep

只有用户要求“全面、彻底、deep”或 requirements 指定 `profile: deep` 时，
生成传统拆分报告：

```text
output/<task-name>/
├── code/
├── tests/
├── tools/                         # 可选 visual debugger
├── doc/
│   ├── 00_summary.txt
│   ├── 01_debug.txt
│   ├── 02_style.txt
│   ├── 03_test.txt
│   └── 04_optimization.txt
├── verification.json
└── changes.patch
```

Deep 报告可使用 `output/_template/doc/`。每项说明应包含文件名和精确行号；
必要时展示小段 `-`/`+` 对照，但 `changes.patch` 仍是完整差异的权威来源。

## Deep 评分卡

```text
Debug:        10 - (high×3 + medium×2 + low×1) / 2  (min 0)
Style:        10 - (high×2 + medium×1 + low×0.5)     (min 0)
Testing:      10 if no gaps, 8 if ≤2 gaps, 6 if ≤5, 4 if ≤10, else 2
Optimization: 10 if all optimal, 8 if 1 non-optimal, 6 if 2, else 4
Overall:      (Debug + Style + Testing + Optimization) / 4
```

等级：A(9–10)、B(7–8)、C(5–6)、D(3–4)、F(0–2)。Quick/Standard
可以给出结论性状态，不要求评分，避免为日常任务制造额外文档工作。

## 通用检查清单

- [ ] 未修改 `input/`
- [ ] `code/` 是可运行工作区，包含源码、适用测试和必要构建配置
- [ ] `changes.patch` 已由 `src/generate_diff.py` 生成
- [ ] 测试/样式结果和超时、缺失工具等限制均有明确记录
- [ ] 生成物没有写入公共 `src/`
- [ ] Deep 模式才强制生成 00–04 拆分报告
