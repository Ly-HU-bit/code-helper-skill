#描述
这是关于input文件夹中内容的描述

#输入格式
每个任务都放在一个folder内，里面可能有：
目标code、一份用户要求（bug描述、优化要求等等）（.md或.txt）、用户提供的style要求（.md或.txt）、用户提供的测试用例

# 执行 profile

默认使用面向日常任务的 `quick` profile（目标 3–5 分钟）。可在需求文件中指定：

```
profile: quick      # 270 秒；debug + 自动 style + 现有测试
profile: standard   # 480 秒；增加测试补全和有意义的优化
profile: deep       # 900 秒；完整四项审查和拆分报告
```

用户直接提出“全面/彻底/deep”时可自动选择 `deep`。其他情况不要因为文件夹内
包含构建产物而升级模式；先通过 manifest 排除 `.idea/`、`out/`、`build/`、
缓存、依赖与二进制文件，再按源码文件数和行数判断规模。

#预设检测

CodeHelper 支持通过 `preset:` 指令快速切换代码规范。在 `requirements.md` 或 `requirements.txt` 中添加一行：

```
preset: <preset_name>
```

可用预设：`ucb61b_java`、`google_java`、`pep8_python`。详见 `spec/presets/README.md`。

如果 requirements 中包含 `preset:` 行，则使用对应预设的规范覆盖默认风格要求。未指定时默认使用 `ucb61b_java` 规范，Python 项目使用 PEP 8。

用户也可以在 requirements 中混合预设和自定义要求：
```
preset: pep8_python
额外要求: 所有public函数必须有type hints
```

#rule
不要更改input文件夹中的初始内容，你可以复制，并在output文件夹中修改
如果用户没有提供上述信息（code除外），使用 quick profile 和 spec 默认要求
如果用户提供要求/模板，按照用户的完成
除非用户提供的测试用例本身存在错误，不要删除其提供的测试用例，但可以增加其他测试用例（详见 spec/tests.md）
