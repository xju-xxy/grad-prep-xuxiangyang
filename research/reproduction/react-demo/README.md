# ReAct 复现笔记

> 复现论文：ReAct: Synergizing Reasoning and Acting in Language Models（ICLR 2023）
> 使用模型：智谱 GLM-5.3-Flash（API 方式，不依赖本地显卡）
> 复现时间：2026年10月

---

## 这个项目做了什么

用大模型接口从零写了一个"会边想边查"的问答 Agent。
它拿到问题之后不会直接瞎答，而是自己决定什么时候该上网搜、什么时候该用计算器，
每一步都先写一句"思考"，再调用工具，看到工具返回的结果之后再决定下一步，最后给出答案。

和原论文的差别：原论文用谷歌的 PaLM + 维基百科 API，我这里换成了智谱的 GLM 接口和智谱联网搜索，
另外自己加了一个 Calculate 计算器工具。核心的 Thought-Action-Observation 循环是一样的。

## 怎么运行

```bash
# 第一次使用：创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 在 .env 文件里填上智谱 API Key（格式：ZHIPUAI_API_KEY=你的key）

# 运行默认示例
.venv\Scripts\python.exe react_agent.py

# 带自己的问题运行
.venv\Scripts\python.exe react_agent.py "你想问的问题"
```

## 文件说明

```
react-demo/
├── react_agent.py     # 主程序：ReAct 循环在这里
├── prompt.py          # 系统提示词（教模型怎么按格式输出）
├── tools.py           # 两个工具：search 联网搜索、calculate 计算器
├── test_tools.py      # 单独测试工具能不能用（开发时用的）
├── test_search.py     # 单独测试搜索接口返回什么（开发时用的）
├── hello_glm.py       # 第一个 hello world，验证 API Key 和网络通不通
├── requirements.txt   # 依赖清单
└── .env               # 存放 API Key（已被 .gitignore 忽略，不会提交）
```

## 核心思路（用自己的话记下来）

大模型本身不会上网，也不擅长算数，它只会生成文字。
我的做法是在提示词里跟它约定一个"暗号"格式：

```
Thought 1: 这里写思考过程
Action 1: Search[关键词]
```

程序用正则表达式把 `Search[关键词]` 这段从模型输出里抠出来，真正去执行搜索，
再把结果以 `Observation 1: ...` 的形式拼回对话，让模型看结果继续想下一步。
循环到模型输出 `Finish[答案]` 为止。
我设了最多跑 6 轮，防止模型一直不结束白白烧 token。

这个机制就是论文里说的"reasoning and acting interleaved"：
思考帮模型调整计划，行动帮模型从外部拿真实信息。

## 踩过的最大的坑：模型会假装调用工具

第一次跑的时候我差点以为一次成功了，白高兴一场。模型在一条回复里把"搜索→观察→计算→观察→答案"
整条流程全自己写完了，连本该由程序返回的 Observation 都是它编的。
当时程序里的搜索和计算器其实一次都没执行（没有打印"程序执行工具"那行字），
答案只是碰巧对了。这就是论文里说的幻觉问题——这次碰巧对不代表下次还对。

后来想通了原因：我给的 few-shot 示范把整条轨迹写在了一起，模型有样学样，把观察结果也自己补了。

修的办法用了两层：
1. 提示词里加纪律：每轮只能输出一个 Thought + 一个 Action，写完 Action 必须停笔；
   Observation 永远由系统提供，不许自己编。
2. 代码里加保险：只认本轮第一个 Action，第一个 Action 之后模型私自写的内容一律截断，
   强制它停下来等真实的工具结果。

教训：验证 Agent 不能只看最终答案对不对，必须盯中间过程，确认工具是真被调用了。

## 测试记录

- 问"雅安地震哪年？到2026多少周年？" → 模型先 Search 再 Calculate，答 2013 年、13 周年。对。
- 问"汶川、唐山地震分别哪年？相隔多少年？" → Search 两次 + Calculate 一次，答 08 年和 76 年、相隔 32 年。对。
- 问"水的沸点是多少？" → 明明可以直接答的常识，它还是搜了一遍。答案对，但多此一举。

第三个问题暴露了一个不足：模型有点工具依赖，常识题也要搜一遍。
可能是我的提示词里"事实性问题必须查证"写得太死了。
后面想加一条规则：很有把握的常识可以直接 Finish。这算是准确率和搜索成本之间的权衡。

## 和原论文比还有哪些没做

- 论文在 HotpotQA、Fever 数据集上做了大规模定量评测，我只测了几个例子
- 论文还做了 ReAct 和 CoT（纯推理）、Act-only（纯行动）的对照实验，我没做
- 论文里 ALFWorld、WebShop 那种需要连续多步操作的环境没接

## 和我的研究方向的关系

我方向是知识增强的多 Agent 灾害态势推理与辅助决策，这个是打地基的一步：
- "先查事实再推理"正是知识增强/检索的雏形
- 单个 Agent 会边想边用工具之后，下一步（AutoGen）就是把多个这样的 Agent 拼起来分工协作，
  对应我方向的"多 Agent"
- 设想：把 Search 换成灾情数据库查询，Calculate 换成灾情评估模型，
  就是一个灾害态势推理 Agent 的骨架

## 下一步计划

1. 复现 AutoGen，做多 Agent 协作（导师催的方向就是这个）
2. 顺手把上面说的"常识题乱搜"的问题改掉
3. 有余力的话给 Agent 加一个灾害信息专用工具试试