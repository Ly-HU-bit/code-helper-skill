#描述
这是一份关于如何为code生成/增加tests的说明

#要求
如果用户input中提供了doctest，优先以它作为蓝本，除非用户给出的test有错误，否则不要删除其doctest
Standard/Deep 新添的测试应该考虑非法输入和各类 edge case；Deep 模式要求
每个公共/非简单功能函数至少有相应测试。Quick 模式只为本次修复增加必要测试。
在用户给出的doctest有错误情况下，在output中说明文件中作为bug的一部分指出
Quick 模式只运行现有测试；仅在复现本次修复所必需时新增最小测试。
Standard 模式为变更或高风险公共行为补充边界测试。
只有 Deep 模式或用户显式要求可视化时，才为链表、BFS 等抽象数据结构生成
visual debugger，并存放在 `output/<task>/tools/`，不得写入公共 `src/`。
对于新增的测试case，在test、output.doc中给出说明——如：检查的可能的错误点

#执行检查清单
进行test审查时，逐项检查以下内容：

##测试覆盖
- [ ] Deep 模式下，每个public/非简单函数至少有一个对应测试
- [ ] 测试了正常输入（happy path）
- [ ] 测试了边界输入（空列表、单元素、最大值、最小值、零值）
- [ ] 测试了非法输入（null、越界、类型错误）——如果适用
- [ ] 测试了合并/聚合场景（如2048的tile合并规则）
- [ ] 测试了多步操作序列（不仅仅是单步）

##测试质量
- [ ] 用户提供的测试用例未被删除（除非其本身有错误）
- [ ] 测试用例包含清晰的断言消息（assert message）
- [ ] 每个测试只测一件事（单一职责）
- [ ] 测试用例不依赖执行顺序（相互独立）

##测试框架
- [ ] 识别项目使用的测试框架（JUnit 5, pytest, unittest等）
- [ ] 新增测试使用与项目一致的框架

##可视化调试器（仅 Deep/显式请求）
- [ ] 如果可视化能显著帮助理解链表/BFS/树等结构 → 已创建visual debugger于output/<task>/tools/
- [ ] visual debugger使用tkinter或等效GUI库
- [ ] visual debugger能逐步展示数据结构状态变化
