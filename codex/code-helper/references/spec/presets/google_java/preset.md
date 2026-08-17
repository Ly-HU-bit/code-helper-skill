# Google Java Style Guide Preset

## 适用场景
遵循 Google Java Style Guide 的项目

## 风格规范
- 变量/方法命名: lowerCamelCase
- 类命名: UpperCamelCase
- 常量命名: CONSTANT_CASE
- 缩进: 2空格 (Google标准)
- 大括号: K&R风格
- 列宽限制: 100字符
- 参考: https://google.github.io/styleguide/javaguide.html

## 文档要求
- Javadoc for public classes and methods
- @param for each parameter
- @return for non-void return values
- @throws for checked exceptions

## 测试框架
- JUnit 5 (org.junit.jupiter.api)
- 无特定assertion库偏好

## 复杂度要求
- 不强制复杂度限制
- 以可读性为优先

## 额外规则
- import顺序: static imports → third-party → java.* → javax.*
- 禁止wildcard imports (import java.util.*)
- 每行一条语句
