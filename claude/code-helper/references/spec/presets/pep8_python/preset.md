# PEP 8 Python Preset

## 适用场景
标准Python项目，遵循PEP 8规范

## 风格规范
- 变量/函数命名: snake_case
- 类命名: PascalCase
- 常量命名: UPPER_SNAKE_CASE
- 私有成员: _leading_underscore
- 缩进: 4空格
- 列宽: 79字符 (代码), 72字符 (docstring)
- 参考: https://peps.python.org/pep-0008/

## 文档要求
- 模块级 docstring
- 类和函数 docstring
- 使用 """triple double quotes"""
- 函数文档: 简述 + Args/Returns/Raises

## 测试框架
- pytest (首选) 或 unittest
- 测试文件命名: test_*.py 或 *_test.py

## 复杂度要求
- 优先优化时间复杂度
- n ≤ 100 时 O(n²) 可接受
- 空间换时间可接受 (内存充足为前提)

## 额外规则
- import顺序: stdlib → third-party → local
- 每行一条import
- 调试: 保留原代码（注释掉），勿删除
- import可解决问题 → 在doc中说明
