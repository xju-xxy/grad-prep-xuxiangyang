// 几个到处要用的小组件，手写的，没引任何 UI 库

import type { ReactNode } from 'react'
import type { RiskLevel } from '../engine/types'

export function GlassCard({
  children,
  className = '',
  soft = false,
}: {
  children: ReactNode
  className?: string
  soft?: boolean
}) {
  return (
    <div
      className={`${soft ? 'glass-soft' : 'glass'} rounded-2xl shadow-panel ${className}`}
    >
      {children}
    </div>
  )
}

// 带左侧色条的小标题
export function SectionTitle({
  icon,
  title,
  desc,
  accent = '#22d3ee',
}: {
  icon: ReactNode
  title: string
  desc?: string
  accent?: string
}) {
  return (
    <div className="flex items-start gap-3">
      <span
        className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
        style={{ background: `${accent}22`, color: accent }}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span
            className="h-4 w-[3px] rounded-full"
            style={{ background: accent }}
          />
          <h2 className="text-[15px] font-semibold tracking-wide text-slate-100">
            {title}
          </h2>
        </div>
        {desc && <p className="mt-1 text-xs leading-relaxed text-slate-400">{desc}</p>}
      </div>
    </div>
  )
}

const RISK_STYLE: Record<RiskLevel, { color: string; bg: string; label: string }> = {
  高: { color: '#fca5a5', bg: 'rgba(239,68,68,0.16)', label: '高风险' },
  中: { color: '#fcd34d', bg: 'rgba(251,191,36,0.16)', label: '中风险' },
  低: { color: '#6ee7b7', bg: 'rgba(52,211,153,0.16)', label: '低风险' },
}

export function RiskBadge({
  level,
  score,
  compact = false,
}: {
  level: RiskLevel
  score?: number
  compact?: boolean
}) {
  const s = RISK_STYLE[level]
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full font-semibold tabnum ${
        compact ? 'px-3 py-1 text-xs' : 'px-4 py-1.5 text-sm'
      }`}
      style={{ background: s.bg, color: s.color, border: `1px solid ${s.color}55` }}
    >
      <span
        className="h-2 w-2 rounded-full animate-breathe"
        style={{ background: s.color, boxShadow: `0 0 10px ${s.color}` }}
      />
      {s.label}
      {score !== undefined && <span className="opacity-80">· {score}</span>}
    </span>
  )
}

// 带呼吸点的状态标签
export function Pill({
  children,
  color = '#22d3ee',
}: {
  children: ReactNode
  color?: string
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium"
      style={{ background: `${color}1f`, color, border: `1px solid ${color}3d` }}
    >
      {children}
    </span>
  )
}

// 细进度条
export function Meter({
  value,
  color = '#22d3ee',
  height = 6,
}: {
  value: number
  color?: string
  height?: number
}) {
  return (
    <div
      className="w-full overflow-hidden rounded-full bg-white/[0.06]"
      style={{ height }}
    >
      <div
        className="h-full rounded-full transition-all duration-700 ease-out"
        style={{
          width: `${Math.max(0, Math.min(100, value))}%`,
          background: `linear-gradient(90deg, ${color}66, ${color})`,
          boxShadow: `0 0 12px ${color}80`,
        }}
      />
    </div>
  )
}
