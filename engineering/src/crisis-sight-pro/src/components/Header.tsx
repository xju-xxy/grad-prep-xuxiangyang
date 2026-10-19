// 顶栏：品牌名 + 一句话定位 + 右侧几个小指标

import { Activity, Cpu, ShieldCheck } from 'lucide-react'
import { Pill } from './ui'

export function Header({
  kbCount,
  historyCount,
}: {
  kbCount: number
  historyCount: number
}) {
  return (
    <header className="relative mx-auto flex max-w-7xl flex-col gap-5 px-5 pb-4 pt-9 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-4">
        <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl border border-cyanline-500/30 bg-cyanline-500/10">
          <Activity className="h-6 w-6 text-cyanline-500" />
          <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-cyanline-500 animate-breathe" />
        </div>
        <div>
          <h1 className="text-sheen text-2xl font-bold tracking-tight sm:text-[26px]">
            CrisisSight Pro
          </h1>
          <p className="mt-0.5 text-[13px] text-slate-400">
            知识增强的多智能体灾害态势推理与辅助决策系统
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Pill color="#22d3ee">
          <Cpu className="h-3 w-3" />
          本地推演引擎 · 免 Key
        </Pill>
        <Pill color="#818cf8">
          <ShieldCheck className="h-3 w-3" />
          4 智能体 × 2 轮
        </Pill>
        <Pill color="#fbbf24">
          知识库 {kbCount} 类 · 记录 {historyCount} 条
        </Pill>
      </div>
    </header>
  )
}
