// 推演记录存取。只存最近若干条，扔在 localStorage 里，不涉及任何后端。

import type { AnalysisResult, RiskLevel } from '../engine/types'

const STORAGE_KEY = 'crisis-sight-pro:history'
const MAX_RECORDS = 8

// 列表页不需要整份结果，只留个摘要 + 完整结果，点击回看时直接还原
export interface HistoryRecord {
  id: string
  createdAt: number
  disasterType: string
  severity: string
  riskLevel: RiskLevel
  sceneBrief: string
  result: AnalysisResult
}

export function loadHistory(): HistoryRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as HistoryRecord[]
    if (!Array.isArray(parsed)) return []
    return parsed
  } catch {
    return []
  }
}

export function saveRecord(result: AnalysisResult): HistoryRecord[] {
  const record: HistoryRecord = {
    id: result.id,
    createdAt: result.createdAt,
    disasterType: result.input.disasterType,
    severity: result.input.severity,
    riskLevel: result.riskLevel,
    sceneBrief:
      result.input.scene.length > 46
        ? `${result.input.scene.slice(0, 46)}…`
        : result.input.scene,
    result,
  }
  const list = [record, ...loadHistory().filter((r) => r.id !== record.id)].slice(
    0,
    MAX_RECORDS,
  )
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    // 超出配额就放弃写入，不影响主流程
  }
  return list
}

export function clearHistory(): HistoryRecord[] {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // 忽略
  }
  return []
}
