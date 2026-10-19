// 四个 Agent 的编排与推演引擎。
// 不用后端、不用 API Key，全部在这里按知识库 + 关键词做确定性推演，
// 同样的输入每次结果都一样，方便演示和复现。

import { lookup, splitItems } from './knowledgeBase'
import type {
  AgentMessage,
  AgentName,
  AnalysisResult,
  InputPayload,
  KbEntry,
  KbField,
  Metric,
  ReportSections,
  RiskLevel,
  Severity,
} from './types'

// 每个 Agent 的展示信息：配色 + 图标名（图标在组件里按名字取）
export const AGENT_META: Record<
  AgentName,
  { role: string; tag: string; accent: string; soft: string; ring: string }
> = {
  情报官: {
    role: '情报官',
    tag: '要素提取',
    accent: '#22d3ee',
    soft: 'rgba(34,211,238,0.14)',
    ring: 'rgba(34,211,238,0.55)',
  },
  研判官: {
    role: '研判官',
    tag: '态势研判',
    accent: '#818cf8',
    soft: 'rgba(129,140,248,0.14)',
    ring: 'rgba(129,140,248,0.55)',
  },
  决策官: {
    role: '决策官',
    tag: '行动建议',
    accent: '#34d399',
    soft: 'rgba(52,211,153,0.14)',
    ring: 'rgba(52,211,153,0.55)',
  },
  审核官: {
    role: '审核官',
    tag: '不确定性审核',
    accent: '#fbbf24',
    soft: 'rgba(251,191,36,0.14)',
    ring: 'rgba(251,191,36,0.55)',
  },
}

export const AGENT_ORDER: AgentName[] = ['情报官', '研判官', '决策官', '审核官']

// 严重程度对应的基础分
const SEVERITY_BASE: Record<Severity, number> = {
  轻微: 30,
  一般: 46,
  严重: 66,
  特重: 85,
}

// 用来把灾情描述「读」出紧迫感的关键词，命中越多风险分越高
const URGENCY_WORDS = [
  '伤亡',
  '死亡',
  '失联',
  '被困',
  '埋压',
  '倒塌',
  '坍塌',
  '爆炸',
  '泄漏',
  '溃坝',
  '决堤',
  '堰塞湖',
  '中毒',
  '淹没',
  '大量',
  '严重',
  '紧急',
  '特大',
  '彻夜',
  '突发',
  '失控',
]

// 五个风险维度各自的关键词表，用于从描述里算分数
const DIM_WORDS: Record<string, string[]> = {
  人员安全: ['人员', '伤亡', '死亡', '失联', '被困', '埋压', '居民', '群众', '中毒', '冻伤', '溺'],
  设施损毁: ['建筑', '房屋', '道路', '桥梁', '隧道', '管网', '电力', '设施', '堤防', '泵站', '水库'],
  交通中断: ['交通', '道路', '铁路', '公路', '机场', '航运', '停运', '封闭', '中断', '通行', '拥堵'],
  通信受阻: ['通信', '信号', '网络', '断电', '基站', '信息', '停电'],
  次生灾害: ['滑坡', '泥石流', '内涝', '堰塞湖', '火灾', '污染', '疫', '结冰', '倒灌'],
}

function countHits(text: string, words: string[]): number {
  let n = 0
  for (const w of words) {
    if (text.includes(w)) n += 1
  }
  return n
}

function clamp(v: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, Math.round(v)))
}

function riskLevelOf(score: number): RiskLevel {
  if (score >= 70) return '高'
  if (score >= 45) return '中'
  return '低'
}

function riskTone(level: RiskLevel): string {
  if (level === '高') return '规模与承灾体密度都上来了，得按重特大事件对待'
  if (level === '中') return '压力可控但底数不清，得边处置边补信息'
  return '整体在可控范围，重点是别漏掉局部风险点'
}

// 生成一段「要素提取」风格的文字，供情报官两轮发言复用
function elementLine(label: string, value: string): string {
  return `- ${label}：${value}`
}

