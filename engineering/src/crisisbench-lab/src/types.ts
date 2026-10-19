export type LayerName = '事实层' | '推理层' | '决策层'

/** 每层三项：[命中, 总数, 命中率] */
export interface MatrixCell {
  事实层: [number, number, number]
  推理层: [number, number, number]
  决策层: [number, number, number]
}

export interface ConfigNode {
  file: string
  rescore_plus: string | null
  rescore_flash: string | null
  matrix: Record<string, MatrixCell>
}

export interface TestEntry {
  对: string
  mcnemar: Record<string, number | string>
  wilcoxon: Record<string, number | string | null>
  bootstrap_ci_95: [number, number]
  mean_diff_pp: number
}

export interface ErrorEntry {
  counts: Record<string, number>
  total_loss: number
}

export interface VerifierEntry {
  calc_ok: number
  calc_total: number
  resource: number
  trap: number
  capacity: number
}

export interface AdjudicationRow {
  场景: string
  编号: string
  要点: string
  规则: number | string
  flash: number | string
  plus: number | string
  多数票: number | string
  裁定: number | string
  理由: string
  复核?: number | string
}

export interface Analysis {
  meta: { 时间: string }
  configs: Record<string, ConfigNode>
  tests: Record<string, TestEntry>
  kappa: Record<string, number>
  self_consistency: Record<string, number>
  errors: Record<string, ErrorEntry>
  verifier: Record<string, VerifierEntry>
  adjudication: AdjudicationRow[]
}

export interface CostBlock {
  场景数: number
  调用数: number
  prompt: number
  completion: number
  total: number
  耗时秒: number
}

export interface CostRow {
  配置: string
  被测模型: string
  主运行: CostBlock | null
  探针: CostBlock | null
  plus裁判: CostBlock | null
  A7自一致: CostBlock | null
  明细: [string, CostBlock][]
  协议合计: CostBlock
}

export interface CostSummary {
  rows: CostRow[]
}

export interface RubricItem {
  point: string
  from?: string
  mech?: string
  to?: string
}

export interface Scenario {
  id: string
  category: string
  disaster: string
  timePoint: string
  intel: string[]
  resources: string[]
  rubric: {
    事实层: RubricItem[]
    推理层: RubricItem[]
    决策层: RubricItem[]
  }
}

export interface ScenarioFile {
  meta: Record<string, string>
  scenarios: Scenario[]
}

export interface Dataset {
  analysis: Analysis
  cost: CostSummary
  scenarios: ScenarioFile
  adjudication: AdjudicationRow[]
}
