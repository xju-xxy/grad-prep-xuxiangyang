// 主应用：输入台 → 推演流水线 → 结果面板，三段式流程切换

import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { History, RotateCcw, MapPin, Clock3, Layers, BookOpenCheck, Workflow, Gauge } from 'lucide-react'
import { analyze } from './engine/agents'
import { DISASTER_TYPES } from './engine/knowledgeBase'
import type { AnalysisResult, InputPayload } from './engine/types'
import {
  clearHistory,
  loadHistory,
  saveRecord,
  type HistoryRecord,
} from './lib/history'
import { Backdrop } from './components/Backdrop'
import { Header } from './components/Header'
import { InputConsole } from './components/InputConsole'
import { PipelineView } from './components/PipelineView'
import { ResultPanel } from './components/ResultPanel'
import { ChartsPanel } from './components/Charts'
import { HistoryPanel } from './components/HistoryPanel'
import { GlassCard } from './components/ui'

type Phase = 'idle' | 'running' | 'done'

const FEATURES = [
  { icon: Workflow, title: '四智能体两轮编排', desc: '情报、研判、决策、审核各司其职，第二轮做交叉复核。', accent: '#22d3ee' },
  { icon: BookOpenCheck, title: '灾害知识库增强', desc: '10 类灾害的特征、危害、应对、次生灾害、监测项，逐条注入发言。', accent: '#818cf8' },
  { icon: Gauge, title: '可视化态势感知', desc: '风险维度、处置优先级、资源占比，都从推演结果现算。', accent: '#34d399' },
]

export default function App() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [historyOpen, setHistoryOpen] = useState(false)
  const pipelineRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setHistory(loadHistory())
  }, [])

  // 八段全出完就切到结果态并落一条记录
  useEffect(() => {
    if (phase === 'running' && result && activeIndex >= result.messages.length) {
      setPhase('done')
      setHistory(saveRecord(result))
    }
  }, [phase, activeIndex, result])

  const handleComplete = useCallback((index: number) => {
    setActiveIndex((prev) => Math.max(prev, index + 1))
  }, [])

  function handleStart(input: InputPayload) {
    const res = analyze(input)
    setResult(res)
    setActiveIndex(0)
    setPhase('running')
    window.setTimeout(
      () => pipelineRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      60,
    )
  }

  function handleSkip() {
    if (!result) return
    setActiveIndex(result.messages.length)
    setPhase('done')
    setHistory(saveRecord(result))
  }

  function handlePickHistory(record: HistoryRecord) {
    setResult(record.result)
    setActiveIndex(record.result.messages.length)
    setPhase('done')
    setHistoryOpen(false)
    window.setTimeout(
      () => pipelineRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      60,
    )
  }

  const showFlow = phase !== 'idle' && result

  return (
    <div className="relative min-h-screen">
      <Backdrop />
      <Header kbCount={DISASTER_TYPES.length} historyCount={history.length} />

      <main className="mx-auto max-w-7xl px-5 pb-24 pt-2">
        {!showFlow && (
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            <InputConsole onStart={handleStart} onPickHistory={() => setHistoryOpen(true)} />

            <div className="grid gap-4 sm:grid-cols-3">
              {FEATURES.map((f, i) => (
                <motion.div
                  key={f.title}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.45, delay: 0.1 + i * 0.08 }}
                >
                  <GlassCard className="lift h-full p-5">
                    <span
                      className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
                      style={{ background: `${f.accent}1f`, color: f.accent }}
                    >
                      <f.icon className="h-5 w-5" />
                    </span>
                    <h3 className="text-[14px] font-semibold text-slate-100">{f.title}</h3>
                    <p className="mt-1.5 text-[12.5px] leading-relaxed text-slate-400">{f.desc}</p>
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {showFlow && (
          <div className="space-y-6">
            {/* 本次推演摘要条 */}
            <GlassCard soft className="flex flex-wrap items-center gap-x-5 gap-y-3 px-5 py-4">
              <span className="text-[13px] font-semibold text-slate-100">
                {result.input.disasterType}
                <span className="ml-2 text-[12px] font-normal text-slate-500">
                  {result.input.severity}
                </span>
              </span>
              {result.input.location && (
                <span className="inline-flex items-center gap-1.5 text-[12px] text-slate-400">
                  <MapPin className="h-3.5 w-3.5" />
                  {result.input.location}
                </span>
              )}
              {result.input.timeHint && (
                <span className="inline-flex items-center gap-1.5 text-[12px] text-slate-400">
                  <Clock3 className="h-3.5 w-3.5" />
                  {result.input.timeHint}
                </span>
              )}
              <span className="hidden max-w-[38ch] truncate text-[12px] text-slate-500 lg:inline">
                {result.input.scene}
              </span>

              <div className="ml-auto flex items-center gap-2">
                <button
                  onClick={() => setHistoryOpen(true)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[12px] text-slate-300 transition-colors hover:border-white/25 hover:text-white"
                >
                  <History className="h-3.5 w-3.5" />
                  推演记录
                </button>
                <button
                  onClick={() => {
                    setPhase('idle')
                    setResult(null)
                    setActiveIndex(0)
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-cyanline-500/30 bg-cyanline-500/10 px-3 py-1.5 text-[12px] text-cyanline-400 transition-colors hover:bg-cyanline-500/20"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  重新输入
                </button>
              </div>
            </GlassCard>

            <div ref={pipelineRef} className="scroll-mt-6">
              <PipelineView
                result={result}
                activeIndex={activeIndex}
                onComplete={handleComplete}
                onSkip={handleSkip}
              />
            </div>

            {phase === 'done' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="space-y-6 pt-2"
              >
                <div className="flex items-center gap-3">
                  <Layers className="h-4 w-4 text-cyanline-500" />
                  <span className="text-[13px] font-semibold uppercase tracking-wider text-slate-400">
                    推演结果
                  </span>
                  <span className="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent" />
                </div>
                <ResultPanel result={result} />
                <ChartsPanel result={result} />
              </motion.div>
            )}
          </div>
        )}
      </main>

      <footer className="mx-auto max-w-7xl px-5 pb-10 text-center text-[11.5px] text-slate-600">
        CrisisSight Pro · 纯前端实现，推演在浏览器本地完成，不联网、不需要 API Key
      </footer>

      <HistoryPanel
        open={historyOpen}
        records={history}
        onPick={handlePickHistory}
        onClear={() => setHistory(clearHistory())}
        onClose={() => setHistoryOpen(false)}
      />
    </div>
  )
}
