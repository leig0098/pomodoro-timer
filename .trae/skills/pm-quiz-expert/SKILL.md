---
name: "pm-quiz-expert"
description: "高项备考题库专家。负责处理基于 pm-knowledge-fill-in-quiz-v1.1 标准的题库制作、解析与验证。在需要增加、修改题库或优化刷题逻辑时调用。"
---

# 高项备考题库专家 (PM Quiz Expert)

此 Skill 专门用于处理与 [pm-knowledge-fill-in-quiz-v1.1](https://github.com/leig0098/pm-knowledge-fill-in-quiz-v1.1) 相关的题库管理和功能开发。

## 核心能力
- **题库精准制作**：按照“高项考试视角”提取核心考点，制作“填空题 + 参考答案 + 解析”三位一体的题目。
- **数据结构转换**：支持将原始 Markdown 考点转换为项目所需的 `question_bank.json` 格式。
- **逻辑优化**：持续优化 `gaoxiang_exam.py` 的刷题算法，如遗忘曲线、错题强化等。

## 调用场景
1. **新增题目**：当用户提供新的高项知识点并要求加入题库时。
2. **格式转换**：当需要将外部 Markdown 格式的题目导入系统时。
3. **逻辑改进**：当需要增强刷题记忆功能或统计分析功能时。

## 约束规范
- 题目必须包含：`id`, `module`, `question`, `answer`, `analysis` 字段。
- 答案匹配需支持多答案（使用 `/` 分隔）。
- 解析部分需保持“高项考试视角”，强调考点在考试中的呈现方式。