export function analyze(input: InputPayload): AnalysisResult {
  const scene = input.scene.trim()
  const { key: kbKey, entry } = lookup(input.disasterType)

  // ---- 风险打分：严重程度打底，再用关键词命中做加成 ----
  const urgency = countHits(scene, URGENCY_WORDS)
  const riskScore = clamp(SEVERITY_BASE[input.severity] + urgency * 4)
  const riskLevel = riskLevelOf(riskScore)
  const confidence = clamp(88 - urgency * 3 - (scene.length < 30 ? 12 : 0), 40, 92)

  // ---- 五维风险：维度分从关键词命中 + 知识库危害描述里推出来 ----
  const base = SEVERITY_BASE[input.severity]
  const secondaryItems = splitItems(entry.次生灾害)
  const dims: Metric[] = [
    {
      name: '人员安全',
      value: clamp(base * 0.75 + countHits(scene, DIM_WORDS.人员安全) * 8 + (entry.主要危害.includes('人员') ? 8 : 0)),
    },
    {
      name: '设施损毁',
      value: clamp(base * 0.7 + countHits(scene, DIM_WORDS.设施损毁) * 8 + (entry.主要危害.includes('损毁') ? 7 : 0)),
    },
    {
      name: '交通中断',
      value: clamp(base * 0.6 + countHits(scene, DIM_WORDS.交通中断) * 9 + (entry.主要危害.includes('交通') ? 8 : 0)),
    },
    {
      name: '通信受阻',
      value: clamp(base * 0.55 + countHits(scene, DIM_WORDS.通信受阻) * 9 + (entry.次生灾害.includes('通信') ? 10 : 0)),
    },
    {
      name: '次生灾害',
      value: clamp(
        base * 0.6 + secondaryItems.length * 6 + countHits(scene, DIM_WORDS.次生灾害) * 7,
      ),
    },
  ]
  const byName = (name: string) => dims.find((d) => d.name === name)?.value ?? 0

  // ---- 分时段处置优先级：越靠前优先级越高，数值跟着风险分走 ----
  const timeline: Metric[] = [
    { name: '0-6h', value: clamp(riskScore + 8) },
    { name: '6-24h', value: clamp(riskScore - 6) },
    { name: '24-72h', value: clamp(riskScore - 24) },
    { name: '72h+', value: clamp(riskScore - 46) },
  ]

  // ---- 资源需求占比：从五维分派生出原始权值再归一化到 100 ----
  const rawResources = [
    { name: '救援搜救力量', w: byName('人员安全') * 0.6 + byName('设施损毁') * 0.25 + 15 },
    { name: '医疗防疫物资', w: byName('人员安全') * 0.7 + 10 },
    { name: '工程抢修机械', w: byName('设施损毁') * 0.55 + byName('交通中断') * 0.4 + 12 },
    { name: '通信电力保障', w: byName('通信受阻') * 0.6 + 8 },
    { name: '次生灾害处置', w: byName('次生灾害') * 0.7 + 10 },
  ]
  const rawTotal = rawResources.reduce((s, r) => s + r.w, 0) || 1
  const resources: Metric[] = rawResources.map((r) => ({
    name: r.name,
    value: Math.round((r.w / rawTotal) * 1000) / 10,
  }))

  // ---- 两轮八段发言 ----
  const messages: AgentMessage[] = []
  const kbRefsUsed = new Set<KbField>()

  for (const round of [1, 2] as const) {
    for (const agent of AGENT_ORDER) {
      const { content, kbRefs } = speak(agent, round, {
        input,
        scene,
        kbKey,
        entry,
        riskLevel,
        riskScore,
        confidence,
        dims,
        secondaryItems,
      })
      kbRefs.forEach((r) => kbRefsUsed.add(r))
      messages.push({ agent, round, content, kbRefs })
    }
  }

  const round1 = (agent: AgentName) =>
    messages.find((m) => m.agent === agent && m.round === 1)?.content ?? ''

  const report: ReportSections = {
    title: `${input.disasterType}灾害态势推演与决策建议报告`,
    summary: `灾种：${input.disasterType}；知识库命中：${kbKey}；风险等级：${riskLevel}（${riskScore}/100）。`,
    态势概述: round1('情报官'),
    风险研判: round1('研判官'),
    分级行动建议: round1('决策官'),
    不确定性与盲点: round1('审核官'),
  }

  return {
    id: `cs-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
    createdAt: Date.now(),
    input: { ...input, scene },
    kbKey,
    kbEntry: entry,
    riskLevel,
    riskScore,
    kbRefs: Array.from(kbRefsUsed),
    messages,
    report,
    radar: dims,
    timeline,
    resources,
    confidence,
  }
}

interface SpeakCtx {
  input: InputPayload
  scene: string
  kbKey: string
  entry: KbEntry
  riskLevel: RiskLevel
  riskScore: number
  confidence: number
  dims: Metric[]
  secondaryItems: string[]
}

// 单段发言的生成。命中知识库的字段会记进 kbRefs，界面上标「引用知识库」。
function speak(
  agent: AgentName,
  round: 1 | 2,
  ctx: SpeakCtx,
): { content: string; kbRefs: KbField[] } {
  const { input, scene, kbKey, entry, riskLevel, secondaryItems } = ctx
  const place = input.location.trim() || '事发区域'
  const when = input.timeHint.trim() || '近期'
  const topDims = [...ctx.dims].sort((a, b) => b.value - a.value).slice(0, 2)

  if (round === 1) {
    switch (agent) {
      case '情报官':
        return {
          kbRefs: ['特征', '主要危害', '监测指标'],
          content: [
            `【灾情要素提取】灾种判定为「${input.disasterType}」，知识库命中条目「${kbKey}」。`,
            elementLine('时间与地点', `${when}，${place}`),
            elementLine('灾情概述', scene),
            elementLine('类型特征', entry.特征),
            elementLine('主要危害', entry.主要危害),
            elementLine('已识别的风险维度', topDims.map((d) => `${d.name}(${d.value})`).join('、')),
            `需重点跟进的监测指标：${entry.监测指标}`,
          ].join('\n'),
        }
      case '研判官':
        return {
          kbRefs: ['主要危害', '次生灾害'],
          content: [
            `【态势研判】把描述里的线索和知识库对了一遍，主要威胁是：${entry.主要危害}`,
            `次生灾害这条不能松：${entry.次生灾害}。其中「${secondaryItems[0] ?? '次生风险'}」和当前场景关联最紧。`,
            `风险等级定为「${riskLevel}」（${ctx.riskScore}/100）。${riskTone(riskLevel)}。`,
            `最高的两个维度是 ${topDims.map((d) => `${d.name} ${d.value}`).join(' 与 ')}，资源得先往这两块压。`,
          ].join('\n'),
        }
      case '决策官':
        return {
          kbRefs: ['应对要点'],
          content: [
            `【分级行动建议】`,
            `立即行动（0-6h）：启动应急响应，先保人——疏散${place}的危险区群众，专业救援力量带装备进场，同步封闭高风险路段与作业面。`,
            `短期安排（6-24h）：围绕知识库要点铺开——${entry.应对要点}`,
            `部门协同：应急牵头、气象水利交通卫健电力各口联动作业，信息每 2 小时对齐一次，别让现场和指挥部两套数。`,
          ].join('\n'),
        }
      case '审核官':
        return {
          kbRefs: ['监测指标', '次生灾害'],
          content: [
            `【不确定性提示与盲点】这份结论建立在一段描述上，得标清楚边界。`,
            `一是缺精确底数：伤亡、失联、受损面积、生命线中断情况都还没有数据，风险等级「${riskLevel}」是初步判断。`,
            `二是次生灾害（${entry.次生灾害}）的演化依赖现场监测，${entry.监测指标}没闭环之前，研判要滚动更新。`,
            `三是建议补充受灾人口、基础设施受损清单和到场救援力量三张表。`,
          ].join('\n'),
        }
    }
  }

  // 第二轮：对上一轮的补充与交叉验证
  switch (agent) {
    case '情报官':
      return {
        kbRefs: ['监测指标'],
        content: [
          `【第二轮补充】上一轮的信息还有洞，建议立刻补三样：`,
          `1) 现场监测数据，重点是 ${entry.监测指标}；`,
          `2) 人口分布与流动情况，尤其是${place}的常住与暂住人口；`,
          `3) 生命线工程中断与救援资源到位清单。`,
        ].join('\n'),
      }
    case '研判官':
      return {
        kbRefs: ['次生灾害'],
        content: [
          `【第二轮补充】交叉核对后维持「${riskLevel}」不变，但要把注意力放到连锁演化上。`,
          `「${secondaryItems[0] ?? '次生风险'}」一旦触发，会顺着 ${secondaryItems.join('、')} 这条链子往外扩，得提前布局阻断点。`,
        ].join('\n'),
      }
    case '决策官':
      return {
        kbRefs: ['应对要点'],
        content: [
          `【第二轮补充】在前期措施之外补三件事：`,
          `对口支援与医疗救治提前进场；对次生灾害风险点安排专人盯守、专人报告；`,
          `对外信息发布统一口径，别让谣言先跑在前面。`,
        ].join('\n'),
      }
    case '审核官':
      return {
        kbRefs: ['监测指标'],
        content: [
          `【第二轮补充】仍有盲点没闭合：受灾范围边界、交通阻断程度、物资缺口这三块数据都还飘着。`,
          `建议把现场信息更新频率压到 6 小时一轮，每轮复核一次风险等级，别让结论跑在事实前面。当前置信度约 ${ctx.confidence}%。`,
        ].join('\n'),
      }
    default:
      return { kbRefs: [], content: '' }
  }
}
