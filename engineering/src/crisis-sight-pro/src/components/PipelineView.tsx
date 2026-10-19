// 推演流水线：八个发言节点按顺序点亮，已完成的自动折叠到上方

import { useState } from 'react'
import { GitBranch, FastForward, ChevronsDownUp, ChevronsUpDown } from 'lucide-react'
import type { AnalysisResult } from '../engine/types'
import { AgentCard } from './AgentCard'
import { GlassCard, Meter, RiskBadge, SectionTitle } from './ui'

export function PipelineView({
  result,
  activeIndex,
  onComplete,
  onSkip,
}: {
  result: AnalysisResult
  activeIndex: number
  onComplete: (index: number) => void
  onSkip: () => void
}) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const total = result.messages.length
  const finished = activeIndex >= total
  const progress = Math.round((Math.min(activeIndex, total) / total) * 100)

  function toggle(index: number) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  function toggleAll() {
    if (expanded.size > 0) setExpanded(new Set())
    else setExpanded(new Set(result.messages.map((_, i) => i)))
  }

  return (
    <GlassCard className="p-6 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <SectionTitle
          icon={<GitBranch className="h-4 w-4" />}
          title="多智能体推演流水线"
          desc="情报 → 研判 → 决策 → 审核，每轮发言都从灾害知识库里取素材。"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={toggleAll}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[12px] text-slate-300 transition-colors hover:border-white/25 hover:text-white"
          >
            {expanded.size > 0 ? (
              <ChevronsDownUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronsUpDown className="h-3.5 w-3.5" />
            )}
            {expanded.size > 0 ? '全部收起' : '全部展开'}
          </button>
          {!finished && (
            <button
              onClick={onSkip}
              className="inline-flex items-center gap-1.5 rounded-lg border border-cyanline-500/30 bg-cyanline-500/10 px-3 py-1.5 text-[12px] text-cyanline-400 transition-colors hover:bg-cyanline-500/20"
            >
              <FastForward className="h-3.5 w-3.5" />
              跳过动画
            </button>
          )}
        </div>
      </div>

      {/* 总体进度 */}
      <div className="mt-5 flex items-center gap-4">
        <div className="flex-1">
          <Meter value={progress} color="#22d3ee" />
        </div>
        <span className="tabnum shrink-0 text-[12px] text-slate-400">
          {Math.min(activeIndex, total)} / {total} 段
        </span>
        <RiskBadge level={result.riskLevel} score={result.riskScore} compact />
      </div>

      {/* 发言列表 */}
      <div className="mt-5 space-y-3">
        {result.messages.map((m, i) => {
          const state = i < activeIndex ? 'done' : i === activeIndex ? 'active' : 'pending'
          const showRoundHead = i === 0 || i === 4
          return (
            <div key={`${result.id}-${i}`}>
              {showRoundHead && (
                <div className="mb-3 mt-1 flex items-center gap-3">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    {i === 0 ? '第一轮 · 各自成文给出结论' : '第二轮 · 交叉补充与复核'}
                  </span>
                  <span className="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent" />
                </div>
              )}
              <AgentCard
                message={m}
                index={i}
                state={state}
                expanded={expanded.has(i)}
                onComplete={onComplete}
                onToggle={toggle}
              />
            </div>
          )
        })}
      </div>
    </GlassCard>
  )
}
