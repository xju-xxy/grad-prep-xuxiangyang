# 四维坐标对比表

> 用综述（arXiv:2402.01680）的四维框架给 12 个多智能体系统打的标签（GLM-4-Flash，温度 0.1）。标签是模型输出按 schema 归一化后的结果，原始输出和判定依据见 predictions.json。

| 系统 | 来源 | 环境接口 | 人设 | 通信范式 | 通信结构 | 反馈来源 | 能力机制 | 多模态空白 | 幻觉级联 | 群体优化缺失 | 缺应急benchmark |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MetaGPT | 综述点名 | None | Pre-defined | 合作 | 共享消息池 | 无 |  | × | × | × | × |
| ChatDev | 综述点名 | Sandbox | Pre-defined | 合作 | 分层 | 其他Agent/人类 | 记忆机制 | × | × | × | × |
| CAMEL | 综述点名 | None | Model-Generated | 合作 | 去中心化 | 其他Agent | 记忆机制 | × | × | × | × |
| AutoGen | 综述点名 | None | Pre-defined | 合作/辩论 | 中心化/去中心化 | 其他Agent/人类 | 记忆机制 | × | × | × | × |
| 多智能体辩论（Du et al.） | 综述点名 | None | Model-Generated | 辩论 | 去中心化 | 其他Agent | 记忆机制 | × | × | × | × |
| ChatEval | 综述点名 | None | Pre-defined | 辩论 | 去中心化 | 其他Agent |  | × | × | × | × |
| 狼人杀（Werewolf） | 综述点名 | Sandbox | Pre-defined | 竞争 | 中心化 | 其他Agent/人类 | 记忆机制 | × | × | × | × |
| 阿瓦隆（Avalon） | 综述点名 | None | Pre-defined | 竞争 | 去中心化 | 其他Agent/人类 | 记忆机制 | × | × | × | × |
| RoCo | 综述点名 | Physical | Pre-defined | 合作 | 去中心化 | 环境/其他Agent | 记忆机制 | √ | × | × | × |
| 虚拟政府应急响应（Xiao et al. 2023） | 综述点名 | Sandbox | Pre-defined | 合作 | 中心化 | 环境/其他Agent | 记忆机制 | × | × | × | × |
| autogen-demo（我自己的复现） | 自己的系统 | Sandbox | Pre-defined | 合作 | 分层/共享消息池 | 环境/其他Agent/人类 | 记忆机制 | × | × | × | × |
| crisis-sight（我自己的系统） | 自己的系统 | Sandbox | Pre-defined | 合作 | 分层 | 环境/其他Agent/人类 | 记忆机制 | × | × | × | × |
