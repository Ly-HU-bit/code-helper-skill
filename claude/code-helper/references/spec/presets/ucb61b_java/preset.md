# UCB CS 61B Java Preset

## 适用场景
UC Berkeley CS 61B (Data Structures) 课程作业

## 风格规范
- 变量/方法命名: camelCase
- 类命名: PascalCase
- 常量命名: UPPER_SNAKE_CASE
- 循环临时变量可使用短名 (i, j, x, y)
- 缩进: 4空格
- 大括号: K&R风格 (不换行)
- 操作符: 两侧空格
- 参考: https://sp24.datastructur.es/resources/guides/style/

## 文档要求
- @param: 说明每个输入参数
- @return: 说明返回值
- 每个非getter/setter方法需文档

## 测试框架
- JUnit 5 (org.junit.jupiter.api)
- Google Truth assertions (com.google.common.truth)
- 超时: @Timeout(60)

## 复杂度要求
- 优先优化时间复杂度
- n ≤ 100 时 O(n²) 可接受
- 不得改变主框架架构

## 额外规则
- 调试: 保留原代码（注释掉），勿删除
- 测试: 不删除用户提供的测试用例
- import可解决问题 → 在doc中说明即可，勿改动
