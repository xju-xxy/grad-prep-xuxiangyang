# 工程项目说明

> 项目介绍 + 功能说明 + 运行截图

## 项目名

CrisisSight（危机慧眼）· 知识增强的多 Agent 灾害态势推演系统

## 项目简介

把自己科研方向（知识增强的多 Agent 灾害态势推理与辅助决策）落成一个能跑的 Web 系统：
用户输入一段灾情描述，四个智能体（情报官 → 研判官 → 决策官 → 审核官）按顺序各发言两轮，
发言时强制注入内置灾害知识库的条目，最后汇总成四段式决策建议报告。
不用任何外部 API Key 也能跑（demo 模式，模板规则确定性输出），配了 DeepSeek Key 就切到 LLM 模式真实推理。

## 功能列表

- [x] 灾情描述 + 灾害类型输入（10 类灾害：地震/洪涝/台风/山火/滑坡/泥石流/化工泄漏/城市内涝/寒潮/其他）
- [x] 四 Agent 两轮编排：情报官（提取要素）→ 研判官（态势研判+风险等级）→ 决策官（分级行动建议）→ 审核官（不确定性提示与盲点）
- [x] 内置灾害知识库增强：每个 Agent 的发言都注入命中条目的特征/危害/应对要点/次生灾害/监测指标
- [x] 双模式运行：demo 模式免 Key 离线可跑；LLM 模式直连 DeepSeek API（失败自动回退模板，保证不崩）
- [x] 前端展示：决策建议报告 + 各 Agent 两轮完整发言 + 知识库命中来源折叠面板
- [x] 示例场景一键填充（地震/洪涝/山火/化工泄漏 4 个预置场景，选了直接填好）
- [x] 推演流程时间轴（8 个节点，点击可跳到对应发言）+ 风险等级徽章（高/中/低配色）+ 角色卡片色条区分
- [x] 报告导出：一键复制报告 / 下载 Markdown 文件
- [x] 推演记录：本地保存最近 5 次推演（localStorage），点击可回看

## 技术栈

- 语言：Python
- 框架：Flask（Web 后端 + 静态页面托管）
- 前端：原生 HTML / CSS / JavaScript（无框架，应急指挥大屏风格界面）
- 模型接口：requests 直调 DeepSeek chat/completions（optional，仅 LLM 模式需要）
- 数据库：无（知识库存内存字典，推演记录存浏览器 localStorage）

## 运行方式

```bash
# 1. 进到项目目录
cd engineering/src/crisis-sight

# 2. 装依赖（只需要 flask）
pip install -r requirements.txt

# 3. 启动（没配 Key 自动进入 demo 模式）
python app.py

# 4. 浏览器打开
# http://127.0.0.1:5000/
```

想用 LLM 模式（真实大模型推理），启动前设好环境变量：

```bash
# PowerShell
$env:DEEPSEEK_API_KEY = "sk-你的key"
```

不设 Key 也完全能跑，demo 模式的发言是知识库 + 模板规则拼出来的，用来演示流程、验证前后端没问题。

## 项目结构

```
crisis-sight/
├── app.py             Flask 主程序（/ 首页 + /api/analyze 分析接口）
├── agents.py          四 Agent 两轮编排（demo/llm 双路径）
├── kb.py              10 类灾害中文知识库 + 别名映射 + 命中查找
├── config.py          读环境变量 DEEPSEEK_API_KEY
├── requirements.txt   只依赖 flask
├── README.md          本项目更细的说明
└── static/            前端三件套（index.html / style.css / app.js）
```

## 设计思路（为什么这么做）

1. **为啥是四 Agent 流水线**：情报、研判、决策、审核正好对应态势推理的四个环节，最后加一个"审核官"是因为上个月读的论文里反复提到 LLM 会瞎编——让一个角色专门挑盲点，比让一个模型一口气给结论更稳。
2. **知识库为什么要强行注入**：demo 模式出的是确定性内容，LLM 模式每条发言都带知识库条目，这就是课题里"知识增强"的落地方式——先锚定事实再推理，降低幻觉。
3. **为什么搞 demo 模式**：评审/自己随时想跑都能跑，不烧钱；想验证真实推理效果再开 Key。

## 运行截图

| 首页 | 推演结果（四个 Agent × 两轮发言） |
|------|------|
| ![首页](screenshots/home.png) | ![推演结果](screenshots/result-full.png) |

结果页底部（知识库命中来源）见 [screenshots/result-bottom.png](screenshots/result-bottom.png)。

详细源码见 `src/crisis-sight/`，接口和数据结构的说明在 `src/crisis-sight/README.md`。

## 新版：CrisisSight Pro（src/crisis-sight-pro/）

Flask 那版能跑，但界面是手搓的 CSS，动画和图表都比较糙。于是我又用 React + TypeScript 重写了一版，推演逻辑和灾害知识库从 Python 整体搬到了前端，不用起后端、不用配 Key，打开页面就能推演。

技术栈换成了 Vite 5 + React 18 + TypeScript + Tailwind CSS 3，动画用 Framer Motion，图表用 Recharts，图标统一走 lucide-react。界面走应急指挥大屏的路子：深蓝黑底 + 青蓝强调色 + 玻璃拟态面板。

业务上比旧版多了几样：推演过程做成了逐段浮现的时间轴（当前 Agent 高亮、已完成折叠），结果面板加了风险维度雷达图、分时段处置优先级柱状图、资源需求占比饼图，这些数据都是从推演结果里现算的，不是写死的。其余功能（四智能体两轮发言、知识库命中来源、报告复制/下载、localStorage 记录）跟旧版一致。

```bash
cd src/crisis-sight-pro
npm install
npm run dev     # 打开 http://localhost:5173
```

更细的说明（目录结构、设计取舍、已知不足）见 `src/crisis-sight-pro/README.md`。

## CrisisBench 评测可视化平台

第二个系统，`src/crisisbench-lab/`。把我论文项目 CrisisBench（多智能体灾害态势推理评测基
准，36 个场景 × 三层要点）的真实实验结果做成可交互看板：总览、分层得分对比、雷达对比、场景
浏览、裁判可靠性、成本、图表库七个 Tab。数字全部从 `research/crisis-bench/results/` 下的结
果文件现算，页面上都标了出处，没有编造。

技术栈是 Vite + React 18 + TypeScript + Tailwind v3 + Recharts + Framer Motion，纯前端，
不需要后端。跑法：`cd engineering/src/crisisbench-lab` 然后 `npm install`、`npm run dev`
（开发端口 5174）。细节见 `src/crisisbench-lab/README.md`。