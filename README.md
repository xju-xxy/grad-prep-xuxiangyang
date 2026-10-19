# grad-prep-xuxiangyang

> 个人简介 + 两项任务的进度总览

## 个人简介

- 姓名：徐向阳（xuxiangyang）
- 专业：医学工程
- 研究方向：知识增强的多 Agent 灾害态势推理与辅助决策
- 基础：正在系统学习深度学习（神经网络、PyTorch、MuJoCo 仿真）

## 任务进度总览

### 📚 科研部分（research/）

精读论文 65 篇（CCF-A 会议 25 篇、CCF-B 14 篇、中科院一区期刊 9 篇），完成笔记 12 篇、复现 12 篇：

| 笔记 | 论文 | 等级 | 复现 |
|------|------|------|------|
| 01 | ResNet（深度学习基础） | CCF-A（CVPR'16） | ✅ CIFAR-10 训练 |
| 02 | U-Net（深度学习基础） | CCF-B（MICCAI'15） | ✅ 合成分割数据 |
| 03 | LLM 灾害管理综述 | ACL 2025 Findings | ✅ 分类框架抽取工具 |
| 04 | WildfireGPT 野火分析 | arXiv'24 | ✅ 画像→规划→分析 + RAG |
| 05 | E-KELL 知识图谱应急决策 | 中科院二区（IJDRR） | ✅ |
| 07 | ReAct 推理+行动 | CCF-A（ICLR'23） | ✅ |
| 08 | AutoGen 多智能体协作 | COLM 2024 | ✅ |
| 09 | 危机推文 LLM 鲁棒性 | CCF-A（WWW'25） | ✅ |
| 21 | SSTKG 时空知识图谱 | CCF-A（WWW'24） | ✅ 影响力建模 |
| 41 | LLM 多智能体综述 | CCF-A（IJCAI'24） | ✅ 四维打标工具 |
| 62 | LogiDebrief 灾后复盘 | CCF-A（IJCAI'25） | ✅ STL 复盘质检 |
| 63 | Sim911 应急调度训练 | CCF-A（AAAI'25） | ✅ 画像仿真陪练 |

另有 DeCrisisMB 论文 PDF（EMNLP Findings'23）待读。研究想法 3 篇（见 research/ideas/）。

### 🛠 工程部分（engineering/）

三个项目：

- **CrisisSight（旧版）**：Python + Flask + 原生前端，多智能体灾情推演（情报 → 研判 → 决策 → 审核）+ 灾害知识库增强 + 双模式（demo 免 Key 可跑 / 接 DeepSeek API 真实推理）
- **CrisisSight Pro（新版）**：Vite + React + TypeScript + Tailwind + Framer Motion + Recharts，界面重做，推演流水线有动画、报告带雷达图与优先级图表；编排引擎跑在前端，免 Key 开箱即用
- **CrisisBench Lab**：Vite + React + TypeScript + Recharts，把 CrisisBench v0.4 的真实实验结果做成看板（总览 / 分层得分 / 雷达对比 / 场景浏览 / 裁判可靠性 / 成本 / 图表），7 个区块数据全部取自 `research/crisis-bench/results/`

两个前端系统各自 `npm install && npm run dev` 即可打开（端口 5173 / 5174）。

## 目录结构

```
grad-prep-xuxiangyang/
├── README.md                  本文件
├── research/                  科研任务（论文、笔记、复现、想法）
│   ├── README.md              论文列表 + 复现进度 + 研究想法总览
│   ├── paper-notes/           阅读笔记
│   ├── papers/                论文 PDF（文件名带 CCF/中科院等级）
│   ├── reproduction/          论文复现（每篇一个子目录）
│   └── ideas/                 研究想法
└── engineering/               工程实践
    ├── README.md              项目介绍
    └── src/                   项目源代码
```

详细说明见 [任务说明](../任务说明.md)。