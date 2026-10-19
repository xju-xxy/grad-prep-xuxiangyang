// 单个 Agent 的发言卡片。三种状态：等待 / 正在发言（打字机）/ 已完成（折叠）

import { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Radar, BrainCircuit, Compass, ShieldCheck, BookMarked, ChevronDown } from 'lucide-react'
import type { AgentMessage, AgentName } from '../engine/types'
import { AGENT_META } from '../engine/agents'
import { useTypewriter } from '../hooks/useTypewriter'

const ICONS: Record<AgentName, typeof Radar> = {
  情报官: Radar,
  研判官: BrainCircuit,
  决策官: Compass,
  审核官: ShieldCheck,
}

export type CardState = 'pending' | 'active' | 'done'

export function AgentCard({
  message,
  index,
  state,
  expanded,
  onComplete,
  onToggle,
}: {
  message: AgentMessage
  index: number
  state: CardState
  expanded: boolean
  onComplete: (index: number) => void
  onToggle: (index: number) => void
}) {
  const meta = AGENT_META[message.agent]
  const Icon = ICONS[message.agent]
  const active = state === 'active'
  const { shown, done } = useTypewriter(message.content, active, 200)
  const fired = useRef(false)

  useEffect(() => {
    if (active && done && !fired.current) {
      fired.current = true
      onComplete(index)
    }
  }, [active, done, index, onComplete])

  const collapsed = state === 'done' && !expanded

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="relative overflow-hidden rounded-2xl border transition-colors"
      style={{
        borderColor: active ? meta.ring : 'rgba(120,160,220,0.12)',
        background: active
          ? `linear-gradient(120deg, ${meta.soft}, rgba(12,20,38,0.7))`
          : 'rgba(13,21,38,0.62)',
        boxShadow: active ? `0 0 0 1px ${meta.ring}, 0 20px 60px -34px ${meta.accent}` : undefined,
        opacity: state === 'pending' ? 0.55 : 1,
      }}
    >
      {/* 左侧彩色状态条 */}
      <span
        className="absolute inset-y-0 left-0 w-[3px]"
        style={{ background: meta.accent, opacity: state === 'pending' ? 0.3 : 1 }}
      />

      <button
        onClick={() => state === 'done' && onToggle(index)}
        className={`flex w-full items-center gap-3 px-5 py-3.5 text-left ${
          state === 'done' ? 'cursor-pointer' : 'cursor-default'
        }`}
      >
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
          style={{ background: meta.soft, color: meta.accent }}
        >
          <Icon className="h-4 w-4" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[13.5px] font-semibold text-slate-100">
              {message.agent}
            </span>
            <span
              className="rounded-md px-1.5 py-0.5 text-[10.5px]"
              style={{ background: meta.soft, color: meta.accent }}
            >
              {meta.tag}
            </span>
            <span className="tabnum text-[10.5px] text-slate-500">
              第 {message.round} 轮
            </span>
            {active && (
              <span className="flex items-center gap-1 text-[10.5px] text-cyanline-400">
                <span className="h-1.5 w-1.5 rounded-full bg-cyanline-500 animate-breathe" />
                正在发言
              </span>
            )}
            {state === 'pending' && (
              <span className="text-[10.5px] text-slate-500">等待中…</span>
            )}
          </div>

          {/* 折叠时露一行摘要 */}
          {collapsed && (
            <p className="mt-1 truncate text-[12.5px] text-slate-400">
              {message.content.replace(/^【[^】]*】/, '').replace(/\n/g, ' ').slice(0, 64)}…
            </p>
          )}
        </div>

        {state === 'done' && (
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-slate-500 transition-transform ${
              expanded ? 'rotate-180' : ''
            }`}
          />
        )}
      </button>

      <AnimatePresence initial={false}>
        {!collapsed && state !== 'pending' && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-4 pl-[62px]">
              <p
                className={`whitespace-pre-line text-[13.5px] leading-[1.85] text-slate-200 ${
                  active ? 'caret' : ''
                }`}
              >
                {active ? shown : message.content}
              </p>

              {message.kbRefs.length > 0 && (
                <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-white/5 pt-3">
                  <span className="inline-flex items-center gap-1 text-[10.5px] text-slate-500">
                    <BookMarked className="h-3 w-3" />
                    引用知识库
                  </span>
                  {message.kbRefs.map((r) => (
                    <span
                      key={r}
                      className="rounded-md border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-[10.5px] text-slate-400"
                    >
                      {r}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 等待态的呼吸提示 */}
      {state === 'pending' && (
        <div className="px-5 pb-4 pl-[62px]">
          <div className="flex gap-1.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-slate-600 animate-breathe"
                style={{ animationDelay: `${i * 0.18}s` }}
              />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
