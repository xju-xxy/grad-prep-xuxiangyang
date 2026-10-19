// 推演相关的类型定义，前后端（这里只有前端）共用的数据结构都放这儿

export type DisasterType =
  | '地震'
  | '洪涝'
  | '台风'
  | '山火'
  | '滑坡'
  | '泥石流'
  | '化工泄漏'
  | '城市内涝'
  | '寒潮'
  | '其他'

export type Severity = '轻微' | '一般' | '严重' | '特重'

export type AgentName = '情报官' | '研判官' | '决策官' | '审核官'

export type RiskLevel = '高' | '中' | '低'

// 知识库条目的五个字段，跟旧版 kb.py 保持一致
export interface KbEntry {
  特征: string
  主要危害: string
  应对要点: string
  次生灾害: string
  监测指标: string
}

// 命中知识库时记录引用了哪几个字段，方便在发言里标注来源
export type KbField = keyof KbEntry

export interface AgentMessage {
  agent: AgentName
  round: 1 | 2
  content: string
  // 这段发言参考了知识库的哪些字段
  kbRefs: KbField[]
}

export interface InputPayload {
  scene: string
  disasterType: DisasterType
  severity: Severity
  location: string
  timeHint: string
}

export interface ReportSections {
  title: string
  summary: string
  态势概述: string
  风险研判: string
  分级行动建议: string
  不确定性与盲点: string
}

export interface Metric {
  name: string
  value: number
}

export interface AnalysisResult {
  id: string
  createdAt: number
  input: InputPayload
  kbKey: string
  kbEntry: KbEntry
  riskLevel: RiskLevel
  riskScore: number
  // 本次研判里被实际引用的知识库字段
  kbRefs: KbField[]
  messages: AgentMessage[]
  report: ReportSections
  radar: Metric[]
  timeline: Metric[]
  resources: Metric[]
  confidence: number
}
