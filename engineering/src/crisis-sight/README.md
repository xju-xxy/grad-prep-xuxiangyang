# 危机慧眼 · Crisis Sight

知识增强的多Agent灾害态势推理与辅助决策系统（研究生考核项目工程实践）。

## 项目介绍

本系统演示「多智能体 + 知识库增强」在灾情研判中的应用。用户输入灾情描述并选择灾害类型后，后端编排 4 个 Agent（情报官 → 研判官 → 决策官 → 审核官）依次发言两轮，各自结合内置灾害知识库完成灾情要素提取、态势研判、分级行动建议与不确定性提示，最终生成一份四段式决策建议报告。

## 功能

- 首页表单：灾情描述文本框 + 灾害类型下拉（地震/洪涝/台风/山火/滑坡/泥石流/化工泄漏/城市内涝/寒潮/其他，默认「地震」）+ 推演按钮
- 4 个 Agent 两轮顺序发言，各司其职
- 内置 8 类以上灾害中文知识库，每类含特征、主要危害、应对要点、次生灾害、监测指标
- 双运行模式：demo 模式（默认，无 API Key，确定性可跑）与 LLM 模式（设置环境变量 DEEPSEEK_API_KEY 后走 DeepSeek 接口）
- 结果页展示四段式报告、每个 Agent 的完整发言、知识库命中条目来源

## 技术栈

- Python 3.14 + Flask
- 原生 HTML / CSS / JavaScript（无构建工具）
- LLM 模式使用 requests 直接调用 DeepSeek（OpenAI 兼容）接口

## 运行方式

```bash
pip install -r requirements.txt
python app.py
```

浏览器访问 <http://127.0.0.1:5000>

## LLM 模式配置

默认未设置 API Key 时进入 demo 模式，Agent 发言基于知识库 + 模板规则生成，开箱即用。

如需启用 LLM 模式，设置环境变量后重启服务：

- Windows PowerShell：`$env:DEEPSEEK_API_KEY="你的key"`
- Linux/macOS：`export DEEPSEEK_API_KEY="你的key"`

LLM 模式下，系统将知识库命中内容注入提示词，调用 `https://api.deepseek.com/chat/completions`（`model="deepseek-chat"`）；未命中知识库时提示通用应急常识。接口调用失败会自动回退到模板规则，保证系统可用。请勿将真实 Key 硬编码到代码中。

## 系统架构

```
浏览器 (static/index.html + style.css + app.js)
        │  POST /api/analyze   GET /
        ▼
   app.py            Flask 路由层
        │
        ▼
   agents.py         4 个 Agent 编排（demo / llm 两条路径）
        │                       │
        ├── kb.py      内置灾害知识库
        └── config.py  读取环境变量 (DEEPSEEK_API_KEY)
```

## 目录结构

```
crisis-sight/
├── app.py            # Flask 主程序 + 路由
├── agents.py         # 4 个 Agent 编排逻辑
├── kb.py             # 灾害知识库
├── config.py         # 环境变量读取
├── requirements.txt  # 依赖（仅 flask）
├── README.md
└── static/           # index.html、style.css、app.js
```