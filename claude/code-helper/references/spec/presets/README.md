# CodeHelper Presets

预设（Preset）让你快速切换项目的代码规范和风格要求，无需每次手动编写 style guide。

## 使用方式

在 `input/<project>/` 中创建一个 `requirements.md` 或 `requirements.txt`，写入：

```
preset: ucb61b_java
```

或同时指定多个覆盖：

```
preset: pep8_python
额外要求: 所有public函数必须有type hints
```

## 可用预设

| Preset | 语言 | 风格指南 | 测试框架 |
|--------|------|----------|----------|
| `ucb61b_java` | Java | UCB CS 61B Style | JUnit 5 + Truth |
| `google_java` | Java | Google Java Style | JUnit 5 |
| `pep8_python` | Python | PEP 8 | pytest / unittest |

## 未指定预设时

默认使用 `ucb61b_java` 的规范作为 CodeHelper 的通用默认值（详见 `spec/stylecheck.md`）。如果检测到 Python 项目则使用 PEP 8 标准。

## 自定义

在 `spec/presets/custom/` 下创建你自己的 preset.md，然后在 requirements 中引用 `preset: custom`。
