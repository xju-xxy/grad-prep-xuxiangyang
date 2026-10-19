# CrisisBench 评测可视化平台

## 这平台干嘛的

我做了个实验基准 CrisisBench，用来测多智能体灾害态势推理到底行不行：36 个中文灾害场景，
每个场景拆成「事实层 / 推理层 / 决策层」三层给分，跑若干组配置（multi 多智能体、single 单
模型直出、去掉审核官的消融、接 Verifier 的对照、glm-4-flash 与 glm-4-plus 两个模型档位），
最后用三裁判多数票统一口径打分。

实验跑完，结果全塞在一堆 json 和 markdown 里，对着看太累。于是写了这个前端看板，把结果摊
成能点的图表：想看哪个配置、哪一层、哪个场景、花了多少 token，直接切 Tab 就行。它不是我
现编的数字，所有数都是从仓库里那几份结果文件现算的。

## 数据从哪来

页面上每个数字都能在这些文件里找到出处（运行时由浏览器 fetch 加载）：

| 文件 | 用在哪 |
|---|---|
| `research/crisis-bench/results/v0.4-analysis.json` | 主力：每个配置的逐场景三层得分矩阵、配对检验、kappa、错误类型、Verifier 检出 |
| `research/crisis-bench/results/cost-summary.json` | 成本页的调用次数 / token / 耗时 |
| `research/crisis-bench/results/adjudication.json` | 裁判可靠性页的逐条裁判打分与人工终裁 |
| `research/crisis-bench/results/RESULTS-v0.4.md` | 核对用（人工排版的分层得分表） |
| `research/crisis-bench/scenarios/scenarios.json` | 场景浏览页的三层要点、情报与资源 |
| `research/crisis-bench/figures/*.png` | 图表库页的原图 |

有个小脚本 `scripts/prepare-data.mjs` 负责把这些文件裁剪、复制到 `public/`：主体 json 原样
搬，scenarios.json 太大（含规则打分用的 match 关键词表），只留页面要用的字段；五张 png 复制
到 `public/figures/`。改完源文件重跑一次这个脚本就行。

至于「三层总分」「各配置总分」这种聚合值，是页面里按 `命中要点 / 总要点` 现算的，不写死。

## 怎么跑

```powershell
# 进目录
cd engineering\src\crisisbench-lab

# 装依赖（国内网络加镜像；npm 缓存目录如果有权限问题就手动指一个可写目录）
npm install --registry=https://registry.npmmirror.com

# 起开发服务，默认 http://localhost:5174/
npm run dev

# 打包
npm run build
```

dev 端口在 `vite.config.ts` 里固定成 5174，是因为仓库里另一个前端（crisis-sight）占了别的
口，避免撞车。

## 技术栈

- Vite + React 18 + TypeScript
- Tailwind CSS v3（自己手写组件，没引 UI 库）
- Recharts 画柱状图 / 雷达图
- Framer Motion 做 Tab 切换和卡片动效
- lucide-react 出图标
- 纯前端，不需要后端和 API Key

## 目录结构

```
crisisbench-lab/
├── index.html
├── vite.config.ts          端口 5174
├── tailwind.config.js      主题色、字体、阴影
├── scripts/
│   └── prepare-data.mjs    从 research 裁剪数据到 public
├── public/
│   ├── data/               analysis.json / cost-summary.json / adjudication.json / scenarios.json
│   └── figures/            五张实验图
└── src/
    ├── App.tsx             侧边导航 + 数据加载 + Tab 切换
    ├── types.ts            结果文件的类型定义
    ├── lib/
    │   ├── data.ts         数据加载 + 派生指标（分层均值、场景得分、一致率…）
    │   ├── theme.ts        全站配置配色（每个配置一套固定色）
    │   └── format.ts       百分比 / 百分点 / p 值格式化
    ├── components/ui.tsx   卡片、标题、Chip、骨架屏等基础件
    └── views/              七个页面区块
```

页面分了七个 Tab：总览、分层得分、雷达对比、场景浏览、裁判可靠性、成本、图表库。

## 设计取舍

1. **不引 UI 组件库**。这看板就几张表和几个图，自己用 Tailwind 拼更省心，也不会带进来一堆用
   不上的样式。配色定死在 `lib/theme.ts`，每个配置一个色，图表、图例、卡片全站统一，不出现
   Recharts 默认那套花花绿绿的色。
2. **聚合值现算，不预存**。分层均分、总分、类别得分都从前端从 matrix 累加，好处是源文件一改，
   刷新就对上，不会出现「json 更新了、看板里的汇总还是旧的」。
3. **浅色为主**。底用 `#F8FAFC`，白卡片 + 细边框 + 轻阴影，强调色是靛蓝 `#4F46E5`，辅助青
   绿 / 琥珀 / 品红用来区分不同配置。学术看板该有的克制，但卡片 hover 会微抬，Tab 切换有过
   渡，不至于死板。
4. **数字可追溯**。结论旁边都标了「来源：xxx.json」，省得别人（包括我自己）回头怀疑数字是
   不是编的。
5. **结论照实写**。执行下来 multi 反而比 single 低、去掉审核官反而更高、kappa 贴着 0 走，这
   些都不好看，但页面上照原样展出，不粉饰。

## 已知不足

- 只有 36 个场景、单个标注人（我），结论的统计效力有限，别当成定论。
- 三裁判 kappa 都很低，靠多数票凑出来的分数本身有噪声，看板只是把现状展示出来，没有解决它。
- cost-summary.json 没有金额字段，所以成本页只给了 token 和耗时，没折算成钱。
- 场景浏览页的筛选只做了灾种和类别，没做按层要点文本搜索。
- 图表用的是 Recharts，交互能力有限（比如没做框选、下钻），数据量大时会有点吃力。
