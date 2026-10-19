import type {
  AdjudicationRow,
  Analysis,
  Dataset,
  LayerName,
  Scenario,
} from '../types'
import { CONFIG_ORDER, LAYERS } from './theme'

const base = import.meta.env.BASE_URL || '/'

async function getJson<T>(name: string): Promise<T> {
  const res = await fetch(`${base}data/${name}`)
  if (!res.ok) throw new Error(`读取 ${name} 失败（HTTP ${res.status}）`)
  return (await res.json()) as T
}

export async function loadDataset(): Promise<Dataset> {
  const [analysis, cost, scenarios, adjudication] = await Promise.all([
    getJson<Analysis>('analysis.json'),
    getJson<Dataset['cost']>('cost-summary.json'),
    getJson<Dataset['scenarios']>('scenarios.json'),
    getJson<AdjudicationRow[]>('adjudication.json'),
  ])
  return { analysis, cost, scenarios, adjudication }
}

/* ---------- 由 matrix 现算的派生指标（全部来自源文件，不额外造数） ---------- */

export interface LayerScore {
  hit: number
  total: number
  score: number // 百分比 0-100
}

export interface ConfigScore {
  layers: Record<LayerName, LayerScore>
  overall: LayerScore
}

export function configScore(analysis: Analysis, key: string): ConfigScore {
  const node = analysis.configs[key]
  const layers = {} as Record<LayerName, LayerScore>
  let oh = 0
  let ot = 0
  for (const layer of LAYERS) {
    let hit = 0
    let total = 0
    for (const cell of Object.values(node.matrix)) {
      const trio = cell[layer]
      hit += trio[0]
      total += trio[1]
    }
    layers[layer] = { hit, total, score: total ? (hit / total) * 100 : 0 }
    oh += hit
    ot += total
  }
  return { layers, overall: { hit: oh, total: ot, score: ot ? (oh / ot) * 100 : 0 } }
}

export function sceneScore(analysis: Analysis, key: string, sid: string): LayerScore {
  const cell = analysis.configs[key]?.matrix?.[sid]
  if (!cell) return { hit: 0, total: 0, score: 0 }
  let hit = 0
  let total = 0
  for (const layer of LAYERS) {
    hit += cell[layer][0]
    total += cell[layer][1]
  }
  return { hit, total, score: total ? (hit / total) * 100 : 0 }
}

/** 某配置在某一类场景（链式/单灾种/信息矛盾）上的加权得分 */
export function categoryScore(
  analysis: Analysis,
  key: string,
  scenarios: Scenario[],
  category: string,
): LayerScore {
  let hit = 0
  let total = 0
  for (const s of scenarios) {
    if (s.category !== category) continue
    const cell = analysis.configs[key]?.matrix?.[s.id]
    if (!cell) continue
    for (const layer of LAYERS) {
      hit += cell[layer][0]
      total += cell[layer][1]
    }
  }
  return { hit, total, score: total ? (hit / total) * 100 : 0 }
}

export const sortedConfigs = (analysis: Analysis) =>
  [...CONFIG_ORDER].filter((k) => analysis.configs[k])

/* ---------- 裁判可靠性 ---------- */

export interface JudgeAgreement {
  rater: string
  agree: number
  total: number
  rate: number // 百分比
}

const num = (v: number | string | null | undefined): number | null => {
  if (v === '' || v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

/** 各裁判与人工终裁（裁定列）的一致率 */
export function judgeAgreement(rows: AdjudicationRow[]): JudgeAgreement[] {
  const raters: ['规则' | 'flash' | 'plus' | '多数票', string][] = [
    ['规则', '规则打分'],
    ['flash', 'glm-4-flash 裁判'],
    ['plus', 'glm-4-plus 裁判'],
    ['多数票', '三裁判多数票'],
  ]
  return raters.map(([field, label]) => {
    let agree = 0
    let total = 0
    for (const r of rows) {
      const a = num(r[field])
      const b = num(r['裁定'])
      if (a === null || b === null) continue
      total += 1
      if (a === b) agree += 1
    }
    return { rater: label, agree, total, rate: total ? (agree / total) * 100 : 0 }
  })
}

export interface AdjudicationStat {
  total: number
  disputed: number // 多数票与人工终裁不一致（被改判）
  reviewed: number // 标注人复核确认过的条目
}

export function adjudicationStat(rows: AdjudicationRow[]): AdjudicationStat {
  let disputed = 0
  let reviewed = 0
  for (const r of rows) {
    const mv = num(r['多数票'])
    const fin = num(r['裁定'])
    if (mv !== null && fin !== null && mv !== fin) disputed += 1
    const rv = num(r['复核'])
    if (rv === 1) reviewed += 1
  }
  return { total: rows.length, disputed, reviewed }
}

/* ---------- 场景 ---------- */

export const countRubricPoints = (s: Scenario) =>
  s.rubric.事实层.length + s.rubric.推理层.length + s.rubric.决策层.length

export const uniqueSorted = (arr: string[]) => [...new Set(arr)].sort((a, b) => a.localeCompare(b, 'zh'))
