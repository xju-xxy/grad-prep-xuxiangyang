# CrisisBench「相关工作」参考文献核实表

> 核实方式：英文/中文关键词逐条 WebSearch，并与本仓库 `paper-notes/`、`domain-review.md`、`paper-draft.md` 内已有笔记交叉比对。
> 结论速览：**20 项中无一项纯虚构**，全部能找到真实对应工作；但有 3 项需要改名/改描述（#8 VERIMAP 拼写、#10 PMC 的全称、#14 E-KELL 的内容描述），详见建议。

| 论文中称呼 | 核实结果 | 真实标题 | 出处(arXiv/ACL/DOI/会议) | 建议 |
|---|---|---|---|---|
| 1. LLM-as-a-judge / MT-Bench (Zheng et al.) | 存在 | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | arXiv:2306.05685；NeurIPS 2023 Datasets & Benchmarks | 保留，补全正式条目 |
| 2. HELM | 存在 | Holistic Evaluation of Language Models | arXiv:2211.09110；TMLR 08/2023（Liang et al.） | 保留，确定会议为 TMLR 2023 |
| 3. BIG-bench | 存在 | Beyond the Imitation Game: Quantifying and extrapolating the capabilities of language models | arXiv:2206.04615（445 作者合作） | 保留 |
| 4. AgentBench | 存在 | AgentBench: Evaluating LLMs as Agents | arXiv:2308.03688；ICLR 2024 | 保留 |
| 5. AutoGen（微软多智能体） | 存在 | AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation | arXiv:2308.08155（Wu et al.）；COLM 2024 | 保留，草案已标 COLM 2024，正确 |
| 6. ReAct (Yao et al.) | 存在 | ReAct: Synergizing Reasoning and Acting in Language Models | arXiv:2210.03629；ICLR 2023 | 保留 |
| 7. MetaAgent | 存在 | MetaAgent: Automatically Constructing Multi-Agent Systems Based on Finite State Machines | arXiv:2507.22606；ICML 2025（PMLR 267:75667-75694，Zhang/Liu/Xiao） | 保留，补全全称与 ICML 2025 |
| 8. VERIMAP | 存在（**名称需更正**） | Verification-Aware Planning for Multi-Agent Systems（框架名 **VeriMAP**，非 VERIMAP） | arXiv:2510.17109（2025-10） | 更正拼写为 VeriMAP；"每子任务可执行验证函数"描述准确 |
| 9. LEGOMem | 存在 | LEGOMem: Modular Procedural Memory for Multi-agent LLM Systems for Workflow Automation | arXiv:2510.04851（Han et al.）；收录于 25th AAMAS（按 Semantic Scholar，建议核对卷期） | 保留，补全会议卷期 |
| 10. PMC | 存在（**并非"Programmatic Memory"**） | Planning with Multi-Constraints via Collaborative Language Agents（**PMC** = Planning with Multi-Constraints） | arXiv:2405.16510；COLING 2025 (2025.coling-main.672) | 写全称为"Planning with Multi-Constraints"，标注 COLING 2025；如确要引"程序性记忆"另引 LEGOMem 或 PRO-LONG/PMCoder |
| 11. GraphRAG（微软） | 存在 | From Local to Global: A Graph RAG Approach to Query-Focused Summarization | arXiv:2404.16130（Edge et al., Microsoft Research） | 保留；草案第 15 条写"GraphRAG 综述"，如引综述需另换条目 |
| 12. CogMG | 存在 | CogMG: Collaborative Augmentation Between Large Language Model and Knowledge Graph | arXiv:2406.17231（周童/陈玉博等） | 保留，补全条目 |
| 13. RAG (Lewis et al. 2020) | 存在 | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | arXiv:2005.11401；NeurIPS 2020 | 保留，补全正式条目 |
| 14. E-KELL | 存在（**内容描述有出入**） | Enhancing emergency decision-making with knowledge graphs and large language models | arXiv:2311.08732；IJDRR 2024, Vol 113: 104804, DOI:10.1016/j.ijdrr.2024.104804（Minze Chen 等） | 保留引用，但删去"F1 59.31%→65.63%"与"历史灾害事件三元组 KGQA"描述：实际是危化品应急决策支持、专家主观评分≈9.06，未检索到该 F1 数字；"IJDRR 2023"应改为 2024 |
| 15. Sim911 | 存在 | Sim911: Towards Effective and Equitable 9-1-1 Dispatcher Training with an LLM-Enabled Simulation | arXiv:2412.16844；AAAI 2025, DOI:10.1609/aaai.v39i27.35006 | 保留（AAAI 2025 属实） |
| 16. LogiDebrief | 存在 | LogiDebrief: A Signal-Temporal Logic Based Automated Debriefing Approach with Large Language Models Integration | IJCAI 2025；arXiv:2505.03985（Zirong Chen、Meiyi Ma 等） | 保留；描述用"信号时序逻辑(STL)"更准确 |
| 17. DisasterTD | 存在（**对象描述需修正**） | DisasterTD: Disaster Toponym Disambiguation Using Multimodal LLMs and Cross-View Geolocalization | arXiv:2607.24856；IEEE TGRS（据作者主页，建议核对） | 保留，但对象是"灾害图像地名消歧/落图"，非"推特"，建议改写描述 |
| 18. RescueADI | 存在 | RescueADI: Adaptive Disaster Interpretation in Remote Sensing Images with Autonomous Agents | arXiv:2410.13384；另见 IEEE Xplore 10849780 | 保留 |
| 19. 危机推文评测 (WWW'25) | 存在 | Evaluating Robustness of LLMs on Crisis-Related Microblogs across Events, Information Types, and Linguistic Features | WWW 2025, DOI:10.1145/3696410.3714511；arXiv:2412.10413（Imran/Ofli, QCRI） | 保留，补全条目；"洪水/求助类/错别字软肋"与论文结论一致 |
| 20. 时空 KGQA | 存在（多个代表） | 代表：① SSTKG: Simple Spatio-Temporal Knowledge Graph for Interpretable and Versatile Dynamic Information Embedding；② CronKGQA: Question Answering Over Temporal Knowledge Graphs | ① WWW 2024, arXiv:2402.12132；② ACL 2021（另可引 STCQA, KBS 2025, arXiv:2402.11542） | 任选 1~2 个真实代表即可，建议 SSTKG + CronKGQA |

---

## 给论文的修改建议

1. **全部保留、无虚构项**：20 项引用全部能在 WebSearch 中找到真实对应工作，**无需删除任何一条**，也没有"纯胡编的名字"。
2. **必须更名的 1 项**：
   - **#8 VERIMAP → VeriMAP**，全称 "Verification-Aware Planning for Multi-Agent Systems"（arXiv:2510.17109）。当前拼写 "VERIMAP" 是笔误，正文"每子任务配可执行验证函数"的描述与该文完全吻合。
3. **必须改全称/纠正含义的 1 项**：
   - **#10 PMC ≠ "Programmatic Memory"**，真实全称为 "Planning with Multi-Constraints via Collaborative Language Agents"（COLING 2025, arXiv:2405.16510）。若论文确想强调"程序性记忆（procedural/programmatic memory）"，请直接引 **LEGOMem**（已在清单 #9），或补充 PRO-LONG（arXiv:2607.20064）、PMCoder（arXiv:2608.06811）这类真实记忆框架，但不要再用 "PMC" 这个歧义缩写。
4. **必须修正描述的 2 项**：
   - **#14 E-KELL**：保留引用，但 "F1 从 59.31% 提升至 65.63%" 和 "历史灾害事件三元组知识图谱问答" 与实际论文不符（实际是危化品泄漏应急决策支持，用消防/指挥专家主观评分 ≈9.06 分量化改进）；该 F1 数字未在检索证据中出现，疑似从其他论文混入，建议删去。会议写 **IJDRR 2024**（非 2023）。
   - **#17 DisasterTD**：实际是"灾害**图像**地名消歧/落图（MLLM + 跨视角地理定位）"，不是"推特地名"，建议把"推特"改为"灾害图像/社交媒体影像"。
5. **需补全正式条目的经典项**：#1 MT-Bench（NeurIPS 2023 D&B）、#2 HELM（TMLR 2023）、#4 AgentBench（ICLR 2024）、#5 AutoGen（COLM 2024，草案已标对）、#6 ReAct（ICLR 2023）、#13 RAG（NeurIPS 2020）。
6. **#7 MetaAgent、#9 LEGOMem、#12 CogMG、#15 Sim911、#16 LogiDebrief、#18 RescueADI、#19 危机推文、#20 时空 KGQA** 均已确认真实，只需把条目补全（作者/会议/卷期/DOI/arXiv）。
7. **一处额外提示**：草案第 15 条把 GraphRAG 写成"GraphRAG 综述"；如果正文要引的是"综述"而非 Edge et al. 的原论文，需要单独找一篇 GraphRAG 综述条目，否则建议直接引 Edge et al. 2024 原论文（arXiv:2404.16130）。

> 附：以上每一条"真实标题/出处"均为 WebSearch 实际返回的检索结果（arXiv/ACL/ACM/IEEE/Elsevier/PMLR），未擅自定义或补造卷期页码；标注"建议核对/待核对"处表示检索证据不足以唯一确定卷期页码，投稿前需回到原文确认。