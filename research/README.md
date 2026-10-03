# 科研任务总览

> 论文列表 + 复现进度 + 研究想法总览
>
> **研究方向（2026-10 起）：知识增强的多 Agent 灾害态势推理与辅助决策**
> 学习路线见：[learning-roadmap.md](learning-roadmap.md)

## 论文列表

### 新方向：多 Agent / 知识增强 / 灾害应急决策（重点）

| 序号 | 论文标题 | 年份 | 会议/期刊 | 链接 | 笔记 | 复现 |
|------|----------|------|-----------|------|------|------|
| 03 | Harnessing Large Language Models for Disaster Management: A Survey（LLM灾害管理综述） | 2025 | arXiv 综述 | https://arxiv.org/abs/2501.06932 | ⬜ | — |
| 04 | A RAG-Based Multi-Agent LLM System for Natural Hazard Resilience and Adaptation（WildfireGPT） | 2024 | arXiv（自然灾害RAG多Agent） | https://arxiv.org/abs/2402.07877 | ⬜ | 候选 |
| 05 | Enhancing Emergency Decision-making with Knowledge Graphs and Large Language Models（E-KELL） | 2024 | Int. J. Disaster Risk Reduction（一区） | https://arxiv.org/abs/2311.08732 | ⬜ | 候选 |
| 06 | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks（RAG 开山之作） | 2020 | NeurIPS 2020 | https://arxiv.org/abs/2005.11401 | ⬜ | ⬜ |
| 07 | ReAct: Synergizing Reasoning and Acting in Language Models | 2022 | ICLR 2023 | https://arxiv.org/abs/2210.03629 | ⬜ | ⬜ |
| 08 | AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation | 2023 | arXiv（COLM 2024） | https://arxiv.org/abs/2308.08155 | ⬜ | ⬜ |

### 前期方向：深度学习基础（已完成笔记，保留）

| 序号 | 论文标题 | 年份 | 会议/期刊 | 链接 | 笔记 | 复现 |
|------|----------|------|-----------|------|------|------|
| 01 | Deep Residual Learning for Image Recognition (ResNet) | 2015 | CVPR | https://arxiv.org/abs/1512.03385 | ✅ | ⬜ |
| 02 | U-Net: Convolutional Networks for Biomedical Image Segmentation | 2015 | MICCAI | https://arxiv.org/abs/1505.04597 | ✅ | ⬜ |

### 建议阅读顺序

1. **03 综述**：先建立领域全局地图（不求全懂，知道大家都在做什么）
2. **07 ReAct**：理解单个 Agent 怎么"思考+行动"（较短，适合入门）
3. **06 RAG**：理解知识增强的核心技术
4. **08 AutoGen**：理解多 Agent 怎么协作
5. **04 WildfireGPT**：方向最贴合的实战系统
6. **05 E-KELL**：一区期刊，知识图谱+应急决策，做复现的重点候选

## 复现进度

| 序号 | 论文 | 环境 | 状态 | 备注 |
|------|------|------|------|------|
| 04 | WildfireGPT | 待定 | ⬜ | RAG+多Agent，需准备野火领域文档 |
| 05 | E-KELL | 待定 | ⬜ | KG+LLM 应急决策，中文预案数据 |

## 研究想法（ideas/）

| 序号 | 标题 | 拟投会议/期刊 | 状态 |
|------|------|----------------|------|
| 01 | (待填) | | ⬜ |

## 目录说明

- `learning-roadmap.md` 0基础学习路线（5个阶段）
- `paper-notes/`  每篇论文的阅读笔记，文件名格式 `03-论文简称.md`，模板见 `_template.md`
- `papers/`        论文 PDF（01～08 已下载）
- `reproduction/` 论文复现，每篇一个子目录，含 README + 代码 + results/
- `ideas/`         自己的研究想法，每个想法一个文件
