#描述
这是style-checking的默认要求文档，当用户没有在input中给出自己的style要求时，按此文档要求执行

#style要求
变量命名：除循环中临时变量外，其余变量名应与其实际含义挂钩，并采用驼峰命名法；特殊语法规则（class、macro...）按照相关惯例命名
函数文档：除简单函数外，一切函数都应该有如下signature：@param：说明输入变量含义；@return：说明返回值；以及关于函数功能的介绍
函数过于冗长，不能做到一个函数只做一件事的，拆出helper-method
全文缩进、括号匹配风格应该保持一致：
具体以此为蓝本：https://sp24.datastructur.es/resources/guides/style/
在output的doc中，对如下style修改做出说明：更改函数体结构的、修改变量名称的
Quick/Standard 报告只说明有意义的结构或命名修改并列出涉及位置，完整对照以
`changes.patch` 为准。Deep 模式可按类型合并展示局部 diff。

#执行检查清单
进行style check时，逐项检查以下内容：

##命名
- [ ] 变量名使用camelCase（非snake_case），且与实际含义挂钩
- [ ] 类名使用PascalCase
- [ ] 常量使用UPPER_SNAKE_CASE
- [ ] 循环临时变量（i, j, x, y）可使用短名称

##文档
- [ ] 每个非简单函数（>5行代码）有JavaDoc/Python docstring
- [ ] 文档包含@param（输入参数说明）
- [ ] 文档包含@return（返回值说明）
- [ ] 文档包含一句功能概述

##结构
- [ ] 每个函数只做一件事
- [ ] 超过50行的函数已拆分helper method
- [ ] 没有重复代码块

##格式
- [ ] 全文缩进一致（4空格或1 tab，不混用）
- [ ] 大括号风格一致（Java: K&R 即不换行，或Allman 即换行，全文统一）
- [ ] 操作符两侧有空格: `a == b` 而非 `a==b`
- [ ] for循环分号后有空格: `for (int i = 0; i < n; i++)`
- [ ] 逗号后有空格: `foo(a, b)` 而非 `foo(a,b)`

##禁止项
- [ ] 无未使用的import
- [ ] 无魔法数字（magic numbers），应定义为命名常量
- [ ] 无过长行（Java≤100字符, Python≤79字符）

##文档输出
- [ ] 报告列出有意义修改的位置，changes.patch 包含完整代码对照
- [ ] 同类修改（如批量重命名）合并展示，列出所有涉及行号
- [ ] 引用了具体的规范条款作为修改依据
