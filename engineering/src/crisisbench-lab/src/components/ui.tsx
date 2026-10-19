import type { ReactNode } from 'react'
import { motion } from 'framer-motion'

export function Card({
  children,
  className = '',
  hover = false,
}: {
  children: ReactNode
  className?: string
  hover?: boolean
}) {
  return (
    <div
      className={`rounded-2xl border border-slate-200/80 bg-white shadow-card ${
        hover ? 'transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-lift' : ''
      } ${className}`}
    >
      {children}
    </div>
  )
}

export function SectionTitle({
  title,
  desc,
  right,
}: {
  title: string
  desc?: string
  right?: ReactNode
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-ink-900">{title}</h2>
        {desc && <p className="mt-1 text-sm text-ink-500">{desc}</p>}
      </div>
      {right}
    </div>
  )
}

export function SourceNote({ children }: { children: ReactNode }) {
  return (
    <p className="mt-3 flex items-start gap-1.5 text-xs leading-relaxed text-ink-500">
      <span className="mt-[3px] inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-brand/60" />
      <span>{children}</span>
    </p>
  )
}

export function StatCard({
  label,
  value,
  unit,
  hint,
  tone = 'brand',
}: {
  label: string
  value: ReactNode
  unit?: string
  hint?: string
  tone?: 'brand' | 'teal' | 'amber' | 'pink' | 'slate'
}) {
  const tones: Record<string, string> = {
    brand: 'text-brand',
    teal: 'text-teal-600',
    amber: 'text-amber-600',
    pink: 'text-pink-600',
    slate: 'text-ink-700',
  }
  return (
    <Card hover className="p-5">
      <div className="text-[13px] font-medium text-ink-500">{label}</div>
      <div className={`num mt-2 flex items-baseline gap-1 font-semibold ${tones[tone]}`}>
        <span className="text-3xl tracking-tight">{value}</span>
        {unit && <span className="text-sm text-ink-500">{unit}</span>}
      </div>
      {hint && <div className="mt-2 text-xs text-ink-500">{hint}</div>}
    </Card>
  )
}

export function Chip({
  active,
  color,
  children,
  onClick,
}: {
  active?: boolean
  color?: string
  children: ReactNode
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      style={active && color ? { backgroundColor: color, borderColor: color } : undefined}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
        active
          ? 'border-transparent text-white'
          : 'border-slate-200 bg-white text-ink-700 hover:border-slate-300 hover:bg-slate-50'
      }`}
    >
      {color && !active && (
        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      )}
      {children}
    </button>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-200/70 ${className}`} />
}

export function PageWrap({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="mx-auto w-full max-w-6xl px-5 py-6 sm:px-8 sm:py-8"
    >
      {children}
    </motion.div>
  )
}
