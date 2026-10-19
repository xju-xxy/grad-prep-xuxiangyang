import type { LayerName } from '../types'

export interface ConfigMeta {
  key: string
  short: string // 图例 / 卡片上的短名
  pipeline: string // 编排方式
  model: string
  color: string
  soft: string
}

// 全站固定配色：每个配置一套色，图表 / 图例 / 卡片保持一致
export const CONFIGS: Record<string, ConfigMeta> = {
  'multi@glm-4-flash': {
    key: 'multi@glm-4-flash',
    short: 'multi · flash',
    pipeline: 'multi',
    model: 'glm-4-flash',
    color: '#4F46E5',
    soft: '#EEF2FF',
  },
  'single@glm-4-flash': {
    key: 'single@glm-4-flash',
    short: 'single · flash',
    pipeline: 'single',
    model: 'glm-4-flash',
    color: '#0D9488',
    soft: '#ECFDF5',
  },
  'multi-noaudit@glm-4-flash': {
    key: 'multi-noaudit@glm-4-flash',
    short: 'noaudit · flash',
    pipeline: 'multi-noaudit',
    model: 'glm-4-flash',
    color: '#D97706',
    soft: '#FFF7ED',
  },
  'multi-verify@glm-4-flash': {
    key: 'multi-verify@glm-4-flash',
    short: 'verify · flash',
    pipeline: 'multi-verify',
    model: 'glm-4-flash',
    color: '#DB2777',
    soft: '#FDF2F8',
  },
  'multi@glm-4-plus': {
    key: 'multi@glm-4-plus',
    short: 'multi · plus',
    pipeline: 'multi',
    model: 'glm-4-plus',
    color: '#7C3AED',
    soft: '#F5F3FF',
  },
  'single@glm-4-plus': {
    key: 'single@glm-4-plus',
    short: 'single · plus',
    pipeline: 'single',
    model: 'glm-4-plus',
    color: '#0284C7',
    soft: '#F0F9FF',
  },
}

export const CONFIG_ORDER = [
  'multi@glm-4-flash',
  'single@glm-4-flash',
  'multi-noaudit@glm-4-flash',
  'multi-verify@glm-4-flash',
  'multi@glm-4-plus',
  'single@glm-4-plus',
]

export const LAYERS: LayerName[] = ['事实层', '推理层', '决策层']

export const CATEGORY_COLORS: Record<string, string> = {
  链式: '#4F46E5',
  单灾种: '#0D9488',
  信息矛盾: '#D97706',
}

export const meta = (key: string): ConfigMeta =>
  CONFIGS[key] ?? {
    key,
    short: key,
    pipeline: key,
    model: '',
    color: '#64748B',
    soft: '#F1F5F9',
  }
